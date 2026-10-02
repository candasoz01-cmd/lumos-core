/**
 * #904 Security Reviewer bulguları:
 * 1) /api/integrations/meta/* ve /api/auth/meta/* çıkıştan sonra kopyalanmış çerezi
 *    reddetmeli (ortak oturum sürümü doğrulaması).
 * 2) Küresel iptal (epoch artışı) GET ile veya çapraz siteden tetiklenememeli.
 */
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import logoutHandler from "../api/auth/logout.js";
import metaCallback from "../api/auth/meta/callback.js";
import metaStart from "../api/auth/meta/start.js";
import metaConnections from "../api/integrations/meta/connections.js";
import instagramConnections from "../api/integrations/meta/instagram/connections.js";
import pagesConnections from "../api/integrations/meta/pages/connections.js";
import metaSync from "../api/integrations/meta/sync.js";
import metaToken from "../api/integrations/meta/token.js";
import whatsappConnections from "../api/integrations/meta/whatsapp/connections.js";
import { hostedSessionClaims } from "../api/_lib/hosted_lumos.js";
import { openLiveSession, sealSession } from "../api/_lib/lumos_session.js";
import { currentEpoch } from "../api/_lib/session_epoch.js";

const epochDir = mkdtempSync(path.join(tmpdir(), "lumos-meta-epoch-"));
process.env.LUMOS_SESSION_EPOCH_PATH = path.join(epochDir, "epoch.json");
process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";

let counter = 0;
function login() {
  counter += 1;
  const lumosId = `lumos_meta_epoch_${counter}`;
  const sealed = sealSession({
    sid: `sid-${lumosId}`,
    lumos_id: lumosId,
    sub: `google-${lumosId}`,
    provider: "google_web",
    name: "Ada",
    email: "ada@example.test",
    package: "base",
    sv: currentEpoch(lumosId),
    exp: Math.floor(Date.now() / 1000) + 3600,
  });
  return { lumosId, sealed };
}

function makeRes() {
  return {
    statusCode: 0,
    headers: {},
    body: "",
    setHeader(name, value) {
      this.headers[name.toLowerCase()] = value;
    },
    end(payload) {
      this.body = payload ?? "";
      return this;
    },
  };
}

const cookie = (sealed, extra = {}) => ({
  method: "GET",
  url: "/",
  headers: { cookie: `lumos_session=${sealed}`, host: "welockai.com" },
  ...extra,
});

async function call(handler, req) {
  const res = makeRes();
  await handler(req, res);
  return res;
}

async function logout(req) {
  return call(logoutHandler, req);
}

const jsonSurfaces = [
  ["integrations/meta/connections", metaConnections],
  ["integrations/meta/instagram/connections", instagramConnections],
  ["integrations/meta/pages/connections", pagesConnections],
  ["integrations/meta/whatsapp/connections", whatsappConnections],
  ["integrations/meta/token", metaToken],
  ["integrations/meta/sync", metaSync, "POST"],
];

test("openLiveSession rejects a copied cookie after logout and accepts a fresh login", async () => {
  const { lumosId, sealed } = login();
  assert.ok(openLiveSession(cookie(sealed)));
  const out = await logout(cookie(sealed, { method: "POST" }));
  assert.equal(out.statusCode, 200);
  assert.equal(openLiveSession(cookie(sealed)), null);
  assert.equal(hostedSessionClaims(cookie(sealed)), null);
  const fresh = sealSession({
    sid: "sid-fresh", lumos_id: lumosId, sub: `google-${lumosId}`, provider: "google_web",
    sv: currentEpoch(lumosId), exp: Math.floor(Date.now() / 1000) + 3600,
  });
  assert.ok(openLiveSession(cookie(fresh)));
});

for (const [name, handler, method = "GET"] of jsonSurfaces) {
  test(`${name}: copied cookie is rejected after logout, valid cookie is not 401`, async () => {
    const { sealed } = login();
    const before = await call(handler, cookie(sealed, { method, body: {} }));
    assert.notEqual(before.statusCode, 401, "valid session must pass the session gate");
    await logout(cookie(sealed, { method: "POST" }));
    const after = await call(handler, cookie(sealed, { method, body: {} }));
    assert.equal(after.statusCode, 401);
    // Bearer bu yüzeylerde hiç kabul edilmez (yalnız çerez).
    const bearer = await call(handler, {
      method, body: {}, url: "/", headers: { authorization: `Bearer ${login().sealed}`, host: "welockai.com" },
    });
    assert.equal(bearer.statusCode, 401);
  });
}

test("auth/meta/start redirects a copied cookie to lumos_session_required after logout", async () => {
  const { sealed } = login();
  const req = cookie(sealed, { url: "/api/auth/meta/start?provider=instagram" });
  const before = await call(metaStart, req);
  assert.doesNotMatch(String(before.headers.location || ""), /lumos_session_required/);
  await logout(cookie(sealed, { method: "POST" }));
  const after = await call(metaStart, req);
  assert.equal(after.statusCode, 302);
  assert.match(String(after.headers.location), /lumos_session_required/);
});

test("auth/meta/callback treats a copied cookie as invalid_state after logout", async () => {
  const { sealed } = login();
  await logout(cookie(sealed, { method: "POST" }));
  const res = await call(metaCallback, cookie(sealed, { url: "/api/auth/meta/callback?code=x&state=y" }));
  assert.equal(res.statusCode, 302);
  assert.match(String(res.headers.location), /invalid_state/);
});

test("GET logout clears cookies but does not bump the global epoch (CSRF-safe)", async () => {
  const { lumosId, sealed } = login();
  const before = currentEpoch(lumosId);
  const res = await logout(cookie(sealed, { method: "GET" }));
  assert.equal(res.statusCode, 302);
  assert.match(String(res.headers.location), /logged_out=1/);
  assert.ok(res.headers["set-cookie"].every((c) => /Max-Age=0/.test(c)));
  assert.equal(currentEpoch(lumosId), before);
  assert.ok(openLiveSession(cookie(sealed)), "copied token stays valid until an explicit POST logout");
});

test("cross-site POST logout is blocked: no epoch bump, no cookie clearing", async () => {
  const { lumosId, sealed } = login();
  const before = currentEpoch(lumosId);
  for (const headers of [
    { origin: "https://evil.example" },
    { origin: "null" },
    { "sec-fetch-site": "cross-site" },
    { "sec-fetch-site": "same-site" },
  ]) {
    const res = await logout({
      method: "POST", url: "/api/auth/logout",
      headers: { cookie: `lumos_session=${sealed}`, host: "welockai.com", ...headers },
    });
    assert.equal(res.statusCode, 403, JSON.stringify(headers));
    assert.equal(res.headers["set-cookie"], undefined);
    assert.equal(currentEpoch(lumosId), before);
  }
  assert.ok(openLiveSession(cookie(sealed)));
});

test("same-origin, no-Origin and Bearer POST logout still revoke globally", async () => {
  const sameOrigin = login();
  const a = await logout({
    method: "POST", url: "/api/auth/logout",
    headers: { cookie: `lumos_session=${sameOrigin.sealed}`, host: "welockai.com",
      origin: "https://welockai.com", "sec-fetch-site": "same-origin" },
  });
  assert.equal(a.statusCode, 200);
  assert.equal(openLiveSession(cookie(sameOrigin.sealed)), null);

  const bare = login();
  const b = await logout({ method: "POST", headers: { cookie: `lumos_session=${bare.sealed}` } });
  assert.equal(b.statusCode, 200);
  assert.equal(openLiveSession(cookie(bare.sealed)), null);

  const mobile = login();
  const c = await logout({ method: "POST", headers: { authorization: `Bearer ${mobile.sealed}` } });
  assert.equal(c.statusCode, 200);
  assert.equal(hostedSessionClaims({ headers: { authorization: `Bearer ${mobile.sealed}` } }), null);
});
