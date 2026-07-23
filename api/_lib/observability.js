/**
 * Gözlemlenebilirlik: Sentry (hata yakalama) + Axiom (yapılandırılmış log).
 *
 * Kasıtlı olarak bağımlılıksız (npm paketi eklemez) — repo kökünde `api/*`
 * fonksiyonları için hiçbir dependency yok ve Vercel installCommand yalnızca
 * `ui/` altını kuruyor; buraya bir SDK eklemek build'i bozardı. Bunun yerine
 * Sentry'nin store API'sine ve Axiom'un ingest API'sine doğrudan fetch ile
 * yazılıyor.
 *
 * SENTRY_DSN / LUMOS_AXIOM_TOKEN tanımlı değilse her fonksiyon sessiz no-op'tur
 * — ortam yapılandırılmadan hiçbir istek atılmaz, hiçbir hata fırlatılmaz.
 *
 * Yalnızca aşağıdaki allowlist alanları dışa gönderilir; email, name, picture,
 * sub, access_token, code, state, cookie, client_secret gibi hiçbir kimlik/gizli
 * alan bu modülden geçmez.
 */
import { randomBytes } from "node:crypto";

const CAPTURE_TIMEOUT_MS = 1800;

const ALLOWED_CONTEXT_FIELDS = [
  "route",
  "status",
  "errorCode",
  "provider",
  "door",
  "lumosId",
  "method",
  "path",
  "durationMs",
  "upstreamStatus",
  "attempt",
];

function sentryDsn() {
  return (process.env.SENTRY_DSN || "").trim();
}

function axiomToken() {
  return (process.env.LUMOS_AXIOM_TOKEN || "").trim();
}

function axiomDataset() {
  return (process.env.LUMOS_AXIOM_DATASET || "lumos-production").trim();
}

function parseDsn(dsn) {
  try {
    const u = new URL(dsn);
    const projectId = u.pathname.replace(/^\//, "").trim();
    if (!projectId || !u.username) return null;
    return {
      publicKey: u.username,
      storeUrl: `${u.protocol}//${u.host}/api/${projectId}/store/`,
    };
  } catch {
    return null;
  }
}

/** Yalnızca izinli alanları geçirir — bilinmeyen/hassas alanlar sessizce düşer. */
function safeContext(context) {
  const out = {};
  if (!context || typeof context !== "object") return out;
  for (const key of ALLOWED_CONTEXT_FIELDS) {
    if (context[key] !== undefined && context[key] !== null) {
      out[key] = context[key];
    }
  }
  return out;
}

async function postWithTimeout(url, init) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), CAPTURE_TIMEOUT_MS);
  try {
    await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Gerçek bir hata/istisna için — 5xx, beklenmeyen exception, sağlayıcı hatası.
 * Rutin 401 (giriş yapılmamış) gibi beklenen durumlar için KULLANILMAZ.
 */
export async function captureError(error, context = {}) {
  const dsn = parseDsn(sentryDsn());
  if (!dsn) return;
  const err = error instanceof Error ? error : new Error(String(error));
  const ctx = safeContext(context);
  const payload = {
    event_id: randomBytes(16).toString("hex"),
    timestamp: new Date().toISOString(),
    level: "error",
    logger: "lumos-api",
    platform: "node",
    message: err.message,
    tags: { route: ctx.route || "unknown", errorCode: ctx.errorCode || "unknown" },
    extra: { ...ctx, stack: (err.stack || "").slice(0, 2000) },
  };
  try {
    await postWithTimeout(dsn.storeUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Sentry-Auth": `Sentry sentry_version=7, sentry_key=${dsn.publicKey}, sentry_client=lumos-observability/1.0`,
      },
      body: JSON.stringify(payload),
    });
  } catch {
    // Gözlem çağrısı hiçbir zaman asıl isteği bozmamalı.
  }
}

/**
 * Genel yapılandırılmış log — Axiom'a, no-op token yoksa.
 */
export async function logEvent(name, context = {}) {
  const token = axiomToken();
  if (!token) return;
  try {
    await postWithTimeout(`https://api.axiom.co/v1/datasets/${axiomDataset()}/ingest`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify([{ _time: new Date().toISOString(), event: name, ...safeContext(context) }]),
    });
  } catch {
    // Gözlem çağrısı hiçbir zaman asıl isteği bozmamalı.
  }
}

/**
 * Güvenlikle ilgili ret/başarısızlık (invalid_state, bridge_proxy_unauthorized vb.)
 * — hem Axiom'a (aranabilir kayıt) hem Sentry'ye (uyarı seviyesinde mesaj) düşer.
 */
export async function captureSecurityEvent(name, context = {}) {
  const ctx = safeContext(context);
  await Promise.allSettled([
    logEvent(`security.${name}`, ctx),
    (async () => {
      const dsn = parseDsn(sentryDsn());
      if (!dsn) return;
      const payload = {
        event_id: randomBytes(16).toString("hex"),
        timestamp: new Date().toISOString(),
        level: "warning",
        logger: "lumos-security",
        platform: "node",
        message: `security_event:${name}`,
        tags: { route: ctx.route || "unknown", security: "true" },
        extra: ctx,
      };
      try {
        await postWithTimeout(dsn.storeUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Sentry-Auth": `Sentry sentry_version=7, sentry_key=${dsn.publicKey}, sentry_client=lumos-observability/1.0`,
          },
          body: JSON.stringify(payload),
        });
      } catch {
        // no-op
      }
    })(),
  ]);
}
