import assert from "node:assert/strict";
import { Readable } from "node:stream";
import test from "node:test";
import {
  applyForwardBody,
  bufferFromBodyValue,
  forwardRequestHeaders,
  isAllowedBridgePath,
  isAuthenticatedLumosSession,
  isProxyCallerAuthorized,
  readRawBody,
} from "../api/bridge/[...path].js";
import { sealSession } from "../api/_lib/lumos_session.js";

const BOUNDARY = "----lumos-proxy-multipart-test";
const AUDIO = Buffer.from([0x1a, 0x45, 0xdf, 0xa3]);

function buildMultipartBody(
  audio = AUDIO,
  boundary = BOUNDARY,
  field = "audio",
  filename = "clip.webm",
) {
  const prefix = Buffer.from(
    `--${boundary}\r\n` +
      `Content-Disposition: form-data; name="${field}"; filename="${filename}"\r\n` +
      `Content-Type: audio/webm\r\n\r\n`,
    "utf8",
  );
  const suffix = Buffer.from(`\r\n--${boundary}--\r\n`, "utf8");
  return Buffer.concat([prefix, audio, suffix]);
}

function multipartContentType(boundary = BOUNDARY) {
  return `multipart/form-data; boundary=${boundary}`;
}

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
    send(payload) {
      this.payload = payload;
      return this;
    },
    json(payload) {
      this.payload = payload;
      return this;
    },
  };
}

test("bufferFromBodyValue accepts Buffer, Uint8Array, and string", () => {
  const buf = Buffer.from("abc");
  assert.equal(bufferFromBodyValue(buf), buf);
  assert.deepEqual(bufferFromBodyValue(new Uint8Array([1, 2])), Buffer.from([1, 2]));
  assert.deepEqual(bufferFromBodyValue("hi"), Buffer.from("hi", "utf8"));
  assert.equal(bufferFromBodyValue(null), null);
});

test("readRawBody uses preloaded req.body buffer (Vercel dev path)", async () => {
  const body = buildMultipartBody();
  const req = {
    body,
    headers: { "content-type": multipartContentType() },
  };
  const raw = await readRawBody(req);
  assert.deepEqual(raw, body);
});

test("readRawBody reads Node stream via data/end events", async () => {
  const body = buildMultipartBody();
  const stream = Readable.from([body]);
  const raw = await readRawBody(stream);
  assert.deepEqual(raw, body);
});

test("readRawBody reads async iterable request", async () => {
  const body = buildMultipartBody();
  const req = {
    async *[Symbol.asyncIterator]() {
      yield body.subarray(0, 8);
      yield body.subarray(8);
    },
  };
  const raw = await readRawBody(req);
  assert.deepEqual(raw, body);
});

test("forwardRequestHeaders preserves multipart Content-Type boundary", () => {
  const ct = multipartContentType();
  const headers = forwardRequestHeaders(
    {
      headers: {
        "content-type": ct,
        host: "localhost:3000",
        "x-kando-token": "client-should-not-forward",
        "x-lumos-bridge-auth": "proxy-auth-should-not-forward",
        authorization: "Bearer browser-session-should-not-forward",
        cookie: "lumos_bridge_proxy_auth=proxy-auth-should-not-forward",
      },
    },
    "server-secret",
  );
  assert.equal(headers["content-type"], ct);
  assert.equal(headers["X-Kando-Token"], "server-secret");
  assert.equal(headers.host, undefined);
  assert.equal(headers["x-kando-token"], undefined);
  assert.equal(headers["x-lumos-bridge-auth"], undefined);
  assert.equal(headers.authorization, undefined);
  assert.equal(headers.cookie, undefined);
});

test("applyForwardBody sets body and matching content-length", () => {
  const body = buildMultipartBody();
  const init = {
    method: "POST",
    headers: {
      "content-type": multipartContentType(),
      "content-length": "9999",
    },
  };
  applyForwardBody(init, body);
  assert.deepEqual(init.body, body);
  assert.equal(init.headers["content-length"], String(body.length));
});

test("bridge proxy path allowlist only accepts supported routes", () => {
  assert.equal(isAllowedBridgePath(["task"]), true);
  assert.equal(isAllowedBridgePath(["chat"]), true);
  assert.equal(isAllowedBridgePath(["last-result"]), true);
  assert.equal(isAllowedBridgePath(["controlled"]), true);
  assert.equal(isAllowedBridgePath(["transcribe"]), true);
  assert.equal(isAllowedBridgePath(["health"]), true);
  assert.equal(isAllowedBridgePath(["status"]), true);
  assert.equal(isAllowedBridgePath(["panel", "upload"]), true);
  assert.equal(isAllowedBridgePath(["task", "extra"]), false);
  assert.equal(isAllowedBridgePath(["admin", "delete"]), false);
  assert.equal(isAllowedBridgePath([]), false);
});

test("bridge proxy caller auth accepts header or cookie token", () => {
  assert.equal(
    isProxyCallerAuthorized(
      { headers: { "x-lumos-bridge-auth": "proxy-auth-token" } },
      "proxy-auth-token",
    ),
    true,
  );
  assert.equal(
    isProxyCallerAuthorized(
      { headers: { cookie: "theme=light; lumos_bridge_proxy_auth=proxy-auth-token" } },
      "proxy-auth-token",
    ),
    true,
  );
  assert.equal(
    isProxyCallerAuthorized(
      { headers: { "x-lumos-bridge-auth": "wrong-token" } },
      "proxy-auth-token",
    ),
    false,
  );
  assert.equal(
    isProxyCallerAuthorized(
      { headers: { cookie: "lumos_bridge_proxy_auth=%E0%A4%A" } },
      "proxy-auth-token",
    ),
    false,
  );
});

test("bridge proxy accepts a valid sealed Lumos session", () => {
  process.env.LUMOS_AUTH_STATE_SECRET = "test-only-secret-32-characters-minimum";
  try {
    const sealed = sealSession({
      sid: "session-test",
      email: "user@example.invalid",
      exp: Math.floor(Date.now() / 1000) + 60,
    });
    assert.equal(
      isAuthenticatedLumosSession({
        headers: { cookie: `lumos_session=${sealed}` },
      }),
      true,
    );
    assert.equal(
      isAuthenticatedLumosSession({
        headers: { cookie: "lumos_session=invalid" },
      }),
      false,
    );
  } finally {
    delete process.env.LUMOS_AUTH_STATE_SECRET;
  }
});

test("handler rejects disallowed bridge paths before upstream fetch", async () => {
  process.env.BRIDGE_UPSTREAM_URL = "http://127.0.0.1:8765";
  process.env.KANDO_BRIDGE_SECRET = "test-secret";
  process.env.LUMOS_BRIDGE_PROXY_AUTH_TOKEN = "proxy-auth-token";

  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new Error("fetch should not be called for disallowed bridge paths");
  };

  const res = makeRes();
  try {
    const { default: handler } = await import("../api/bridge/[...path].js");
    await handler(
      {
        method: "GET",
        url: "/api/bridge/admin/delete",
        query: { path: ["admin", "delete"] },
        headers: { "x-lumos-bridge-auth": "proxy-auth-token" },
      },
      res,
    );

    assert.equal(res.statusCode, 404);
    assert.equal(res.payload.error, "bridge_proxy_forbidden");
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.BRIDGE_UPSTREAM_URL;
    delete process.env.KANDO_BRIDGE_SECRET;
    delete process.env.LUMOS_BRIDGE_PROXY_AUTH_TOKEN;
  }
});

test("handler rejects missing proxy caller auth before upstream fetch", async () => {
  process.env.BRIDGE_UPSTREAM_URL = "http://127.0.0.1:8765";
  process.env.KANDO_BRIDGE_SECRET = "test-secret";
  process.env.LUMOS_BRIDGE_PROXY_AUTH_TOKEN = "proxy-auth-token";

  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new Error("fetch should not be called without proxy auth");
  };

  const res = makeRes();
  try {
    const { default: handler } = await import("../api/bridge/[...path].js");
    await handler(
      {
        method: "POST",
        url: "/api/bridge/transcribe",
        query: { path: ["transcribe"] },
        headers: { "content-type": multipartContentType() },
        body: buildMultipartBody(),
      },
      res,
    );

    assert.equal(res.statusCode, 401);
    assert.equal(res.payload.error, "bridge_proxy_unauthorized");
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.BRIDGE_UPSTREAM_URL;
    delete process.env.KANDO_BRIDGE_SECRET;
    delete process.env.LUMOS_BRIDGE_PROXY_AUTH_TOKEN;
  }
});

test("handler keeps proxy closed when proxy auth env is not configured", async () => {
  process.env.BRIDGE_UPSTREAM_URL = "http://127.0.0.1:8765";
  process.env.KANDO_BRIDGE_SECRET = "test-secret";
  delete process.env.LUMOS_BRIDGE_PROXY_AUTH_TOKEN;

  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new Error("fetch should not be called when proxy auth env is missing");
  };

  const res = makeRes();
  try {
    const { default: handler } = await import("../api/bridge/[...path].js");
    await handler(
      {
        method: "POST",
        url: "/api/bridge/task",
        query: { path: ["task"] },
        headers: { "x-lumos-bridge-auth": "proxy-auth-token" },
        body: Buffer.from("{}"),
      },
      res,
    );

    assert.equal(res.statusCode, 503);
    assert.equal(res.payload.error, "bridge_proxy_auth_unconfigured");
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.BRIDGE_UPSTREAM_URL;
    delete process.env.KANDO_BRIDGE_SECRET;
    delete process.env.LUMOS_BRIDGE_PROXY_AUTH_TOKEN;
  }
});

test("handler forwards multipart bytes and skips the ngrok browser interstitial", async () => {
  const upstreamBase = "https://demo.ngrok-free.dev";
  const secret = "test-secret";
  const proxyAuth = "proxy-auth-token";
  const body = buildMultipartBody();
  const contentType = multipartContentType();

  process.env.BRIDGE_UPSTREAM_URL = upstreamBase;
  process.env.KANDO_BRIDGE_SECRET = secret;
  process.env.LUMOS_BRIDGE_PROXY_AUTH_TOKEN = proxyAuth;

  const originalFetch = globalThis.fetch;
  /** @type {{ url?: string, init?: RequestInit } | null} */
  let captured = null;
  globalThis.fetch = async (url, init) => {
    captured = { url, init };
    return new Response(
      JSON.stringify({
        ok: false,
        error: "transcribe_engine_unavailable",
        message: "Ses metne çeviri motoru henüz bağlı değil.",
      }),
      {
        status: 503,
        headers: { "content-type": "application/json" },
      },
    );
  };

  const res = makeRes();

  try {
    const { default: handler } = await import("../api/bridge/[...path].js");
    await handler(
      {
        method: "POST",
        url: "/api/bridge/transcribe",
        query: { path: ["transcribe"] },
        headers: {
          "content-type": contentType,
          "content-length": String(body.length),
          "x-lumos-bridge-auth": proxyAuth,
        },
        body,
      },
      res,
    );

    assert.ok(captured);
    assert.equal(captured.url, `${upstreamBase}/transcribe`);
    assert.equal(captured.init.method, "POST");
    assert.equal(captured.init.headers["content-type"], contentType);
    assert.equal(captured.init.headers["content-length"], String(body.length));
    assert.equal(captured.init.headers["X-Kando-Token"], secret);
    assert.equal(captured.init.headers["ngrok-skip-browser-warning"], "1");
    assert.deepEqual(Buffer.from(captured.init.body), body);
    assert.equal(res.statusCode, 503);
    const payload = JSON.parse(Buffer.from(res.payload).toString("utf8"));
    assert.equal(payload.error, "transcribe_engine_unavailable");
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.BRIDGE_UPSTREAM_URL;
    delete process.env.KANDO_BRIDGE_SECRET;
    delete process.env.LUMOS_BRIDGE_PROXY_AUTH_TOKEN;
  }
});
