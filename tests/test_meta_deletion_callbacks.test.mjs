import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import test from "node:test";

import gatewayHandler from "../services/credential-gateway/api/gateway.js";
import { deleteMetaConnectionsForCredential } from "../api/_lib/meta_vault.js";
import { metaAppSecrets, verifyMetaSignedRequest } from "../api/_lib/meta_signed_request.js";
import dataDeletionHandler from "../api/meta/data-deletion.js";
import deauthorizeHandler from "../api/meta/deauthorize.js";
import webhookHandler from "../api/webhooks/meta.js";

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
  LUMOS_META_WEBHOOK_SINK_URL: undefined,
  LUMOS_META_WEBHOOK_SINK_TOKEN: undefined,
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
function harness(initial, { failDeletes = false, failDelete = () => false } = {}) {
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
      if (failDeletes || failDelete(name)) return respond(500, {});
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

test("deauthorize with a forged signature purges nothing", async () => {
  configure();
  const h = harness(seed());
  try {
    const before = new Map(h.secrets);
    const valid = signedRequest("business-secret", { algorithm: "HMAC-SHA256", user_id: "111" });
    const forgedPayload = Buffer.from(JSON.stringify({ algorithm: "HMAC-SHA256", user_id: "222" })).toString("base64url");
    const res = capture();
    await deauthorizeHandler({
      method: "POST",
      url: "/api/meta/deauthorize",
      headers: {},
      body: { signed_request: `${valid.split(".")[0]}.${forgedPayload}` },
    }, res);
    assert.equal(res.statusCode, 400);
    assert.deepEqual(h.secrets, before);
  } finally {
    h.restore();
    cleanup();
  }
});

test("a purge that fails is recorded as failed and never answered with a confirmation code", async () => {
  configure();
  const h = harness(seed(), { failDeletes: true });
  try {
    const res = capture();
    await dataDeletionHandler({
      method: "POST",
      url: "/api/meta/data-deletion",
      headers: {},
      body: { signed_request: signedRequest("business-secret", { algorithm: "HMAC-SHA256", user_id: "111" }) },
    }, res);
    assert.equal(res.statusCode, 503);
    assert.equal(JSON.parse(res.body).confirmation_code, undefined);
    assert.equal(h.secrets.has("CRED__wa_111"), true);
    const failed = [...h.secrets.entries()].filter(([name]) => name.startsWith("DELETION__"));
    assert.equal(failed.length, 1);
    assert.equal(JSON.parse(failed[0][1]).status, "failed");

    const code = failed[0][0].slice("DELETION__".length);
    const statusRes = capture();
    await dataDeletionHandler({ method: "GET", url: `/api/meta/data-deletion?code=${code}`, headers: {} }, statusRes);
    assert.equal(statusRes.statusCode, 200);
    assert.equal(JSON.parse(statusRes.body).status, "failed");
  } finally {
    h.restore();
    cleanup();
  }
});

test("a deletion request with nothing stored completes with zero counts", async () => {
  configure();
  const h = harness(seed());
  try {
    const res = capture();
    await dataDeletionHandler({
      method: "POST",
      url: "/api/meta/data-deletion",
      headers: {},
      body: { signed_request: signedRequest("instagram-secret", { algorithm: "HMAC-SHA256", user_id: "999" }) },
    }, res);
    assert.equal(res.statusCode, 200);
    const { confirmation_code: code } = JSON.parse(res.body);
    const record = JSON.parse(h.secrets.get(`DELETION__${code}`));
    assert.equal(record.status, "completed");
    assert.deepEqual(record.counts, { credentials: 0, connections: 0, inbound: 0, last_inbound: 0, send: 0 });
    assert.equal(h.secrets.size, Object.keys(seed()).length + 1);
  } finally {
    h.restore();
    cleanup();
  }
});

test("a Meta webhook forwarded to the gateway stores only a dedupe key, no content or ids", async () => {
  configure({ LUMOS_META_WEBHOOK_SINK_URL: GATEWAY, LUMOS_META_WEBHOOK_SINK_TOKEN: "gateway-token" });
  const h = harness({});
  try {
    const payload = {
      object: "whatsapp_business_account",
      entry: [{
        id: "W1",
        changes: [{
          field: "messages",
          value: {
            metadata: { phone_number_id: "PN1", display_phone_number: "+900000000000" },
            contacts: [{ wa_id: "905550001122", profile: { name: "Secret Sender" } }],
            messages: [{ id: "wamid.XYZ", from: "905550001122", text: { body: "private message body" } }],
          },
        }],
      }],
    };
    const raw = Buffer.from(JSON.stringify(payload));
    const res = capture();
    await webhookHandler({
      method: "POST",
      body: raw,
      headers: { "x-hub-signature-256": `sha256=${createHmac("sha256", "business-secret").update(raw).digest("hex")}` },
    }, res);
    assert.equal(res.statusCode, 200);
    assert.deepEqual([...h.secrets.keys()].map((name) => name.replace(/[a-f0-9]{64}$/, "<sha256>")), ["WEBHOOK__<sha256>"]);
    const stored = JSON.parse([...h.secrets.values()][0]);
    assert.deepEqual(Object.keys(stored).sort(), ["provider", "received_at"]);
    const everything = JSON.stringify([...h.secrets.entries()]);
    for (const needle of ["private message body", "Secret Sender", "905550001122", "PN1", "W1", "wamid"]) {
      assert.equal(everything.includes(needle), false, needle);
    }
  } finally {
    h.restore();
    cleanup();
  }
});

test("a purge interrupted before the credential is deleted completes on Meta's retry", async () => {
  configure();
  let failCredential = true;
  const h = harness(seed(), { failDelete: (name) => failCredential && name.startsWith("CRED__") });
  const request = () => ({
    method: "POST",
    url: "/api/meta/data-deletion",
    headers: {},
    body: { signed_request: signedRequest("business-secret", { algorithm: "HMAC-SHA256", user_id: "111" }) },
  });
  try {
    const first = capture();
    await dataDeletionHandler(request(), first);
    assert.equal(first.statusCode, 503);
    // Yapraktan köke: bağlı kayıtlar gitti, credential kaldı.
    assert.equal(h.secrets.has("CONN__conn_wa_a"), false);
    assert.equal(h.secrets.has("SEND__m1"), false);
    assert.equal(h.secrets.has("CRED__wa_111"), true);

    failCredential = false;
    const retry = capture();
    await dataDeletionHandler(request(), retry);
    assert.equal(retry.statusCode, 200);
    const { confirmation_code: code } = JSON.parse(retry.body);
    const record = JSON.parse(h.secrets.get(`DELETION__${code}`));
    assert.equal(record.status, "completed");
    assert.equal(record.counts.credentials, 1);
    assert.equal(h.secrets.has("CRED__wa_111"), false);
  } finally {
    h.restore();
    cleanup();
  }
});

test("purge also removes the same owner's orphaned connection records for providers in scope", async () => {
  configure();
  const initial = seed();
  // Eski revoke akışının artığı: credential'ı silinmiş bağlantı kayıtları.
  initial.CONN__orphan_wa_a = connection("orphan_wa_a", "whatsapp", "lumos-a", "meta:whatsapp:gone", { phone_number_id: "PN9", waba_id: "W9" });
  initial.LASTIN__PN9__7 = JSON.stringify({ last_inbound_at: 1 });
  initial.CONN__orphan_ig_a = connection("orphan_ig_a", "instagram", "lumos-a", "meta:instagram:gone");
  initial.CONN__orphan_wa_b = connection("orphan_wa_b", "whatsapp", "lumos-b", "meta:whatsapp:gone-b");
  const h = harness(initial);
  try {
    const res = capture();
    await dataDeletionHandler({
      method: "POST",
      url: "/api/meta/data-deletion",
      headers: {},
      body: { signed_request: signedRequest("business-secret", { algorithm: "HMAC-SHA256", user_id: "111" }) },
    }, res);
    assert.equal(res.statusCode, 200);
    assert.equal(h.secrets.has("CONN__orphan_wa_a"), false);
    assert.equal(h.secrets.has("LASTIN__PN9__7"), false);
    // Kapsam dışı sağlayıcı ve başka sahip: dokunulmaz.
    assert.equal(h.secrets.has("CONN__orphan_ig_a"), true);
    assert.equal(h.secrets.has("CONN__orphan_wa_b"), true);
  } finally {
    h.restore();
    cleanup();
  }
});
