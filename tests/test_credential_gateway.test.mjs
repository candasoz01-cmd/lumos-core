import assert from "node:assert/strict";
import test from "node:test";

import gatewayHandler from "../services/credential-gateway/api/gateway.js";
import healthHandler from "../services/credential-gateway/api/health.js";
import {
  listMetaCredentials,
  metaCredentialMetadata,
  resolveMetaCredentialByRef,
  writeMetaCredential,
} from "../api/_lib/meta_vault.js";

const INFISICAL = "https://infisical.test";

function configure() {
  process.env.LUMOS_CREDENTIAL_GATEWAY_TOKEN = "gateway-token";
  process.env.LUMOS_INFISICAL_URL = INFISICAL;
  process.env.LUMOS_INFISICAL_CLIENT_ID = "machine-id";
  process.env.LUMOS_INFISICAL_CLIENT_SECRET = "machine-secret";
  process.env.LUMOS_INFISICAL_PROJECT_ID = "project-id";
  process.env.LUMOS_INFISICAL_ENVIRONMENT = "prod";
  process.env.LUMOS_INFISICAL_SECRET_PATH = "/meta";
  // İstemci tarafı (meta_vault.js) gateway'e bu env'lerle bağlanır.
  process.env.LUMOS_CREDENTIAL_VAULT_WRITE_URL = "https://gateway.test/api/gateway";
  process.env.LUMOS_CREDENTIAL_VAULT_WRITE_TOKEN = "gateway-token";
}

function cleanup() {
  for (const key of [
    "LUMOS_CREDENTIAL_GATEWAY_TOKEN",
    "LUMOS_INFISICAL_URL",
    "LUMOS_INFISICAL_CLIENT_ID",
    "LUMOS_INFISICAL_CLIENT_SECRET",
    "LUMOS_INFISICAL_PROJECT_ID",
    "LUMOS_INFISICAL_ENVIRONMENT",
    "LUMOS_INFISICAL_SECRET_PATH",
    "LUMOS_CREDENTIAL_VAULT_WRITE_URL",
    "LUMOS_CREDENTIAL_VAULT_WRITE_TOKEN",
  ]) delete process.env[key];
}

// Basit Infisical sahtesi: secret adı → değer.
function fakeInfisical(initial = {}) {
  const secrets = new Map(Object.entries(initial));
  const fetchImpl = async (url, options = {}) => {
    const parsed = new URL(url);
    const respond = (status, body) => ({
      ok: status >= 200 && status < 300,
      status,
      async json() { return body; },
    });
    if (parsed.pathname === "/api/v1/auth/universal-auth/login") {
      return respond(200, { accessToken: "infisical-token" });
    }
    if (parsed.pathname === "/api/v3/secrets/raw" && (!options.method || options.method === "GET")) {
      return respond(200, {
        secrets: [...secrets.entries()].map(([secretKey, secretValue]) => ({ secretKey, secretValue })),
      });
    }
    const match = parsed.pathname.match(/^\/api\/v3\/secrets\/raw\/(.+)$/);
    if (match) {
      const name = decodeURIComponent(match[1]);
      if (!options.method || options.method === "GET") {
        if (!secrets.has(name)) return respond(404, {});
        return respond(200, { secret: { secretKey: name, secretValue: secrets.get(name) } });
      }
      if (options.method === "POST") {
        if (secrets.has(name)) return respond(409, {});
        secrets.set(name, JSON.parse(options.body).secretValue);
        return respond(200, {});
      }
      if (options.method === "PATCH") {
        secrets.set(name, JSON.parse(options.body).secretValue);
        return respond(200, {});
      }
      if (options.method === "DELETE") {
        if (!secrets.has(name)) return respond(404, {});
        secrets.delete(name);
        return respond(200, {});
      }
    }
    return respond(500, {});
  };
  return { secrets, fetchImpl };
}

// Gateway handler'ı gerçek HTTP istemcisi gibi çağıran köprü: meta_vault.js'in
// fetch'i doğrudan handler'a bağlanır → istemci+sunucu sözleşmesi tek testte.
function gatewayFetch(infisicalFetch) {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = infisicalFetch;
  return {
    async call(url, options = {}) {
      const req = {
        method: options.method || "GET",
        headers: Object.fromEntries(
          Object.entries(options.headers || {}).map(([k, v]) => [k.toLowerCase(), v]),
        ),
        body: options.body,
      };
      let statusCode = 0;
      let body = "";
      const res = {
        setHeader() {},
        set statusCode(value) { statusCode = value; },
        get statusCode() { return statusCode; },
        end(payload) { body = payload || ""; },
      };
      await gatewayHandler(req, res);
      return { ok: statusCode >= 200 && statusCode < 300, status: statusCode, async json() { return JSON.parse(body); } };
    },
    restore() { globalThis.fetch = originalFetch; },
  };
}

test("Gateway fails closed without bearer token and on unsupported operation", async () => {
  configure();
  const { fetchImpl } = fakeInfisical();
  const bridge = gatewayFetch(fetchImpl);
  try {
    const denied = await bridge.call("https://gateway.test/api/gateway", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operation: "credential.list", owner_lumos_id: "lumos-1" }),
    });
    assert.equal(denied.status, 401);
    const unsupported = await bridge.call("https://gateway.test/api/gateway", {
      method: "POST",
      headers: { Authorization: "Bearer gateway-token" },
      body: JSON.stringify({ operation: "credential.export", owner_lumos_id: "lumos-1" }),
    });
    assert.equal(unsupported.status, 400);
    assert.equal((await unsupported.json()).error, "unsupported_operation");
  } finally {
    bridge.restore();
    cleanup();
  }
});

test("Client upsert→list→resolve-by-ref round trip works against gateway", async () => {
  configure();
  const { secrets, fetchImpl } = fakeInfisical();
  const bridge = gatewayFetch(fetchImpl);
  try {
    await writeMetaCredential({
      vaultRef: "meta:whatsapp:ref-one",
      purposeCode: "integration.meta.whatsapp.read",
      provider: "whatsapp",
      lumosId: "lumos-1",
      providerAccountId: "acct-1",
      accessToken: "token-1",
      tokenType: "bearer",
      expiresAt: 1000,
      authMode: "facebook_login",
    }, bridge.call);
    await writeMetaCredential({
      vaultRef: "meta:whatsapp:ref-two",
      purposeCode: "integration.meta.whatsapp.read",
      provider: "whatsapp",
      lumosId: "lumos-1",
      providerAccountId: "acct-2",
      accessToken: "token-2",
      tokenType: "bearer",
      expiresAt: 2000,
      authMode: "facebook_login",
    }, bridge.call);
    assert.equal([...secrets.keys()].filter((name) => name.startsWith("CRED__")).length, 2);

    const rows = await listMetaCredentials("lumos-1", "whatsapp", bridge.call);
    assert.equal(rows.length, 2);
    assert.deepEqual(new Set(rows.map((row) => row.providerAccountId)), new Set(["acct-1", "acct-2"]));
    assert.ok(rows.every((row) => !JSON.stringify(row).includes("token-")));

    const resolved = await resolveMetaCredentialByRef("lumos-1", "meta:whatsapp:ref-two", bridge.call);
    assert.equal(resolved.accessToken, "token-2");
    assert.equal(resolved.providerAccountId, "acct-2");

    const metadata = await metaCredentialMetadata("lumos-1", "whatsapp", bridge.call);
    assert.equal(metadata.configured, true);
  } finally {
    bridge.restore();
    cleanup();
  }
});

test("Owner scoping hides other users and legacy v1-style records stay readable", async () => {
  configure();
  const legacy = JSON.stringify({
    vault_ref: "meta:facebook:legacy",
    provider: "facebook",
    owner_lumos_id: "lumos-1",
    provider_account_id: "fb-acct",
    credential: { access_token: "legacy-token", token_type: "bearer", expires_at: 99, auth_mode: "facebook_login" },
  });
  const { fetchImpl } = fakeInfisical({
    LEGACY_RECORD: legacy,
    NOISE_CONFIG: "plain-string-value",
    BROKEN_JSON_OBJECT: JSON.stringify({ hello: "world" }),
  });
  const bridge = gatewayFetch(fetchImpl);
  try {
    const rows = await listMetaCredentials("lumos-1", "", bridge.call);
    assert.equal(rows.length, 1);
    assert.equal(rows[0].vaultRef, "meta:facebook:legacy");
    const foreign = await listMetaCredentials("lumos-2", "", bridge.call);
    assert.equal(foreign.length, 0);
    const resolved = await resolveMetaCredentialByRef("lumos-1", "meta:facebook:legacy", bridge.call);
    assert.equal(resolved.accessToken, "legacy-token");
    // Şemaya oturmayan JSON objesi sessizce kaybolmaz — sayaçta raporlanır.
    const raw = await bridge.call("https://gateway.test/api/gateway", {
      method: "POST",
      headers: { Authorization: "Bearer gateway-token" },
      body: JSON.stringify({ operation: "credential.list", owner_lumos_id: "lumos-1" }),
    });
    assert.equal((await raw.json()).unparsed_records, 1);
  } finally {
    bridge.restore();
    cleanup();
  }
});

test("webhook.ingest dedupes by event key and never requires owner id", async () => {
  configure();
  const { fetchImpl } = fakeInfisical();
  const bridge = gatewayFetch(fetchImpl);
  const eventKey = "a".repeat(64);
  try {
    const first = await bridge.call("https://gateway.test/api/gateway", {
      method: "POST",
      headers: { Authorization: "Bearer gateway-token" },
      body: JSON.stringify({ operation: "webhook.ingest", provider: "whatsapp", event_key: eventKey, payload: {} }),
    });
    assert.deepEqual(await first.json(), { ok: true, status: "accepted" });
    const second = await bridge.call("https://gateway.test/api/gateway", {
      method: "POST",
      headers: { Authorization: "Bearer gateway-token" },
      body: JSON.stringify({ operation: "webhook.ingest", provider: "whatsapp", event_key: eventKey, payload: {} }),
    });
    assert.deepEqual(await second.json(), { ok: true, status: "duplicate" });
  } finally {
    bridge.restore();
    cleanup();
  }
});

test("connection.upsert/list persists rows owner-scoped without exposing credential_ref", async () => {
  configure();
  const { secrets, fetchImpl } = fakeInfisical();
  const bridge = gatewayFetch(fetchImpl);
  try {
    const upsert = await bridge.call("https://gateway.test/api/gateway", {
      method: "POST",
      headers: { Authorization: "Bearer gateway-token" },
      body: JSON.stringify({
        operation: "connection.upsert",
        owner_lumos_id: "lumos-1",
        connection_id: "conn_wa_abc123",
        provider: "whatsapp",
        credential_ref: "meta:whatsapp:ref-1",
        waba_id: "waba-1",
        waba_name: "Test WABA",
        phone_number_id: "phone-1",
        display_phone_number: "+1 555 000 0001",
        verified_name: "Test Number",
        last_verified_at: 1234,
      }),
    });
    assert.deepEqual(await upsert.json(), { ok: true, connection_id: "conn_wa_abc123" });
    assert.ok(secrets.has("CONN__conn_wa_abc123"));

    const list = await bridge.call("https://gateway.test/api/gateway", {
      method: "POST",
      headers: { Authorization: "Bearer gateway-token" },
      body: JSON.stringify({ operation: "connection.list", owner_lumos_id: "lumos-1", provider: "whatsapp" }),
    });
    const payload = await list.json();
    assert.equal(payload.connections.length, 1);
    assert.equal(payload.connections[0].connection_id, "conn_wa_abc123");
    assert.equal(payload.connections[0].last_verified_at, 1234);
    // credential_ref iç referans — liste yanıtına sızmaz.
    assert.ok(!JSON.stringify(payload).includes("meta:whatsapp:ref-1"));

    const foreign = await bridge.call("https://gateway.test/api/gateway", {
      method: "POST",
      headers: { Authorization: "Bearer gateway-token" },
      body: JSON.stringify({ operation: "connection.list", owner_lumos_id: "lumos-2" }),
    });
    assert.equal((await foreign.json()).connections.length, 0);

    // CONN__ kayıtları credential.list'in unparsed sayacına karışmaz.
    const credentialList = await bridge.call("https://gateway.test/api/gateway", {
      method: "POST",
      headers: { Authorization: "Bearer gateway-token" },
      body: JSON.stringify({ operation: "credential.list", owner_lumos_id: "lumos-1" }),
    });
    assert.equal((await credentialList.json()).unparsed_records, 0);
  } finally {
    bridge.restore();
    cleanup();
  }
});

test("D2: inbound envelope is stored without body and drives last-inbound lookup", async () => {
  configure();
  const { secrets, fetchImpl } = fakeInfisical();
  const bridge = gatewayFetch(fetchImpl);
  const call = (body) => bridge.call("https://gateway.test/api/gateway", {
    method: "POST",
    headers: { Authorization: "Bearer gateway-token" },
    body: JSON.stringify(body),
  });
  try {
    const stored = await call({
      operation: "inbound.store",
      provider: "whatsapp",
      message_id: "wamid.ABC==",
      from_wa_id: "15551234567",
      phone_number_id: "phone-1",
      waba_id: "waba-1",
      timestamp: 1786400000,
      message_type: "text",
      content_hash: "hash-1",
    });
    assert.deepEqual(await stored.json(), { ok: true, status: "stored" });
    // Zarfta gövde YOK: kayıtlarda serbest metin alanı bulunmaz.
    const inboundRaw = [...secrets.entries()].find(([name]) => name.startsWith("INBOUND__"))[1];
    assert.ok(!("text" in JSON.parse(inboundRaw)) && !("body" in JSON.parse(inboundRaw)));

    const duplicate = await call({
      operation: "inbound.store",
      provider: "whatsapp",
      message_id: "wamid.ABC==",
      from_wa_id: "15551234567",
      phone_number_id: "phone-1",
      waba_id: "waba-1",
    });
    assert.deepEqual(await duplicate.json(), { ok: true, status: "duplicate" });

    const last = await call({
      operation: "inbound.last",
      from_wa_id: "15551234567",
      phone_number_id: "phone-1",
    });
    const lastPayload = await last.json();
    assert.equal(lastPayload.last_inbound_at, 1786400000);
    assert.equal(lastPayload.message_id, "wamid.ABC==");

    const unknown = await call({
      operation: "inbound.last",
      from_wa_id: "15550000000",
      phone_number_id: "phone-1",
    });
    assert.equal((await unknown.json()).last_inbound_at, 0);
  } finally {
    bridge.restore();
    cleanup();
  }
});

test("D2: connection.lookup requires exact waba+phone match and fails closed", async () => {
  configure();
  const { fetchImpl } = fakeInfisical({
    CONN__conn_wa_x: JSON.stringify({
      connection_id: "conn_wa_x",
      owner_lumos_id: "lumos-1",
      provider: "whatsapp",
      waba_id: "waba-1",
      phone_number_id: "phone-1",
    }),
  });
  const bridge = gatewayFetch(fetchImpl);
  const call = (body) => bridge.call("https://gateway.test/api/gateway", {
    method: "POST",
    headers: { Authorization: "Bearer gateway-token" },
    body: JSON.stringify(body),
  });
  try {
    const hit = await call({ operation: "connection.lookup", phone_number_id: "phone-1", waba_id: "waba-1" });
    const payload = await hit.json();
    assert.equal(payload.connection_id, "conn_wa_x");
    assert.equal(payload.owner_lumos_id, "lumos-1");
    // Yalnız phone eşleşmesi YETMEZ — waba uyuşmazsa 404.
    const miss = await call({ operation: "connection.lookup", phone_number_id: "phone-1", waba_id: "waba-OTHER" });
    assert.equal(miss.status, 404);
  } finally {
    bridge.restore();
    cleanup();
  }
});

test("D2: send.reserve is idempotent and finalize records outcome on the same record", async () => {
  configure();
  const { secrets, fetchImpl } = fakeInfisical();
  const bridge = gatewayFetch(fetchImpl);
  const call = (body) => bridge.call("https://gateway.test/api/gateway", {
    method: "POST",
    headers: { Authorization: "Bearer gateway-token" },
    body: JSON.stringify(body),
  });
  try {
    const reserved = await call({
      operation: "send.reserve",
      inbound_message_id: "wamid.XYZ==",
      connection_id: "conn_wa_x",
      domain_id: "domain-1",
    });
    assert.deepEqual(await reserved.json(), { ok: true, status: "reserved" });
    const duplicate = await call({
      operation: "send.reserve",
      inbound_message_id: "wamid.XYZ==",
      connection_id: "conn_wa_x",
    });
    assert.deepEqual(await duplicate.json(), { ok: true, status: "duplicate" });

    const orphanFinalize = await call({
      operation: "send.finalize",
      inbound_message_id: "wamid.NOPE==",
      status: "sent",
    });
    assert.equal(orphanFinalize.status, 404);

    const finalized = await call({
      operation: "send.finalize",
      inbound_message_id: "wamid.XYZ==",
      status: "sent",
      provider_message_id: "wamid.OUT==",
    });
    assert.deepEqual(await finalized.json(), { ok: true, status: "sent" });
    const record = JSON.parse([...secrets.entries()].find(([name]) => name.startsWith("SEND__"))[1]);
    assert.equal(record.status, "sent");
    assert.equal(record.provider_message_id, "wamid.OUT==");
    assert.ok(record.reserved_at > 0 && record.finalized_at > 0);

    // D2 kayıtları credential.list'in unparsed sayacına karışmaz.
    const credentialList = await call({ operation: "credential.list", owner_lumos_id: "lumos-1" });
    assert.equal((await credentialList.json()).unparsed_records, 0);
  } finally {
    bridge.restore();
    cleanup();
  }
});

test("Health endpoint stays secret-free", () => {
  let body = "";
  const res = { setHeader() {}, statusCode: 0, end(payload) { body = payload; } };
  healthHandler({ method: "GET" }, res);
  assert.equal(res.statusCode, 200);
  assert.deepEqual(JSON.parse(body), {
    ok: true,
    service: "lumos-credential-gateway",
    schema: "lumos-credential-v2",
  });
});
