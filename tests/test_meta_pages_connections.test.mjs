import assert from "node:assert/strict";
import test from "node:test";

import handler from "../api/integrations/meta/pages/connections.js";
import { pagesConnectionId } from "../api/_lib/meta_connections.js";
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

function ok(body) {
  return { ok: true, async json() { return body; } };
}

function stubFetch({ pages, graphFails = false, storedConnections = [] }) {
  const upserts = [];
  const fetchImpl = async (url, options = {}) => {
    const target = String(url);
    if (target.startsWith("https://vault.test/credentials")) {
      const body = JSON.parse(options.body);
      if (body.operation === "credential.list") {
        return ok({
          ok: true,
          credentials: [{
            vault_ref: "meta:pages:ref-1",
            provider: "pages",
            provider_account_id: "fb-user-1",
            expires_at: 0,
            auth_mode: "facebook_login",
          }],
        });
      }
      if (body.operation === "credential.resolve") {
        return ok({
          ok: true,
          vault_ref: "meta:pages:ref-1",
          provider: "pages",
          provider_account_id: "fb-user-1",
          credential: { access_token: "secret-pages-token", token_type: "bearer", expires_at: 0, auth_mode: "facebook_login" },
        });
      }
      if (body.operation === "connection.upsert") {
        upserts.push(body);
        return ok({ ok: true, connection_id: body.connection_id });
      }
      if (body.operation === "connection.list") return ok({ ok: true, connections: storedConnections });
      return ok({ ok: false });
    }
    if (graphFails) return { ok: false, status: 500, async json() { return {}; } };
    if (target.includes("me/accounts")) return ok({ data: pages });
    return { ok: false, status: 404, async json() { return {}; } };
  };
  fetchImpl.upserts = upserts;
  return fetchImpl;
}

test("Each managed Page becomes a permanent connection row and persists last_verified_at", async () => {
  configure();
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = stubFetch({
      pages: [{ id: "page-1", name: "We Lock AI - ChatLumos" }],
    });
    const res = response();
    await handler(sessionRequest(), res);
    assert.equal(res.statusCode, 200);
    const payload = JSON.parse(res.body);
    assert.equal(payload.connections.length, 1);
    const row = payload.connections[0];
    assert.equal(row.page_id, "page-1");
    assert.equal(row.page_name, "We Lock AI - ChatLumos");
    assert.equal(row.status, "verified");
    assert.deepEqual(row.requested_scopes, ["pages_show_list"]);
    assert.equal(row.connection_id, pagesConnectionId("lumos-1", "page-1"));
    assert.ok(Number(row.last_verified_at) > 0);
    assert.equal(globalThis.fetch.upserts.length, 1);
    assert.equal(globalThis.fetch.upserts[0].credential_ref, "meta:pages:ref-1");
    assert.ok(!res.body.includes("secret-pages-token"));
    assert.ok(!res.body.includes("meta:pages:ref-1"));
  } finally {
    globalThis.fetch = originalFetch;
    cleanup();
  }
});

test("Empty Page list reports a gap instead of fabricating rows", async () => {
  configure();
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = stubFetch({ pages: [] });
    const res = response();
    await handler(sessionRequest(), res);
    assert.equal(res.statusCode, 200);
    const payload = JSON.parse(res.body);
    assert.deepEqual(payload.connections, []);
    assert.equal(payload.gaps[0].reason, "pages_empty");
  } finally {
    globalThis.fetch = originalFetch;
    cleanup();
  }
});

test("Graph outage serves stored rows as unverified or 502 when store is empty", async () => {
  configure();
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = stubFetch({
      pages: [],
      graphFails: true,
      storedConnections: [{
        connection_id: "conn_page_stored1",
        provider: "pages",
        page_id: "page-1",
        page_name: "We Lock AI - ChatLumos",
        last_verified_at: 1700000000,
      }],
    });
    const res = response();
    await handler(sessionRequest(), res);
    assert.equal(res.statusCode, 200);
    const payload = JSON.parse(res.body);
    assert.equal(payload.mode, "stored_last_known");
    assert.equal(payload.connections[0].status, "unverified");
    assert.equal(payload.connections[0].last_verified_at, 1700000000);

    globalThis.fetch = stubFetch({ pages: [], graphFails: true });
    const outage = response();
    await handler(sessionRequest(), outage);
    assert.equal(outage.statusCode, 502);
    assert.equal(JSON.parse(outage.body).error, "pages_enumeration_unavailable");
  } finally {
    globalThis.fetch = originalFetch;
    cleanup();
  }
});
