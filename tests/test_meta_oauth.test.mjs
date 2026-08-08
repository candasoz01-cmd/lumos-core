import assert from "node:assert/strict";
import test from "node:test";

import {
  buildMetaAuthorizeUrl,
  extendMetaToken,
  metaProviderConfig,
  metaVaultRef,
  refreshMetaToken,
  revokeMetaToken,
} from "../api/_lib/meta_oauth.js";
import { writeMetaCredential } from "../api/_lib/meta_vault.js";
import callbackHandler from "../api/auth/meta/callback.js";
import startHandler, { META_FLOW_COOKIE } from "../api/auth/meta/start.js";
import tokenHandler from "../api/integrations/meta/token.js";
import {
  makeState,
  openSession,
  sealSession,
} from "../api/_lib/lumos_session.js";

function response() {
  return {
    statusCode: 0,
    headers: {},
    setHeader(name, value) { this.headers[name.toLowerCase()] = value; },
    end(body) { this.body = body; },
  };
}

function env() {
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-auth-state-secret-32-characters";
  process.env.LUMOS_META_GRAPH_VERSION = "v99.0";
  process.env.LUMOS_META_APP_ID = "meta-app-id";
  process.env.LUMOS_META_APP_SECRET = "meta-app-secret";
  process.env.LUMOS_INSTAGRAM_APP_ID = "instagram-app-id";
  process.env.LUMOS_INSTAGRAM_APP_SECRET = "instagram-app-secret";
  process.env.LUMOS_WHATSAPP_LOGIN_CONFIG_ID = "whatsapp-config-id";
  process.env.LUMOS_CREDENTIAL_VAULT_WRITE_URL = "https://vault.test/credentials";
  process.env.LUMOS_CREDENTIAL_VAULT_WRITE_TOKEN = "vault-write-token";
}

function cleanEnv() {
  for (const key of [
    "LUMOS_AUTH_STATE_SECRET",
    "LUMOS_META_GRAPH_VERSION",
    "LUMOS_META_APP_ID",
    "LUMOS_META_APP_SECRET",
    "LUMOS_INSTAGRAM_APP_ID",
    "LUMOS_INSTAGRAM_APP_SECRET",
    "LUMOS_WHATSAPP_LOGIN_CONFIG_ID",
    "LUMOS_CREDENTIAL_VAULT_WRITE_URL",
    "LUMOS_CREDENTIAL_VAULT_WRITE_TOKEN",
  ]) delete process.env[key];
}

function lumosSession() {
  return sealSession({
    sid: "session-1",
    lumos_id: "lumos_test_user",
    provider: "google_web",
    sub: "google-subject",
    exp: Math.floor(Date.now() / 1000) + 600,
  });
}

function cookieValue(setCookie) {
  return String(setCookie).split(";", 1)[0].split("=").slice(1).join("=");
}

test("Meta OAuth uses provider-specific read-only authorization surfaces", () => {
  env();
  try {
    const facebook = new URL(buildMetaAuthorizeUrl("facebook", "signed-state"));
    assert.equal(facebook.hostname, "www.facebook.com");
    assert.equal(facebook.searchParams.get("scope"), "pages_show_list,pages_read_engagement");
    const whatsapp = new URL(buildMetaAuthorizeUrl("whatsapp", "signed-state"));
    assert.equal(whatsapp.searchParams.get("config_id"), "whatsapp-config-id");
    assert.equal(whatsapp.searchParams.get("scope"), "business_management,whatsapp_business_management");
    assert.doesNotMatch(whatsapp.searchParams.get("scope"), /messaging/);
    const instagram = new URL(buildMetaAuthorizeUrl("instagram", "signed-state"));
    assert.equal(instagram.hostname, "www.instagram.com");
    assert.equal(instagram.searchParams.get("scope"), "instagram_business_basic");
    assert.equal(metaProviderConfig("instagram").identityUrl, "https://graph.instagram.com/me?fields=id,username");
  } finally {
    cleanEnv();
  }
});

test("Meta OAuth start requires an authenticated Lumos session", async () => {
  env();
  try {
    const res = response();
    await startHandler({ method: "GET", url: "/api/auth/meta/start?provider=facebook", headers: {} }, res);
    assert.equal(res.statusCode, 302);
    assert.equal(res.headers.location, "/integrations/meta?meta_error=lumos_session_required");
  } finally {
    cleanEnv();
  }
});

test("Meta OAuth start fails closed before authorization when vault is unavailable", async () => {
  env();
  delete process.env.LUMOS_CREDENTIAL_VAULT_WRITE_TOKEN;
  try {
    const res = response();
    await startHandler({
      method: "GET",
      url: "/api/auth/meta/start?provider=facebook",
      headers: { cookie: `lumos_session=${lumosSession()}` },
    }, res);
    assert.equal(res.statusCode, 302);
    assert.equal(res.headers.location, "/integrations/meta?meta_error=meta_vault_not_configured");
    assert.equal(res.headers["set-cookie"], undefined);
  } finally {
    cleanEnv();
  }
});

test("Meta OAuth start binds provider, state and Lumos identity in an HttpOnly cookie", async () => {
  env();
  try {
    const res = response();
    await startHandler({
      method: "GET",
      url: "/api/auth/meta/start?provider=instagram",
      headers: { cookie: `lumos_session=${lumosSession()}` },
    }, res);
    assert.equal(res.statusCode, 302);
    assert.match(res.headers["set-cookie"], /HttpOnly; Secure; SameSite=Lax/);
    const flow = openSession(cookieValue(res.headers["set-cookie"]));
    assert.equal(flow.kind, "meta_oauth");
    assert.equal(flow.provider, "instagram");
    assert.equal(flow.lumos_id, "lumos_test_user");
    assert.equal(new URL(res.headers.location).searchParams.get("state"), flow.state);
  } finally {
    cleanEnv();
  }
});

test("Vault writer sends credential only to the configured private bridge", async () => {
  env();
  let request;
  try {
    const result = await writeMetaCredential({
      vaultRef: "meta:facebook:opaque",
      purposeCode: "integration.meta.facebook.read",
      provider: "facebook",
      lumosId: "lumos_test_user",
      providerAccountId: "account-1",
      accessToken: "raw-access-token",
      tokenType: "bearer",
      expiresAt: 1234,
    }, async (url, init) => {
      request = { url, init, body: JSON.parse(init.body) };
      return { ok: true, async json() { return { ok: true, vault_ref: "meta:facebook:opaque" }; } };
    });
    assert.deepEqual(result, { vaultRef: "meta:facebook:opaque" });
    assert.equal(request.url, "https://vault.test/credentials");
    assert.equal(request.init.headers.Authorization, "Bearer vault-write-token");
    assert.equal(request.body.credential.access_token, "raw-access-token");
  } finally {
    cleanEnv();
  }
});

test("Meta callback rejects a flow whose state is not bound to the cookie", async () => {
  env();
  try {
    const state = makeState();
    const flow = sealSession({
      kind: "meta_oauth",
      provider: "facebook",
      state,
      lumos_id: "lumos_test_user",
      exp: Math.floor(Date.now() / 1000) + 600,
    });
    const res = response();
    await callbackHandler({
      method: "GET",
      url: `/api/auth/meta/callback?code=code&state=${encodeURIComponent(makeState())}`,
      headers: { cookie: `lumos_session=${lumosSession()}; ${META_FLOW_COOKIE}=${flow}` },
    }, res);
    assert.equal(res.statusCode, 302);
    assert.match(res.headers.location, /meta_error=invalid_state/);
  } finally {
    cleanEnv();
  }
});

test("Meta callback exchanges server-side, resolves identity and stores an opaque vault ref", async () => {
  env();
  const originalFetch = globalThis.fetch;
  const seen = [];
  try {
    const state = makeState();
    const flow = sealSession({
      kind: "meta_oauth",
      provider: "facebook",
      state,
      lumos_id: "lumos_test_user",
      exp: Math.floor(Date.now() / 1000) + 600,
    });
    globalThis.fetch = async (url, init = {}) => {
      seen.push({ url: String(url), init });
      if (String(url).includes("oauth/access_token")) {
        return { ok: true, async json() { return { access_token: "raw-access-token", token_type: "bearer", expires_in: 3600 }; } };
      }
      if (String(url).includes("/me?fields=")) {
        return { ok: true, async json() { return { id: "meta-account-1", name: "Page Owner" }; } };
      }
      const body = JSON.parse(init.body);
      return { ok: true, async json() { return { ok: true, vault_ref: body.vault_ref }; } };
    };
    const res = response();
    await callbackHandler({
      method: "GET",
      url: `/api/auth/meta/callback?code=one-time-code&state=${encodeURIComponent(state)}`,
      headers: { cookie: `lumos_session=${lumosSession()}; ${META_FLOW_COOKIE}=${flow}` },
    }, res);
    assert.equal(res.statusCode, 302);
    assert.equal(res.headers.location, "/integrations/meta?provider=facebook&meta_status=authorized");
    assert.doesNotMatch(res.headers.location, /raw-access-token|meta-account-1/);
    const vaultRequest = seen.find((item) => item.url === "https://vault.test/credentials");
    const vaultBody = JSON.parse(vaultRequest.init.body);
    assert.equal(vaultBody.credential.access_token, "raw-access-token");
    assert.equal(vaultBody.vault_ref, metaVaultRef("lumos_test_user", "facebook", "meta-account-1"));
  } finally {
    globalThis.fetch = originalFetch;
    cleanEnv();
  }
});

test("Meta token extension uses the provider-specific long-lived exchange", async () => {
  env();
  const seen = [];
  try {
    const facebook = await extendMetaToken("facebook", "short-facebook", async (url) => {
      seen.push(String(url));
      return { ok: true, async json() { return { access_token: "long-facebook", expires_in: 5000 }; } };
    });
    const instagram = await extendMetaToken("instagram", "short-instagram", async (url) => {
      seen.push(String(url));
      return { ok: true, async json() { return { access_token: "long-instagram", expires_in: 6000 }; } };
    });
    assert.equal(facebook.accessToken, "long-facebook");
    assert.equal(instagram.accessToken, "long-instagram");
    assert.match(seen[0], /fb_exchange_token=short-facebook/);
    assert.match(seen[1], /graph\.instagram\.com\/access_token/);
    assert.match(seen[1], /ig_exchange_token/);
  } finally {
    cleanEnv();
  }
});

test("Instagram refresh and Meta revoke stay server-side", async () => {
  env();
  const seen = [];
  try {
    const refreshed = await refreshMetaToken("instagram", "long-instagram", async (url, init = {}) => {
      seen.push({ url: String(url), init });
      return { ok: true, async json() { return { access_token: "new-instagram", expires_in: 7000 }; } };
    }, "instagram_login");
    const revoked = await revokeMetaToken("instagram", "new-instagram", async (url, init = {}) => {
      seen.push({ url: String(url), init });
      return { ok: true, async json() { return { success: true }; } };
    }, "instagram_login");
    assert.equal(refreshed.accessToken, "new-instagram");
    assert.deepEqual(revoked, { revoked: true });
    assert.match(seen[0].url, /refresh_access_token/);
    assert.equal(seen[1].init.method, "DELETE");
    assert.equal(seen[1].init.headers.Authorization, "Bearer new-instagram");
  } finally {
    cleanEnv();
  }
});

test("Meta revoke accepts the Graph API bare boolean success response", async () => {
  env();
  try {
    const revoked = await revokeMetaToken("facebook", "facebook-token", async () => ({
      ok: true,
      async json() { return true; },
    }));
    assert.deepEqual(revoked, { revoked: true });
  } finally {
    cleanEnv();
  }
});

test("Instagram Facebook Login lifecycle stays on Facebook Graph", async () => {
  env();
  const seen = [];
  try {
    await refreshMetaToken("instagram", "facebook-token", async (url) => {
      seen.push(String(url));
      return { ok: true, async json() { return { access_token: "extended-facebook", expires_in: 3600 }; } };
    }, "facebook_login");
    await revokeMetaToken("instagram", "extended-facebook", async (url) => {
      seen.push(String(url));
      return { ok: true, async json() { return true; } };
    }, "facebook_login");
    assert.equal(new URL(seen[0]).hostname, "graph.facebook.com");
    assert.equal(new URL(seen[1]).hostname, "graph.facebook.com");
  } finally {
    cleanEnv();
  }
});

test("Token metadata returns expiry without resolving or exposing the credential", async () => {
  env();
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async (_url, init) => {
      const body = JSON.parse(init.body);
      assert.equal(body.operation, "credential.metadata");
      return { ok: true, async json() { return { ok: true, configured: true, vault_ref: "opaque", expires_at: 9999 }; } };
    };
    const res = response();
    await tokenHandler({
      method: "GET",
      url: "/api/integrations/meta/token?provider=facebook",
      headers: { cookie: `lumos_session=${lumosSession()}` },
    }, res);
    assert.equal(res.statusCode, 200);
    assert.deepEqual(JSON.parse(res.body), {
      ok: true,
      provider: "facebook",
      status: "authorized",
      expires_at: 9999,
      renewable: true,
    });
    assert.doesNotMatch(res.body, /token|vault_ref|opaque/i);
  } finally {
    globalThis.fetch = originalFetch;
    cleanEnv();
  }
});

test("Token refresh resolves inside the vault boundary and stores only the rotated token", async () => {
  env();
  const originalFetch = globalThis.fetch;
  const operations = [];
  try {
    globalThis.fetch = async (url, init = {}) => {
      if (String(url) === "https://vault.test/credentials") {
        const body = JSON.parse(init.body);
        operations.push(body);
        if (body.operation === "credential.metadata") {
          return { ok: true, async json() { return {
            ok: true,
            configured: true,
            vault_ref: "meta:instagram:opaque",
            expires_at: 100,
          }; } };
        }
        if (body.operation === "credential.resolve") {
          return { ok: true, async json() { return {
            ok: true,
            vault_ref: "meta:instagram:opaque",
            provider_account_id: "ig-account",
            credential: { access_token: "old-token", token_type: "bearer", expires_at: 100, auth_mode: "instagram_login" },
          }; } };
        }
        return { ok: true, async json() { return { ok: true, vault_ref: body.vault_ref }; } };
      }
      return { ok: true, async json() { return { access_token: "rotated-token", expires_in: 3600 }; } };
    };
    const res = response();
    await tokenHandler({
      method: "POST",
      url: "/api/integrations/meta/token",
      headers: { cookie: `lumos_session=${lumosSession()}`, origin: "https://welockai.com", host: "welockai.com" },
      body: { action: "refresh", provider: "instagram" },
    }, res);
    assert.equal(res.statusCode, 200);
    assert.equal(JSON.parse(res.body).status, "refreshed");
    assert.doesNotMatch(res.body, /old-token|rotated-token/);
    assert.deepEqual(operations.map((item) => item.operation), ["credential.metadata", "credential.resolve", "credential.upsert"]);
    assert.equal(operations[2].credential.access_token, "rotated-token");
  } finally {
    globalThis.fetch = originalFetch;
    cleanEnv();
  }
});

test("Non-expiring token refresh reads metadata without resolving the secret", async () => {
  env();
  const originalFetch = globalThis.fetch;
  let operation = "";
  try {
    globalThis.fetch = async (_url, init) => {
      operation = JSON.parse(init.body).operation;
      return { ok: true, async json() { return {
        ok: true,
        configured: true,
        vault_ref: "meta:whatsapp:opaque",
        expires_at: 0,
      }; } };
    };
    const res = response();
    await tokenHandler({
      method: "POST",
      url: "/api/integrations/meta/token",
      headers: { cookie: `lumos_session=${lumosSession()}`, origin: "https://welockai.com", host: "welockai.com" },
      body: { action: "refresh", provider: "whatsapp" },
    }, res);
    assert.equal(res.statusCode, 200);
    assert.equal(JSON.parse(res.body).status, "non_expiring");
    assert.equal(operation, "credential.metadata");
  } finally {
    globalThis.fetch = originalFetch;
    cleanEnv();
  }
});

test("Revoke deletes the local vault credential even when Meta revoke fails", async () => {
  env();
  const originalFetch = globalThis.fetch;
  const operations = [];
  try {
    globalThis.fetch = async (url, init = {}) => {
      if (String(url) === "https://vault.test/credentials") {
        const body = JSON.parse(init.body);
        operations.push(body.operation);
        if (body.operation === "credential.resolve") {
          return { ok: true, async json() { return {
            ok: true,
            vault_ref: "meta:facebook:opaque",
            provider_account_id: "fb-account",
            credential: { access_token: "revoked-token", token_type: "bearer", expires_at: 100 },
          }; } };
        }
        return { ok: true, async json() { return { ok: true, vault_ref: "meta:facebook:opaque" }; } };
      }
      return { ok: false, async json() { return {}; } };
    };
    const res = response();
    await tokenHandler({
      method: "POST",
      url: "/api/integrations/meta/token",
      headers: { cookie: `lumos_session=${lumosSession()}`, origin: "https://welockai.com", host: "welockai.com" },
      body: { action: "revoke", provider: "facebook" },
    }, res);
    assert.equal(res.statusCode, 502);
    assert.deepEqual(JSON.parse(res.body), {
      ok: false,
      provider: "facebook",
      status: "revoked_local",
      upstream_revoked: false,
    });
    assert.deepEqual(operations, ["credential.resolve", "credential.delete"]);
    assert.doesNotMatch(res.body, /revoked-token/);
  } finally {
    globalThis.fetch = originalFetch;
    cleanEnv();
  }
});

test("Token mutation rejects a cross-site request before vault access", async () => {
  env();
  const originalFetch = globalThis.fetch;
  let fetched = false;
  try {
    globalThis.fetch = async () => {
      fetched = true;
      throw new Error("unexpected_fetch");
    };
    const res = response();
    await tokenHandler({
      method: "POST",
      url: "/api/integrations/meta/token",
      headers: { cookie: `lumos_session=${lumosSession()}`, origin: "https://attacker.test", host: "welockai.com" },
      body: { action: "revoke", provider: "facebook" },
    }, res);
    assert.equal(res.statusCode, 403);
    assert.equal(JSON.parse(res.body).error, "same_origin_required");
    assert.equal(fetched, false);
  } finally {
    globalThis.fetch = originalFetch;
    cleanEnv();
  }
});
