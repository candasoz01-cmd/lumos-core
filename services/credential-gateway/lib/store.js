// Credential kayıt düzeni ve format-agnostik okuma (ADR-021).
// Yazma: secret adı vault_ref'ten deterministik türetilir, değer JSON.
// Okuma: path altındaki TÜM sırlar parse edilir; v2 şeması dışındaki
// (ör. kayıp v1'in yazdığı) JSON kayıtlar da alanlar eşleştiği sürece kabul
// edilir. Parse edilemeyenler sessizce atlanmaz — sayısı raporlanır.

function clean(value) {
  return String(value || "").trim();
}

export function secretNameForRef(vaultRef) {
  // Infisical secret adları için güvenli alfabe: [A-Za-z0-9_-]
  return `CRED__${clean(vaultRef).replace(/[^A-Za-z0-9_-]/g, "_")}`;
}

export function encodeCredentialRecord(input, nowSeconds) {
  return JSON.stringify({
    schema: "lumos-credential-v2",
    vault_ref: clean(input.vault_ref),
    purpose_code: clean(input.purpose_code),
    provider: clean(input.provider),
    owner_lumos_id: clean(input.owner_lumos_id),
    provider_account_id: clean(input.provider_account_id),
    credential: {
      access_token: clean(input.credential?.access_token),
      token_type: clean(input.credential?.token_type) || "bearer",
      expires_at: Number(input.credential?.expires_at || 0),
      auth_mode: clean(input.credential?.auth_mode),
    },
    updated_at: nowSeconds,
  });
}

export function parseCredentialRecord(rawValue) {
  let parsed;
  try {
    parsed = JSON.parse(rawValue);
  } catch {
    return null;
  }
  if (!parsed || typeof parsed !== "object") return null;
  const credential = parsed.credential && typeof parsed.credential === "object"
    ? parsed.credential
    : parsed;
  const record = {
    vault_ref: clean(parsed.vault_ref),
    purpose_code: clean(parsed.purpose_code),
    provider: clean(parsed.provider),
    owner_lumos_id: clean(parsed.owner_lumos_id || parsed.lumos_id),
    provider_account_id: clean(parsed.provider_account_id),
    credential: {
      access_token: clean(credential.access_token),
      token_type: clean(credential.token_type) || "bearer",
      expires_at: Number(credential.expires_at || 0),
      auth_mode: clean(credential.auth_mode),
    },
    updated_at: Number(parsed.updated_at || 0),
  };
  if (!record.vault_ref || !record.provider || !record.owner_lumos_id) return null;
  return record;
}

export function scanCredentialRecords(secrets) {
  const records = [];
  let unparsed = 0;
  for (const secret of secrets) {
    const name = clean(secret?.name);
    if (!name || name.startsWith("WEBHOOK__") || name.startsWith("CONN__")) continue;
    const record = parseCredentialRecord(secret.value);
    if (record) {
      records.push({ ...record, secret_name: name });
      continue;
    }
    // JSON objesi olup şemaya oturmayanlar (muhtemel v1 kaydı) görünür kalsın;
    // düz string config sırları sayılmaz.
    let maybeObject = false;
    try {
      const parsed = JSON.parse(secret.value);
      maybeObject = Boolean(parsed) && typeof parsed === "object";
    } catch {
      maybeObject = false;
    }
    if (maybeObject || name.startsWith("CRED")) unparsed += 1;
  }
  return { records, unparsed };
}
