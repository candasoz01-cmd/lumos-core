/** GET /api/auth/meta/start?provider=... -> read-only Meta OAuth */
import {
  COOKIE,
  makeState,
  openSession,
  readCookie,
  sealSession,
  sessionLumosId,
} from "../../_lib/lumos_session.js";
import {
  buildMetaAuthorizeUrl,
  metaProviderConfig,
  missingMetaConfiguration,
} from "../../_lib/meta_oauth.js";
import { metaVaultWriteConfiguration } from "../../_lib/meta_vault.js";
import { captureError, logEvent } from "../../_lib/observability.js";

const META_FLOW_COOKIE = "lumos_meta_oauth";
const ROUTE = "meta_oauth_start";

function redirectError(res, code) {
  res.statusCode = 302;
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("Location", `/integrations/meta?meta_error=${encodeURIComponent(code)}`);
  res.end();
}

export function metaFlowCookieHeader(value) {
  return `${META_FLOW_COOKIE}=${value}; Path=/auth/meta; HttpOnly; Secure; SameSite=Lax; Max-Age=600`;
}

export default async function handler(req, res) {
  if (req.method !== "GET") {
    res.statusCode = 405;
    res.end("method_not_allowed");
    return;
  }
  const claims = openSession(readCookie(req, COOKIE));
  const lumosId = sessionLumosId(claims);
  if (!claims?.sid || !lumosId) {
    redirectError(res, "lumos_session_required");
    return;
  }
  const requestUrl = new URL(req.url || "/", "https://welockai.com");
  const provider = String(requestUrl.searchParams.get("provider") || "").trim().toLowerCase();
  if (!metaProviderConfig(provider)) {
    redirectError(res, "meta_provider_invalid");
    return;
  }
  if (missingMetaConfiguration(provider).length) {
    await captureError(new Error("meta_oauth_not_configured"), { route: ROUTE, provider, errorCode: "meta_oauth_not_configured" });
    redirectError(res, "meta_oauth_not_configured");
    return;
  }
  if (!metaVaultWriteConfiguration().configured) {
    await captureError(new Error("meta_vault_not_configured"), { route: ROUTE, provider, errorCode: "meta_vault_not_configured" });
    redirectError(res, "meta_vault_not_configured");
    return;
  }
  try {
    const state = makeState();
    const now = Math.floor(Date.now() / 1000);
    const flow = sealSession({
      kind: "meta_oauth",
      provider,
      state,
      lumos_id: lumosId,
      iat: now,
      exp: now + 600,
    });
    const location = buildMetaAuthorizeUrl(provider, state);
    res.statusCode = 302;
    res.setHeader("Set-Cookie", metaFlowCookieHeader(flow));
    res.setHeader("Location", location);
    res.setHeader("Cache-Control", "no-store");
    res.end();
    await logEvent("oauth.start", { route: ROUTE, provider, lumosId });
  } catch {
    await captureError(new Error("meta_oauth_start_failed"), { route: ROUTE, provider, errorCode: "meta_oauth_start_failed" });
    redirectError(res, "meta_oauth_start_failed");
  }
}

export { META_FLOW_COOKIE };
