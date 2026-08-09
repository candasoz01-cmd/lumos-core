function clean(value) {
  return String(value || "").trim();
}

export function metaVaultWriteConfiguration() {
  const url = clean(process.env.LUMOS_CREDENTIAL_VAULT_WRITE_URL);
  const token = clean(process.env.LUMOS_CREDENTIAL_VAULT_WRITE_TOKEN);
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:") return { configured: false, url: "", token: "" };
  } catch {
    return { configured: false, url: "", token: "" };
  }
  return { configured: Boolean(token), url, token };
}

async function callMetaVault(operation, fields, fetchImpl = fetch) {
  const config = metaVaultWriteConfiguration();
  if (!config.configured) throw new Error("meta_vault_not_configured");
  const response = await fetchImpl(config.url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${config.token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ operation, ...fields }),
    signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) throw new Error("meta_vault_operation_failed");
  const payload = await response.json();
  if (payload?.ok !== true) throw new Error("meta_vault_operation_invalid_response");
  return payload;
}

export async function writeMetaCredential(input, fetchImpl = fetch) {
  const payload = await callMetaVault(
    "credential.upsert",
    {
      vault_ref: input.vaultRef,
      purpose_code: input.purposeCode,
      provider: input.provider,
      owner_lumos_id: input.lumosId,
      provider_account_id: input.providerAccountId,
      credential: {
        access_token: input.accessToken,
        token_type: input.tokenType,
        expires_at: input.expiresAt,
        auth_mode: input.authMode,
      },
    },
    fetchImpl,
  );
  if (clean(payload?.vault_ref) !== input.vaultRef) {
    throw new Error("meta_vault_write_invalid_response");
  }
  return { vaultRef: input.vaultRef };
}

export async function metaCredentialMetadata(lumosId, provider, fetchImpl = fetch) {
  const payload = await callMetaVault(
    "credential.metadata",
    { owner_lumos_id: lumosId, provider },
    fetchImpl,
  );
  const vaultRef = clean(payload.vault_ref);
  return {
    configured: payload.configured === true && Boolean(vaultRef),
    vaultRef,
    expiresAt: Number(payload.expires_at || 0),
  };
}

export async function resolveMetaCredential(lumosId, provider, fetchImpl = fetch) {
  const payload = await callMetaVault(
    "credential.resolve",
    { owner_lumos_id: lumosId, provider },
    fetchImpl,
  );
  const accessToken = clean(payload?.credential?.access_token);
  const vaultRef = clean(payload?.vault_ref);
  const providerAccountId = clean(payload?.provider_account_id);
  const storedAuthMode = clean(payload?.credential?.auth_mode);
  if (!accessToken || !vaultRef || !providerAccountId) {
    throw new Error("meta_vault_credential_missing");
  }
  return {
    accessToken,
    tokenType: clean(payload?.credential?.token_type) || "bearer",
    expiresAt: Number(payload?.credential?.expires_at || 0),
    vaultRef,
    providerAccountId,
    authMode: storedAuthMode || (provider === "instagram" ? "" : "facebook_login"),
  };
}

export async function deleteMetaCredential(lumosId, provider, vaultRef, fetchImpl = fetch) {
  const payload = await callMetaVault(
    "credential.delete",
    { owner_lumos_id: lumosId, provider, vault_ref: vaultRef },
    fetchImpl,
  );
  if (clean(payload?.vault_ref) !== vaultRef) {
    throw new Error("meta_vault_delete_invalid_response");
  }
  return { deleted: true, vaultRef };
}

// ---------------------------------------------------------------- ADR-021 S1
// Çoklu bağlantı modeli: credential ≠ bağlantı. Bir kullanıcı+provider altında
// BİRDEN FAZLA credential yaşayabilir; liste secret'sız metadata döner, çözümleme
// vault_ref ile hesap-kapsamlı yapılır. Eski owner+provider tekil fonksiyonlar
// geçiş süresince aynen korunur (ADR-021 §2).

export async function listMetaCredentials(lumosId, provider, fetchImpl = fetch) {
  const fields = { owner_lumos_id: lumosId };
  if (clean(provider)) fields.provider = clean(provider);
  const payload = await callMetaVault("credential.list", fields, fetchImpl);
  const items = Array.isArray(payload?.credentials) ? payload.credentials : [];
  return items
    .map((item) => ({
      vaultRef: clean(item?.vault_ref),
      provider: clean(item?.provider),
      providerAccountId: clean(item?.provider_account_id),
      expiresAt: Number(item?.expires_at || 0),
      authMode: clean(item?.auth_mode),
    }))
    .filter((item) => item.vaultRef && item.provider && item.providerAccountId);
}

// ---------------------------------------------------------------- ADR-021 S5
// Bağlantı kayıtları: connection_id kalıcı iç kimlik; credential'a vault_ref
// REFERANSI ile bağlanır (upsert'te gönderilir, listede geri DÖNMEZ).

export async function upsertMetaConnection(lumosId, connection, fetchImpl = fetch) {
  const payload = await callMetaVault(
    "connection.upsert",
    {
      owner_lumos_id: lumosId,
      connection_id: connection.connectionId,
      provider: connection.provider,
      credential_ref: connection.credentialRef,
      waba_id: connection.wabaId,
      waba_name: connection.wabaName,
      business_id: connection.businessId,
      business_name: connection.businessName,
      phone_number_id: connection.phoneNumberId,
      display_phone_number: connection.displayPhoneNumber,
      verified_name: connection.verifiedName,
      last_verified_at: connection.lastVerifiedAt,
    },
    fetchImpl,
  );
  if (clean(payload?.connection_id) !== connection.connectionId) {
    throw new Error("meta_connection_upsert_invalid_response");
  }
  return { connectionId: connection.connectionId };
}

export async function listMetaConnections(lumosId, provider, fetchImpl = fetch) {
  const fields = { owner_lumos_id: lumosId };
  if (clean(provider)) fields.provider = clean(provider);
  const payload = await callMetaVault("connection.list", fields, fetchImpl);
  const items = Array.isArray(payload?.connections) ? payload.connections : [];
  return items
    .map((item) => ({
      connectionId: clean(item?.connection_id),
      provider: clean(item?.provider),
      wabaId: clean(item?.waba_id),
      wabaName: clean(item?.waba_name),
      businessId: clean(item?.business_id),
      businessName: clean(item?.business_name),
      phoneNumberId: clean(item?.phone_number_id),
      displayPhoneNumber: clean(item?.display_phone_number),
      verifiedName: clean(item?.verified_name),
      lastVerifiedAt: Number(item?.last_verified_at || 0),
    }))
    .filter((item) => item.connectionId && item.provider);
}

export async function resolveMetaCredentialByRef(lumosId, vaultRef, fetchImpl = fetch) {
  const ref = clean(vaultRef);
  if (!ref) throw new Error("meta_vault_ref_required");
  const payload = await callMetaVault(
    "credential.resolve",
    { owner_lumos_id: lumosId, vault_ref: ref },
    fetchImpl,
  );
  if (clean(payload?.vault_ref) !== ref) {
    throw new Error("meta_vault_resolve_ref_mismatch");
  }
  const accessToken = clean(payload?.credential?.access_token);
  const providerAccountId = clean(payload?.provider_account_id);
  if (!accessToken || !providerAccountId) {
    throw new Error("meta_vault_credential_missing");
  }
  return {
    accessToken,
    tokenType: clean(payload?.credential?.token_type) || "bearer",
    expiresAt: Number(payload?.credential?.expires_at || 0),
    vaultRef: ref,
    providerAccountId,
    authMode: clean(payload?.credential?.auth_mode),
  };
}
