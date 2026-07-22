import assert from "node:assert/strict";
import test from "node:test";
import * as catchAll from "../api/bridge/[...path].js";
import * as panelUploadRoute from "../api/bridge/panel/upload.js";

const BOUNDARY = "----lumos-panel-upload-test";

function buildMultipartBody(boundary = BOUNDARY) {
  const prefix = Buffer.from(
    `--${boundary}\r\n` +
      `Content-Disposition: form-data; name="file"; filename="note.txt"\r\n` +
      `Content-Type: text/plain\r\n\r\n`,
    "utf8",
  );
  const suffix = Buffer.from(`\r\n--${boundary}--\r\n`, "utf8");
  return Buffer.concat([prefix, Buffer.from("lumos", "utf8"), suffix]);
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

test("dedicated panel/upload route reuses the proxy handler, no forked logic", () => {
  assert.equal(panelUploadRoute.default, catchAll.default);
});

test("dedicated panel/upload route keeps bodyParser disabled", () => {
  assert.equal(panelUploadRoute.config, catchAll.config);
  assert.equal(panelUploadRoute.config.api.bodyParser, false);
});

test("panel/upload resolves from req.url alone (no catch-all query.path)", async () => {
  const upstreamBase = "http://127.0.0.1:8765";
  const secret = "test-secret";
  const proxyAuth = "proxy-auth-token";
  const body = buildMultipartBody();
  const contentType = multipartContentType();

  process.env.BRIDGE_UPSTREAM_URL = upstreamBase;
  process.env.KANDO_BRIDGE_SECRET = secret;
  process.env.LUMOS_BRIDGE_PROXY_AUTH_TOKEN = proxyAuth;

  const originalFetch = globalThis.fetch;
  let captured = null;
  globalThis.fetch = async (url, init) => {
    captured = { url, init };
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  const res = makeRes();
  try {
    // Vercel ayrı dosya route'unda catch-all'ın `query.path` dizisini vermez;
    // segmentler yalnız req.url'den çözülmeli.
    await panelUploadRoute.default(
      {
        method: "POST",
        url: "/api/bridge/panel/upload",
        query: {},
        headers: {
          "content-type": contentType,
          "content-length": String(body.length),
          "x-lumos-bridge-auth": proxyAuth,
        },
        body,
      },
      res,
    );

    assert.ok(captured, "upstream fetch çağrılmalı");
    // Canonical upstream yolu korunur: rewrite/alias yok.
    assert.equal(captured.url, `${upstreamBase}/panel/upload`);
    assert.equal(captured.init.method, "POST");
    assert.equal(captured.init.headers["content-type"], contentType);
    assert.equal(captured.init.headers["X-Kando-Token"], secret);
    assert.deepEqual(Buffer.from(captured.init.body), body);
    assert.equal(res.statusCode, 200);
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.BRIDGE_UPSTREAM_URL;
    delete process.env.KANDO_BRIDGE_SECRET;
    delete process.env.LUMOS_BRIDGE_PROXY_AUTH_TOKEN;
  }
});

test("panel/upload without caller auth returns 401, not a routing 404", async () => {
  process.env.BRIDGE_UPSTREAM_URL = "http://127.0.0.1:8765";
  process.env.KANDO_BRIDGE_SECRET = "test-secret";
  process.env.LUMOS_BRIDGE_PROXY_AUTH_TOKEN = "proxy-auth-token";

  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new Error("fetch should not be called without proxy auth");
  };

  const res = makeRes();
  try {
    await panelUploadRoute.default(
      {
        method: "POST",
        url: "/api/bridge/panel/upload",
        query: {},
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

test("panel/upload keeps the secret-unconfigured guard closed", async () => {
  process.env.BRIDGE_UPSTREAM_URL = "http://127.0.0.1:8765";
  process.env.LUMOS_BRIDGE_PROXY_AUTH_TOKEN = "proxy-auth-token";
  delete process.env.KANDO_BRIDGE_SECRET;

  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new Error("fetch should not be called when the bridge secret is missing");
  };

  const res = makeRes();
  try {
    await panelUploadRoute.default(
      {
        method: "POST",
        url: "/api/bridge/panel/upload",
        query: {},
        headers: {
          "content-type": multipartContentType(),
          "x-lumos-bridge-auth": "proxy-auth-token",
        },
        body: buildMultipartBody(),
      },
      res,
    );

    assert.equal(res.statusCode, 503);
    assert.equal(res.payload.error, "bridge_proxy_secret_unconfigured");
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.BRIDGE_UPSTREAM_URL;
    delete process.env.LUMOS_BRIDGE_PROXY_AUTH_TOKEN;
    delete process.env.KANDO_BRIDGE_SECRET;
  }
});
