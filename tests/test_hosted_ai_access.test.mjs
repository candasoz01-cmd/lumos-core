import assert from "node:assert/strict";
import test from "node:test";

import chatHandler from "../api/bridge/chat.js";
import mobileChatHandler from "../api/mobile/chat.js";
import realtimeHandler from "../api/mobile/realtime-token.js";
import { isHostedAiAllowed } from "../api/_lib/hosted_ai_access.js";
import { openSession, sealSession, sessionLumosId } from "../api/_lib/lumos_session.js";
import { usageGuard } from "../api/_lib/usage_guard.js";

// Kalıcı kullanım sayacı ayrı dosyalarda test edilir (test_usage_guard_*.test.mjs);
// bu dosyada sayaç "izin ver" cevabı verir ki sağlayıcı davranışı ölçülebilsin.
usageGuard.consume = async () => ({ ok: true });

// Bu dosya erişim kapısının KAPALI varsayılanını test eder.
// Herkese açma modu yoktur; LUMOS_HOSTED_AI_ACCESS=open hiçbir şey açmamalıdır.

const SECRET = "test-only-secret-32-characters-minimum";

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
    end(payload) {
      this.body = payload;
      return this;
    },
  };
}

function claims(sub) {
  return {
    sid: `session-${sub}`,
    sub,
    provider: "google_web",
    name: "Test Kullanıcı",
    email: `${sub}@example.test`,
    package: "base",
    exp: Math.floor(Date.now() / 1000) + 60,
  };
}

function lumosIdFor(sealed) {
  return sessionLumosId(openSession(sealed));
}

async function withEnv(vars, fn) {
  const saved = {};
  for (const [k, v] of Object.entries(vars)) {
    saved[k] = process.env[k];
    if (v === undefined) delete process.env[k];
    else process.env[k] = v;
  }
  const originalFetch = globalThis.fetch;
  let upstreamCalls = 0;
  globalThis.fetch = async () => {
    upstreamCalls += 1;
    return {
      ok: true,
      async json() {
        return {
          output: [{ content: [{ type: "output_text", text: "Merhaba!" }] }],
          value: "ek_test",
          expires_at: Math.floor(Date.now() / 1000) + 60,
        };
      },
    };
  };
  try {
    return await fn(() => upstreamCalls);
  } finally {
    globalThis.fetch = originalFetch;
    for (const [k, v] of Object.entries(saved)) {
      if (v === undefined) delete process.env[k];
      else process.env[k] = v;
    }
  }
}

test("only explicitly listed ids are allowed; empty or missing list allows nobody", () => {
  assert.equal(isHostedAiAllowed("lumos-a", {}), false);
  assert.equal(isHostedAiAllowed("lumos-a", { LUMOS_HOSTED_AI_ALLOWED_IDS: "" }), false);
  assert.equal(isHostedAiAllowed("lumos-a", { LUMOS_HOSTED_AI_ALLOWED_IDS: " , " }), false);
  assert.equal(isHostedAiAllowed("", { LUMOS_HOSTED_AI_ALLOWED_IDS: "lumos-a" }), false);
  assert.equal(isHostedAiAllowed("lumos-a", { LUMOS_HOSTED_AI_ALLOWED_IDS: " lumos-a , lumos-b" }), true);
  assert.equal(isHostedAiAllowed("lumos-c", { LUMOS_HOSTED_AI_ALLOWED_IDS: "lumos-a,lumos-b" }), false);
  assert.equal(isHostedAiAllowed("lumos-a", { LUMOS_HOSTED_AI_ACCESS: "open" }), false);
  assert.equal(isHostedAiAllowed("lumos-a", { LUMOS_HOSTED_AI_ACCESS: "open", LUMOS_HOSTED_AI_ALLOWED_IDS: "" }), false);
});

test("chat: signed-in user not on the list never reaches the provider", async () => {
  await withEnv(
    { LUMOS_AUTH_STATE_SECRET: SECRET, OPENAI_API_KEY: "k", LUMOS_HOSTED_AI_ACCESS: undefined, LUMOS_HOSTED_AI_ALLOWED_IDS: undefined },
    async (calls) => {
      const sealed = sealSession(claims("outsider"));
      const res = makeRes();
      await chatHandler({ method: "POST", headers: { cookie: `lumos_session=${sealed}` }, body: { message: "Merhaba" } }, res);
      assert.equal(res.statusCode, 403);
      assert.equal(res.payload.error, "hosted_ai_not_enabled");
      assert.equal(calls(), 0);
    },
  );
});

test("chat: listed user reaches the provider", async () => {
  await withEnv({ LUMOS_AUTH_STATE_SECRET: SECRET, OPENAI_API_KEY: "k", LUMOS_HOSTED_AI_ACCESS: undefined }, async (calls) => {
    const sealed = sealSession(claims("founder"));
    process.env.LUMOS_HOSTED_AI_ALLOWED_IDS = lumosIdFor(sealed);
    const res = makeRes();
    await chatHandler({ method: "POST", headers: { cookie: `lumos_session=${sealed}` }, body: { message: "Merhaba" } }, res);
    delete process.env.LUMOS_HOSTED_AI_ALLOWED_IDS;
    assert.equal(res.statusCode, 200);
    assert.equal(res.payload.reply, "Merhaba!");
    assert.ok(calls() >= 1);
  });
});

test("chat: identity status still answers without a model call when not listed", async () => {
  await withEnv({ LUMOS_AUTH_STATE_SECRET: SECRET, OPENAI_API_KEY: "k", LUMOS_HOSTED_AI_ALLOWED_IDS: undefined }, async () => {
    const sealed = sealSession(claims("outsider2"));
    const res = makeRes();
    await chatHandler({ method: "POST", headers: { cookie: `lumos_session=${sealed}` }, body: { message: "ben kimim" } }, res);
    assert.equal(res.statusCode, 200);
    assert.equal(res.payload.mode, "hosted_identity_status");
  });
});

test("realtime: signed-in user not on the list gets 403 and no client secret is minted", async () => {
  await withEnv(
    { LUMOS_AUTH_STATE_SECRET: SECRET, OPENAI_API_KEY_REALTIME: "rk", LUMOS_HOSTED_AI_ALLOWED_IDS: undefined },
    async (calls) => {
      const sealed = sealSession(claims("outsider3"));
      const res = makeRes();
      await realtimeHandler({ method: "POST", headers: { cookie: `lumos_session=${sealed}` }, body: {} }, res);
      assert.equal(res.statusCode, 403);
      assert.equal(res.payload.error, "hosted_ai_not_enabled");
      assert.equal(calls(), 0);
    },
  );
});

for (const [name, handler] of [["chat", chatHandler], ["mobile chat", mobileChatHandler]]) {
  test(`${name}: "open" setting does not bypass the list`, async () => {
    await withEnv(
      { LUMOS_AUTH_STATE_SECRET: SECRET, OPENAI_API_KEY: "k", LUMOS_HOSTED_AI_ACCESS: "open", LUMOS_HOSTED_AI_ALLOWED_IDS: undefined },
      async (calls) => {
        const sealed = sealSession(claims(`open-${name.replace(" ", "-")}`));
        const res = makeRes();
        await handler({ method: "POST", headers: { cookie: `lumos_session=${sealed}` }, body: { message: "Merhaba" } }, res);
        assert.equal(res.statusCode, 403);
        assert.equal(calls(), 0);
      },
    );
  });

  test(`${name}: request without a session gets 401 and never reaches the provider`, async () => {
    await withEnv({ LUMOS_AUTH_STATE_SECRET: SECRET, OPENAI_API_KEY: "k" }, async (calls) => {
      const res = makeRes();
      await handler({ method: "POST", headers: {}, body: { message: "Merhaba" } }, res);
      assert.equal(res.statusCode, 401);
      assert.equal(calls(), 0);
    });
  });
}

test("mobile chat: signed-in user not on the list never reaches the provider", async () => {
  await withEnv(
    { LUMOS_AUTH_STATE_SECRET: SECRET, OPENAI_API_KEY: "k", LUMOS_HOSTED_AI_ALLOWED_IDS: undefined },
    async (calls) => {
      const sealed = sealSession(claims("mobile-outsider"));
      const res = makeRes();
      await mobileChatHandler({ method: "POST", headers: { authorization: `Bearer ${sealed}` }, body: { message: "Merhaba" } }, res);
      assert.equal(res.statusCode, 403);
      assert.equal(res.payload.error, "hosted_ai_not_enabled");
      assert.equal(calls(), 0);
    },
  );
});

test("mobile chat: listed user reaches the provider", async () => {
  await withEnv({ LUMOS_AUTH_STATE_SECRET: SECRET, OPENAI_API_KEY: "k" }, async (calls) => {
    const sealed = sealSession(claims("mobile-founder"));
    process.env.LUMOS_HOSTED_AI_ALLOWED_IDS = lumosIdFor(sealed);
    const res = makeRes();
    await mobileChatHandler({ method: "POST", headers: { authorization: `Bearer ${sealed}` }, body: { message: "Merhaba" } }, res);
    delete process.env.LUMOS_HOSTED_AI_ALLOWED_IDS;
    assert.equal(res.statusCode, 200);
    assert.ok(calls() >= 1);
  });
});

test("realtime: request without a session gets 401 and no client secret is minted", async () => {
  await withEnv({ LUMOS_AUTH_STATE_SECRET: SECRET, OPENAI_API_KEY_REALTIME: "rk" }, async (calls) => {
    const res = makeRes();
    await realtimeHandler({ method: "POST", headers: {}, body: {} }, res);
    assert.equal(res.statusCode, 401);
    assert.equal(calls(), 0);
  });
});

test("realtime: \"open\" setting does not bypass the list", async () => {
  await withEnv(
    { LUMOS_AUTH_STATE_SECRET: SECRET, OPENAI_API_KEY_REALTIME: "rk", LUMOS_HOSTED_AI_ACCESS: "open", LUMOS_HOSTED_AI_ALLOWED_IDS: undefined },
    async (calls) => {
      const sealed = sealSession(claims("realtime-open"));
      const res = makeRes();
      await realtimeHandler({ method: "POST", headers: { cookie: `lumos_session=${sealed}` }, body: {} }, res);
      assert.equal(res.statusCode, 403);
      assert.equal(calls(), 0);
    },
  );
});

test("realtime: listed user reaches the provider", async () => {
  await withEnv({ LUMOS_AUTH_STATE_SECRET: SECRET, OPENAI_API_KEY_REALTIME: "rk" }, async (calls) => {
    const sealed = sealSession(claims("realtime-founder"));
    process.env.LUMOS_HOSTED_AI_ALLOWED_IDS = lumosIdFor(sealed);
    const res = makeRes();
    await realtimeHandler({ method: "POST", headers: { cookie: `lumos_session=${sealed}` }, body: {} }, res);
    delete process.env.LUMOS_HOSTED_AI_ALLOWED_IDS;
    assert.notEqual(res.statusCode, 403);
    assert.equal(calls(), 1);
  });
});
