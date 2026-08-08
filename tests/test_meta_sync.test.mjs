import assert from "node:assert/strict";
import test from "node:test";

import { metaSyncRequest, syncMetaReadOnly } from "../api/_lib/meta_sync.js";
import handler from "../api/integrations/meta/sync.js";
import { sealSession } from "../api/_lib/lumos_session.js";

function configure() {
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-auth-state-secret-32-characters";
  process.env.LUMOS_META_GRAPH_VERSION = "v99.0";
  process.env.LUMOS_CREDENTIAL_VAULT_WRITE_URL = "https://vault.test/credentials";
  process.env.LUMOS_CREDENTIAL_VAULT_WRITE_TOKEN = "vault-token";
}

function cleanup() {
  for (const key of [
    "LUMOS_AUTH_STATE_SECRET",
    "LUMOS_META_GRAPH_VERSION",
    "LUMOS_CREDENTIAL_VAULT_WRITE_URL",
    "LUMOS_CREDENTIAL_VAULT_WRITE_TOKEN",
  ]) delete process.env[key];
}

function session() {
  return sealSession({ sid: "session", lumos_id: "lumos_user", exp: Math.floor(Date.now() / 1000) + 600 });
}

function response() {
  return {
    statusCode: 0,
    headers: {},
    setHeader(name, value) { this.headers[name.toLowerCase()] = value; },
    end(body) { this.body = body; },
  };
}

test("Instagram Login and Facebook Login use distinct Graph hosts", () => {
  configure();
  try {
    const direct = metaSyncRequest("instagram", { authMode: "instagram_login", providerAccountId: "ig-1" });
    const business = metaSyncRequest("instagram", { authMode: "facebook_login", providerAccountId: "ig-business-1" });
    assert.equal(new URL(direct.url).hostname, "graph.instagram.com");
    assert.equal(new URL(direct.url).pathname, "/me");
    assert.equal(new URL(business.url).hostname, "graph.facebook.com");
    assert.equal(new URL(business.url).pathname, "/v99.0/ig-business-1");
  } finally {
    cleanup();
  }
});

test("Instagram read-only sync keeps token in Authorization and normalizes identity", async () => {
  configure();
  let request;
  try {
    const result = await syncMetaReadOnly("instagram", {
      authMode: "instagram_login",
      providerAccountId: "ig-1",
      accessToken: "secret-token",
    }, async (url, init) => {
      request = { url: String(url), init };
      return { ok: true, async json() { return { id: "ig-1", username: "lumos", account_type: "BUSINESS", media_count: 12 }; } };
    });
    assert.equal(request.init.method, "GET");
    assert.equal(request.init.headers.Authorization, "Bearer secret-token");
    assert.doesNotMatch(request.url, /secret-token/);
    assert.deepEqual(result.accounts, [{ id: "ig-1", username: "lumos", account_type: "BUSINESS", media_count: 12 }]);
  } finally {
    cleanup();
  }
});

test("Facebook and WhatsApp sync normalize only account metadata", async () => {
  configure();
  try {
    const facebook = await syncMetaReadOnly("facebook", { accessToken: "token", authMode: "facebook_login" }, async () => ({
      ok: true,
      async json() { return { data: [{ id: "page-1", name: "Lumos Page", access_token: "must-not-leak" }] }; },
    }));
    assert.deepEqual(facebook.accounts, [{ id: "page-1", name: "Lumos Page" }]);

    const whatsapp = await syncMetaReadOnly("whatsapp", { accessToken: "token", authMode: "facebook_login" }, async () => ({
      ok: true,
      async json() { return { data: [{ id: "biz-1", name: "Lumos", owned_whatsapp_business_accounts: { data: [{ id: "waba-1", name: "Support" }] } }] }; },
    }));
    assert.deepEqual(whatsapp.businesses, [{ id: "biz-1", name: "Lumos" }]);
    assert.deepEqual(whatsapp.accounts, [{ id: "waba-1", name: "Support", business_id: "biz-1" }]);
    assert.doesNotMatch(JSON.stringify({ facebook, whatsapp }), /must-not-leak|access_token/);
  } finally {
    cleanup();
  }
});

test("Hosted read-only sync resolves credential server-side and never returns it", async () => {
  configure();
  const originalFetch = globalThis.fetch;
  const calls = [];
  try {
    globalThis.fetch = async (url, init = {}) => {
      calls.push({ url: String(url), init });
      if (String(url) === "https://vault.test/credentials") {
        return { ok: true, async json() { return {
          ok: true,
          vault_ref: "meta:instagram:opaque",
          provider_account_id: "ig-1",
          credential: { access_token: "secret-token", token_type: "bearer", expires_at: 100, auth_mode: "instagram_login" },
        }; } };
      }
      return { ok: true, async json() { return { id: "ig-1", username: "lumos", media_count: 3 }; } };
    };
    const res = response();
    await handler({
      method: "POST",
      url: "/api/integrations/meta/sync",
      headers: { cookie: `lumos_session=${session()}`, origin: "https://welockai.com", host: "welockai.com" },
      body: { provider: "instagram" },
    }, res);
    assert.equal(res.statusCode, 200);
    assert.equal(JSON.parse(res.body).status, "synced");
    assert.doesNotMatch(res.body, /secret-token|vault_ref|opaque/);
    assert.equal(calls[1].init.method, "GET");
  } finally {
    globalThis.fetch = originalFetch;
    cleanup();
  }
});

test("Hosted sync rejects cross-site mutation before vault resolution", async () => {
  configure();
  const originalFetch = globalThis.fetch;
  let fetched = false;
  try {
    globalThis.fetch = async () => { fetched = true; throw new Error("unexpected_fetch"); };
    const res = response();
    await handler({
      method: "POST",
      headers: { cookie: `lumos_session=${session()}`, origin: "https://attacker.test", host: "welockai.com" },
      body: { provider: "facebook" },
    }, res);
    assert.equal(res.statusCode, 403);
    assert.equal(fetched, false);
  } finally {
    globalThis.fetch = originalFetch;
    cleanup();
  }
});
