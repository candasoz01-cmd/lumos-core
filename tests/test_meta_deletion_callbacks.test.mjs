import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import test from "node:test";

import gatewayHandler from "../services/credential-gateway/api/gateway.js";
import { deleteMetaConnectionsForCredential } from "../api/_lib/meta_vault.js";
import { metaAppSecrets, verifyMetaSignedRequest } from "../api/_lib/meta_signed_request.js";
import dataDeletionHandler from "../api/meta/data-deletion.js";
import deauthorizeHandler from "../api/meta/deauthorize.js";

const INFISICAL = "https://infisical.test";
const GATEWAY = "https://gateway.test/api/gateway";

const ENV = {
  LUMOS_CREDENTIAL_GATEWAY_TOKEN: "gateway-token",
  LUMOS_INFISICAL_URL: INFISICAL,
  LUMOS_INFISICAL_CLIENT_ID: "machine-id",
  LUMOS_INFISICAL_CLIENT_SECRET: "machine-secret",
  LUMOS_INFISICAL_PROJECT_ID: "project-id",
  LUMOS_INFISICAL_ENVIRONMENT: "prod",
  LUMOS_INFISICAL_SECRET_PATH: "/meta",
  LUMOS_CREDENTIAL_VAULT_WRITE_URL: GATEWAY,
  LUMOS_CREDENTIAL_VAULT_WRITE_TOKEN: "gateway-token",
  LUMOS_META_APP_SECRET: "consumer-secret",
  LUMOS_INSTAGRAM_APP_SECRET: "instagram-secret",
  LUMOS_WHATSAPP_APP_SECRET: "business-secret",
};

function configure(overrides = {}) {
  for (const [key, value] of Object.entries({ ...ENV, ...overrides })) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
}

function cleanup() {
  for (const key of Object.keys(ENV)) delete process.env[key];
}

function signedRequest(secret, payload) {
  const encoded = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const signature = createHmac("sha256", secret).update(encoded).digest("base64url");
  return `${signature}.${encoded}`;
}

function credential(vaultRef, provider, owner, accountId) {
  return JSON.stringify({
    schema: "lumos-credential-v2",
    vault_ref: vaultRef,
    provider,
    owner_lumos_id: owner,
    provider_account_id: accountId,
    credential: { access_token: `token-${vaultRef}`, token_type: "bearer", expires_at: 0, auth_mode: "facebook_login" },
    updated_at: 1,
  });
}

function connection(connectionId, provider, owner, credentialRef, extra = {}) {
  return JSON.stringify({
    schema: "lumos-connection-v1",
    connection_id: connectionId,
    owner_lumos_id: owner,
    provider,
    credential_ref: credentialRef,
    ...extra,
  });
}

// Infisical sahtesi ve gateway köprüsü: istemci (meta_vault.js) → gateway
// handler → Infisical, tek süreçte uçtan uca.
function harness(initial) {
  const secrets = new Map(Object.entries(initial));
  const respond = (status, body) => ({ ok: status >= 200 && status < 300, status, async json() { return body; } });
  const infisical = async (url, options = {}) => {
    const parsed = new URL(url);
    if (parsed.pathname === "/api/v1/auth/universal-auth/login") return respond(200, { accessToken: "infisical-token" });
    if (parsed.pathname === "/api/v3/secrets/raw" && (!options.method || options.method === "GET")) {
      return respond(200, { secrets: [...secrets.entries()].map(([secretKey, secretValue]) => ({ secretKey, secretValue })) });
    }
    const match = parsed.pathname.match(/^\/api\/v3\/secrets\/raw\/(.+)$/);
    if (!match) return respond(500, {});
    const name = decodeURIComponent(match[1]);
    const method = options.method || "GET";
    if (method === "GET") {
      return secrets.has(name) ? respond(200, { secret: { secretKey: name, secretValue: secrets.get(name) } }) : respond(404, {});
    }
    if (method === "POST") {
      if (secrets.has(name)) return respond(409, {});
      secrets.set(name, JSON.parse(options.body).secretValue);
      return respond(200, {});
    }
    if (method === "PATCH") {
      secrets.set(name, JSON.parse(options.body).secretValue);
      return respond(200, {});
    }
    if (method === "DELETE") {
      if (!secrets.has(name)) return respond(404, {});
      secrets.delete(name);
      return respond(200, {});
    }
    return respond(500, {});
  };
  const original = globalThis.fetch;
  globalThis.fetch = async (url, options = {}) => {
    if (String(url) !== GATEWAY) return infisical(url, options);
    const req = {
      method: options.method || "GET",
      headers: Object.fromEntries(Object.entries(options.headers || {}).map(([k, v]) => [k.toLowerCase(), v])),
      body: options.body,
    };
    const res = capture();
    await gatewayHandler(req, res);
    return { ok: res.statusCode >= 200 && res.statusCode < 300, status: res.statusCode, async json() { return JSON.parse(res.body); } };
  };
  return { secrets, restore() { globalThis.fetch = original; } };
}

function capture() {
  return {
    statusCode: 0,
    body: "",
    setHeader() {},
    end(payload) { this.body = payload || ""; },
  };
}

function seed() {
  return {
    // Hedef: Business app kullanıcısı 111 — WhatsApp credential + bağlantı ağacı.
    CRED__wa_111: credential("meta:whatsapp:wa111", "whatsapp", "lumos-a", "111"),
    CONN__conn_wa_a: connection("conn_wa_a", "whatsapp", "lumos-a", "meta:whatsapp:wa111", { phone_number_id: "PN1", waba_id: "W1" }),
    INBOUND__m1: JSON.stringify({ schema: "lumos-inbound-v1", message_id: "m1", phone_number_id: "PN1", waba_id: "W1", from_wa_id: "9001" }),
    LASTIN__PN1__9001: JSON.stringify({ last_inbound_at: 5, message_id: "m1" }),
    SEND__m1: JSON.stringify({ schema: "lumos-send-v1", inbound_message_id: "m1", connection_id: "conn_wa_a", status: "sent" }),
    // Aynı sayısal kimlik, başka uygulama (tüketici app): dokunulmamalı.
    CRED__fb_111: credential("meta:facebook:fb111", "facebook", "lumos-a", "111"),
    // Başka kullanıcı: dokunulmamalı.
    CRED__wa_222: credential("meta:whatsapp:wa222", "whatsapp", "lumos-b", "222"),
    CONN__conn_wa_b: connection("conn_wa_b", "whatsapp", "lumos-b", "meta:whatsapp:wa222", { phone_number_id: "PN2", waba_id: "W2" }),
    INBOUND__m2: JSON.stringify({ schema: "lumos-inbound-v1", message_id: "m2", phone_number_id: "PN2", waba_id: "W2", from_wa_id: "9002" }),
    WEBHOOK__abc: JSON.stringify({ provider: "whatsapp", received_at: 1 }),
  };
}

test("signed_request verifies per app and rejects tampering, wrong algorithm and bad user ids", () => {
  const apps = metaAppSecrets({ ...ENV });
  const payload = { algorithm: "HMAC-SHA256", user_id: "111", issued_at: 10 };
  assert.deepEqual(verifyMetaSignedRequest(signedRequest("business-secret", payload), apps), {
    userId: "111",
    providers: ["pages", "whatsapp"],
    issuedAt: 10,
  });
  assert.deepEqual(verifyMetaSignedRequest(signedRequest("consumer-secret", payload), apps)?.providers, ["facebook"]);
  assert.deepEqual(verifyMetaSignedRequest(signedRequest("instagram-secret", payload), apps)?.providers, ["instagram"]);
  // Business app sırrı yoksa WhatsApp tüketici app'e düşer (meta_oauth.js ile aynı kural).
  const single = metaAppSecrets({ LUMOS_META_APP_SECRET: "consumer-secret" });
  assert.deepEqual(verifyMetaSignedRequest(signedRequest("consumer-secret", payload), single)?.providers, ["facebook", "whatsapp"]);

  const valid = signedRequest("business-secret", payload);
  const [signature, body] = valid.split(".");
  const forged = Buffer.from(JSON.stringify({ ...payload, user_id: "222" })).toString("base64url");
  assert.equal(verifyMetaSignedRequest(`${signature}.${forged}`, apps), null);
  assert.equal(verifyMetaSignedRequest(signedRequest("other-secret", payload), apps), null);
  assert.equal(verifyMetaSignedRequest(signedRequest("business-secret", { ...payload, algorithm: "none" }), apps), null);
  assert.equal(verifyMetaSignedRequest(signedRequest("business-secret", { ...payload, user_id: "../x" }), apps), null);
  assert.equal(verifyMetaSignedRequest(`${signature}`, apps), null);
  assert.equal(verifyMetaSignedRequest(`${signature}.${body}`, []), null);
});

test("data deletion purges the user's credentials and linked records, then reports status", async () => {
  configure();
  const h = harness(seed());
  try {
    const res = capture();
    await dataDeletionHandler({
      method: "POST",
      url: "/api/meta/data-deletion",
      headers: {},
      body: { signed_request: signedRequest("business-secret", { algorithm: "HMAC-SHA256", user_id: "111", issued_at: 1 }) },
    }, res);
    assert.equal(res.statusCode, 200);
    const body = JSON.parse(res.body);
    assert.match(body.confirmation_code, /^[A-Za-z0-9_-]{16,64}$/);
    assert.equal(body.url, `https://welockai.com/legal/meta-deletion?code=${body.confirmation_code}`);

    for (const name of ["CRED__wa_111", "CONN__conn_wa_a", "INBOUND__m1", "LASTIN__PN1__9001", "SEND__m1"]) {
      assert.equal(h.secrets.has(name), false, `${name} should be deleted`);
    }
    for (const name of ["CRED__fb_111", "CRED__wa_222", "CONN__conn_wa_b", "INBOUND__m2", "WEBHOOK__abc"]) {
      assert.equal(h.secrets.has(name), true, `${name} should remain`);
    }
    const record = JSON.parse(h.secrets.get(`DELETION__${body.confirmation_code}`));
    assert.equal(record.status, "completed");
    assert.doesNotMatch(JSON.stringify(record), /111|lumos-a/);

    const statusRes = capture();
    await dataDeletionHandler({ method: "GET", url: `/api/meta/data-deletion?code=${body.confirmation_code}`, headers: {} }, statusRes);
    assert.equal(statusRes.statusCode, 200);
    const status = JSON.parse(statusRes.body);
    assert.equal(status.status, "completed");
    assert.deepEqual(status.counts, { credentials: 1, connections: 1, inbound: 1, lastInbound: 1, send: 1 });
  } finally {
    h.restore();
    cleanup();
  }
});

test("data deletion accepts a form-encoded body and rejects an invalid signature before touching the vault", async () => {
  configure();
  const h = harness(seed());
  try {
    const form = new URLSearchParams({
      signed_request: signedRequest("consumer-secret", { algorithm: "HMAC-SHA256", user_id: "111" }),
    }).toString();
    const res = capture();
    await dataDeletionHandler({ method: "POST", url: "/api/meta/data-deletion", headers: {}, body: form }, res);
    assert.equal(res.statusCode, 200);
    assert.equal(h.secrets.has("CRED__fb_111"), false);
    assert.equal(h.secrets.has("CRED__wa_111"), true);

    const before = h.secrets.size;
    const bad = capture();
    await dataDeletionHandler({
      method: "POST",
      url: "/api/meta/data-deletion",
      headers: {},
      body: { signed_request: signedRequest("attacker", { algorithm: "HMAC-SHA256", user_id: "222" }) },
    }, bad);
    assert.equal(bad.statusCode, 400);
    assert.equal(h.secrets.size, before);
  } finally {
    h.restore();
    cleanup();
  }
});

test("data deletion never reports success when the gateway cannot purge", async () => {
  configure({ LUMOS_CREDENTIAL_VAULT_WRITE_URL: undefined });
  try {
    const res = capture();
    await dataDeletionHandler({
      method: "POST",
      url: "/api/meta/data-deletion",
      headers: {},
      body: { signed_request: signedRequest("business-secret", { algorithm: "HMAC-SHA256", user_id: "111" }) },
    }, res);
    assert.equal(res.statusCode, 503);
    const body = JSON.parse(res.body);
    assert.equal(body.ok, false);
    assert.equal(body.url, undefined);
    assert.equal(body.confirmation_code, undefined);
  } finally {
    cleanup();
  }
});

test("status lookup rejects malformed codes and does not invent a status", async () => {
  configure();
  const h = harness({});
  try {
    const malformed = capture();
    await dataDeletionHandler({ method: "GET", url: "/api/meta/data-deletion?code=../../x", headers: {} }, malformed);
    assert.equal(malformed.statusCode, 400);
    const unknown = capture();
    await dataDeletionHandler({ method: "GET", url: "/api/meta/data-deletion?code=AAAAAAAAAAAAAAAAAAAAAAAA", headers: {} }, unknown);
    assert.equal(unknown.statusCode, 503);
    assert.equal(JSON.parse(unknown.body).ok, false);
  } finally {
    h.restore();
    cleanup();
  }
});

test("deauthorize purges through the same path and rejects unsigned calls", async () => {
  configure();
  const h = harness(seed());
  try {
    const res = capture();
    await deauthorizeHandler({
      method: "POST",
      url: "/api/meta/deauthorize",
      headers: {},
      body: { signed_request: signedRequest("business-secret", { algorithm: "HMAC-SHA256", user_id: "111" }) },
    }, res);
    assert.equal(res.statusCode, 200);
    assert.deepEqual(JSON.parse(res.body), { ok: true, status: "completed" });
    assert.equal(h.secrets.has("CRED__wa_111"), false);
    assert.equal(h.secrets.has("CONN__conn_wa_a"), false);

    const denied = capture();
    await deauthorizeHandler({ method: "POST", url: "/api/meta/deauthorize", headers: {}, body: {} }, denied);
    assert.equal(denied.statusCode, 400);
  } finally {
    h.restore();
    cleanup();
  }
});

test("connection.delete removes only the owner's connection tree for that credential", async () => {
  configure();
  const initial = seed();
  // Başka sahibin aynı credential_ref'i taşıyan kaydı (tahrifat) silinmemeli.
  initial.CONN__conn_forged = connection("conn_forged", "whatsapp", "lumos-b", "meta:whatsapp:wa111");
  const h = harness(initial);
  try {
    const result = await deleteMetaConnectionsForCredential("lumos-a", "meta:whatsapp:wa111");
    assert.deepEqual(result.counts, { credentials: 0, connections: 1, inbound: 1, lastInbound: 1, send: 1 });
    assert.equal(h.secrets.has("CONN__conn_wa_a"), false);
    assert.equal(h.secrets.has("CONN__conn_forged"), true);
    assert.equal(h.secrets.has("CRED__wa_111"), true);
  } finally {
    h.restore();
    cleanup();
  }
});
