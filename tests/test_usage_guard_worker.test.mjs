import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";

import { signRequest } from "../ops/usage-guard/auth.mjs";
import { handleRequest, UsageCounter } from "../ops/usage-guard/worker.mjs";
import { signUsageRequest } from "../api/_lib/usage_guard.js";

const SECRET = "test-only-usage-guard-secret-32-characters";
const NOW = Date.parse("2026-11-17T10:00:00Z");
const ID = "lumos_AbCdEfGh12345678";

function sqlShim() {
  const db = new DatabaseSync(":memory:");
  return {
    exec(query, ...b) {
      const stmt = db.prepare(query);
      if (/^\s*SELECT/i.test(query)) {
        const rows = stmt.all(...b);
        return { toArray: () => rows };
      }
      stmt.run(...b);
      return { toArray: () => [] };
    },
  };
}

// Cloudflare Durable Object namespace taklidi: idFromName("global") her zaman aynı nesne.
function makeEnv(vars = {}) {
  const objects = new Map();
  const doEnv = { ...vars };
  const USAGE = {
    names: [],
    idFromName(name) {
      USAGE.names.push(name);
      return name;
    },
    get(id) {
      if (!objects.has(id)) objects.set(id, new UsageCounter({ storage: { sql: sqlShim() } }, doEnv));
      const obj = objects.get(id);
      return { fetch: (url, init) => obj.fetch(new Request(url, init)) };
    },
  };
  return { LUMOS_USAGE_GUARD_SECRET: SECRET, USAGE, ...vars, _objects: objects };
}

async function signed(body, { ts = NOW, secret = SECRET } = {}) {
  return new Request("https://usage.example/consume", {
    method: "POST",
    headers: { "x-lumos-ts": String(ts), "x-lumos-sig": await signRequest(secret, String(ts), body) },
    body,
  });
}

test("valid signed request is counted and allowed", async () => {
  const env = makeEnv();
  const res = await handleRequest(await signed(JSON.stringify({ lumos_id: ID, kind: "chat" })), env, NOW);
  assert.equal(res.status, 200);
  const payload = await res.json();
  assert.equal(payload.allowed, true);
  assert.equal(payload.remaining.user_minute, 9);
  assert.deepEqual(env.USAGE.names, ["global"], "single Durable Object");
});

test("limit reached returns 429 with the scope", async () => {
  const env = makeEnv({ LUMOS_USAGE_USER_PER_MINUTE: "2" });
  const body = JSON.stringify({ lumos_id: ID, kind: "realtime" });
  assert.equal((await handleRequest(await signed(body), env, NOW)).status, 200);
  assert.equal((await handleRequest(await signed(body), env, NOW)).status, 200);
  const third = await handleRequest(await signed(body), env, NOW);
  assert.equal(third.status, 429);
  assert.deepEqual(await third.json(), { allowed: false, scope: "user_minute" });
});

test("Vercel client signature is accepted by the Worker (same HMAC format)", async () => {
  const env = makeEnv();
  const body = JSON.stringify({ lumos_id: ID, kind: "chat" });
  const req = new Request("https://usage.example/consume", {
    method: "POST",
    headers: { "x-lumos-ts": String(NOW), "x-lumos-sig": signUsageRequest(SECRET, String(NOW), body) },
    body,
  });
  assert.equal((await handleRequest(req, env, NOW)).status, 200);
});

test("wrong secret, stale timestamp, tampered body and missing signature are rejected without counting", async () => {
  const env = makeEnv();
  const body = JSON.stringify({ lumos_id: ID, kind: "chat" });
  assert.equal((await handleRequest(await signed(body, { secret: "x".repeat(40) }), env, NOW)).status, 401);
  assert.equal((await handleRequest(await signed(body, { ts: NOW - 61_000 }), env, NOW)).status, 401);
  const tampered = await signed(body);
  const forged = new Request(tampered.url, {
    method: "POST",
    headers: tampered.headers,
    body: JSON.stringify({ lumos_id: "lumos_OtherUser12345", kind: "chat" }),
  });
  assert.equal((await handleRequest(forged, env, NOW)).status, 401);
  const unsigned = new Request("https://usage.example/consume", { method: "POST", body });
  assert.equal((await handleRequest(unsigned, env, NOW)).status, 401);
  assert.equal(env._objects.size, 0, "no counter touched");
});

test("invalid input, wrong method, unknown path and missing configuration", async () => {
  const env = makeEnv();
  assert.equal((await handleRequest(await signed(JSON.stringify({ lumos_id: "bad", kind: "chat" })), env, NOW)).status, 400);
  assert.equal((await handleRequest(await signed(JSON.stringify({ lumos_id: ID, kind: "image" })), env, NOW)).status, 400);
  assert.equal((await handleRequest(await signed("not json"), env, NOW)).status, 400);
  assert.equal((await handleRequest(new Request("https://usage.example/consume"), env, NOW)).status, 405);
  assert.equal((await handleRequest(new Request("https://usage.example/other", { method: "POST" }), env, NOW)).status, 404);
  const noSecret = { USAGE: env.USAGE };
  assert.equal((await handleRequest(await signed(JSON.stringify({ lumos_id: ID, kind: "chat" })), noSecret, NOW)).status, 503);
});

test("Durable Object failure (e.g. free quota exhausted) fails closed with 503", async () => {
  const env = {
    LUMOS_USAGE_GUARD_SECRET: SECRET,
    USAGE: {
      idFromName: () => "global",
      get: () => ({
        fetch: async () => {
          throw new Error("Exceeded allowed rows written in Durable Objects free tier");
        },
      }),
    },
  };
  const res = await handleRequest(await signed(JSON.stringify({ lumos_id: ID, kind: "chat" })), env, NOW);
  assert.equal(res.status, 503);
});

test("concurrent requests through the single object never exceed the limit", async () => {
  const env = makeEnv({ LUMOS_USAGE_USER_PER_MINUTE: "10" });
  const body = JSON.stringify({ lumos_id: ID, kind: "chat" });
  const requests = await Promise.all(Array.from({ length: 25 }, () => signed(body)));
  const statuses = await Promise.all(requests.map((r) => handleRequest(r, env, NOW).then((x) => x.status)));
  assert.equal(statuses.filter((s) => s === 200).length, 10);
  assert.equal(statuses.filter((s) => s === 429).length, 15);
});
