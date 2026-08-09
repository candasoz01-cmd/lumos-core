import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { Readable } from "node:stream";
import test from "node:test";

import handler, { config } from "../api/webhooks/meta.js";
import { RawBodyTooLargeError, readBoundedRawBody } from "../api/_lib/raw_body.js";

function response() {
  return {
    statusCode: 0,
    headers: {},
    setHeader(name, value) { this.headers[name.toLowerCase()] = value; },
    end(body) { this.body = body; },
  };
}

function configure() {
  process.env.LUMOS_META_WEBHOOK_VERIFY_TOKEN = "verify-token";
  process.env.LUMOS_META_APP_SECRET = "meta-app-secret";
  process.env.LUMOS_INSTAGRAM_APP_SECRET = "instagram-app-secret";
  process.env.LUMOS_META_WEBHOOK_SINK_URL = "https://sink.test/meta";
  process.env.LUMOS_META_WEBHOOK_SINK_TOKEN = "sink-token";
}

function cleanup() {
  for (const key of [
    "LUMOS_META_WEBHOOK_VERIFY_TOKEN",
    "LUMOS_META_APP_SECRET",
    "LUMOS_INSTAGRAM_APP_SECRET",
    "LUMOS_META_WEBHOOK_SINK_URL",
    "LUMOS_META_WEBHOOK_SINK_TOKEN",
    "LUMOS_META_WEBHOOK_MAX_BYTES",
  ]) delete process.env[key];
}

function signature(body, secret = "meta-app-secret") {
  return `sha256=${createHmac("sha256", secret).update(body).digest("hex")}`;
}

test("Meta webhook keeps Vercel body parsing disabled", () => {
  assert.equal(config.api.bodyParser, false);
});

test("Raw webhook reader preserves streamed bytes and enforces the limit", async () => {
  const body = await readBoundedRawBody(Readable.from([Buffer.from("abc"), Buffer.from("def")]), 6);
  assert.equal(body.toString("utf8"), "abcdef");
  await assert.rejects(
    readBoundedRawBody(Readable.from([Buffer.alloc(4), Buffer.alloc(3)]), 6),
    RawBodyTooLargeError,
  );
});

test("Empty preloaded body does not hide signed bytes still available on the stream", async () => {
  const request = Readable.from([Buffer.from("signed-stream-body")]);
  request.body = Buffer.alloc(0);
  const body = await readBoundedRawBody(request, 64);
  assert.equal(body.toString("utf8"), "signed-stream-body");
});

test("Meta webhook challenge requires the configured verify token", async () => {
  configure();
  try {
    const accepted = response();
    await handler({
      method: "GET",
      url: "/api/webhooks/meta?hub.mode=subscribe&hub.verify_token=verify-token&hub.challenge=challenge-123",
      headers: {},
    }, accepted);
    assert.equal(accepted.statusCode, 200);
    assert.equal(accepted.body, "challenge-123");

    const rejected = response();
    await handler({
      method: "GET",
      url: "/api/webhooks/meta?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=challenge-123",
      headers: {},
    }, rejected);
    assert.equal(rejected.statusCode, 403);
    assert.doesNotMatch(rejected.body, /verify-token/);
  } finally {
    cleanup();
  }
});

test("Invalid webhook signature is rejected before the private sink", async () => {
  configure();
  const originalFetch = globalThis.fetch;
  let fetched = false;
  try {
    globalThis.fetch = async () => { fetched = true; throw new Error("unexpected_fetch"); };
    const body = Buffer.from(JSON.stringify({ object: "page", entry: [] }));
    const res = response();
    await handler({ method: "POST", body, headers: { "x-hub-signature-256": "sha256=00" } }, res);
    assert.equal(res.statusCode, 401);
    assert.equal(fetched, false);
  } finally {
    globalThis.fetch = originalFetch;
    cleanup();
  }
});

test("Signed WhatsApp webhook is sent to the durable sink with an opaque replay key", async () => {
  configure();
  const originalFetch = globalThis.fetch;
  let request;
  try {
    const body = Buffer.from(JSON.stringify({ object: "whatsapp_business_account", entry: [{ id: "waba-1" }] }));
    globalThis.fetch = async (url, init) => {
      request = { url: String(url), init, body: JSON.parse(init.body) };
      return { ok: true, async json() { return { ok: true, status: "accepted" }; } };
    };
    const res = response();
    await handler({ method: "POST", body, headers: { "x-hub-signature-256": signature(body) } }, res);
    assert.equal(res.statusCode, 200);
    assert.deepEqual(JSON.parse(res.body), { ok: true, status: "accepted" });
    assert.equal(request.url, "https://sink.test/meta");
    assert.equal(request.init.headers.Authorization, "Bearer sink-token");
    assert.equal(request.body.operation, "webhook.ingest");
    assert.equal(request.body.provider, "whatsapp");
    assert.match(request.body.event_key, /^[a-f0-9]{64}$/);
    assert.doesNotMatch(res.body, /waba-1|sink-token/);
  } finally {
    globalThis.fetch = originalFetch;
    cleanup();
  }
});

test("Instagram app secret is accepted and durable duplicate is acknowledged", async () => {
  configure();
  const originalFetch = globalThis.fetch;
  try {
    const body = Buffer.from(JSON.stringify({ object: "instagram", entry: [{ id: "ig-1" }] }));
    globalThis.fetch = async () => ({
      ok: true,
      async json() { return { ok: true, status: "duplicate" }; },
    });
    const res = response();
    await handler({
      method: "POST",
      body,
      headers: { "x-hub-signature-256": signature(body, "instagram-app-secret") },
    }, res);
    assert.equal(res.statusCode, 200);
    assert.deepEqual(JSON.parse(res.body), { ok: true, status: "duplicate" });
  } finally {
    globalThis.fetch = originalFetch;
    cleanup();
  }
});

test("WhatsApp app secret signs webhooks when the Business app split is active", async () => {
  configure();
  process.env.LUMOS_WHATSAPP_APP_SECRET = "whatsapp-app-secret";
  const originalFetch = globalThis.fetch;
  try {
    const body = Buffer.from(JSON.stringify({ object: "whatsapp_business_account", entry: [{ id: "waba-1" }] }));
    globalThis.fetch = async () => ({
      ok: true,
      async json() { return { ok: true, status: "accepted" }; },
    });
    const res = response();
    await handler({
      method: "POST",
      body,
      headers: { "x-hub-signature-256": signature(body, "whatsapp-app-secret") },
    }, res);
    assert.equal(res.statusCode, 200);
    assert.deepEqual(JSON.parse(res.body), { ok: true, status: "accepted" });
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.LUMOS_WHATSAPP_APP_SECRET;
    cleanup();
  }
});

test("Webhook body limit fails closed before signature or sink processing", async () => {
  configure();
  process.env.LUMOS_META_WEBHOOK_MAX_BYTES = "1024";
  const originalFetch = globalThis.fetch;
  let fetched = false;
  try {
    globalThis.fetch = async () => { fetched = true; throw new Error("unexpected_fetch"); };
    const body = Buffer.alloc(1025, 65);
    const res = response();
    await handler({ method: "POST", body, headers: { "x-hub-signature-256": signature(body) } }, res);
    assert.equal(res.statusCode, 413);
    assert.equal(fetched, false);
  } finally {
    globalThis.fetch = originalFetch;
    cleanup();
  }
});

test("Valid signed webhook fails closed when durable sink is unavailable", async () => {
  configure();
  delete process.env.LUMOS_META_WEBHOOK_SINK_TOKEN;
  try {
    const body = Buffer.from(JSON.stringify({ object: "page", entry: [] }));
    const res = response();
    await handler({ method: "POST", body, headers: { "x-hub-signature-256": signature(body) } }, res);
    assert.equal(res.statusCode, 503);
    assert.equal(JSON.parse(res.body).error, "meta_webhook_sink_not_configured");
  } finally {
    cleanup();
  }
});
