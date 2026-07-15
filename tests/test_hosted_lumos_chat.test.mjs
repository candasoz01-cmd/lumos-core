import assert from "node:assert/strict";
import test from "node:test";
import handler from "../api/bridge/chat.js";
import {
  buildGeminiRequest,
  buildOpenAIRequest,
  geminiReply,
  localTimeReply,
  openAIReply,
} from "../api/_lib/hosted_lumos.js";
import { sealSession } from "../api/_lib/lumos_session.js";

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

test("hosted request keeps bounded history and current image", () => {
  const request = buildGeminiRequest({
    message: "Bunu açıkla",
    history: [{ role: "assistant", content: "Önceki yanıt" }],
    imageData: "aGVsbG8=",
    photoType: "image/png",
  });
  assert.equal(request.contents.length, 2);
  assert.equal(request.contents[0].role, "model");
  assert.equal(request.contents[1].parts[0].text, "Bunu açıkla");
  assert.equal(request.contents[1].parts[1].inlineData.mimeType, "image/png");
});

test("hosted reply joins text parts", () => {
  assert.equal(
    geminiReply({ candidates: [{ content: { parts: [{ text: "Mer" }, { text: "haba" }] } }] }),
    "Merhaba",
  );
});

test("OpenAI request is stateless and uses the efficient hosted model", () => {
  const request = buildOpenAIRequest({ message: "Merhaba", history: [] });
  assert.equal(request.model, "gpt-5.6-luna");
  assert.equal(request.store, false);
  assert.equal(request.reasoning.effort, "none");
});

test("OpenAI reply reads output text parts", () => {
  assert.equal(
    openAIReply({ output: [{ content: [{ type: "output_text", text: "Merhaba!" }] }] }),
    "Merhaba!",
  );
});

test("time questions stay local", () => {
  assert.match(localTimeReply("Saat kaç?"), /^Saat \d{2}:\d{2}\. Bugün /);
  assert.equal(localTimeReply("Merhaba"), "");
});

test("hosted chat requires a sealed Lumos session", async () => {
  const res = makeRes();
  await handler({ method: "POST", headers: {}, body: { message: "Merhaba" } }, res);
  assert.equal(res.statusCode, 401);
});

test("hosted chat calls OpenAI first without exposing its key", async () => {
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";
  process.env.OPENAI_API_KEY = "private-openai-test-key";
  const sealed = sealSession({ exp: Math.floor(Date.now() / 1000) + 60 });
  const originalFetch = globalThis.fetch;
  let requestHeaders;
  globalThis.fetch = async (_url, init) => {
    requestHeaders = init.headers;
    return {
      ok: true,
      async json() {
        return { output: [{ content: [{ type: "output_text", text: "Merhaba!" }] }] };
      },
    };
  };
  const res = makeRes();
  try {
    await handler(
      {
        method: "POST",
        headers: { cookie: `lumos_session=${sealed}` },
        body: { message: "Merhaba" },
      },
      res,
    );
    assert.equal(res.statusCode, 200);
    assert.equal(res.payload.reply, "Merhaba!");
    assert.equal(requestHeaders.Authorization, "Bearer private-openai-test-key");
    assert.equal(res.payload.provider, "openai");
    assert.equal(JSON.stringify(res.payload).includes("private-openai-test-key"), false);
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.LUMOS_AUTH_STATE_SECRET;
    delete process.env.OPENAI_API_KEY;
  }
});

test("hosted chat falls back to Google when OpenAI is unavailable", async () => {
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";
  process.env.OPENAI_API_KEY = "private-openai-test-key";
  process.env.LUMOS_GOOGLE_GEMINI_API_KEY = "private-google-test-key";
  const sealed = sealSession({ exp: Math.floor(Date.now() / 1000) + 60 });
  const originalFetch = globalThis.fetch;
  const urls = [];
  globalThis.fetch = async (url) => {
    urls.push(String(url));
    if (String(url).includes("api.openai.com")) return { ok: false };
    return {
      ok: true,
      async json() {
        return { candidates: [{ content: { parts: [{ text: "Yedek yanıt" }] } }] };
      },
    };
  };
  const res = makeRes();
  try {
    await handler(
      {
        method: "POST",
        headers: { cookie: `lumos_session=${sealed}` },
        body: { message: "Merhaba" },
      },
      res,
    );
    assert.equal(res.statusCode, 200);
    assert.equal(res.payload.provider, "google");
    assert.equal(res.payload.reply, "Yedek yanıt");
    assert.equal(urls.length, 2);
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.LUMOS_AUTH_STATE_SECRET;
    delete process.env.OPENAI_API_KEY;
    delete process.env.LUMOS_GOOGLE_GEMINI_API_KEY;
  }
});
