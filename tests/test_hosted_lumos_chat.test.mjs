import assert from "node:assert/strict";
import test from "node:test";
import handler from "../api/bridge/chat.js";
import sessionHandler from "../api/auth/session.js";
import callbackHandler from "../api/auth/google/callback.js";
import {
  buildGeminiRequest,
  buildOpenAIRequest,
  explicitMemoryText,
  geminiReply,
  hasLumosSession,
  identityStatusReply,
  loadAllowedMemory,
  loadHostedUserContext,
  localTimeReply,
  memoryWriteStatusReply,
  openAIReply,
  rememberExplicitMemory,
} from "../api/_lib/hosted_lumos.js";
import {
  authSecret,
  lumosIdForProviderIdentity,
  makeState,
  MOBILE_OAUTH_COOKIE,
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

test("session cryptography fails closed when no server secret exists", () => {
  const stateSecret = process.env.LUMOS_AUTH_STATE_SECRET;
  const clientSecret = process.env.LUMOS_GOOGLE_WEB_CLIENT_SECRET;
  delete process.env.LUMOS_AUTH_STATE_SECRET;
  delete process.env.LUMOS_GOOGLE_WEB_CLIENT_SECRET;
  try {
    assert.throws(() => authSecret(), /lumos_auth_secret_unconfigured/);
  } finally {
    if (stateSecret) process.env.LUMOS_AUTH_STATE_SECRET = stateSecret;
    if (clientSecret) process.env.LUMOS_GOOGLE_WEB_CLIENT_SECRET = clientSecret;
  }
});

test("hosted local replies still work when the connected profile is unavailable", async () => {
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";
  const sealed = sealSession(userClaims({ name: "", email: "" }));
  const res = makeRes();
  try {
    await handler(
      {
        method: "POST",
        headers: { cookie: `lumos_session=${sealed}` },
        body: { message: "Saat kaç?" },
      },
      res,
    );
    assert.equal(res.statusCode, 200);
    assert.equal(res.payload.mode, "hosted_local");
    assert.equal(res.payload.identity.profile_status, "unavailable");
  } finally {
    delete process.env.LUMOS_AUTH_STATE_SECRET;
  }
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

test("Google callback returns a sealed mobile session to the requesting app state", async () => {
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
  const oauthState = makeState();
  const appState = "mobile_state_12345678901234567890";
  const mobileFlow = sealSession({
    kind: "mobile_oauth",
    app_state: appState,
    // Akış bu denemeye bağlıdır: oauth_state, callback'e gelen state ile eşleşmeli.
    oauth_state: oauthState,
    exp: Math.floor(Date.now() / 1000) + 60,
  });
  const req = {
    method: "GET",
    url: `/api/auth/google/callback?code=test-code&state=${encodeURIComponent(oauthState)}`,
    headers: {
      cookie: `lumos_oauth_state=${oauthState}; ${MOBILE_OAUTH_COOKIE}=${mobileFlow}`,
    },
  };
  const res = makeRes();
  try {
    await callbackHandler(req, res);
    assert.equal(res.statusCode, 302);
    const location = new URL(res.headers.location);
    assert.equal(location.protocol, "lumos:");
    const fragment = new URLSearchParams(location.hash.slice(1));
    assert.equal(fragment.get("state"), appState);
    const mobileClaims = openSession(fragment.get("session"));
    assert.equal(mobileClaims.email, "ada@example.test");
    assert.equal(mobileClaims.lumos_id, lumosIdForProviderIdentity("google_web", "google-subject-one"));
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

test("hosted memory reuses the configured private bridge by default", async () => {
  process.env.BRIDGE_UPSTREAM_URL = "https://bridge.example.test/";
  process.env.KANDO_BRIDGE_SECRET = "existing-bridge-secret";
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async (url, init) => {
      assert.equal(url, "https://bridge.example.test/memory/hosted/lookup");
      assert.equal(init.headers.Authorization, "Bearer existing-bridge-secret");
      return {
        ok: true,
        async json() {
          return { consent: true, memories: [] };
        },
      };
    };
    assert.deepEqual(await loadAllowedMemory("lumos_test"), {
      status: "empty",
      items: [],
    });
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.BRIDGE_UPSTREAM_URL;
    delete process.env.KANDO_BRIDGE_SECRET;
  }
});

test("explicit memory intent is narrow and does not capture ordinary chat", () => {
  assert.equal(explicitMemoryText("Bunu hatırla: Çayı şekersiz içerim"), "Çayı şekersiz içerim");
  assert.equal(explicitMemoryText("Please remember that I prefer short answers"), "I prefer short answers");
  assert.equal(explicitMemoryText("Bugün ne yapalım?"), "");
});

test("explicit memory write stays closed without consent", async () => {
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async () => {
      throw new Error("fetch_must_not_run");
    };
    assert.deepEqual(
      await rememberExplicitMemory(
        "lumos_test",
        "Bunu hatırla: Çayı şekersiz içerim",
        "google_web",
        "not_granted",
      ),
      { status: "consent_required" },
    );
    assert.equal(
      memoryWriteStatusReply({ memory_write_status: "consent_required" }),
      "Kişisel hafıza iznin kapalı; bu bilgiyi kaydetmedim.",
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("explicit memory write uses the consent-gated sibling endpoint", async () => {
  process.env.LUMOS_MEMORY_LOOKUP_URL = "https://memory.example.test/memory/hosted/lookup";
  process.env.LUMOS_MEMORY_SERVICE_TOKEN = "private-memory-token";
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async (url, init) => {
      assert.equal(url, "https://memory.example.test/memory/hosted/remember");
      assert.equal(init.headers.Authorization, "Bearer private-memory-token");
      assert.deepEqual(JSON.parse(init.body), {
        lumos_id: "lumos_test",
        summary: "Çayı şekersiz içerim",
        source_provider: "google_web",
      });
      return {
        ok: true,
        async json() {
          return { ok: true, stored: true };
        },
      };
    };
    assert.deepEqual(
      await rememberExplicitMemory(
        "lumos_test",
        "Hatırla: Çayı şekersiz içerim",
        "google_web",
        "empty",
      ),
      { status: "stored", summary: "Çayı şekersiz içerim" },
    );
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
    // PR-005: sağlayıcı kanıtı Authorization başlığıdır; yanıt gövdesinde olmaz.
    assert.equal("provider" in res.payload, false);
    assert.equal("model" in res.payload, false);
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
    // PR-005: yedeğe düşüldüğü iki ayrı çağrıdan anlaşılır, yanıt gövdesinden değil.
    assert.equal("provider" in res.payload, false);
    assert.equal(res.payload.reply, "Yedek yanıt");
    assert.equal(urls.length, 2);
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.LUMOS_AUTH_STATE_SECRET;
    delete process.env.OPENAI_API_KEY;
    delete process.env.LUMOS_GOOGLE_GEMINI_API_KEY;
  }
});

test("hosted chat accepts a sealed mobile bearer session", async () => {
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";
  const claims = userClaims();
  const sealed = sealSession(claims);
  try {
    const context = await loadHostedUserContext(
      { headers: { authorization: `Bearer ${sealed}` } },
      { conversation_id: "mobile-conversation" },
    );
    assert.equal(context.ok, true);
    assert.equal(context.lumos_id, sessionLumosId(claims));
    assert.equal(context.conversation_id, "mobile-conversation");
  } finally {
    delete process.env.LUMOS_AUTH_STATE_SECRET;
  }
});

test("stale mobile oauth cookie cannot hijack a web login", async () => {
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";
  const now = Math.floor(Date.now() / 1000);
  try {
    // Terk edilmiş/paralel bir mobil akıştan kalan çerez: oauth_state BAŞKA.
    const staleFlow = sealSession({
      kind: "mobile_oauth",
      app_state: "abandoned-mobile-app-state-value",
      oauth_state: makeState(),
      iat: now,
      exp: now + 600,
    });
    const webState = makeState();
    const req = {
      method: "GET",
      url: `/api/auth/google/callback?error=access_denied&state=${encodeURIComponent(webState)}`,
      headers: {
        cookie: `lumos_oauth_state=${webState}; ${MOBILE_OAUTH_COOKIE}=${staleFlow}`,
      },
    };
    const res = makeRes();
    await callbackHandler(req, res);

    // Web girişi deep-link'e kaçırılmamalı.
    assert.equal(res.statusCode, 302);
    assert.ok(String(res.headers["location"]).startsWith("/auth?error="));
    assert.ok(!String(res.headers["location"]).includes("lumos://"));
  } finally {
    delete process.env.LUMOS_AUTH_STATE_SECRET;
  }
});

test("bridge session check accepts the same bearer token as hosted chat", () => {
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";
  try {
    const sealed = sealSession(userClaims());
    const flowToken = sealSession({
      kind: "mobile_oauth",
      nonce: "flow-only",
      exp: Math.floor(Date.now() / 1000) + 60,
    });
    const bearerReq = { headers: { authorization: `Bearer ${sealed}` } };
    // hasLumosSession ile hostedSessionClaims aynı kaynağı görmeli:
    // aksi halde /bridge/health 401 verirken /mobile/chat çalışır.
    assert.equal(hasLumosSession(bearerReq), true);
    assert.equal(
      hasLumosSession({ headers: { authorization: `Bearer ${flowToken}` } }),
      false,
    );
    assert.equal(hasLumosSession({ headers: {} }), false);
  } finally {
    delete process.env.LUMOS_AUTH_STATE_SECRET;
  }
});
