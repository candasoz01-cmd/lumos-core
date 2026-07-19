import assert from "node:assert/strict";
import test from "node:test";
import { captureError, captureSecurityEvent, logEvent } from "../api/_lib/observability.js";

test("captureError is a silent no-op when SENTRY_DSN is unset", async () => {
  delete process.env.SENTRY_DSN;
  let called = false;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    called = true;
    return { ok: true };
  };
  try {
    await captureError(new Error("should not send"), { route: "test" });
    assert.equal(called, false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("logEvent is a silent no-op when LUMOS_AXIOM_TOKEN is unset", async () => {
  delete process.env.LUMOS_AXIOM_TOKEN;
  let called = false;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    called = true;
    return { ok: true };
  };
  try {
    await logEvent("test.event", { route: "test" });
    assert.equal(called, false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("captureError posts to the DSN's store endpoint and never leaks disallowed fields", async () => {
  process.env.SENTRY_DSN = "https://public_key_abc@o123.ingest.sentry.io/456";
  const originalFetch = globalThis.fetch;
  let capturedUrl;
  let capturedBody;
  globalThis.fetch = async (url, init) => {
    capturedUrl = String(url);
    capturedBody = init.body;
    return { ok: true };
  };
  try {
    await captureError(new Error("token_http_error"), {
      route: "google_callback",
      errorCode: "token_http_error",
      status: 400,
      email: "user@example.test",
      access_token: "should-never-appear",
      code: "should-never-appear",
      sub: "should-never-appear",
    });
    assert.equal(capturedUrl, "https://o123.ingest.sentry.io/api/456/store/");
    const parsed = JSON.parse(capturedBody);
    assert.equal(parsed.message, "token_http_error");
    assert.equal(parsed.extra.route, "google_callback");
    assert.equal(parsed.extra.errorCode, "token_http_error");
    assert.equal(JSON.stringify(parsed).includes("example.test"), false);
    assert.equal(JSON.stringify(parsed).includes("should-never-appear"), false);
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.SENTRY_DSN;
  }
});

test("logEvent posts to the Axiom ingest endpoint for the configured dataset", async () => {
  process.env.LUMOS_AXIOM_TOKEN = "test-axiom-token";
  process.env.LUMOS_AXIOM_DATASET = "lumos-test";
  const originalFetch = globalThis.fetch;
  let capturedUrl;
  let capturedHeaders;
  let capturedBody;
  globalThis.fetch = async (url, init) => {
    capturedUrl = String(url);
    capturedHeaders = init.headers;
    capturedBody = init.body;
    return { ok: true };
  };
  try {
    await logEvent("oauth.callback.success", { route: "google_callback", lumosId: "lumos_abc123" });
    assert.equal(capturedUrl, "https://api.axiom.co/v1/datasets/lumos-test/ingest");
    assert.equal(capturedHeaders.Authorization, "Bearer test-axiom-token");
    const parsed = JSON.parse(capturedBody);
    assert.equal(parsed[0].event, "oauth.callback.success");
    assert.equal(parsed[0].lumosId, "lumos_abc123");
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.LUMOS_AXIOM_TOKEN;
    delete process.env.LUMOS_AXIOM_DATASET;
  }
});

test("captureSecurityEvent fans out to both Axiom and Sentry without throwing when unconfigured", async () => {
  delete process.env.SENTRY_DSN;
  delete process.env.LUMOS_AXIOM_TOKEN;
  await assert.doesNotReject(captureSecurityEvent("invalid_state", { route: "google_callback" }));
});

test("capture helpers never throw even if the network call fails", async () => {
  process.env.SENTRY_DSN = "https://public_key_abc@o123.ingest.sentry.io/456";
  process.env.LUMOS_AXIOM_TOKEN = "test-axiom-token";
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new Error("network down");
  };
  try {
    await assert.doesNotReject(captureError(new Error("boom"), { route: "x" }));
    await assert.doesNotReject(logEvent("x", {}));
    await assert.doesNotReject(captureSecurityEvent("x", {}));
  } finally {
    globalThis.fetch = originalFetch;
    delete process.env.SENTRY_DSN;
    delete process.env.LUMOS_AXIOM_TOKEN;
  }
});
