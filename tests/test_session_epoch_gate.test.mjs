/**
 * #904 HIGH bulgusu: çıkıştan sonra kopyalanmış eski çerez veya Bearer, ortak
 * `hostedSessionClaims()` yolunu kullanan hiçbir yüzeyde geçerli kalmamalı.
 * Her yüzey için aynı desen: çıkıştan ÖNCE çalışır (kontrol), çıkıştan SONRA 401
 * döner ve ilgili dış çağrı (hafıza servisi, OpenAI, köprü) hiç yapılmaz.
 */
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import logoutHandler from "../api/auth/logout.js";
import bridgeHealth from "../api/bridge/health.js";
import bridgeProxy from "../api/bridge/[...path].js";
import bridgeStatus from "../api/bridge/status.js";
import memoryHandler from "../api/mobile/memory.js";
import realtimeHandler from "../api/mobile/realtime-token.js";
import workspaceHub from "../api/mobile/workspace-hub.js";
import {
  hasLumosSession,
  hostedSessionClaims,
  hostedSessionRevoked,
  loadHostedUserContext,
} from "../api/_lib/hosted_lumos.js";
import { sealSession } from "../api/_lib/lumos_session.js";
import { currentEpoch } from "../api/_lib/session_epoch.js";

const epochDir = mkdtempSync(path.join(tmpdir(), "lumos-epoch-gate-"));
process.env.LUMOS_SESSION_EPOCH_PATH = path.join(epochDir, "epoch.json");
process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";

let counter = 0;
function newId() {
  counter += 1;
  return `lumos_epoch_gate_${counter}`;
}

function claims(lumosId, overrides = {}) {
  return {
    sid: `sid-${lumosId}`,
    lumos_id: lumosId,
    sub: `google-${lumosId}`,
    provider: "google_web",
    name: "Ada Lovelace",
    email: "ada@example.test",
    package: "base",
    sv: currentEpoch(lumosId),
    exp: Math.floor(Date.now() / 1000) + 3600,
    ...overrides,
  };
}

/** Çıkıştan önce alınmış, "kopyalanabilir" tek mühürlü belirteç. */
function login(lumosId = newId()) {
  return { lumosId, sealed: sealSession(claims(lumosId)) };
}

const asCookie = (sealed, extra = {}) => ({
  method: "GET",
  headers: { cookie: `lumos_session=${sealed}` },
  ...extra,
});
const asBearer = (sealed, extra = {}) => ({
  method: "GET",
  headers: { authorization: `Bearer ${sealed}` },
  ...extra,
});

function makeRes() {
  return {
    statusCode: 0,
    headers: {},
    body: "",
    payload: undefined,
    status(code) {
      this.statusCode = code;
      return this;
    },
    setHeader(key, value) {
      this.headers[key.toLowerCase()] = value;
    },
    json(payload) {
      this.payload = payload;
      return this;
    },
    send(payload) {
      this.body = payload;
      return this;
    },
    end(payload) {
      this.body = payload;
      return this;
    },
  };
}

async function logoutWith(req) {
  const res = makeRes();
  await logoutHandler({ ...req, method: "POST" }, res);
  assert.equal(res.statusCode, 200);
  return res;
}

async function withEnv(vars, fn) {
  const saved = {};
  for (const [key, value] of Object.entries(vars)) {
    saved[key] = process.env[key];
    process.env[key] = value;
  }
  try {
    return await fn();
  } finally {
    for (const [key, value] of Object.entries(saved)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
}

async function withFetch(impl, fn) {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(url), init });
    return impl(String(url), init);
  };
  try {
    return await fn(calls);
  } finally {
    globalThis.fetch = original;
  }
}

const jsonResponse = (payload) => ({
  ok: true,
  status: 200,
  async json() {
    return payload;
  },
});

// ---------------------------------------------------------------- ortak kapı

test("shared gate rejects a copied cookie and a copied Bearer after logout", async () => {
  const { sealed } = login();
  assert.ok(hostedSessionClaims(asCookie(sealed)), "cookie works before logout");
  assert.ok(hostedSessionClaims(asBearer(sealed)), "Bearer works before logout");
  assert.equal(hasLumosSession(asCookie(sealed)), true);

  await logoutWith(asCookie(sealed));

  assert.equal(hostedSessionClaims(asCookie(sealed)), null);
  assert.equal(hostedSessionClaims(asBearer(sealed)), null);
  assert.equal(hostedSessionRevoked(asCookie(sealed)), true);
  assert.equal(hostedSessionRevoked(asBearer(sealed)), true);
  assert.equal(hasLumosSession(asCookie(sealed)), false);
  assert.equal(hasLumosSession(asBearer(sealed)), false);
});

test("logout with a Bearer token alone revokes the Bearer and the copied cookie", async () => {
  const { sealed, lumosId } = login();
  assert.equal(currentEpoch(lumosId), 0);

  await logoutWith(asBearer(sealed));

  assert.equal(currentEpoch(lumosId), 1, "Bearer logout must bump the epoch");
  assert.equal(hostedSessionClaims(asBearer(sealed)), null);
  assert.equal(hostedSessionClaims(asCookie(sealed)), null);
});

test("a revoked token cannot bump the epoch again; a new login stays valid", async () => {
  const { sealed, lumosId } = login();
  await logoutWith(asCookie(sealed));
  assert.equal(currentEpoch(lumosId), 1);

  const fresh = sealSession(claims(lumosId)); // yeni giriş: sv = güncel sürüm
  assert.ok(hostedSessionClaims(asCookie(fresh)), "new login is accepted");

  // Kopyalanmış eski belirteç çıkış çağırsa bile sürümü artıramaz ve yeni oturumu düşüremez.
  await logoutWith(asCookie(sealed));
  await logoutWith(asBearer(sealed));
  assert.equal(currentEpoch(lumosId), 1);
  assert.ok(hostedSessionClaims(asCookie(fresh)), "new login survives a stale logout");
  assert.ok(hostedSessionClaims(asBearer(fresh)), "new Bearer survives a stale logout");
});

test("chat context reports session_revoked for a copied Bearer, unauthorized without a token", async () => {
  const { sealed } = login();
  await logoutWith(asCookie(sealed));

  const revoked = await loadHostedUserContext(asBearer(sealed), {});
  assert.deepEqual(
    { ok: revoked.ok, error: revoked.error, status: revoked.status },
    { ok: false, error: "session_revoked", status: 401 },
  );
  const none = await loadHostedUserContext({ method: "POST", headers: {} }, {});
  assert.equal(none.error, "unauthorized");
});

// ------------------------------------------------------------ memory grant/delete

const MEMORY_ENV = {
  LUMOS_MEMORY_LOOKUP_URL: "https://memory.test/memory/hosted/lookup",
  LUMOS_MEMORY_SERVICE_TOKEN: "memory-service-test-token",
};

function memoryService(url) {
  if (url.endsWith("/lookup")) return jsonResponse({ consent: true, memories: ["a"] });
  if (url.endsWith("/consent")) return jsonResponse({ consent: true });
  if (url.endsWith("/delete")) return jsonResponse({ ok: true, consent: false, deleted: 2 });
  return jsonResponse({});
}

const memoryCalls = (calls) => calls.filter((call) => call.url.startsWith("https://memory.test"));

test("memory read, grant and delete stop working for copied cookie and Bearer after logout", async () => {
  await withEnv(MEMORY_ENV, () =>
    withFetch(memoryService, async (calls) => {
      const { sealed } = login();
      const post = (body, make) => make(sealed, { method: "POST", body });

      for (const make of [asCookie, asBearer]) {
        const read = makeRes();
        await memoryHandler(make(sealed), read);
        assert.equal(read.statusCode, 200);
        const grant = makeRes();
        await memoryHandler(post({ action: "grant", consent: true }, make), grant);
        assert.equal(grant.statusCode, 200);
        const del = makeRes();
        await memoryHandler(post({ action: "delete", confirm: true }, make), del);
        assert.equal(del.statusCode, 200);
        assert.equal(del.payload.deleted, 2);
      }
      const callsBefore = memoryCalls(calls).length;
      assert.ok(callsBefore >= 6, "control: memory service was used before logout");

      await logoutWith(asCookie(sealed));

      for (const make of [asCookie, asBearer]) {
        for (const req of [
          make(sealed),
          post({ action: "grant", consent: true }, make),
          post({ action: "delete", confirm: true }, make),
        ]) {
          const res = makeRes();
          await memoryHandler(req, res);
          assert.equal(res.statusCode, 401, `${req.method} ${req.body?.action || "read"}`);
          assert.equal(res.payload.error, "unauthorized");
        }
      }
      assert.equal(memoryCalls(calls).length, callsBefore, "no memory service call after logout");
    }),
  );
});

// ---------------------------------------------------------------- realtime token

test("realtime client secret is not minted for a copied cookie or Bearer after logout", async () => {
  await withEnv({ OPENAI_API_KEY: "private-openai-test-key" }, () =>
    withFetch(
      () => jsonResponse({ value: "rt-client-secret", expires_at: 123 }),
      async (calls) => {
        const { sealed } = login();
        const realtimeCalls = () => calls.filter((c) => c.url.includes("/realtime/client_secrets"));

        const ok = makeRes();
        await realtimeHandler(asCookie(sealed, { method: "POST", body: {} }), ok);
        assert.equal(ok.statusCode, 200);
        assert.equal(ok.payload.client_secret.value, "rt-client-secret");
        assert.equal(realtimeCalls().length, 1, "control: secret minted before logout");

        await logoutWith(asCookie(sealed));

        for (const make of [asCookie, asBearer]) {
          const res = makeRes();
          await realtimeHandler(make(sealed, { method: "POST", body: {} }), res);
          assert.equal(res.statusCode, 401);
          assert.equal(res.payload.error, "unauthorized");
        }
        assert.equal(realtimeCalls().length, 1, "no provider call after logout");
      },
    ),
  );
});

// ------------------------------------------------------------------ workspace hub

test("workspace hub rejects a copied cookie and Bearer after logout", async () => {
  const { sealed } = login();
  for (const make of [asCookie, asBearer]) {
    const res = makeRes();
    await workspaceHub(make(sealed), res);
    assert.equal(res.statusCode, 200, "control: hub works before logout");
  }

  await logoutWith(asBearer(sealed));

  for (const make of [asCookie, asBearer]) {
    const res = makeRes();
    await workspaceHub(make(sealed), res);
    assert.equal(res.statusCode, 401);
    assert.equal(res.payload.error, "unauthorized");
  }
});

// ----------------------------------------------------------------- bridge proxy

const BRIDGE_TOKEN = "bridge-proxy-test-token";

function bridgeEnv(lumosId) {
  return {
    BRIDGE_UPSTREAM_URL: "https://bridge.test",
    LUMOS_BRIDGE_PROXY_AUTH_TOKEN: BRIDGE_TOKEN,
    KANDO_BRIDGE_SECRET: "bridge-secret-test",
    LUMOS_BRIDGE_ALLOWED_LUMOS_IDS: lumosId,
  };
}

const bridgeUpstream = () => ({
  status: 200,
  headers: new Headers({ "content-type": "application/json" }),
  async arrayBuffer() {
    return new TextEncoder().encode('{"ok":true}').buffer;
  },
});

const bridgeReq = (headers) => ({
  method: "GET",
  headers,
  query: { path: ["status"] },
  url: "/api/bridge/status",
});

test("bridge proxy does not forward for a copied cookie or Bearer after logout", async () => {
  const { sealed, lumosId } = login();
  await withEnv(bridgeEnv(lumosId), () =>
    withFetch(bridgeUpstream, async (calls) => {
      const upstream = () => calls.filter((c) => c.url.startsWith("https://bridge.test"));

      for (const headers of [
        { cookie: `lumos_session=${sealed}` },
        { authorization: `Bearer ${sealed}` },
      ]) {
        const res = makeRes();
        await bridgeProxy(bridgeReq(headers), res);
        assert.equal(res.statusCode, 200, "control: allowlisted session proxies before logout");
      }
      const forwarded = upstream().length;
      assert.equal(forwarded, 2);

      await logoutWith(asCookie(sealed));

      for (const headers of [
        { cookie: `lumos_session=${sealed}` },
        { authorization: `Bearer ${sealed}` },
      ]) {
        const res = makeRes();
        await bridgeProxy(bridgeReq(headers), res);
        assert.equal(res.statusCode, 401);
        assert.equal(res.payload.error, "bridge_proxy_unauthorized");
      }
      assert.equal(upstream().length, forwarded, "no upstream call after logout");

      // Köprü proxy belirteci ayrı bir kimlik doğrulama yoludur; oturum epoch'undan etkilenmez.
      const viaProxyToken = makeRes();
      await bridgeProxy(bridgeReq({ "x-lumos-bridge-auth": BRIDGE_TOKEN }), viaProxyToken);
      assert.equal(viaProxyToken.statusCode, 200);
    }),
  );
});

test("bridge health and status reject a copied cookie and Bearer after logout", async () => {
  await withEnv({ OPENAI_API_KEY: "private-openai-test-key" }, async () => {
    const { sealed } = login();
    const health = makeRes();
    await bridgeHealth(asCookie(sealed), health);
    assert.equal(health.statusCode, 200, "control: health works before logout");

    await logoutWith(asCookie(sealed));

    for (const handler of [bridgeHealth, bridgeStatus]) {
      for (const make of [asCookie, asBearer]) {
        const res = makeRes();
        await handler(make(sealed), res);
        assert.equal(res.statusCode, 401);
        assert.equal(res.payload.error, "unauthorized");
      }
    }
  });
});
