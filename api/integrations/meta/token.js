/** Meta credential lifecycle: metadata, refresh and revoke. Raw token is never returned. */
import {
  COOKIE,
  openSession,
  readCookie,
  sessionLumosId,
} from "../../_lib/lumos_session.js";
import {
  META_PROVIDERS,
  metaPurposeCode,
  refreshMetaToken,
  revokeMetaToken,
} from "../../_lib/meta_oauth.js";
import {
  deleteMetaCredential,
  metaCredentialMetadata,
  resolveMetaCredential,
  writeMetaCredential,
} from "../../_lib/meta_vault.js";
import { captureError, logEvent } from "../../_lib/observability.js";

const ROUTE = "meta_token_lifecycle";

function json(res, status, payload) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(payload));
}

function authenticatedLumosId(req) {
  const claims = openSession(readCookie(req, COOKIE));
  return claims?.sid ? sessionLumosId(claims) : "";
}

function providerFrom(value) {
  const provider = String(value || "").trim().toLowerCase();
  return META_PROVIDERS.includes(provider) ? provider : "";
}

function requestBody(req) {
  if (req.body && typeof req.body === "object") return req.body;
  try {
    return JSON.parse(String(req.body || "{}"));
  } catch {
    return {};
  }
}

function hasSameOrigin(req) {
  const origin = String(req.headers?.origin || req.headers?.Origin || "").trim();
  const host = String(req.headers?.host || req.headers?.Host || "").trim().toLowerCase();
  if (!origin || !host) return false;
  try {
    const parsed = new URL(origin);
    const secure = parsed.protocol === "https:" || parsed.hostname === "localhost";
    return secure && parsed.host.toLowerCase() === host;
  } catch {
    return false;
  }
}

export default async function handler(req, res) {
  if (!new Set(["GET", "POST"]).has(req.method)) {
    json(res, 405, { ok: false, error: "method_not_allowed" });
    return;
  }
  const lumosId = authenticatedLumosId(req);
  if (!lumosId) {
    json(res, 401, { ok: false, error: "lumos_session_required" });
    return;
  }
  if (req.method === "POST" && !hasSameOrigin(req)) {
    json(res, 403, { ok: false, error: "same_origin_required" });
    return;
  }
  const body = requestBody(req);
  const url = new URL(req.url || "/", "https://welockai.com");
  const provider = providerFrom(req.method === "GET" ? url.searchParams.get("provider") : body.provider);
  if (!provider) {
    json(res, 400, { ok: false, error: "meta_provider_invalid" });
    return;
  }

  try {
    if (req.method === "GET") {
      const metadata = await metaCredentialMetadata(lumosId, provider);
      json(res, 200, {
        ok: true,
        provider,
        status: metadata.configured ? "authorized" : "not_connected",
        expires_at: metadata.expiresAt,
        renewable: metadata.expiresAt > 0,
      });
      return;
    }

    const action = String(body.action || "").trim().toLowerCase();
    if (!new Set(["refresh", "revoke"]).has(action)) {
      json(res, 400, { ok: false, error: "meta_token_action_invalid" });
      return;
    }
    if (action === "refresh") {
      const metadata = await metaCredentialMetadata(lumosId, provider);
      if (!metadata.configured) {
        json(res, 409, { ok: false, provider, error: "meta_credential_not_configured" });
        return;
      }
      if (metadata.expiresAt === 0) {
        json(res, 200, { ok: true, provider, status: "non_expiring", expires_at: 0 });
        return;
      }
      const credential = await resolveMetaCredential(lumosId, provider);
      const refreshed = await refreshMetaToken(provider, credential.accessToken, fetch, credential.authMode);
      const now = Math.floor(Date.now() / 1000);
      const expiresAt = refreshed.expiresIn > 0 ? now + refreshed.expiresIn : 0;
      await writeMetaCredential({
        vaultRef: credential.vaultRef,
        purposeCode: metaPurposeCode(provider),
        provider,
        lumosId,
        providerAccountId: credential.providerAccountId,
        accessToken: refreshed.accessToken,
        tokenType: refreshed.tokenType,
        expiresAt,
        authMode: credential.authMode,
      });
      json(res, 200, { ok: true, provider, status: "refreshed", expires_at: expiresAt });
      await logEvent("oauth.token_refreshed", { route: ROUTE, provider, lumosId });
      return;
    }

    const credential = await resolveMetaCredential(lumosId, provider);
    let upstreamRevoked = true;
    try {
      await revokeMetaToken(provider, credential.accessToken, fetch, credential.authMode);
    } catch {
      upstreamRevoked = false;
    }
    await deleteMetaCredential(lumosId, provider, credential.vaultRef);
    json(res, upstreamRevoked ? 200 : 502, {
      ok: upstreamRevoked,
      provider,
      status: upstreamRevoked ? "revoked" : "revoked_local",
      upstream_revoked: upstreamRevoked,
    });
    await logEvent("oauth.token_revoked", { route: ROUTE, provider, lumosId, status: upstreamRevoked ? "revoked" : "revoked_local" });
  } catch (error) {
    const errorCode = String(error?.message || "meta_token_lifecycle_failed");
    await captureError(new Error(errorCode), { route: ROUTE, provider, errorCode });
    json(res, 502, { ok: false, provider, error: errorCode });
  }
}
