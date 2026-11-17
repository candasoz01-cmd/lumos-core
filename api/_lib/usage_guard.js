// Barındırılan yapay zekâ çağrısından önce kalıcı kullanım sayacına danışır.
// Sayaç: ops/usage-guard (Cloudflare Worker + tek Durable Object).
//
// Kapalı varsayılan (fail-closed): adres veya gizli anahtar tanımsızsa, sayaç
// cevap vermezse ya da beklenmedik cevap dönerse model çağrısına izin verilmez.

import { createHmac } from "node:crypto";

const TIMEOUT_MS = 3000;
const MIN_SECRET_LENGTH = 32;

export function signUsageRequest(secret, timestamp, body) {
  return createHmac("sha256", secret).update(`${timestamp}.${body}`).digest("hex");
}

export async function consumeHostedAiQuota(lumosId, kind, options = {}) {
  const env = options.env || process.env;
  const fetchImpl = options.fetchImpl || globalThis.fetch;
  const now = options.now || Date.now;
  const base = String(env.LUMOS_USAGE_GUARD_URL || "").trim().replace(/\/+$/, "");
  const secret = String(env.LUMOS_USAGE_GUARD_SECRET || "").trim();
  if (!base.startsWith("https://") || secret.length < MIN_SECRET_LENGTH) {
    return { ok: false, status: 503, error: "usage_guard_unconfigured" };
  }
  const body = JSON.stringify({ lumos_id: String(lumosId || ""), kind });
  const timestamp = String(now());
  try {
    const res = await fetchImpl(`${base}/consume`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-lumos-ts": timestamp,
        "x-lumos-sig": signUsageRequest(secret, timestamp, body),
      },
      body,
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    const payload = await res.json().catch(() => null);
    if (res.status === 200 && payload?.allowed === true) return { ok: true };
    if (res.status === 429 && payload?.allowed === false) {
      return { ok: false, status: 429, error: "usage_limited", scope: String(payload.scope || "") };
    }
    return { ok: false, status: 503, error: "usage_guard_unavailable" };
  } catch {
    return { ok: false, status: 503, error: "usage_guard_unavailable" };
  }
}

// Testlerin sayaç ağ çağrısını sağlayıcı çağrısından ayırabilmesi için tek giriş noktası.
export const usageGuard = { consume: consumeHostedAiQuota };

export function usageDeniedPayload(result) {
  return result.status === 429
    ? {
        error: "usage_limited",
        errorKind: "rate_limited",
        scope: result.scope,
        message: "Kullanım sınırına ulaşıldı. Lütfen daha sonra tekrar deneyin.",
      }
    : {
        error: result.error,
        errorKind: "usage_guard_unavailable",
        message: "Kullanım denetimi şu an doğrulanamıyor; güvenlik için istek gönderilmedi.",
      };
}
