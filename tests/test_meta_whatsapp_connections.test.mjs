import assert from "node:assert/strict";
import test from "node:test";

import handler from "../api/integrations/meta/whatsapp/connections.js";
import { whatsappConnectionId } from "../api/_lib/meta_connections.js";
import { COOKIE, sealSession } from "../api/_lib/lumos_session.js";

function configure() {
  process.env.LUMOS_AUTH_STATE_SECRET = "auth-state-secret-for-tests";
  process.env.LUMOS_META_GRAPH_VERSION = "v26.0";
  process.env.LUMOS_CREDENTIAL_VAULT_WRITE_URL = "https://vault.test/credentials";
  process.env.LUMOS_CREDENTIAL_VAULT_WRITE_TOKEN = "vault-write-token";
}

function cleanup() {
  for (const key of [
    "LUMOS_AUTH_STATE_SECRET",
    "LUMOS_META_GRAPH_VERSION",
    "LUMOS_CREDENTIAL_VAULT_WRITE_URL",
    "LUMOS_CREDENTIAL_VAULT_WRITE_TOKEN",
  ]) delete process.env[key];
}

function sessionRequest() {
  const cookie = sealSession({
    sid: "sid-1",
    lumos_id: "lumos-1",
    exp: Math.floor(Date.now() / 1000) + 600,
  });
  return { method: "GET", headers: { cookie: `${COOKIE}=${cookie}` } };
}

function response() {
  return {
    statusCode: 0,
    headers: {},
    body: "",
    setHeader(name, value) { this.headers[name] = value; },
    end(payload) { this.body = payload || ""; },
  };
}

function vaultResponse(body) {
  return { ok: true, async json() { return body; } };
}

const CREDENTIAL_LIST = {
  ok: true,
  credentials: [{
    vault_ref: "meta:whatsapp:ref-1",
    provider: "whatsapp",
    provider_account_id: "wa-user-1",
    expires_at: 0,
    auth_mode: "facebook_login",
  }],
};

const CREDENTIAL_RESOLVE = {
  ok: true,
  vault_ref: "meta:whatsapp:ref-1",
  provider: "whatsapp",
  provider_account_id: "wa-user-1",
  credential: {
    access_token: "secret-graph-token",
    token_type: "bearer",
    expires_at: 0,
    auth_mode: "facebook_login",
  },
};

function stubFetch({ businesses, phonesByWaba, graphFails = false, storedConnections = [] }) {
  const upserts = [];
  const fetchImpl = async (url, options = {}) => {
    const target = String(url);
    if (target.startsWith("https://vault.test/credentials")) {
      const body = JSON.parse(options.body);
      if (body.operation === "credential.list") return vaultResponse(CREDENTIAL_LIST);
      if (body.operation === "credential.resolve") return vaultResponse(CREDENTIAL_RESOLVE);
      if (body.operation === "connection.upsert") {
        upserts.push(body);
        return vaultResponse({ ok: true, connection_id: body.connection_id });
      }
      if (body.operation === "connection.list") {
        return vaultResponse({ ok: true, connections: storedConnections });
      }
      return vaultResponse({ ok: false });
    }
    if (graphFails) return { ok: false, status: 500, async json() { return {}; } };
    if (target.includes("me/businesses")) return vaultResponse({ data: businesses });
    const phoneMatch = target.match(/v26\.0\/([^/]+)\/phone_numbers/);
    if (phoneMatch) return vaultResponse({ data: phonesByWaba[phoneMatch[1]] || [] });
    return { ok: false, status: 404, async json() { return {}; } };
  };
  fetchImpl.upserts = upserts;
  return fetchImpl;
}

test("Each phone number becomes a distinct permanent connection row without leaks", async () => {
  configure();
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = stubFetch({
      businesses: [{
        id: "biz-1",
        name: "We Lock AI",
        owned_whatsapp_business_accounts: { data: [{ id: "waba-1", name: "Test WABA" }] },
      }],
      phonesByWaba: {
        "waba-1": [
          { id: "phone-1", display_phone_number: "+1 555 000 0001", verified_name: "Lumos DE" },
          { id: "phone-2", display_phone_number: "+1 555 000 0002", verified_name: "Lumos TR" },
        ],
      },
    });
    const res = response();
    await handler(sessionRequest(), res);
    assert.equal(res.statusCode, 200);
    const payload = JSON.parse(res.body);
    assert.equal(payload.connections.length, 2);
    const [first, second] = payload.connections;
    assert.notEqual(first.connection_id, second.connection_id);
    assert.equal(first.waba_id, "waba-1");
    assert.equal(first.phone_number_id, "phone-1");
    assert.equal(first.credential_account_id, "wa-user-1");
    assert.equal(first.status, "verified");
    assert.deepEqual(first.requested_scopes, ["business_management", "whatsapp_business_management"]);
    // Kalıcılık: aynı üçlü her çağrıda aynı connection_id'yi üretir.
    assert.equal(first.connection_id, whatsappConnectionId("lumos-1", "waba-1", "phone-1"));
    // S5: her canlı satır kalıcı kayda yazılır (credential_ref ile, kopya yok).
    assert.equal(globalThis.fetch.upserts.length, 2);
    assert.equal(globalThis.fetch.upserts[0].credential_ref, "meta:whatsapp:ref-1");
    assert.ok(Number(first.last_verified_at) > 0);
    // Sızıntı yok: token ve vault_ref gövdede geçmez.
    assert.ok(!res.body.includes("secret-graph-token"));
    assert.ok(!res.body.includes("meta:whatsapp:ref-1"));
  } finally {
    globalThis.fetch = originalFetch;
    cleanup();
  }
});

test("Empty enumeration reports gaps instead of fabricating rows", async () => {
  configure();
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = stubFetch({
      businesses: [{
        id: "biz-1",
        name: "We Lock AI",
        owned_whatsapp_business_accounts: { data: [{ id: "waba-1", name: "Test WABA" }] },
      }],
      phonesByWaba: { "waba-1": [] },
    });
    const res = response();
    await handler(sessionRequest(), res);
    assert.equal(res.statusCode, 200);
    const payload = JSON.parse(res.body);
    assert.deepEqual(payload.connections, []);
    assert.equal(payload.gaps.length, 1);
    assert.equal(payload.gaps[0].reason, "phone_numbers_empty");
    assert.equal(payload.gaps[0].waba_id, "waba-1");
  } finally {
    globalThis.fetch = originalFetch;
    cleanup();
  }
});

test("Graph outage on every credential is reported as 502, not an empty success", async () => {
  configure();
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = stubFetch({ businesses: [], phonesByWaba: {}, graphFails: true });
    const res = response();
    await handler(sessionRequest(), res);
    assert.equal(res.statusCode, 502);
    const payload = JSON.parse(res.body);
    assert.equal(payload.ok, false);
    assert.equal(payload.error, "whatsapp_enumeration_unavailable");
    assert.equal(payload.gaps[0].reason, "enumeration_failed");
  } finally {
    globalThis.fetch = originalFetch;
    cleanup();
  }
});

test("Graph outage with stored history serves last-known rows as unverified", async () => {
  configure();
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = stubFetch({
      businesses: [],
      phonesByWaba: {},
      graphFails: true,
      storedConnections: [{
        connection_id: "conn_wa_stored1",
        provider: "whatsapp",
        waba_id: "waba-1",
        waba_name: "Test WABA",
        phone_number_id: "phone-1",
        display_phone_number: "+1 555 000 0001",
        verified_name: "Test Number",
        last_verified_at: 1700000000,
      }],
    });
    const res = response();
    await handler(sessionRequest(), res);
    assert.equal(res.statusCode, 200);
    const payload = JSON.parse(res.body);
    assert.equal(payload.mode, "stored_last_known");
    assert.equal(payload.connections.length, 1);
    assert.equal(payload.connections[0].status, "unverified");
    assert.equal(payload.connections[0].last_verified_at, 1700000000);
    // Kesinti yine görünür: gaps boş değil.
    assert.equal(payload.gaps[0].reason, "enumeration_failed");
  } finally {
    globalThis.fetch = originalFetch;
    cleanup();
  }
});

test("Session and method gates fail closed", async () => {
  configure();
  try {
    const unauthorized = response();
    await handler({ method: "GET", headers: {} }, unauthorized);
    assert.equal(unauthorized.statusCode, 401);
    const wrongMethod = response();
    await handler({ method: "POST", headers: {} }, wrongMethod);
    assert.equal(wrongMethod.statusCode, 405);
  } finally {
    cleanup();
  }
});
