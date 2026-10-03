// Meta `signed_request` doğrulaması — veri silme ve yetki kaldırma geri
// çağrıları (KARAR-2, candasoz01-cmd/lumos-core#903).
// Biçim: "<imza_base64url>.<yük_base64url>"; imza, yük dizesinin uygulama
// sırrıyla HMAC-SHA256'sıdır. Hangi sır doğrularsa o uygulamanın
// sağlayıcıları silme kapsamına girer.
import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";

function clean(value) {
  return String(value || "").trim();
}

function base64UrlDecode(value) {
  return Buffer.from(clean(value).replace(/-/g, "+").replace(/_/g, "/"), "base64");
}

// Uygulama sırrı → o uygulamayla alınan credential'ların sağlayıcıları.
// Kaynak: api/_lib/meta_oauth.js metaProviderConfig. WhatsApp ayrı Business
// app sırrı yoksa tüketici app'e düşer; Pages'in böyle bir yedeği yoktur.
export function metaAppSecrets(env = process.env) {
  const metaSecret = clean(env.LUMOS_META_APP_SECRET);
  const instagramSecret = clean(env.LUMOS_INSTAGRAM_APP_SECRET);
  const whatsappSecret = clean(env.LUMOS_WHATSAPP_APP_SECRET);
  const apps = [];
  if (metaSecret) apps.push({ secret: metaSecret, providers: whatsappSecret ? ["facebook"] : ["facebook", "whatsapp"] });
  if (instagramSecret) apps.push({ secret: instagramSecret, providers: ["instagram"] });
  if (whatsappSecret) apps.push({ secret: whatsappSecret, providers: ["whatsapp", "pages"] });
  return apps;
}

export function verifyMetaSignedRequest(signedRequest, apps = metaAppSecrets()) {
  const parts = clean(signedRequest).split(".");
  if (parts.length !== 2 || !parts[0] || !parts[1]) return null;
  const [encodedSignature, encodedPayload] = parts;
  const provided = base64UrlDecode(encodedSignature);
  let payload;
  try {
    payload = JSON.parse(base64UrlDecode(encodedPayload).toString("utf8"));
  } catch {
    return null;
  }
  if (clean(payload?.algorithm).toUpperCase() !== "HMAC-SHA256") return null;
  const userId = clean(payload?.user_id);
  if (!/^[0-9]{1,64}$/.test(userId)) return null;

  const providers = new Set();
  for (const app of apps) {
    const expected = createHmac("sha256", app.secret).update(encodedPayload).digest();
    if (provided.length === expected.length && timingSafeEqual(provided, expected)) {
      for (const provider of app.providers) providers.add(provider);
    }
  }
  if (!providers.size) return null;
  return { userId, providers: [...providers].sort(), issuedAt: Number(payload?.issued_at || 0) };
}

export function signedRequestFromBody(body) {
  if (body && typeof body === "object" && !Buffer.isBuffer(body)) return clean(body.signed_request);
  const text = Buffer.isBuffer(body) ? body.toString("utf8") : typeof body === "string" ? body : "";
  return clean(new URLSearchParams(text).get("signed_request"));
}

export function newDeletionConfirmationCode() {
  return randomBytes(18).toString("base64url");
}

export function isDeletionConfirmationCode(value) {
  return /^[A-Za-z0-9_-]{16,64}$/.test(clean(value));
}
