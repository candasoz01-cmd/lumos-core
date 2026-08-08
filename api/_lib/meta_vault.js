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
  if (!accessToken || !vaultRef || !providerAccountId) {
    throw new Error("meta_vault_credential_missing");
  }
  return {
    accessToken,
    tokenType: clean(payload?.credential?.token_type) || "bearer",
    expiresAt: Number(payload?.credential?.expires_at || 0),
    vaultRef,
    providerAccountId,
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
