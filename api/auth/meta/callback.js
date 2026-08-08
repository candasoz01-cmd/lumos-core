/** GET /api/auth/meta/callback -> code exchange -> private credential vault */
import {
  COOKIE,
  openSession,
  readCookie,
  sessionLumosId,
  stateMatchesCookie,
  verifyState,
} from "../../_lib/lumos_session.js";
import {
  exchangeMetaCode,
  extendMetaToken,
  fetchMetaIdentity,
  metaPurposeCode,
  metaProviderConfig,
  metaVaultRef,
} from "../../_lib/meta_oauth.js";
import { writeMetaCredential } from "../../_lib/meta_vault.js";
import { captureError, captureSecurityEvent, logEvent } from "../../_lib/observability.js";
import { META_FLOW_COOKIE } from "./start.js";

const ROUTE = "meta_oauth_callback";

function clearMetaFlowCookieHeader() {
  return `${META_FLOW_COOKIE}=; Path=/auth/meta; HttpOnly; Secure; SameSite=Lax; Max-Age=0`;
}

function redirectResult(res, provider, key, value) {
  const query = new URLSearchParams({ provider, [key]: value });
  res.statusCode = 302;
  res.setHeader("Set-Cookie", clearMetaFlowCookieHeader());
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("Location", `/integrations/meta?${query.toString()}`);
  res.end();
}

export default async function handler(req, res) {
  if (req.method !== "GET") {
    res.statusCode = 405;
    res.end("method_not_allowed");
    return;
  }
  const url = new URL(req.url || "/", "https://welockai.com");
  const code = String(url.searchParams.get("code") || "").trim();
  const state = String(url.searchParams.get("state") || "").trim();
  const providerError = String(url.searchParams.get("error") || "").trim();
  const claims = openSession(readCookie(req, COOKIE));
  const lumosId = sessionLumosId(claims);
  const flow = openSession(readCookie(req, META_FLOW_COOKIE));
  const provider = String(flow?.provider || "").trim().toLowerCase();

  let stateOk = false;
  try {
    stateOk = flow?.kind === "meta_oauth" &&
      Boolean(claims?.sid) &&
      Boolean(lumosId) &&
      lumosId === String(flow.lumos_id || "") &&
      verifyState(state) &&
      stateMatchesCookie(state, flow.state);
  } catch {
    stateOk = false;
  }
  if (!stateOk) {
    await captureSecurityEvent("invalid_state", { route: ROUTE, provider });
    redirectResult(res, provider, "meta_error", "invalid_state");
    return;
  }
  if (providerError) {
    await logEvent("oauth.callback.provider_error", { route: ROUTE, provider, errorCode: providerError });
    redirectResult(res, provider, "meta_error", "provider_denied");
    return;
  }
  if (!code) {
    redirectResult(res, provider, "meta_error", "missing_code");
    return;
  }

  try {
    const shortToken = await exchangeMetaCode(provider, code);
    const token = provider === "whatsapp" && shortToken.expiresIn === 0
      ? shortToken
      : await extendMetaToken(provider, shortToken.accessToken);
    const identity = await fetchMetaIdentity(provider, token.accessToken);
    const vaultRef = metaVaultRef(lumosId, provider, identity.accountId);
    const purposeCode = metaPurposeCode(provider);
    const now = Math.floor(Date.now() / 1000);
    await writeMetaCredential({
      vaultRef,
      purposeCode,
      provider,
      lumosId,
      providerAccountId: identity.accountId,
      accessToken: token.accessToken,
      tokenType: token.tokenType,
      expiresAt: token.expiresIn > 0 ? now + token.expiresIn : 0,
      authMode: metaProviderConfig(provider)?.authMode || "",
    });
    redirectResult(res, provider, "meta_status", "authorized");
    await logEvent("oauth.callback.success", { route: ROUTE, provider, lumosId });
  } catch (error) {
    const errorCode = String(error?.message || "meta_oauth_callback_failed");
    await captureError(new Error(errorCode), { route: ROUTE, provider, errorCode });
    redirectResult(res, provider, "meta_error", errorCode);
  }
}
