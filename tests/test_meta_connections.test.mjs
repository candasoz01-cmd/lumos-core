/** ADR-021 S2 — bağlantı listesi API testleri (çoklu yol + AÇIK etiketli fallback). */
import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import handler from "../api/integrations/meta/connections.js";
import { sealSession } from "../api/_lib/lumos_session.js";

const realFetch = globalThis.fetch;

beforeEach(() => {
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-auth-state-secret-32-characters";
  process.env.LUMOS_CREDENTIAL_VAULT_WRITE_URL = "https://vault.test/credentials";
  process.env.LUMOS_CREDENTIAL_VAULT_WRITE_TOKEN = "vault-token";
});

afterEach(() => {
  globalThis.fetch = realFetch;
  for (const key of [
    "LUMOS_AUTH_STATE_SECRET",
    "LUMOS_CREDENTIAL_VAULT_WRITE_URL",
    "LUMOS_CREDENTIAL_VAULT_WRITE_TOKEN",
  ]) delete process.env[key];
});

function session() {
  return sealSession({ sid: "session", lumos_id: "lumos_user", exp: Math.floor(Date.now() / 1000) + 600 });
}

function request(headers = {}) {
  return { method: "GET", headers: { cookie: `lumos_session=${session()}`, ...headers } };
}

function response() {
  return {
    statusCode: 0,
    headers: {},
    setHeader(name, value) { this.headers[name.toLowerCase()] = value; },
    end(body) { this.body = body; },
  };
}

function vaultStub(byOperation) {
  globalThis.fetch = async (url, options) => {
    const body = JSON.parse(options.body);
    const result = byOperation[body.operation];
    if (!result) return { ok: true, json: async () => ({ ok: false }) };
    return { ok: true, json: async () => result(body) };
  };
}

test("multi mode: credential.list rows become connection rows, no secrets", async () => {
  const future = Math.floor(Date.now() / 1000) + 9999;
  vaultStub({
    "credential.list": () => ({
      ok: true,
      credentials: [
        { vault_ref: "vr-1", provider: "facebook", provider_account_id: "fb-1",
          expires_at: future, auth_mode: "facebook_login",
          credential: { access_token: "LEAK" } },
        { vault_ref: "vr-2", provider: "whatsapp", provider_account_id: "wa-1",
          expires_at: 1, auth_mode: "facebook_login" },
      ],
    }),
  });
  const res = response();
  await handler(request(), res);
  const payload = JSON.parse(res.body);
  assert.equal(res.statusCode, 200);
  assert.equal(payload.mode, "multi");
  assert.equal(payload.connections.length, 2);
  assert.deepEqual(payload.connections[0], {
    connection_id: "conn_facebook_fb-1",
    provider: "facebook",
    provider_account_id: "fb-1",
    status: "authorized",
    expires_at: future,
    auth_mode: "facebook_login",
  });
  assert.equal(payload.connections[1].status, "expired"); // süresi geçmiş
  assert.equal(res.body.includes("LEAK"), false);
  assert.equal(res.body.includes("vault_ref"), false);
});

test("fallback mode is EXPLICIT: list unsupported -> singular metadata + mode flag", async () => {
  const future = Math.floor(Date.now() / 1000) + 9999;
  vaultStub({
    "credential.list": () => ({ ok: false, error: "unknown_operation" }),
    "credential.metadata": (body) => body.provider === "facebook"
      ? { ok: true, configured: true, vault_ref: "vr-fb", expires_at: future }
      : { ok: true, configured: false, vault_ref: "" },
  });
  const res = response();
  await handler(request(), res);
  const payload = JSON.parse(res.body);
  assert.equal(res.statusCode, 200);
  assert.equal(payload.mode, "single_credential_fallback"); // degraded görünür
  assert.ok(payload.note.includes("credential.list"));
  assert.equal(payload.connections.length, 1);
  assert.equal(payload.connections[0].provider, "facebook");
  assert.equal(payload.connections[0].provider_account_id, "current");
  assert.equal(payload.connections[0].status, "authorized");
});

test("both paths failing -> 503, never a fake empty multi list", async () => {
  globalThis.fetch = async () => ({ ok: false, json: async () => ({}) });
  const res = response();
  await handler(request(), res);
  assert.equal(res.statusCode, 503);
  assert.equal(JSON.parse(res.body).ok, false);
});

test("auth and method gates", async () => {
  const res401 = response();
  await handler({ method: "GET", headers: {} }, res401);
  assert.equal(res401.statusCode, 401);

  const res405 = response();
  await handler({ method: "POST", headers: {} }, res405);
  assert.equal(res405.statusCode, 405);
});
