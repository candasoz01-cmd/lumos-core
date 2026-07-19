/**
 * GET /api/auth/google/start → Google authorize 302
 * Rewrite: /auth/google/start
 */
import {
  makeState,
  redirectUri,
  stateCookieHeader,
} from "../../_lib/lumos_session.js";
import { captureError, logEvent } from "../../_lib/observability.js";

const AUTH = "https://accounts.google.com/o/oauth2/v2/auth";
const SCOPES = "openid email profile";
const ROUTE = "google_start";

// Bu uç yalnızca /auth sayfasındaki bağlantıdan tam sayfa gezinmesiyle
// çağrılır — hata durumunda ham JSON yerine kullanıcının göreceği
// /auth?error=... sayfasına yönlendirir (callback.js ile aynı desen).
function redirectAuthError(res, code) {
  res.statusCode = 302;
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("Location", `/auth?error=${encodeURIComponent(code)}`);
  res.end();
}

export default async function handler(req, res) {
  if (req.method !== "GET") {
    res.statusCode = 405;
    res.end("method_not_allowed");
    return;
  }
  const clientId = (process.env.LUMOS_GOOGLE_WEB_CLIENT_ID || "").trim();
  const cb = redirectUri();
  if (!clientId) {
    await captureError(new Error("missing_client_id"), { route: ROUTE, errorCode: "missing_client_id" });
    redirectAuthError(res, "missing_client_id");
    return;
  }
  // authSecret() (state imzalama anahtarı) yapılandırılmamışsa makeState()
  // fırlatır — bunu 500 yerine anlaşılır bir hataya çeviriyoruz.
  let state;
  try {
    state = makeState();
  } catch {
    await captureError(new Error("auth_not_configured"), { route: ROUTE, errorCode: "auth_not_configured" });
    redirectAuthError(res, "auth_not_configured");
    return;
  }
  const q = new URLSearchParams({
    client_id: clientId,
    redirect_uri: cb,
    response_type: "code",
    scope: SCOPES,
    state,
    access_type: "online",
    include_granted_scopes: "true",
    prompt: "select_account",
  });
  res.statusCode = 302;
  res.setHeader("Set-Cookie", stateCookieHeader(state));
  res.setHeader("Location", `${AUTH}?${q.toString()}`);
  res.setHeader("Cache-Control", "no-store");
  res.end();
  logEvent("oauth.start", { route: ROUTE, provider: "google_web" });
}
