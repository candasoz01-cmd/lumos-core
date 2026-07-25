import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import handler, { REALTIME_MODEL } from "../api/mobile/realtime-token.js";
import { sealSession } from "../api/_lib/lumos_session.js";

const LUMOS_ID = `lumos_${"R".repeat(24)}`;
process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";

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

function bearerRequest(method = "POST") {
  const sealed = sealSession({
    sid: "mobile-realtime-session",
    lumos_id: LUMOS_ID,
    provider: "google_web",
    sub: "google-subject",
    exp: Math.floor(Date.now() / 1000) + 60,
  });
  return {
    method,
    headers: { authorization: `Bearer ${sealed}` },
  };
}

test("realtime token requires POST and an authenticated Lumos identity", async () => {
  const method = makeRes();
  await handler(bearerRequest("GET"), method);
  assert.equal(method.statusCode, 405);

  const auth = makeRes();
  await handler({ method: "POST", headers: {} }, auth);
  assert.equal(auth.statusCode, 401);
  assert.equal(auth.payload.error, "unauthorized");
});

test("realtime token fails closed without a server-side OpenAI key", async () => {
  delete process.env.OPENAI_API_KEY;
  const res = makeRes();
  await handler(bearerRequest(), res);
  assert.equal(res.statusCode, 503);
  assert.equal(res.payload.error, "realtime_unconfigured");
});

test("realtime token returns only the short-lived client secret", async () => {
  process.env.OPENAI_API_KEY = "server-only-standard-key";
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async (url, init) => {
      assert.equal(url, "https://api.openai.com/v1/realtime/client_secrets");
      assert.equal(init.headers.Authorization, "Bearer server-only-standard-key");
      assert.equal(init.headers["OpenAI-Safety-Identifier"], LUMOS_ID);
      const body = JSON.parse(init.body);
      assert.equal(body.session.model, REALTIME_MODEL);
      assert.equal(body.session.audio.input.turn_detection.interrupt_response, true);
      return {
        ok: true,
        async json() {
          return { value: "ek_short_lived", expires_at: 123456 };
        },
      };
    };
    const res = makeRes();
    await handler(bearerRequest(), res);
    assert.equal(res.statusCode, 200);
    assert.deepEqual(res.payload, {
      ok: true,
      client_secret: { value: "ek_short_lived", expires_at: 123456 },
      model: REALTIME_MODEL,
      page: "/canli-ses",
    });
    assert.equal(JSON.stringify(res.payload).includes("server-only-standard-key"), false);
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.OPENAI_API_KEY;
  }
});

test("live voice page uses WebRTC and removes the secret from the address bar", async () => {
  const source = await readFile(
    new URL("../ui/src/pages/canli-ses.astro", import.meta.url),
    "utf8",
  );
  assert.match(source, /new RTCPeerConnection/);
  assert.match(source, /getUserMedia/);
  assert.match(source, /createDataChannel\("oai-events"\)/);
  assert.match(source, /history\.replaceState/);
  assert.match(source, /Basılı tut ve konuş/);
  assert.match(source, /track\.enabled = talking/);
  assert.match(source, /pointerdown/);
  assert.match(source, /pointerup/);
  assert.doesNotMatch(source, /OPENAI_API_KEY/);
});

test.after(() => {
  delete process.env.LUMOS_AUTH_STATE_SECRET;
  delete process.env.OPENAI_API_KEY;
});
