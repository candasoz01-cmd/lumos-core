/**
 * GET /api/auth/session — mühürlü Lumos oturumu (token yok)
 */
import {
  openSession,
  readCookie,
  sessionLumosId,
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
  const lumosId = sessionLumosId(claims);
  if (!lumosId) {
    res.statusCode = 401;
    res.end(JSON.stringify({ ok: false, authenticated: false, error: "identity_missing" }));
    return;
  }
  res.statusCode = 200;
  res.end(
    JSON.stringify({
      ok: true,
      authenticated: true,
      session: {
        session_id: claims.sid,
        lumos_id: lumosId,
        email: claims.email,
        name: claims.name,
        picture: claims.picture || "",
        door: claims.door || "lumos",
        provider: claims.provider || "google_web",
        package: claims.package || "base",
        exp: claims.exp,
      },
    })
  );
}
