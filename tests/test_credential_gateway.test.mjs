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
