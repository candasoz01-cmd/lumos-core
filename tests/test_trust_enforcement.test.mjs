import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import handler from "../api/bridge/chat.js";
import logoutHandler from "../api/auth/logout.js";
import sessionHandler from "../api/auth/session.js";
import { gateHostedModelCall, buildOpenAIRequest, prepareProviderPayload } from "../api/_lib/hosted_lumos.js";
import { sealSession } from "../api/_lib/lumos_session.js";
import { appendOperatorWall, buildOperatorWallRecord } from "../api/_lib/operator_wall.js";

const SECRET = "test-only-secret-32-characters-minimum";
const epochDir = mkdtempSync(path.join(tmpdir(), "lumos-epoch-"));
process.env.LUMOS_SESSION_EPOCH_PATH = path.join(epochDir, "epoch.json");
process.env.LUMOS_AUTH_STATE_SECRET = SECRET;

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
    end(payload) {
      this.body = payload;
      return this;
    },
  };
}

function claims(overrides = {}) {
  return {
    sid: "session-one",
    lumos_id: "lumos_trust_test",
    sub: "google-subject-trust",
    provider: "google_web",
    name: "Ada Lovelace",
    email: "ada@example.test",
    package: "base",
    sv: 0,
    exp: Math.floor(Date.now() / 1000) + 3600,
    ...overrides,
  };
}

function cookieReq(message, extra = {}) {
  return {
    method: "POST",
    headers: { cookie: `lumos_session=${sealSession(claims())}` },
    body: { message, ...extra },
  };
}

test("unknown provider with sensitive data is blocked", () => {
  const gate = gateHostedModelCall({
    providerId: "acme",
    country: "",
    dataClasses: ["email"],
  });
  assert.equal(gate.ok, false);
  assert.equal(gate.reason, "unknown_provider");
  assert.equal(gate.policy.contract_verified, false);
});

test("disallowed region blocks the hosted call", async () => {
  process.env.OPENAI_API_KEY = "private-openai-test-key";
  delete process.env.LUMOS_GOOGLE_GEMINI_API_KEY;
  let called = false;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    called = true;
    return { ok: false, status: 500, async json() { return {}; } };
  };
  const res = makeRes();
  try {
    await handler(cookieReq("Merhaba", { country: "XX" }), res);
    assert.equal(res.statusCode, 403);
    assert.equal(res.payload.error, "provider_policy_blocked");
    assert.equal(res.payload.reason, "disallowed_region");
    assert.equal(res.payload.provider, undefined);
    assert.equal(called, false);
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.OPENAI_API_KEY;
  }
});

test("prepareProviderPayload replaces email phone and id in the model body", () => {
  const prepared = prepareProviderPayload(
    {
      message: "Yaz ada@example.test ve +90 555 123 4567 ve 12345678901",
      history: [{ role: "user", content: "eski ada@example.test" }],
    },
    {
      ok: true,
      profile: { name: "Ada Lovelace", provider: "google_web", connected: true },
      memory: { status: "loaded", items: ["telefonum 555-111-2222"] },
    },
  );
  const request = buildOpenAIRequest(prepared.body, prepared.context);
  const serialized = JSON.stringify(request);
  assert.equal(serialized.includes("ada@example.test"), false);
  assert.equal(serialized.includes("555 123 4567"), false);
  assert.equal(serialized.includes("12345678901"), false);
  assert.equal(serialized.includes("555-111-2222"), false);
  assert.equal(serialized.includes("[email]"), true);
  assert.equal(serialized.includes("[phone]"), true);
  assert.equal(serialized.includes("[id]"), true);
  assert.deepEqual(prepared.dataClasses, ["message_text"]);
});

test("logout invalidates a copied session cookie", async () => {
  const sealed = sealSession(claims({ lumos_id: "lumos_logout_only" }));
  const before = makeRes();
  await sessionHandler({ method: "GET", headers: { cookie: `lumos_session=${sealed}` } }, before);
  assert.equal(before.statusCode, 200);

  const loggedOut = makeRes();
  await logoutHandler(
    { method: "POST", headers: { cookie: `lumos_session=${sealed}` } },
    loggedOut,
  );
  assert.equal(loggedOut.statusCode, 200);

  const after = makeRes();
  await sessionHandler({ method: "GET", headers: { cookie: `lumos_session=${sealed}` } }, after);
  assert.equal(after.statusCode, 401);
  assert.equal(JSON.parse(after.body).error, "session_revoked");

  process.env.OPENAI_API_KEY = "private-openai-test-key";
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new Error("revoked session must not call a provider");
  };
  const chat = makeRes();
  try {
    await handler(
      {
        method: "POST",
        headers: { cookie: `lumos_session=${sealed}` },
        body: { message: "Merhaba" },
      },
      chat,
    );
    assert.equal(chat.statusCode, 401);
    assert.equal(chat.payload.error, "session_revoked");
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.OPENAI_API_KEY;
  }
});

test("provider and model stay on the operator record only", async () => {
  const wall = path.join(epochDir, "wall.jsonl");
  process.env.LUMOS_OPERATOR_WALL_PATH = wall;
  process.env.OPENAI_API_KEY = "private-openai-test-key";
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: true,
    async json() {
      return { output: [{ content: [{ type: "output_text", text: "Tamam" }] }] };
    },
  });
  const res = makeRes();
  try {
    await handler(cookieReq("Merhaba"), res);
    assert.equal(res.statusCode, 200);
    for (const key of ["provider", "model", "region", "retention_policy", "contract_verified", "data_classes_sent"]) {
      assert.equal(Object.hasOwn(res.payload, key), false, key);
    }
    const record = JSON.parse(readFileSync(wall, "utf8").trim().split("\n").at(-1));
    assert.equal(record.audience, "operator");
    assert.equal(record.provider, "openai");
    assert.equal(record.model, "gpt-5.6-luna");
    assert.equal(record.region, "unspecified");
    assert.equal(record.retention_policy, "unknown");
    assert.equal(record.contract_verified, false);
    assert.deepEqual(record.data_classes_sent, ["message_text"]);
    assert.equal(JSON.stringify(record).includes("Merhaba"), false);
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.OPENAI_API_KEY;
    delete process.env.LUMOS_OPERATOR_WALL_PATH;
  }
});

function brokenOperatorWallPath() {
  const blocker = path.join(epochDir, `wall-blocker-${Date.now()}-${Math.random().toString(16).slice(2)}`);
  writeFileSync(blocker, "not a directory\n");
  return path.join(blocker, "wall.jsonl");
}

test("operator wall mkdir failure does not throw and still returns the record", () => {
  process.env.LUMOS_OPERATOR_WALL_PATH = brokenOperatorWallPath();
  try {
    const record = buildOperatorWallRecord({ provider: "openai", outcome: "sent" });
    assert.deepEqual(appendOperatorWall(record), record);
  } finally {
    delete process.env.LUMOS_OPERATOR_WALL_PATH;
  }
});

test("operator wall write failure keeps the successful chat reply", async () => {
  const wallDir = path.join(epochDir, "wall-is-a-directory");
  mkdirSync(wallDir, { recursive: true });
  process.env.LUMOS_OPERATOR_WALL_PATH = wallDir;
  process.env.OPENAI_API_KEY = "private-openai-test-key";
  delete process.env.LUMOS_GOOGLE_GEMINI_API_KEY;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: true,
    async json() {
      return { output: [{ content: [{ type: "output_text", text: "Tamam" }] }] };
    },
  });
  const res = makeRes();
  try {
    await handler(cookieReq("Merhaba"), res);
    assert.equal(res.statusCode, 200);
    assert.equal(res.payload.reply, "Tamam");
    assert.equal(res.payload.mode, "hosted_chat");
    assert.equal(res.payload.error, undefined);
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.OPENAI_API_KEY;
    delete process.env.LUMOS_OPERATOR_WALL_PATH;
  }
});

test("operator wall write failure keeps the policy block", async () => {
  process.env.LUMOS_OPERATOR_WALL_PATH = brokenOperatorWallPath();
  process.env.OPENAI_API_KEY = "private-openai-test-key";
  delete process.env.LUMOS_GOOGLE_GEMINI_API_KEY;
  let called = false;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    called = true;
    return { ok: false, status: 500, async json() { return {}; } };
  };
  const res = makeRes();
  try {
    await handler(cookieReq("Merhaba", { country: "XX" }), res);
    assert.equal(res.statusCode, 403);
    assert.equal(res.payload.error, "provider_policy_blocked");
    assert.equal(res.payload.reason, "disallowed_region");
    assert.equal(called, false);
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.OPENAI_API_KEY;
    delete process.env.LUMOS_OPERATOR_WALL_PATH;
  }
});

test("a failed model stays model_unavailable when the operator wall cannot be written", async () => {
  process.env.LUMOS_OPERATOR_WALL_PATH = brokenOperatorWallPath();
  process.env.OPENAI_API_KEY = "private-openai-test-key";
  delete process.env.LUMOS_GOOGLE_GEMINI_API_KEY;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new Error("upstream down");
  };
  const res = makeRes();
  try {
    await handler(cookieReq("Merhaba"), res);
    assert.equal(res.statusCode, 502);
    assert.equal(res.payload.error, "model_unavailable");
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.OPENAI_API_KEY;
    delete process.env.LUMOS_OPERATOR_WALL_PATH;
  }
});
