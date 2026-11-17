// Vercel → kullanım sayacı Worker'ı arasındaki istek imzası (HMAC-SHA256).
// İmzalanan metin: `${zaman_damgası_ms}.${gövde}`. Saat farkı en fazla 60 sn.
// Yeniden gönderilen (replay) bir istek yalnız aynı kullanıcının sayacını
// artırır; yeni yetki veya model erişimi vermez.

const encoder = new TextEncoder();
export const MIN_SECRET_LENGTH = 32;
export const MAX_SKEW_MS = 60_000;

function toHex(buffer) {
  return [...new Uint8Array(buffer)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function signRequest(secret, timestamp, body) {
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  return toHex(await crypto.subtle.sign("HMAC", key, encoder.encode(`${timestamp}.${body}`)));
}

function constantTimeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length || !a.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export async function verifyRequest(secret, timestamp, body, signature, nowMs) {
  if (typeof secret !== "string" || secret.length < MIN_SECRET_LENGTH) return false;
  const ts = Number(timestamp);
  if (!Number.isFinite(ts) || Math.abs(nowMs - ts) > MAX_SKEW_MS) return false;
  const expected = await signRequest(secret, String(timestamp), body);
  return constantTimeEqual(expected, String(signature || "").toLowerCase());
}
