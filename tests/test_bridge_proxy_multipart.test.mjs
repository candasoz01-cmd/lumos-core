import assert from "node:assert/strict";
import { Readable } from "node:stream";
import test from "node:test";
import {
  applyForwardBody,
  bufferFromBodyValue,
  forwardRequestHeaders,
  readRawBody,
} from "../api/bridge/[...path].js";

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
      },
    },
    "server-secret",
  );
  assert.equal(headers["content-type"], ct);
  assert.equal(headers["X-Kando-Token"], "server-secret");
  assert.equal(headers.host, undefined);
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

test("handler forwards multipart bytes to upstream fetch mock", async () => {
  const upstreamBase = "http://127.0.0.1:8765";
  const secret = "test-secret";
  const body = buildMultipartBody();
  const contentType = multipartContentType();

  process.env.BRIDGE_UPSTREAM_URL = upstreamBase;
  process.env.KANDO_BRIDGE_SECRET = secret;

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

  const res = {
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
    assert.deepEqual(Buffer.from(captured.init.body), body);
    assert.equal(res.statusCode, 503);
    const payload = JSON.parse(Buffer.from(res.payload).toString("utf8"));
    assert.equal(payload.error, "transcribe_engine_unavailable");
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.BRIDGE_UPSTREAM_URL;
    delete process.env.KANDO_BRIDGE_SECRET;
  }
});
