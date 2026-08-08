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

export async function writeMetaCredential(input, fetchImpl = fetch) {
  const config = metaVaultWriteConfiguration();
  if (!config.configured) throw new Error("meta_vault_not_configured");
  const response = await fetchImpl(config.url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${config.token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      operation: "credential.upsert",
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
    }),
  });
  if (!response.ok) throw new Error("meta_vault_write_failed");
  const payload = await response.json();
  if (payload?.ok !== true || clean(payload?.vault_ref) !== input.vaultRef) {
    throw new Error("meta_vault_write_invalid_response");
  }
  return { vaultRef: input.vaultRef };
}
