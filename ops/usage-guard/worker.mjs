// lumos-usage-guard — barındırılan yapay zekâ çağrıları için kalıcı kullanım sayacı.
//
// Tek uç nokta: POST /consume  (gövde: {"lumos_id": "...", "kind": "chat"|"realtime"})
// Başlıklar: x-lumos-ts (ms), x-lumos-sig (HMAC-SHA256, bkz. auth.mjs).
// Cevaplar: 200 {allowed:true}, 429 {allowed:false, scope}, 400/401/405/503 hata.
// Tüm sayaçlar tek Durable Object'tedir (SQLite, Cloudflare ücretsiz planında kullanılabilir).

import { verifyRequest } from "./auth.mjs";
import { consume, ensureSchema, readLimits } from "./limits.mjs";

const LUMOS_ID = /^lumos_[A-Za-z0-9_-]{8,64}$/;
const KINDS = new Set(["chat", "realtime"]);
const MAX_BODY_BYTES = 512;

function json(status, payload) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

export class UsageCounter {
  constructor(ctx, env) {
    this.ctx = ctx;
    this.env = env;
    this.ready = false;
  }

  async fetch(request) {
    const { lumos_id: lumosId } = await request.json();
    const sql = this.ctx.storage.sql;
    if (!this.ready) {
      ensureSchema(sql);
      this.ready = true;
    }
    const result = consume(sql, lumosId, readLimits(this.env), Date.now());
    return json(result.allowed ? 200 : 429, result);
  }
}

export async function handleRequest(request, env, nowMs = Date.now()) {
  const url = new URL(request.url);
  if (url.pathname !== "/consume") return json(404, { error: "not_found" });
  if (request.method !== "POST") return json(405, { error: "method_not_allowed" });
  const secret = String(env.LUMOS_USAGE_GUARD_SECRET || "");
  if (!secret || !env.USAGE) return json(503, { error: "usage_guard_unconfigured" });

  const body = await request.text();
  if (body.length > MAX_BODY_BYTES) return json(400, { error: "body_too_large" });
  const ok = await verifyRequest(
    secret,
    request.headers.get("x-lumos-ts"),
    body,
    request.headers.get("x-lumos-sig"),
    nowMs,
  );
  if (!ok) return json(401, { error: "unauthorized" });

  let parsed;
  try {
    parsed = JSON.parse(body);
  } catch {
    return json(400, { error: "invalid_json" });
  }
  const lumosId = String(parsed?.lumos_id || "");
  const kind = String(parsed?.kind || "");
  if (!LUMOS_ID.test(lumosId) || !KINDS.has(kind)) return json(400, { error: "invalid_request" });

  try {
    const stub = env.USAGE.get(env.USAGE.idFromName("global"));
    const res = await stub.fetch("https://usage-counter/consume", {
      method: "POST",
      body: JSON.stringify({ lumos_id: lumosId, kind }),
    });
    return json(res.status === 200 || res.status === 429 ? res.status : 503, await res.json());
  } catch {
    // Ücretsiz kota dolduğunda Durable Object hata döner: kapalı kal.
    return json(503, { error: "usage_guard_unavailable" });
  }
}

export default {
  fetch: (request, env) => handleRequest(request, env),
};
