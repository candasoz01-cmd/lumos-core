/**
 * POST|GET /api/auth/logout — Lumos oturum çerezini temizle.
 * Küresel iptal (oturum sürümünü artırma) yalnız POST ile yapılır: GET çapraz site
 * gezintisiyle tetiklenebilir (CSRF), bu yüzden yalnız bu tarayıcının çerezlerini siler.
 * POST'ta Origin varsa aynı kaynak olmalı; Sec-Fetch-Site çapraz site ise reddedilir.
 * Oturum ortak kapıdan (çerez veya Bearer) çözülür: yalnız hâlâ geçerli bir oturum
 * sürümü artırabilir; çıkıştan sonra kopyalanmış eski belirteç sürümü tekrar artıramaz.
 */
import {
  clearBridgeProxyCookieHeader,
  clearSessionCookieHeader,
  sessionLumosId,
} from "../_lib/lumos_session.js";
import { hostedSessionClaims } from "../_lib/hosted_lumos.js";
import { logEvent } from "../_lib/observability.js";
import { bumpEpoch } from "../_lib/session_epoch.js";

function header(req, name) {
  return String(req.headers?.[name] ?? req.headers?.[name.toLowerCase()] ?? "").trim();
}

// Tarayıcı POST'ları Origin taşır; Bearer kullanan mobil istemci taşımaz (CSRF vektörü değil).
function crossSitePost(req) {
  const fetchSite = header(req, "sec-fetch-site").toLowerCase();
  if (fetchSite === "cross-site" || fetchSite === "same-site") return true;
  const origin = header(req, "origin");
  if (!origin) return false;
  const host = (header(req, "x-forwarded-host") || header(req, "host")).split(",")[0].trim().toLowerCase();
  try {
    return !host || new URL(origin).host.toLowerCase() !== host;
  } catch {
    return true;
  }
}

export default async function handler(req, res) {
  if (req.method !== "POST" && req.method !== "GET") {
    res.statusCode = 405;
    res.end("method_not_allowed");
    return;
  }
  if (req.method === "POST" && crossSitePost(req)) {
    res.statusCode = 403;
    res.setHeader("Cache-Control", "no-store");
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({ ok: false, error: "cross_site_logout_blocked" }));
    return;
  }
  if (req.method === "POST") {
    try {
      // Mobil istemci yalnız Bearer sunabilir; çerez yoksa Bearer'dan da çıkış yapılır.
      const claims = hostedSessionClaims(req);
      const lumosId = sessionLumosId(claims);
      if (lumosId) bumpEpoch(lumosId);
    } catch {
      // Çerez silinir; sürüm dosyası yazılamazsa kopya belirteç exp dolana kadar kalır.
    }
  }
  res.setHeader("Set-Cookie", [
    clearSessionCookieHeader(),
    clearBridgeProxyCookieHeader(),
  ]);
  res.setHeader("Cache-Control", "no-store");
  if (req.method === "GET") {
    res.statusCode = 302;
    res.setHeader("Location", "/auth?logged_out=1");
    res.end();
    logEvent("oauth.logout", { route: "auth_logout", method: "GET" });
    return;
  }
  res.statusCode = 200;
  res.setHeader("Content-Type", "application/json");
  res.end(JSON.stringify({ ok: true, logged_out: true }));
  logEvent("oauth.logout", { route: "auth_logout", method: "POST" });
}
