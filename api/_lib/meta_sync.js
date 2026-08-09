import { metaGraphVersion } from "./meta_oauth.js";

function clean(value) {
  return String(value || "").trim().slice(0, 256);
}

function safeAccounts(items, fields) {
  if (!Array.isArray(items)) return [];
  return items.slice(0, 50).map((item) => {
    const account = {};
    for (const field of fields) {
      if (field === "media_count") account[field] = Number(item?.[field] || 0);
      else account[field] = clean(item?.[field]);
    }
    return account;
  }).filter((item) => item.id);
}

function graphFacebookUrl(path, fields) {
  const version = metaGraphVersion();
  if (!version) throw new Error("meta_graph_version_not_configured");
  return `https://graph.facebook.com/${version}/${path}?${new URLSearchParams({ fields, limit: "50" })}`;
}

export function metaSyncRequest(provider, credential) {
  if (provider === "instagram" && credential.authMode === "instagram_login") {
    return {
      mode: "instagram_login",
      url: "https://graph.instagram.com/me?fields=id,username,account_type,media_count",
    };
  }
  if (provider === "instagram" && credential.authMode === "facebook_login") {
    return {
      mode: "facebook_login",
      url: graphFacebookUrl(credential.providerAccountId, "id,username,media_count"),
    };
  }
  if (provider === "instagram") throw new Error("meta_sync_auth_mode_missing");
  if (provider === "facebook" || provider === "pages") {
    return {
      mode: "facebook_login",
      url: graphFacebookUrl("me/accounts", "id,name"),
    };
  }
  if (provider === "whatsapp") {
    return {
      mode: "facebook_login",
      url: graphFacebookUrl(
        "me/businesses",
        "id,name,owned_whatsapp_business_accounts{id,name}",
      ),
    };
  }
  throw new Error("meta_sync_provider_unsupported");
}

export async function syncMetaReadOnly(provider, credential, fetchImpl = fetch) {
  const request = metaSyncRequest(provider, credential);
  const response = await fetchImpl(request.url, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${credential.accessToken}`,
      Accept: "application/json",
    },
    signal: AbortSignal.timeout(7000),
  });
  if (!response.ok) throw new Error("meta_sync_http_error");
  const payload = await response.json();

  if (provider === "instagram") {
    const accounts = safeAccounts([payload], ["id", "username", "account_type", "media_count"]);
    if (!accounts.length) throw new Error("meta_sync_identity_missing");
    return { mode: request.mode, accounts };
  }
  if (provider === "facebook" || provider === "pages") {
    return {
      mode: request.mode,
      accounts: safeAccounts(payload?.data, ["id", "name"]),
      has_more: Boolean(payload?.paging?.next),
    };
  }

  const businesses = safeAccounts(payload?.data, ["id", "name"]);
  const whatsappAccounts = [];
  let nestedHasMore = false;
  for (const business of Array.isArray(payload?.data) ? payload.data.slice(0, 50) : []) {
    const ownedPayload = business?.owned_whatsapp_business_accounts;
    const rawOwned = Array.isArray(ownedPayload?.data) ? ownedPayload.data : [];
    if (rawOwned.length > 50 || ownedPayload?.paging?.next) nestedHasMore = true;
    const owned = safeAccounts(rawOwned, ["id", "name"]);
    for (const account of owned) {
      whatsappAccounts.push({ ...account, business_id: clean(business?.id) });
    }
  }
  if (whatsappAccounts.length > 50) nestedHasMore = true;
  return {
    mode: request.mode,
    businesses,
    accounts: whatsappAccounts.slice(0, 50),
    has_more: Boolean(payload?.paging?.next) || nestedHasMore,
  };
}
