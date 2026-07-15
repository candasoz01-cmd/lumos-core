/**
 * GET /api/auth/session — mühürlü Lumos oturumu (token yok)
 */
import {
  bridgeProxyCookieHeader,
  openSession,
  readCookie,
} from "../_lib/lumos_session.js";

export default async function handler(req, res) {
  if (req.method !== "GET") {
    res.statusCode = 405;
    res.end("method_not_allowed");
    return;
  }
  const claims = openSession(readCookie(req));
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  if (!claims) {
    res.statusCode = 401;
    res.end(JSON.stringify({ ok: false, authenticated: false }));
    return;
  }
  const bridgeProxyToken = String(
    process.env.LUMOS_BRIDGE_PROXY_AUTH_TOKEN || ""
  ).trim();
  if (bridgeProxyToken) {
    res.setHeader("Set-Cookie", bridgeProxyCookieHeader(bridgeProxyToken));
  }
  res.statusCode = 200;
  res.end(
    JSON.stringify({
      ok: true,
      authenticated: true,
      session: {
        session_id: claims.sid,
        email: claims.email,
        name: claims.name,
        picture: claims.picture || "",
        door: claims.door || "lumos",
        provider: claims.provider || "google_web",
        exp: claims.exp,
      },
    })
  );
}
