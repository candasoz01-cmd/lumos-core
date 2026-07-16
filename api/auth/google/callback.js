/**
 * GET /api/auth/google/callback — code → token exchange → şifreli Lumos oturumu
 * Rewrite: /auth/google/callback
 * access_token / refresh_token yanıt gövdesine ve çereze yazılmaz.
 */
import { randomBytes } from "node:crypto";
import {
  clearStateCookieHeader,
  readCookie,
  redirectUri,
  lumosIdForProviderIdentity,
  sealSession,
  sessionCookieHeader,
  STATE_COOKIE,
  stateMatchesCookie,
  verifyState,
} from "../../_lib/lumos_session.js";

const TOKEN = "https://oauth2.googleapis.com/token";
const USERINFO = "https://openidconnect.googleapis.com/v1/userinfo";

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

  if (err) {
    res.statusCode = 302;
    res.setHeader("Location", `/auth?error=${encodeURIComponent(err)}`);
    res.end();
    return;
  }
  const cookieState = readCookie(req, STATE_COOKIE);
  if (!verifyState(state) || !stateMatchesCookie(state, cookieState)) {
    // State uyuşmazlığı — secret/state değeri yanıta yazılmaz
    res.statusCode = 400;
    res.setHeader("Content-Type", "application/json");
    res.setHeader("Cache-Control", "no-store");
    res.setHeader("Set-Cookie", clearStateCookieHeader());
    res.end(JSON.stringify({ ok: false, error: "invalid_state" }));
    return;
  }

  const clientId = (process.env.LUMOS_GOOGLE_WEB_CLIENT_ID || "").trim();
  const clientSecret = (process.env.LUMOS_GOOGLE_WEB_CLIENT_SECRET || "").trim();
  const cb = redirectUri();
  if (!clientId || !clientSecret || !code) {
    res.statusCode = 400;
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({ ok: false, error: "missing_credentials_or_code" }));
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
    res.statusCode = 400;
    res.setHeader("Content-Type", "application/json");
    res.end(
      JSON.stringify({
        ok: false,
        error: "token_http_error",
        status: tokenRes.status,
      })
    );
    return;
  }
  const tok = await tokenRes.json();
  const access = tok.access_token;
  if (!access) {
    res.statusCode = 400;
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({ ok: false, error: "no_access_token" }));
    return;
  }

  const infoRes = await fetch(USERINFO, {
    headers: { Authorization: `Bearer ${access}` },
  });
  // Google access_token burada düşer — saklanmaz
  if (!infoRes.ok) {
    res.statusCode = 400;
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({ ok: false, error: "userinfo_http_error" }));
    return;
  }
  const info = await infoRes.json();
  const now = Math.floor(Date.now() / 1000);
  const lumosId = lumosIdForProviderIdentity("google_web", info.sub);
  if (!lumosId) {
    res.statusCode = 400;
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({ ok: false, error: "identity_subject_missing" }));
    return;
  }
  const sealed = sealSession({
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

  res.statusCode = 302;
  const cookies = [sessionCookieHeader(sealed), clearStateCookieHeader()];
  res.setHeader("Set-Cookie", cookies);
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("Location", "/panel?source=google_web&door=lumos");
  res.end();
}
