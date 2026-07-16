/**
 * POST|GET /api/auth/logout — Lumos oturum çerezini temizle
 */
import {
  clearBridgeProxyCookieHeader,
  clearSessionCookieHeader,
} from "../_lib/lumos_session.js";

export default async function handler(req, res) {
  if (req.method !== "POST" && req.method !== "GET") {
    res.statusCode = 405;
    res.end("method_not_allowed");
    return;
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
    return;
  }
  res.statusCode = 200;
  res.setHeader("Content-Type", "application/json");
  res.end(JSON.stringify({ ok: true, logged_out: true }));
}
