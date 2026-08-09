// Lumos Credential Gateway v2 — Infisical depolama katmanı.
// Machine identity (universal auth) ile login olur, tek secret path altında
// her credential'ı ayrı secret olarak tutar. Okuma yolu format-agnostiktir:
// path altındaki tüm sırlar taranıp JSON parse edilir; v1'in (kaynağı kayıp
// Codex deployment'ı) yazdığı kayıtlar da alan adları eşleştiği sürece görünür.

function clean(value) {
  return String(value || "").trim();
}

export function infisicalConfiguration(env = process.env) {
  const config = {
    url: clean(env.LUMOS_INFISICAL_URL) || "https://app.infisical.com",
    clientId: clean(env.LUMOS_INFISICAL_CLIENT_ID),
    clientSecret: clean(env.LUMOS_INFISICAL_CLIENT_SECRET),
    projectId: clean(env.LUMOS_INFISICAL_PROJECT_ID),
    environment: clean(env.LUMOS_INFISICAL_ENVIRONMENT),
    secretPath: clean(env.LUMOS_INFISICAL_SECRET_PATH) || "/",
  };
  const configured = Boolean(
    config.clientId && config.clientSecret && config.projectId && config.environment,
  );
  return { ...config, configured };
}

async function requestJson(fetchImpl, url, options, errorCode) {
  const response = await fetchImpl(url, {
    ...options,
    signal: AbortSignal.timeout(4000),
  });
  if (!response.ok) {
    const error = new Error(errorCode);
    error.statusCode = response.status;
    throw error;
  }
  return response.json();
}

export async function infisicalLogin(config, fetchImpl = fetch) {
  const payload = await requestJson(
    fetchImpl,
    `${config.url}/api/v1/auth/universal-auth/login`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ clientId: config.clientId, clientSecret: config.clientSecret }),
    },
    "infisical_login_failed",
  );
  const accessToken = clean(payload?.accessToken);
  if (!accessToken) throw new Error("infisical_login_failed");
  return accessToken;
}

function secretsQuery(config) {
  return new URLSearchParams({
    workspaceId: config.projectId,
    environment: config.environment,
    secretPath: config.secretPath,
  }).toString();
}

export async function listSecrets(config, accessToken, fetchImpl = fetch) {
  const payload = await requestJson(
    fetchImpl,
    `${config.url}/api/v3/secrets/raw?${secretsQuery(config)}`,
    { headers: { Authorization: `Bearer ${accessToken}` } },
    "infisical_list_failed",
  );
  const secrets = Array.isArray(payload?.secrets) ? payload.secrets : [];
  return secrets.map((secret) => ({
    name: clean(secret?.secretKey),
    value: String(secret?.secretValue ?? ""),
  }));
}

export async function readSecret(config, accessToken, name, fetchImpl = fetch) {
  try {
    const payload = await requestJson(
      fetchImpl,
      `${config.url}/api/v3/secrets/raw/${encodeURIComponent(name)}?${secretsQuery(config)}`,
      { headers: { Authorization: `Bearer ${accessToken}` } },
      "infisical_read_failed",
    );
    return String(payload?.secret?.secretValue ?? "");
  } catch (error) {
    if (error?.statusCode === 404) return "";
    throw error;
  }
}

export async function writeSecret(config, accessToken, name, value, fetchImpl = fetch) {
  const body = JSON.stringify({
    workspaceId: config.projectId,
    environment: config.environment,
    secretPath: config.secretPath,
    secretValue: value,
  });
  const headers = {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  };
  try {
    await requestJson(
      fetchImpl,
      `${config.url}/api/v3/secrets/raw/${encodeURIComponent(name)}`,
      { method: "POST", headers, body },
      "infisical_create_failed",
    );
    return;
  } catch (error) {
    // 400/409: aynı adla secret zaten var → güncelle.
    if (error?.statusCode !== 400 && error?.statusCode !== 409) throw error;
  }
  await requestJson(
    fetchImpl,
    `${config.url}/api/v3/secrets/raw/${encodeURIComponent(name)}`,
    { method: "PATCH", headers, body },
    "infisical_update_failed",
  );
}

export async function deleteSecret(config, accessToken, name, fetchImpl = fetch) {
  const body = JSON.stringify({
    workspaceId: config.projectId,
    environment: config.environment,
    secretPath: config.secretPath,
  });
  try {
    await requestJson(
      fetchImpl,
      `${config.url}/api/v3/secrets/raw/${encodeURIComponent(name)}`,
      {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body,
      },
      "infisical_delete_failed",
    );
  } catch (error) {
    if (error?.statusCode === 404) return;
    throw error;
  }
}
