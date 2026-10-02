/**
 * POST|GET /api/auth/logout — Lumos oturum çerezini temizle ve oturum sürümünü artır.
 * Oturum, ortak kapıdan (çerez veya Bearer) çözülür: yalnız hâlâ geçerli bir oturum
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

export default async function handler(req, res) {
  if (req.method !== "POST" && req.method !== "GET") {
    res.statusCode = 405;
    res.end("method_not_allowed");
    return;
  }
  try {
    // Mobil istemci yalnız Bearer sunabilir; çerez yoksa Bearer'dan da çıkış yapılır.
    const claims = hostedSessionClaims(req);
    const lumosId = sessionLumosId(claims);
    if (lumosId) bumpEpoch(lumosId);
  } catch {
    // Çerez silinir; sürüm dosyası yazılamazsa kopya belirteç exp dolana kadar kalır.
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
