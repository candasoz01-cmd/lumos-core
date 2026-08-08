/** Authenticated, same-origin, read-only Meta account sync. */
import { COOKIE, openSession, readCookie, sessionLumosId } from "../../_lib/lumos_session.js";
import { META_PROVIDERS } from "../../_lib/meta_oauth.js";
import { syncMetaReadOnly } from "../../_lib/meta_sync.js";
import { resolveMetaCredential } from "../../_lib/meta_vault.js";
import { captureError, logEvent } from "../../_lib/observability.js";

const ROUTE = "meta_readonly_sync";

function json(res, status, payload) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(payload));
}

function sameOrigin(req) {
  const origin = String(req.headers?.origin || req.headers?.Origin || "").trim();
  const host = String(req.headers?.host || req.headers?.Host || "").trim().toLowerCase();
  try {
    const parsed = new URL(origin);
    const secure = parsed.protocol === "https:" || parsed.hostname === "localhost";
    return Boolean(host) && secure && parsed.host.toLowerCase() === host;
  } catch {
    return false;
  }
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    json(res, 405, { ok: false, error: "method_not_allowed" });
    return;
  }
  const claims = openSession(readCookie(req, COOKIE));
  const lumosId = claims?.sid ? sessionLumosId(claims) : "";
  if (!lumosId) {
    json(res, 401, { ok: false, error: "lumos_session_required" });
    return;
  }
  if (!sameOrigin(req)) {
    json(res, 403, { ok: false, error: "same_origin_required" });
    return;
  }
  const body = req.body && typeof req.body === "object" ? req.body : {};
  const provider = String(body.provider || "").trim().toLowerCase();
  if (!META_PROVIDERS.includes(provider)) {
    json(res, 400, { ok: false, error: "meta_provider_invalid" });
    return;
  }
  try {
    const credential = await resolveMetaCredential(lumosId, provider);
    const snapshot = await syncMetaReadOnly(provider, credential);
    json(res, 200, {
      ok: true,
      provider,
      status: "synced",
      checked_at: new Date().toISOString(),
      ...snapshot,
    });
    await logEvent("integration.readonly_sync", { route: ROUTE, provider, lumosId, status: "synced" });
  } catch (error) {
    const errorCode = String(error?.message || "meta_sync_failed");
    await captureError(new Error(errorCode), { route: ROUTE, provider, errorCode });
    json(res, 502, { ok: false, provider, error: errorCode });
  }
}
