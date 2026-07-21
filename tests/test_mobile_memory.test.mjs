import assert from "node:assert/strict";
import test from "node:test";

import handler from "../api/mobile/memory.js";
import { sealSession } from "../api/_lib/lumos_session.js";


const LUMOS_ID = `lumos_${"A".repeat(24)}`;

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
  };
}

function bearerRequest(method, body) {
  const sealed = sealSession({
    sid: "mobile-session",
    lumos_id: LUMOS_ID,
    provider: "google_web",
    sub: "google-subject",
    exp: Math.floor(Date.now() / 1000) + 60,
  });
  return {
    method,
    headers: { authorization: `Bearer ${sealed}` },
    body,
  };
}

test("mobile memory requires an authenticated Lumos session", async () => {
  const res = makeRes();
  await handler({ method: "GET", headers: {} }, res);
  assert.equal(res.statusCode, 401);
  assert.equal(res.payload.error, "unauthorized");
});

test("mobile memory reports consent state without exposing memory text", async () => {
  process.env.LUMOS_MEMORY_LOOKUP_URL = "https://memory.example.test/memory/hosted/lookup";
  process.env.LUMOS_MEMORY_SERVICE_TOKEN = "private-memory-token";
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async () => ({
      ok: true,
      async json() {
        return { consent: true, memories: [{ summary: "Özel tercih" }] };
      },
    });
    const res = makeRes();
    await handler(bearerRequest("GET"), res);
    assert.deepEqual(res.payload, { ok: true, status: "loaded", consent: true, count: 1 });
    assert.equal(JSON.stringify(res.payload).includes("Özel tercih"), false);
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.LUMOS_MEMORY_LOOKUP_URL;
    delete process.env.LUMOS_MEMORY_SERVICE_TOKEN;
  }
});

test("mobile memory grant requires explicit consent and derives identity from session", async () => {
  const blocked = makeRes();
  await handler(bearerRequest("POST", { action: "grant" }), blocked);
  assert.equal(blocked.statusCode, 400);
  assert.equal(blocked.payload.error, "explicit_consent_required");

  process.env.LUMOS_MEMORY_LOOKUP_URL = "https://memory.example.test/memory/hosted/lookup";
  process.env.LUMOS_MEMORY_SERVICE_TOKEN = "private-memory-token";
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async (url, init) => {
      assert.equal(url, "https://memory.example.test/memory/hosted/consent");
      assert.deepEqual(JSON.parse(init.body), { lumos_id: LUMOS_ID, consent: true });
      return { ok: true, async json() { return { ok: true, consent: true }; } };
    };
    const res = makeRes();
    await handler(bearerRequest("POST", { action: "grant", consent: true }), res);
    assert.equal(res.statusCode, 200);
    assert.deepEqual(res.payload, { ok: true, consent: true });
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.LUMOS_MEMORY_LOOKUP_URL;
    delete process.env.LUMOS_MEMORY_SERVICE_TOKEN;
  }
});

test("mobile memory delete requires confirmation and removes consent", async () => {
  const blocked = makeRes();
  await handler(bearerRequest("POST", { action: "delete" }), blocked);
  assert.equal(blocked.statusCode, 400);
  assert.equal(blocked.payload.error, "explicit_delete_confirmation_required");

  process.env.LUMOS_MEMORY_LOOKUP_URL = "https://memory.example.test/memory/hosted/lookup";
  process.env.LUMOS_MEMORY_SERVICE_TOKEN = "private-memory-token";
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async (url, init) => {
      assert.equal(url, "https://memory.example.test/memory/hosted/delete");
      assert.deepEqual(JSON.parse(init.body), { lumos_id: LUMOS_ID, confirm: true });
      return { ok: true, async json() { return { ok: true, consent: false, deleted: 3 }; } };
    };
    const res = makeRes();
    await handler(bearerRequest("POST", { action: "delete", confirm: true }), res);
    assert.equal(res.statusCode, 200);
    assert.deepEqual(res.payload, { ok: true, consent: false, deleted: 3 });
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.LUMOS_MEMORY_LOOKUP_URL;
    delete process.env.LUMOS_MEMORY_SERVICE_TOKEN;
  }
});

test.after(() => {
  delete process.env.LUMOS_AUTH_STATE_SECRET;
});

process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";
