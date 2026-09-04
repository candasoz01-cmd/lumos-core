/**
 * PR-005 / ADR-019 kullanıcı yüzü sızıntısı guard testi.
 *
 * Kapsam kabul kriteri ADR-019 § Bekleyen'de tanımlıdır: yalnız model adı değil,
 * tüm internal-only alanlar doğrulanır (`provider`, `model`, `agent_id`,
 * `instance_id`, `session_id`, `workspace_path` / worktree, heartbeat, PR/merge
 * gate). Doğrulama yüzeyi yalnız UI metni değil, kullanıcıya açık API
 * yanıtlarının tamamıdır. Bu ayrıntılar yalnız Lumos Agent Wall'a (iç operatör
 * yüzeyi) açıktır.
 *
 * Desen: tests/test_legacy_layer_names_retired.py (ADR-018).
 */
import assert from "node:assert/strict";
import test from "node:test";
import chatHandler from "../api/bridge/chat.js";
import statusHandler from "../api/bridge/status.js";
import healthHandler from "../api/bridge/health.js";
import { sealSession } from "../api/_lib/lumos_session.js";

const INTERNAL_KEYS = [
  "provider",
  "model",
  "agent_id",
  "agentId",
  "instance_id",
  "instanceId",
  "session_id",
  "sessionId",
  "workspace_path",
  "workspacePath",
  "worktree",
  "heartbeat",
  "merge_gate",
  "pr_gate",
  "branch",
];

// Sağlayıcı / model adları — kullanıcıya açık gövdede hiçbir biçimde geçmez.
const INTERNAL_NAMES =
  /\b(openai|gpt-|o[34]-mini|gemini|google-genai|anthropic|claude|deepseek|kimi|moonshot|mistral)\b/i;

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

function userClaims() {
  return {
    sid: "guard-session",
    sub: "google-subject-guard",
    provider: "google_web",
    name: "Ada Lovelace",
    email: "ada@example.test",
    package: "base",
    exp: Math.floor(Date.now() / 1000) + 60,
  };
}

/** Gövdedeki her anahtarı iç içe gez; internal-only anahtar bulursa yol döndürür. */
function findInternalKeys(value, path = "$") {
  const hits = [];
  if (Array.isArray(value)) {
    value.forEach((item, i) => hits.push(...findInternalKeys(item, `${path}[${i}]`)));
    return hits;
  }
  if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      if (INTERNAL_KEYS.includes(key)) hits.push(`${path}.${key}`);
      hits.push(...findInternalKeys(child, `${path}.${key}`));
    }
  }
  return hits;
}

function assertNoLeak(label, payload) {
  const keyHits = findInternalKeys(payload);
  assert.deepEqual(
    keyHits,
    [],
    `${label}: kullanıcı yüzeyinde iç operatör alanı sızdı → ${keyHits.join(", ")}`,
  );
  const serialized = JSON.stringify(payload ?? {});
  const nameHit = serialized.match(INTERNAL_NAMES);
  assert.equal(
    nameHit,
    null,
    `${label}: kullanıcı yüzeyinde sağlayıcı/model adı sızdı → ${nameHit && nameHit[0]}`,
  );
}

async function withEnv(fn) {
  const saved = {
    LUMOS_AUTH_STATE_SECRET: process.env.LUMOS_AUTH_STATE_SECRET,
    OPENAI_API_KEY: process.env.OPENAI_API_KEY,
  };
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";
  process.env.OPENAI_API_KEY = "private-openai-test-key";
  try {
    return await fn();
  } finally {
    for (const [k, v] of Object.entries(saved)) {
      if (v === undefined) delete process.env[k];
      else process.env[k] = v;
    }
  }
}

test("bridge status kullanıcıya sağlayıcı/model adı vermez", async () => {
  await withEnv(async () => {
    const sealed = sealSession(userClaims());
    const res = makeRes();
    await statusHandler(
      { method: "GET", headers: { cookie: `lumos_session=${sealed}` } },
      res,
    );
    assert.equal(res.statusCode, 200);
    assertNoLeak("GET /api/bridge/status", res.payload);
  });
});

test("bridge health kullanıcıya sağlayıcı/model adı vermez", async () => {
  await withEnv(async () => {
    const sealed = sealSession(userClaims());
    const res = makeRes();
    await healthHandler(
      { method: "GET", headers: { cookie: `lumos_session=${sealed}` } },
      res,
    );
    assert.equal(res.statusCode, 200);
    assertNoLeak("GET /api/bridge/health", res.payload);
  });
});

test("hosted chat yanıtı iç operatör alanlarını taşımaz", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: true,
    async json() {
      return { output: [{ content: [{ type: "output_text", text: "Merhaba!" }] }] };
    },
  });
  try {
    await withEnv(async () => {
      const sealed = sealSession(userClaims());
      const res = makeRes();
      await chatHandler(
        {
          method: "POST",
          headers: { cookie: `lumos_session=${sealed}` },
          body: { message: "Merhaba" },
        },
        res,
      );
      assert.equal(res.statusCode, 200);
      assert.equal(res.payload.reply, "Merhaba!");
      assertNoLeak("POST /api/bridge/chat", res.payload);
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});
