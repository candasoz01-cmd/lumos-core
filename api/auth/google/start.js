/**
 * GET /api/auth/google/start → Google authorize 302
 * Rewrite: /auth/google/start
 */
import {
  makeState,
  redirectUri,
  stateCookieHeader,
} from "../../_lib/lumos_session.js";

const AUTH = "https://accounts.google.com/o/oauth2/v2/auth";
const SCOPES = "openid email profile";

export default async function handler(req, res) {
  if (req.method !== "GET") {
    res.statusCode = 405;
    res.end("method_not_allowed");
    return;
  }
  const clientId = (process.env.LUMOS_GOOGLE_WEB_CLIENT_ID || "").trim();
  const cb = redirectUri();
  if (!clientId) {
    res.statusCode = 400;
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({ ok: false, error: "missing_client_id" }));
    return;
  }
  const state = makeState();
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
}
