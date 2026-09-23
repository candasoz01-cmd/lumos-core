import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";
import { beforeEach, afterEach, test } from "node:test";
import {
  authSecret, makeState, verifyState, sealSession, openSession,
  sessionCookieHeader, lumosIdForProviderIdentity,
} from "../api/_lib/lumos_session.js";
import readiness from "../api/auth/readiness.js";
import session from "../api/auth/session.js";
import chat from "../api/bridge/chat.js";
import logout from "../api/auth/logout.js";

const keys = [
  "NODE_ENV", "VERCEL_ENV", "LUMOS_AUTH_STATE_SECRET", "LUMOS_ID_SECRET",
  "LUMOS_GOOGLE_WEB_CLIENT_ID", "LUMOS_GOOGLE_WEB_CLIENT_SECRET",
  "OPENAI_API_KEY", "LUMOS_GOOGLE_GEMINI_API_KEY", "SENTRY_DSN",
];
let previous;
let originalFetch;
let networkCalls;
beforeEach(() => {
  previous = Object.fromEntries(keys.map((key) => [key, process.env[key]]));
  keys.forEach((key) => delete process.env[key]);
  process.env.VERCEL_ENV = "production";
  process.env.LUMOS_AUTH_STATE_SECRET = randomBytes(32).toString("hex");
  process.env.LUMOS_ID_SECRET = randomBytes(32).toString("hex");
  originalFetch = globalThis.fetch;
  networkCalls = 0;
  globalThis.fetch = async () => { networkCalls++; throw new Error("network_not_allowed_in_test"); };
});
afterEach(() => {
  for (const key of keys) {
    if (previous[key] === undefined) delete process.env[key];
    else process.env[key] = previous[key];
  }
  globalThis.fetch = originalFetch;
  assert.equal(networkCalls, 0);
});
function response() {
  return {
    headers: {}, statusCode: 0,
    setHeader(key, value) { this.headers[key.toLowerCase()] = value; },
    status(code) { this.statusCode = code; return this; },
    json(body) { this.body = JSON.stringify(body); return this; },
    end(body) { this.body = body; return this; },
  };
}
function claims() {
  return { sid: "local-test-session", provider: "google_web", sub: "local-test-user",
    exp: Math.floor(Date.now() / 1000) + 600 };
}

test("hosted state and session reject missing, blank or short dedicated keys despite OAuth secret", () => {
  process.env.LUMOS_GOOGLE_WEB_CLIENT_SECRET = randomBytes(32).toString("hex");
  for (const environment of ["production", "preview"]) {
    process.env.VERCEL_ENV = environment;
    for (const invalid of [undefined, "", " ".repeat(64), "a".repeat(31)]) {
      if (invalid === undefined) delete process.env.LUMOS_AUTH_STATE_SECRET;
      else process.env.LUMOS_AUTH_STATE_SECRET = invalid;
      assert.throws(() => authSecret(), /^Error: lumos_auth_secret_unconfigured$/);
      assert.throws(() => makeState(), /lumos_auth_secret_unconfigured/);
      assert.throws(() => sealSession(claims()), /lumos_auth_secret_unconfigured/);
    }
  }
  delete process.env.VERCEL_ENV;
  process.env.NODE_ENV = "production";
  assert.throws(() => authSecret(), /lumos_auth_secret_unconfigured/);
});

test("valid dedicated key preserves state verification and rejects tampering and rotation", () => {
  const state = makeState();
  assert.equal(verifyState(state), true);
  assert.equal(verifyState(`${state}x`), false);
  const value = claims();
  const sealed = sealSession(value);
  assert.deepEqual(openSession(sealed), value);
  const changed = Buffer.from(sealed, "base64url");
  changed[15] ^= 1;
  assert.equal(openSession(changed.toString("base64url")), null);
  process.env.LUMOS_AUTH_STATE_SECRET = randomBytes(32).toString("hex");
  assert.equal(openSession(sealed), null);
  assert.equal(verifyState(state), false);
});

test("session rejects missing, malformed, zero and expired expiry including exact boundary", () => {
  const now = Math.floor(Date.now() / 1000);
  for (const exp of [undefined, null, 0, -1, "tomorrow", String(now + 600), now, now - 1, now + 0.5, 1e100]) {
    assert.equal(openSession(sealSession({ ...claims(), exp })), null);
  }
  for (const value of [null, [], "claims"]) assert.equal(openSession(sealSession(value)), null);
});

test("invalid sealed sessions cannot read panel identity or reach chat provider", async () => {
  for (const exp of [undefined, "invalid", 0, Math.floor(Date.now() / 1000)]) {
    const cookie = `lumos_session=${sealSession({ ...claims(), exp })}`;
    const res = response();
    await session({ method: "GET", headers: { cookie } }, res);
    assert.equal(res.statusCode, 401);
    const chatRes = response();
    await chat({ method: "POST", headers: { cookie }, body: { message: "Merhaba" } }, chatRes);
    assert.equal(chatRes.statusCode, 401);
  }
});

test("session exposes identity only, cookie flags hold, logout clears cookies", async () => {
  const sealed = sealSession(claims());
  assert.match(sessionCookieHeader(sealed), /; Path=\/; HttpOnly; Secure; SameSite=Lax; Max-Age=604800$/);
  const res = response();
  await session({ method: "GET", headers: { cookie: `lumos_session=${sealed}` } }, res);
  assert.equal(res.statusCode, 200);
  assert.equal(res.headers["cache-control"], "no-store");
  assert.equal(res.body.includes(sealed), false);
  assert.equal(res.body.includes(process.env.LUMOS_AUTH_STATE_SECRET), false);
  const id = lumosIdForProviderIdentity("google_web", "local-test-user");
  process.env.LUMOS_AUTH_STATE_SECRET = randomBytes(32).toString("hex");
  assert.equal(lumosIdForProviderIdentity("google_web", "local-test-user"), id);
  const logoutRes = response();
  await logout({ method: "POST" }, logoutRes);
  assert.equal(logoutRes.statusCode, 200);
  for (const header of logoutRes.headers["set-cookie"]) assert.match(header, /Max-Age=0$/);
});

test("readiness separates configured keys from login and returns no secret values", async () => {
  process.env.LUMOS_GOOGLE_WEB_CLIENT_ID = "local-test-client";
  process.env.LUMOS_GOOGLE_WEB_CLIENT_SECRET = randomBytes(32).toString("hex");
  async function read() {
    const res = response();
    await readiness({ method: "GET" }, res);
    assert.equal(res.statusCode, 200);
    assert.equal(res.headers["cache-control"], "no-store");
    for (const key of ["LUMOS_AUTH_STATE_SECRET", "LUMOS_ID_SECRET", "LUMOS_GOOGLE_WEB_CLIENT_SECRET", "OPENAI_API_KEY", "LUMOS_GOOGLE_GEMINI_API_KEY"]) {
      if (process.env[key]) assert.equal(res.body.includes(process.env[key]), false);
    }
    return JSON.parse(res.body);
  }
  assert.equal((await read()).panel_configured, false);
  process.env.OPENAI_API_KEY = randomBytes(32).toString("hex");
  assert.equal((await read()).panel_configured, true);
  delete process.env.OPENAI_API_KEY;
  process.env.LUMOS_GOOGLE_GEMINI_API_KEY = randomBytes(32).toString("hex");
  assert.equal((await read()).panel_configured, true);
  delete process.env.LUMOS_ID_SECRET;
  const missingIdentity = await read();
  assert.equal(missingIdentity.live_login, true);
  assert.equal(missingIdentity.stable_identity, false);
  assert.equal(missingIdentity.panel_configured, false);
  process.env.LUMOS_ID_SECRET = "short";
  assert.equal((await read()).stable_identity, false);
  process.env.LUMOS_AUTH_STATE_SECRET = "short";
  assert.equal((await read()).live_login, false);
});
