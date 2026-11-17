// Üretime geçiş sırası kanıtı (#968 → #970).
//
// Her adım, o adımda üretimde çalışacak kodun ortam değişkenleriyle nasıl
// davranacağını süreç içinde canlandırır. Sayaç Worker'ı gerçek kodudur
// (ops/usage-guard/worker.mjs + SQLite Durable Object taklidi); Vercel
// istemcisi gerçek HMAC imzasıyla ona konuşur. Yalnız OpenAI çağrısı taklittir.
//
// Doğru sırada kurucu sohbeti hiçbir adımda kesilmemelidir; yanlış sıralar
// ise kapalı (403/503) kalmalı ve sağlayıcıya istek gitmemelidir.

import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";

import chatHandler from "../api/bridge/chat.js";
import { consumeHostedAiQuota, usageGuard } from "../api/_lib/usage_guard.js";
import { openSession, sealSession, sessionLumosId } from "../api/_lib/lumos_session.js";
import { handleRequest, UsageCounter } from "../ops/usage-guard/worker.mjs";

const AUTH_SECRET = "test-only-secret-32-characters-minimum";
const GUARD_URL = "https://lumos-usage-guard.example.workers.dev";
const GUARD_SECRET = "test-only-usage-guard-secret-32-characters";
const MANAGED = [
  "LUMOS_AUTH_STATE_SECRET",
  "OPENAI_API_KEY",
  "LUMOS_HOSTED_AI_ALLOWED_IDS",
  "LUMOS_USAGE_GUARD_URL",
  "LUMOS_USAGE_GUARD_SECRET",
];

function sqlShim() {
  const db = new DatabaseSync(":memory:");
  return {
    exec(q, ...b) {
      const s = db.prepare(q);
      if (/^\s*SELECT/i.test(q)) {
        const rows = s.all(...b);
        return { toArray: () => rows };
      }
      s.run(...b);
      return { toArray: () => [] };
    },
  };
}

function workerEnv(secret = GUARD_SECRET, vars = {}) {
  let object;
  return {
    LUMOS_USAGE_GUARD_SECRET: secret,
    ...vars,
    USAGE: {
      idFromName: () => "global",
      get: () => {
        object ||= new UsageCounter({ storage: { sql: sqlShim() } }, vars);
        return { fetch: (url, init) => object.fetch(new Request(url, init)) };
      },
    },
  };
}

function makeRes() {
  return {
    statusCode: 0,
    headers: {},
    status(c) {
      this.statusCode = c;
      return this;
    },
    setHeader(k, v) {
      this.headers[k.toLowerCase()] = v;
    },
    json(p) {
      this.payload = p;
      return this;
    },
    end() {
      return this;
    },
  };
}

function sessionFor(sub) {
  process.env.LUMOS_AUTH_STATE_SECRET = AUTH_SECRET;
  const sealed = sealSession({
    sid: `s-${sub}`,
    sub,
    provider: "google_web",
    name: sub,
    email: `${sub}@example.test`,
    package: "base",
    exp: Math.floor(Date.now() / 1000) + 600,
  });
  return { sealed, id: sessionLumosId(openSession(sealed)) };
}

// Bir "dağıtım": kod sürümü + o dağıtıma gömülü ortam değişkenleri + Worker durumu.
async function deploy({ code, env, worker }, fn) {
  const saved = Object.fromEntries(MANAGED.map((k) => [k, process.env[k]]));
  for (const k of MANAGED) delete process.env[k];
  Object.assign(process.env, { LUMOS_AUTH_STATE_SECRET: AUTH_SECRET, OPENAI_API_KEY: "k" }, env);
  // #968 kodunda sayaç yoktur: sayaç çağrısı her zaman geçer gibi davranır.
  usageGuard.consume = code === "pr968" ? async () => ({ ok: true }) : consumeHostedAiQuota;
  const original = globalThis.fetch;
  let providerCalls = 0;
  globalThis.fetch = async (url, init) => {
    if (String(url).startsWith(GUARD_URL)) {
      if (!worker) throw new Error("worker not deployed");
      return handleRequest(new Request(url, init), worker);
    }
    providerCalls += 1;
    return { ok: true, json: async () => ({ output: [{ content: [{ type: "output_text", text: "Merhaba!" }] }] }) };
  };
  try {
    return await fn({ providerCalls: () => providerCalls });
  } finally {
    globalThis.fetch = original;
    usageGuard.consume = consumeHostedAiQuota;
    for (const k of MANAGED) {
      if (saved[k] === undefined) delete process.env[k];
      else process.env[k] = saved[k];
    }
  }
}

async function chat(sealed) {
  const res = makeRes();
  await chatHandler({ method: "POST", headers: { cookie: `lumos_session=${sealed}` }, body: { message: "Merhaba" } }, res);
  return res.statusCode;
}

const founder = () => sessionFor("founder");
const stranger = () => sessionFor("stranger");

test("Adım 2 — #968 dağıtıldı, izin listesi dağıtımdan ÖNCE girilmiş: kurucu 200, diğerleri 403", async () => {
  const f = founder();
  const s = stranger();
  await deploy({ code: "pr968", env: { LUMOS_HOSTED_AI_ALLOWED_IDS: f.id } }, async ({ providerCalls }) => {
    assert.equal(await chat(f.sealed), 200);
    assert.equal(await chat(s.sealed), 403);
    assert.equal(providerCalls(), 1);
  });
});

test("YANLIŞ SIRA — #968 izin listesi olmadan dağıtılırsa kurucu dahil herkes 403 (sohbet kesilir)", async () => {
  const f = founder();
  await deploy({ code: "pr968", env: {} }, async ({ providerCalls }) => {
    assert.equal(await chat(f.sealed), 403);
    assert.equal(providerCalls(), 0);
  });
});

test("Adım 4 — Worker yayında + sayaç değişkenleri girilmiş + #970 dağıtıldı: kurucu 200, gerçek imza ve sayaçla", async () => {
  const f = founder();
  const worker = workerEnv();
  await deploy(
    {
      code: "pr970",
      env: { LUMOS_HOSTED_AI_ALLOWED_IDS: f.id, LUMOS_USAGE_GUARD_URL: GUARD_URL, LUMOS_USAGE_GUARD_SECRET: GUARD_SECRET },
      worker,
    },
    async ({ providerCalls }) => {
      assert.equal(await chat(f.sealed), 200);
      assert.equal(await chat(f.sealed), 200);
      assert.equal(providerCalls(), 2);
    },
  );
});

test("Adım 4 — sınır gerçekten uygulanıyor: kullanıcı/dakika 2 iken 3. istek 429 ve sağlayıcıya gitmez", async () => {
  const f = founder();
  const worker = workerEnv(GUARD_SECRET, { LUMOS_USAGE_USER_PER_MINUTE: "2" });
  await deploy(
    {
      code: "pr970",
      env: { LUMOS_HOSTED_AI_ALLOWED_IDS: f.id, LUMOS_USAGE_GUARD_URL: GUARD_URL, LUMOS_USAGE_GUARD_SECRET: GUARD_SECRET },
      worker,
    },
    async ({ providerCalls }) => {
      assert.equal(await chat(f.sealed), 200);
      assert.equal(await chat(f.sealed), 200);
      assert.equal(await chat(f.sealed), 429);
      assert.equal(providerCalls(), 2);
    },
  );
});

for (const [label, setup] of [
  ["sayaç değişkenleri girilmeden #970 dağıtılırsa", { env: {}, worker: workerEnv() }],
  ["Worker yayında değilken #970 dağıtılırsa", { env: { LUMOS_USAGE_GUARD_URL: GUARD_URL, LUMOS_USAGE_GUARD_SECRET: GUARD_SECRET }, worker: null }],
  ["Vercel ve Worker'daki ortak anahtar farklıysa", { env: { LUMOS_USAGE_GUARD_URL: GUARD_URL, LUMOS_USAGE_GUARD_SECRET: GUARD_SECRET }, worker: workerEnv("another-secret-that-is-32-characters-x") }],
]) {
  test(`YANLIŞ SIRA — ${label}: kurucu 503, sağlayıcıya istek yok`, async () => {
    const f = founder();
    await deploy(
      { code: "pr970", env: { LUMOS_HOSTED_AI_ALLOWED_IDS: f.id, ...setup.env }, worker: setup.worker },
      async ({ providerCalls }) => {
        assert.equal(await chat(f.sealed), 503);
        assert.equal(providerCalls(), 0);
      },
    );
  });
}

test("Geri dönüş — #970 dağıtımı #968 dağıtımına geri alınırsa kurucu sohbeti çalışır", async () => {
  const f = founder();
  await deploy({ code: "pr968", env: { LUMOS_HOSTED_AI_ALLOWED_IDS: f.id } }, async () => {
    assert.equal(await chat(f.sealed), 200);
  });
});
