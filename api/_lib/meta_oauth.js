import { createHmac } from "node:crypto";

import { authSecret } from "./lumos_session.js";

export const META_PROVIDERS = Object.freeze(["facebook", "instagram", "whatsapp"]);

function clean(value) {
  return String(value || "").trim();
}

export function metaGraphVersion() {
  return clean(process.env.LUMOS_META_GRAPH_VERSION);
}

export function metaRedirectUri() {
  return clean(process.env.LUMOS_META_OAUTH_REDIRECT_URI) ||
    "https://welockai.com/auth/meta/callback";
}

export function metaProviderConfig(provider) {
  const id = clean(provider).toLowerCase();
  if (!META_PROVIDERS.includes(id)) return null;

  if (id === "instagram") {
    return {
      id,
      clientId: clean(process.env.LUMOS_INSTAGRAM_APP_ID),
      clientSecret: clean(process.env.LUMOS_INSTAGRAM_APP_SECRET),
      authorizeUrl: "https://www.instagram.com/oauth/authorize",
      tokenUrl: "https://api.instagram.com/oauth/access_token",
      scopes: ["instagram_business_basic"],
      identityUrl: "https://graph.instagram.com/me?fields=id,username",
      configurationId: "",
    };
  }

  const graphVersion = metaGraphVersion();
  const base = graphVersion ? `https://graph.facebook.com/${graphVersion}` : "";
  return {
    id,
    clientId: clean(process.env.LUMOS_META_APP_ID),
    clientSecret: clean(process.env.LUMOS_META_APP_SECRET),
    authorizeUrl: graphVersion
      ? `https://www.facebook.com/${graphVersion}/dialog/oauth`
      : "",
    tokenUrl: base ? `${base}/oauth/access_token` : "",
    scopes: id === "facebook"
      ? ["pages_show_list", "pages_read_engagement"]
      : ["business_management", "whatsapp_business_management"],
    identityUrl: base ? `${base}/me?fields=id,name` : "",
    configurationId: id === "whatsapp"
      ? clean(process.env.LUMOS_WHATSAPP_LOGIN_CONFIG_ID)
      : "",
  };
}

export function missingMetaConfiguration(provider) {
  const config = metaProviderConfig(provider);
  if (!config) return ["provider"];
  const missing = [];
  if (!config.clientId) missing.push(config.id === "instagram" ? "LUMOS_INSTAGRAM_APP_ID" : "LUMOS_META_APP_ID");
  if (!config.clientSecret) missing.push(config.id === "instagram" ? "LUMOS_INSTAGRAM_APP_SECRET" : "LUMOS_META_APP_SECRET");
  if (!config.authorizeUrl || !config.tokenUrl || !config.identityUrl) missing.push("LUMOS_META_GRAPH_VERSION");
  if (config.id === "whatsapp" && !config.configurationId) {
    missing.push("LUMOS_WHATSAPP_LOGIN_CONFIG_ID");
  }
  return missing;
}

export function buildMetaAuthorizeUrl(provider, state) {
  const config = metaProviderConfig(provider);
  if (!config || missingMetaConfiguration(provider).length) return "";
  const query = new URLSearchParams({
    client_id: config.clientId,
    redirect_uri: metaRedirectUri(),
    response_type: "code",
    scope: config.scopes.join(","),
    state,
  });
  if (config.id === "whatsapp") {
    query.set("config_id", config.configurationId);
    query.set("override_default_response_type", "true");
  }
  return `${config.authorizeUrl}?${query.toString()}`;
}

export async function exchangeMetaCode(provider, code, fetchImpl = fetch) {
  const config = metaProviderConfig(provider);
  if (!config || missingMetaConfiguration(provider).length || !clean(code)) {
    throw new Error("meta_oauth_not_configured");
  }
  const body = new URLSearchParams({
    client_id: config.clientId,
    client_secret: config.clientSecret,
    code: clean(code),
    grant_type: "authorization_code",
    redirect_uri: metaRedirectUri(),
  });
  const response = await fetchImpl(config.tokenUrl, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!response.ok) throw new Error("meta_token_http_error");
  const payload = await response.json();
  const accessToken = clean(payload?.access_token);
  if (!accessToken) throw new Error("meta_access_token_missing");
  return {
    accessToken,
    tokenType: clean(payload?.token_type) || "bearer",
    expiresIn: Number(payload?.expires_in || 0),
  };
}

export async function fetchMetaIdentity(provider, accessToken, fetchImpl = fetch) {
  const config = metaProviderConfig(provider);
  if (!config?.identityUrl || !clean(accessToken)) throw new Error("meta_identity_not_configured");
  const response = await fetchImpl(config.identityUrl, {
    headers: { Authorization: `Bearer ${accessToken}`, Accept: "application/json" },
  });
  if (!response.ok) throw new Error("meta_identity_http_error");
  const payload = await response.json();
  const accountId = clean(payload?.id);
  if (!accountId) throw new Error("meta_identity_missing");
  return {
    accountId,
    displayName: clean(payload?.username || payload?.name),
  };
}

export function metaVaultRef(lumosId, provider, providerAccountId) {
  const id = clean(provider).toLowerCase();
  if (!clean(lumosId) || !META_PROVIDERS.includes(id) || !clean(providerAccountId)) return "";
  const digest = createHmac("sha256", authSecret())
    .update(`meta-vault-ref-v1:${lumosId}:${id}:${providerAccountId}`)
    .digest("base64url")
    .slice(0, 28);
  return `meta:${id}:${digest}`;
}

export function metaPurposeCode(provider) {
  const id = clean(provider).toLowerCase();
  return META_PROVIDERS.includes(id) ? `integration.meta.${id}.read` : "";
}
