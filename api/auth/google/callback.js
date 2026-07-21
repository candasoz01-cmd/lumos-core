/**
 * GET /api/auth/google/callback — code → token exchange → şifreli Lumos oturumu
 * Rewrite: /auth/google/callback
 * access_token / refresh_token yanıt gövdesine ve çereze yazılmaz.
 */
import { randomBytes } from "node:crypto";
import {
  clearMobileOAuthCookieHeader,
  clearStateCookieHeader,
  readCookie,
  redirectUri,
  lumosIdForProviderIdentity,
  MOBILE_OAUTH_COOKIE,
  openSession,
  sealSession,
  sessionCookieHeader,
  STATE_COOKIE,
  stateMatchesCookie,
  verifyState,
} from "../../_lib/lumos_session.js";
import { captureError, captureSecurityEvent, logEvent } from "../../_lib/observability.js";

const TOKEN = "https://oauth2.googleapis.com/token";
const USERINFO = "https://openidconnect.googleapis.com/v1/userinfo";
const ROUTE = "google_callback";

// Bu uç yalnızca Google'ın tam sayfa yönlendirmesiyle tarayıcıdan çağrılır
// (fetch/XHR ile değil) — bu yüzden her hata dalı ham JSON yerine kullanıcının
// göreceği /auth?error=... sayfasına yönlendirir (bkz. auth.astro hata metni).
// Mobil akış (start.js `?mobile=1&app_state=...`) mühürlü, kısa ömürlü bir
// çerezle taşınır; sonuç web sayfası yerine uygulamanın deep-link'ine döner.
// Mobil çerez YALNIZ bu OAuth denemesine aitse geçerlidir: `oauth_state`,
// Google'ın geri döndürdüğü `state` ile birebir eşleşmelidir. Aksi halde
// bayat/paralel bir mobil çerez normal web girişini deep-link'e kaçırabilirdi.
function mobileAppState(req, oauthState) {
  const flow = openSession(readCookie(req, MOBILE_OAUTH_COOKIE));
  if (flow?.kind !== "mobile_oauth") return "";
  if (!oauthState || String(flow.oauth_state || "") !== String(oauthState)) return "";
  return String(flow.app_state || "").trim();
}

function mobileLocation(appState, params) {
  return `lumos://auth#${new URLSearchParams({ ...params, state: appState }).toString()}`;
}

function redirectAuthError(res, code, extraCookies = [], appState = "") {
  res.statusCode = 302;
  res.setHeader("Set-Cookie", [
    clearStateCookieHeader(),
    clearMobileOAuthCookieHeader(),
    ...extraCookies,
  ]);
  res.setHeader("Cache-Control", "no-store");
  res.setHeader(
    "Location",
    appState ? mobileLocation(appState, { error: code }) : `/auth?error=${encodeURIComponent(code)}`,
  );
  res.end();
}

export default async function handler(req, res) {
  if (req.method !== "GET") {
    res.statusCode = 405;
    res.end("method_not_allowed");
    return;
  }
  const url = new URL(req.url || "/", "https://welockai.com");
  const err = url.searchParams.get("error");
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  // Mobil akışsa sonuç deep-link'e döner; değilse web davranışı aynen korunur.
  const appState = mobileAppState(req, state);
  const failAuth = (code2, extraCookies = []) => redirectAuthError(res, code2, extraCookies, appState);

  if (err) {
    // Google tarafı ret/iptal — kullanıcı akışı, güvenlik olayı değil.
    logEvent("oauth.callback.provider_error", { route: ROUTE, errorCode: err });
    failAuth(err);
    return;
  }

  // authSecret() (state/oturum imzalama anahtarı) yapılandırılmamışsa
  // verifyState/sealSession fırlatır — bunu 500 yerine anlaşılır bir
  // hataya çeviriyoruz.
  let stateOk;
  try {
    const cookieState = readCookie(req, STATE_COOKIE);
    stateOk = verifyState(state) && stateMatchesCookie(state, cookieState);
  } catch {
    await captureError(new Error("auth_not_configured"), { route: ROUTE, errorCode: "auth_not_configured" });
    failAuth("auth_not_configured");
    return;
  }
  if (!stateOk) {
    // State uyuşmazlığı — secret/state değeri yanıta yazılmaz.
    // Güvenlik olayı: CSRF denemesi veya süresi dolmuş/tekrar kullanılan link olabilir.
    await captureSecurityEvent("invalid_state", { route: ROUTE });
    failAuth("invalid_state");
    return;
  }

  const clientId = (process.env.LUMOS_GOOGLE_WEB_CLIENT_ID || "").trim();
  const clientSecret = (process.env.LUMOS_GOOGLE_WEB_CLIENT_SECRET || "").trim();
  const cb = redirectUri();
  if (!clientId || !clientSecret || !code) {
    await captureError(new Error("missing_credentials_or_code"), {
      route: ROUTE,
      errorCode: "missing_credentials_or_code",
    });
    failAuth("missing_credentials_or_code");
    return;
  }

  const body = new URLSearchParams({
    code,
    client_id: clientId,
    client_secret: clientSecret,
    redirect_uri: cb,
    grant_type: "authorization_code",
  });
  const tokenRes = await fetch(TOKEN, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!tokenRes.ok) {
    await captureError(new Error("token_http_error"), {
      route: ROUTE,
      errorCode: "token_http_error",
      upstreamStatus: tokenRes.status,
    });
    failAuth("token_http_error");
    return;
  }
  const tok = await tokenRes.json();
  const access = tok.access_token;
  if (!access) {
    await captureError(new Error("no_access_token"), { route: ROUTE, errorCode: "no_access_token" });
    failAuth("no_access_token");
    return;
  }

  const infoRes = await fetch(USERINFO, {
    headers: { Authorization: `Bearer ${access}` },
  });
  // Google access_token burada düşer — saklanmaz
  if (!infoRes.ok) {
    await captureError(new Error("userinfo_http_error"), {
      route: ROUTE,
      errorCode: "userinfo_http_error",
      upstreamStatus: infoRes.status,
    });
    failAuth("userinfo_http_error");
    return;
  }
  const info = await infoRes.json();
  const now = Math.floor(Date.now() / 1000);
  const lumosId = lumosIdForProviderIdentity("google_web", info.sub);
  if (!lumosId) {
    await captureError(new Error("identity_subject_missing"), {
      route: ROUTE,
      errorCode: "identity_subject_missing",
    });
    failAuth("identity_subject_missing");
    return;
  }
  let sealed;
  try {
    sealed = sealSession({
      sid: randomBytes(18).toString("base64url"),
      lumos_id: lumosId,
      sub: info.sub,
      email: info.email || "",
      name: info.name || "",
      picture: info.picture || "",
      door: "lumos",
      provider: "google_web",
      package: "base",
      iat: now,
      exp: now + 604800,
    });
  } catch {
    await captureError(new Error("auth_not_configured"), { route: ROUTE, errorCode: "auth_not_configured" });
    failAuth("auth_not_configured");
    return;
  }

  res.statusCode = 302;
  const cookies = [
    sessionCookieHeader(sealed),
    clearStateCookieHeader(),
    clearMobileOAuthCookieHeader(),
  ];
  res.setHeader("Set-Cookie", cookies);
  res.setHeader("Cache-Control", "no-store");
  res.setHeader(
    "Location",
    appState
      ? mobileLocation(appState, { session: sealed })
      : "/panel?source=google_web&door=lumos",
  );
  res.end();
  logEvent("oauth.callback.success", { route: ROUTE, provider: "google_web", lumosId });
}
