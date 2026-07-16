import assert from "node:assert/strict";
import test from "node:test";
import handler from "../api/bridge/chat.js";
import sessionHandler from "../api/auth/session.js";
import callbackHandler from "../api/auth/google/callback.js";
import {
  buildGeminiRequest,
  buildOpenAIRequest,
  geminiReply,
  identityStatusReply,
  loadAllowedMemory,
  loadHostedUserContext,
  localTimeReply,
  openAIReply,
} from "../api/_lib/hosted_lumos.js";
import {
  lumosIdForProviderIdentity,
  makeState,
  openSession,
  sealSession,
  sessionLumosId,
} from "../api/_lib/lumos_session.js";

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

function userClaims(overrides = {}) {
  return {
    sid: "session-one",
    sub: "google-subject-one",
    provider: "google_web",
    name: "Ada Lovelace",
    email: "ada@example.test",
    package: "base",
    exp: Math.floor(Date.now() / 1000) + 60,
    ...overrides,
  };
}

async function runGoogleCallback() {
  const state = makeState();
  const req = {
    method: "GET",
    url: `/api/auth/google/callback?code=test-code&state=${encodeURIComponent(state)}`,
    headers: { cookie: `lumos_oauth_state=${state}` },
  };
  const res = makeRes();
  await callbackHandler(req, res);
  const cookies = res.headers["set-cookie"];
  const sealed = String(cookies[0]).split(";", 1)[0].split("=").slice(1).join("=");
  return openSession(sealed);
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

test("Lumos ID is stable across sessions and distinct from session id", () => {
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";
  try {
    const first = userClaims({ sid: "session-one" });
    const second = userClaims({ sid: "session-two" });
    assert.equal(sessionLumosId(first), sessionLumosId(second));
    assert.equal(sessionLumosId(first), lumosIdForProviderIdentity("google_web", first.sub));
    assert.notEqual(sessionLumosId(first), first.sid);
  } finally {
    delete process.env.LUMOS_AUTH_STATE_SECRET;
  }
});

test("Google callback seals one stable Lumos ID while creating a new session id", async () => {
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";
  process.env.LUMOS_GOOGLE_WEB_CLIENT_ID = "google-client";
  process.env.LUMOS_GOOGLE_WEB_CLIENT_SECRET = "google-secret";
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url) => {
    if (String(url).includes("oauth2.googleapis.com/token")) {
      return { ok: true, async json() { return { access_token: "temporary-access" }; } };
    }
    return {
      ok: true,
      async json() {
        return { sub: "google-subject-one", name: "Ada Lovelace", email: "ada@example.test" };
      },
    };
  };
  try {
    const first = await runGoogleCallback();
    const second = await runGoogleCallback();
    assert.equal(first.lumos_id, second.lumos_id);
    assert.notEqual(first.sid, second.sid);
    assert.equal(first.package, "base");
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.LUMOS_AUTH_STATE_SECRET;
    delete process.env.LUMOS_GOOGLE_WEB_CLIENT_ID;
    delete process.env.LUMOS_GOOGLE_WEB_CLIENT_SECRET;
  }
});

test("hosted identity rejects a client Lumos ID mismatch", async () => {
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";
  const sealed = sealSession(userClaims());
  try {
    const context = await loadHostedUserContext(
      { headers: { cookie: `lumos_session=${sealed}` } },
      { identity: { lumos_id: "lumos_wrong" }, conversation_id: "conversation-a" },
    );
    assert.equal(context.ok, false);
    assert.equal(context.error, "identity_mismatch");
    assert.equal(context.status, 409);
  } finally {
    delete process.env.LUMOS_AUTH_STATE_SECRET;
  }
});

test("session API and hosted chat expose the same Lumos ID for every package", async () => {
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";
  const claims = userClaims({ package: "free" });
  const expected = sessionLumosId(claims);
  const sealed = sealSession(claims);
  const req = { method: "GET", headers: { cookie: `lumos_session=${sealed}` } };
  const sessionRes = makeRes();
  const chatRes = makeRes();
  try {
    await sessionHandler(req, sessionRes);
    await handler(
      {
        method: "POST",
        headers: req.headers,
        body: {
          message: "Beni tanıyor musun?",
          identity: { lumos_id: expected },
          conversation_id: "new-conversation",
        },
      },
      chatRes,
    );
    const sessionPayload = JSON.parse(sessionRes.body);
    assert.equal(sessionPayload.session.lumos_id, expected);
    assert.equal(chatRes.payload.identity.lumos_id, expected);
    assert.equal(chatRes.payload.identity.package, "free");
    assert.match(chatRes.payload.reply, /Ada Lovelace/);
  } finally {
    delete process.env.LUMOS_AUTH_STATE_SECRET;
  }
});

test("a new conversation does not create a new user identity", async () => {
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";
  const claims = userClaims();
  const sealed = sealSession(claims);
  const req = { headers: { cookie: `lumos_session=${sealed}` } };
  try {
    const first = await loadHostedUserContext(req, { conversation_id: "conversation-one" });
    const second = await loadHostedUserContext(req, { conversation_id: "conversation-two" });
    assert.equal(first.lumos_id, second.lumos_id);
    assert.notEqual(first.conversation_id, second.conversation_id);
  } finally {
    delete process.env.LUMOS_AUTH_STATE_SECRET;
  }
});

test("identity question names the connected user and reports missing memory explicitly", async () => {
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";
  const claims = userClaims();
  const sealed = sealSession(claims);
  try {
    const context = await loadHostedUserContext(
      { headers: { cookie: `lumos_session=${sealed}` } },
      { identity: { lumos_id: sessionLumosId(claims) }, conversation_id: "conversation-a" },
    );
    assert.equal(context.ok, true);
    assert.equal(context.profile.name, "Ada Lovelace");
    assert.equal(context.memory.status, "unavailable");
    assert.match(identityStatusReply("Beni tanıyor musun?", context), /Ada Lovelace/);
    assert.match(identityStatusReply("Beni tanıyor musun?", context), /Oturum bağlı ama kişisel hafıza yüklenmedi/);
  } finally {
    delete process.env.LUMOS_AUTH_STATE_SECRET;
  }
});

test("personal memory is ignored unless the memory service returns explicit consent", async () => {
  process.env.LUMOS_MEMORY_LOOKUP_URL = "https://memory.example.test/lookup";
  process.env.LUMOS_MEMORY_SERVICE_TOKEN = "private-memory-token";
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async () => ({
      ok: true,
      async json() {
        return { consent: false, memories: ["Bu kayıt kullanılmamalı"] };
      },
    });
    assert.deepEqual(await loadAllowedMemory("lumos_test"), {
      status: "not_granted",
      items: [],
    });

    globalThis.fetch = async (_url, init) => {
      assert.equal(init.headers.Authorization, "Bearer private-memory-token");
      assert.equal(JSON.parse(init.body).lumos_id, "lumos_test");
      return {
        ok: true,
        async json() {
          return { consent: true, memories: ["İzinli tercih"] };
        },
      };
    };
    assert.deepEqual(await loadAllowedMemory("lumos_test"), {
      status: "loaded",
      items: ["İzinli tercih"],
    });
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.LUMOS_MEMORY_LOOKUP_URL;
    delete process.env.LUMOS_MEMORY_SERVICE_TOKEN;
  }
});

test("hosted chat calls OpenAI first without exposing its key", async () => {
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";
  process.env.OPENAI_API_KEY = "private-openai-test-key";
  const sealed = sealSession(userClaims());
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
  const sealed = sealSession(userClaims());
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
