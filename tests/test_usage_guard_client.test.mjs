import assert from "node:assert/strict";
import test from "node:test";

import chatHandler from "../api/bridge/chat.js";
import mobileChatHandler from "../api/mobile/chat.js";
import realtimeHandler from "../api/mobile/realtime-token.js";
import { consumeHostedAiQuota, signUsageRequest, usageGuard } from "../api/_lib/usage_guard.js";
import { openSession, sealSession, sessionLumosId } from "../api/_lib/lumos_session.js";

const SECRET = "test-only-usage-guard-secret-32-characters";
const GUARD_ENV = { LUMOS_USAGE_GUARD_URL: "https://usage.example", LUMOS_USAGE_GUARD_SECRET: SECRET };

function reply(status, payload) {
  return { status, ok: status >= 200 && status < 300, json: async () => payload };
}

test("unconfigured guard fails closed without any network call", async () => {
  let calls = 0;
  const fetchImpl = async () => {
    calls += 1;
    return reply(200, { allowed: true });
  };
  for (const env of [{}, { LUMOS_USAGE_GUARD_URL: "https://usage.example" }, { ...GUARD_ENV, LUMOS_USAGE_GUARD_SECRET: "short" }, { ...GUARD_ENV, LUMOS_USAGE_GUARD_URL: "http://usage.example" }]) {
    const r = await consumeHostedAiQuota("lumos_x", "chat", { env, fetchImpl });
    assert.deepEqual(r, { ok: false, status: 503, error: "usage_guard_unconfigured" });
  }
  assert.equal(calls, 0);
});

test("client signs the request the way the Worker verifies it", async () => {
  let seen;
  const fetchImpl = async (url, init) => {
    seen = { url, init };
    return reply(200, { allowed: true });
  };
  const r = await consumeHostedAiQuota("lumos_x", "chat", { env: GUARD_ENV, fetchImpl, now: () => 1700000000000 });
  assert.deepEqual(r, { ok: true });
  assert.equal(seen.url, "https://usage.example/consume");
  assert.equal(seen.init.headers["x-lumos-ts"], "1700000000000");
  assert.equal(seen.init.headers["x-lumos-sig"], signUsageRequest(SECRET, "1700000000000", seen.init.body));
  assert.equal(JSON.stringify(seen.init).includes(SECRET), false, "secret never sent");
});

test("429 from the counter means usage_limited; anything unexpected fails closed", async () => {
  const limited = await consumeHostedAiQuota("lumos_x", "chat", {
    env: GUARD_ENV,
    fetchImpl: async () => reply(429, { allowed: false, scope: "user_day" }),
  });
  assert.deepEqual(limited, { ok: false, status: 429, error: "usage_limited", scope: "user_day" });
  for (const fetchImpl of [
    async () => reply(500, { error: "x" }),
    async () => reply(200, { allowed: "yes" }),
    async () => reply(200, null),
    async () => {
      throw new Error("timeout");
    },
  ]) {
    const r = await consumeHostedAiQuota("lumos_x", "chat", { env: GUARD_ENV, fetchImpl });
    assert.deepEqual(r, { ok: false, status: 503, error: "usage_guard_unavailable" });
  }
});

// --- Uç noktalar: sayaç reddederse sağlayıcıya gidilmez ---

function makeRes() {
  return {
    statusCode: 0,
    headers: {},
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
    end() {
      return this;
    },
  };
}

function session(sub) {
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";
  const sealed = sealSession({
    sid: `s-${sub}`,
    sub,
    provider: "google_web",
    name: "Test",
    email: `${sub}@example.test`,
    package: "base",
    exp: Math.floor(Date.now() / 1000) + 60,
  });
  process.env.LUMOS_HOSTED_AI_ALLOWED_IDS = sessionLumosId(openSession(sealed));
  return sealed;
}

async function withProviderSpy(fn) {
  const original = globalThis.fetch;
  let providerCalls = 0;
  globalThis.fetch = async () => {
    providerCalls += 1;
    return {
      ok: true,
      json: async () => ({ output: [{ content: [{ type: "output_text", text: "Merhaba!" }] }], value: "ek", expires_at: 1 }),
    };
  };
  process.env.OPENAI_API_KEY = "k";
  process.env.OPENAI_API_KEY_REALTIME = "rk";
  try {
    return await fn(() => providerCalls);
  } finally {
    globalThis.fetch = original;
    usageGuard.consume = consumeHostedAiQuota;
  }
}

const endpoints = [
  ["chat", chatHandler, (s) => ({ method: "POST", headers: { cookie: `lumos_session=${s}` }, body: { message: "Merhaba" } })],
  ["mobile chat", mobileChatHandler, (s) => ({ method: "POST", headers: { authorization: `Bearer ${s}` }, body: { message: "Merhaba" } })],
  ["realtime", realtimeHandler, (s) => ({ method: "POST", headers: { cookie: `lumos_session=${s}` }, body: {} })],
];

for (const [name, handler, request] of endpoints) {
  test(`${name}: usage limit reached → 429 and the provider is never called`, async () => {
    await withProviderSpy(async (providerCalls) => {
      const sealed = session(`limit-${name.replace(" ", "-")}`);
      usageGuard.consume = async () => ({ ok: false, status: 429, error: "usage_limited", scope: "user_minute" });
      const res = makeRes();
      await handler(request(sealed), res);
      assert.equal(res.statusCode, 429);
      assert.equal(res.payload.error, "usage_limited");
      assert.equal(providerCalls(), 0);
    });
  });

  test(`${name}: counter unavailable or unconfigured → 503 and the provider is never called`, async () => {
    await withProviderSpy(async (providerCalls) => {
      const sealed = session(`down-${name.replace(" ", "-")}`);
      delete process.env.LUMOS_USAGE_GUARD_URL;
      delete process.env.LUMOS_USAGE_GUARD_SECRET;
      // Gerçek istemci: yapılandırma yok → kapalı.
      const res = makeRes();
      await handler(request(sealed), res);
      assert.equal(res.statusCode, 503);
      assert.equal(res.payload.error, "usage_guard_unconfigured");
      assert.equal(providerCalls(), 0);
    });
  });

  test(`${name}: counter allows → provider is called exactly once`, async () => {
    await withProviderSpy(async (providerCalls) => {
      const sealed = session(`ok-${name.replace(" ", "-")}`);
      let consumed = [];
      usageGuard.consume = async (id, kind) => {
        consumed.push(kind);
        return { ok: true };
      };
      const res = makeRes();
      await handler(request(sealed), res);
      assert.notEqual(res.statusCode, 429);
      assert.notEqual(res.statusCode, 503);
      assert.equal(providerCalls(), 1);
      assert.deepEqual(consumed, [name === "realtime" ? "realtime" : "chat"]);
    });
  });
}

test("unlisted user is stopped by the allowlist before the counter is consumed", async () => {
  await withProviderSpy(async (providerCalls) => {
    const sealed = session("unlisted");
    process.env.LUMOS_HOSTED_AI_ALLOWED_IDS = "lumos_someone_else_1234";
    let consumed = 0;
    usageGuard.consume = async () => {
      consumed += 1;
      return { ok: true };
    };
    const res = makeRes();
    await chatHandler({ method: "POST", headers: { cookie: `lumos_session=${sealed}` }, body: { message: "Merhaba" } }, res);
    assert.equal(res.statusCode, 403);
    assert.equal(consumed, 0);
    assert.equal(providerCalls(), 0);
  });
});
