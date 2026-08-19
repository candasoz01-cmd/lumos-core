import assert from "node:assert/strict";
import test from "node:test";

import handler from "../api/mobile/workspace-hub.js";
import { sealSession } from "../api/_lib/lumos_session.js";

const LUMOS_ID = `lumos_${"H".repeat(24)}`;
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

function bearerRequest(method = "GET") {
  const sealed = sealSession({
    sid: "mobile-hub-session",
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

test("mobile workspace hub is GET-only and requires authentication", async () => {
  const method = makeRes();
  await handler(bearerRequest("POST"), method);
  assert.equal(method.statusCode, 405);

  const auth = makeRes();
  await handler({ method: "GET", headers: {} }, auth);
  assert.equal(auth.statusCode, 401);
  assert.equal(auth.payload.error, "unauthorized");
});

test("mobile workspace hub returns a fail-closed live snapshot", async () => {
  const res = makeRes();
  await handler(bearerRequest(), res);

  assert.equal(res.statusCode, 200);
  assert.equal(res.headers["cache-control"], "no-store");
  assert.equal(res.payload.ok, true);
  assert.equal(res.payload.hub.source, "live");
  assert.deepEqual(res.payload.hub.quick_access, ["chat", "cloud"]);
  assert.deepEqual(res.payload.hub.approvals, []);
  assert.deepEqual(res.payload.hub.activities, []);

  const cards = Object.fromEntries(
    res.payload.hub.cards.map((item) => [item.workspace_id, item]),
  );
  assert.equal(Object.keys(cards).length, 9);
  assert.equal(cards.chat.state, "connected");
  assert.equal(cards.chat.detail.account_connection_verified, true);
  assert.equal(cards.chat.detail.operations_enabled, false);
  assert.equal(cards.cloud.state, "connected");
  assert.equal(cards.cloud.summary, "Lumos bulut hizmeti erişilebilir");
  assert.equal(cards.cloud.detail.account_connection_verified, false);
  assert.equal(cards.cloud.detail.service_reachability_verified, true);
  assert.equal(cards.cloud.detail.operations_enabled, false);
  for (const workspace of ["mail", "social", "calendar", "files", "tasks", "admin", "github"]) {
    assert.equal(cards[workspace].state, "disconnected");
    assert.equal(cards[workspace].detail.account_connection_verified, false);
    assert.equal(cards[workspace].detail.service_reachability_verified, false);
    assert.equal(cards[workspace].detail.operations_enabled, false);
  }

  const raw = JSON.stringify(res.payload);
  assert.doesNotMatch(raw, /mobile-hub-session|google-subject|lumos_[A-Z]+/);
  assert.doesNotMatch(raw, /\b(?:kando|cando)\b/i);
});

test.after(() => {
  delete process.env.LUMOS_AUTH_STATE_SECRET;
});
