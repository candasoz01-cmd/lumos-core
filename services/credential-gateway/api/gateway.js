// Lumos Credential Gateway v2 — POST /api/gateway
// Sözleşme, lumos-core api/_lib/meta_vault.js istemcisinden birebir türetildi
// (v1 kaynağı kayıp; protokolün doğruluk kaynağı istemci sözleşmesi + testler).
// Fail-closed: token yoksa/yanlışsa 401, depolama yapılandırılmamışsa 503.
import {
  deleteSecret,
  infisicalConfiguration,
  infisicalLogin,
  listSecrets,
  readSecret,
  writeSecret,
} from "../lib/infisical.js";
import {
  encodeCredentialRecord,
  parseCredentialRecord,
  scanCredentialRecords,
  secretNameForRef,
} from "../lib/store.js";

function clean(value) {
  return String(value || "").trim();
}

function json(res, statusCode, body) {
  res.statusCode = statusCode;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(body));
}

function authorized(req) {
  const expected = clean(process.env.LUMOS_CREDENTIAL_GATEWAY_TOKEN);
  const header = clean(req.headers?.authorization);
  return Boolean(expected) && header === `Bearer ${expected}`;
}

function publicRow(record) {
  return {
    vault_ref: record.vault_ref,
    provider: record.provider,
    provider_account_id: record.provider_account_id,
    expires_at: Number(record.credential?.expires_at || 0),
    auth_mode: record.credential?.auth_mode || "",
  };
}

function resolveBody(record) {
  return {
    ok: true,
    vault_ref: record.vault_ref,
    provider: record.provider,
    provider_account_id: record.provider_account_id,
    credential: {
      access_token: record.credential.access_token,
      token_type: record.credential.token_type,
      expires_at: Number(record.credential.expires_at || 0),
      auth_mode: record.credential.auth_mode,
    },
  };
}

async function scanForOwner(config, accessToken, ownerLumosId, fetchImpl) {
  const secrets = await listSecrets(config, accessToken, fetchImpl);
  const { records, unparsed } = scanCredentialRecords(secrets);
  return {
    records: records.filter((record) => record.owner_lumos_id === ownerLumosId),
    unparsed,
  };
}

function newestFirst(records) {
  return [...records].sort((a, b) => (b.updated_at || 0) - (a.updated_at || 0));
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    json(res, 405, { ok: false, error: "method_not_allowed" });
    return;
  }
  if (!authorized(req)) {
    json(res, 401, { ok: false, error: "unauthorized" });
    return;
  }
  const config = infisicalConfiguration();
  if (!config.configured) {
    json(res, 503, { ok: false, error: "storage_not_configured" });
    return;
  }

  let body = req.body;
  if (typeof body === "string") {
    try {
      body = JSON.parse(body);
    } catch {
      body = null;
    }
  }
  const operation = clean(body?.operation);
  const ownerLumosId = clean(body?.owner_lumos_id);
  const provider = clean(body?.provider).toLowerCase();
  const vaultRef = clean(body?.vault_ref);

  // webhook.ingest owner_lumos_id taşımaz (bkz. meta_webhook.js istemcisi):
  // event_key ile idempotent kabul; payload saklanmaz (read-only sınır, ADR-020).
  if (operation === "webhook.ingest") {
    const eventKey = clean(body?.event_key).toLowerCase();
    if (!provider || !/^[a-f0-9]{64}$/.test(eventKey)) {
      json(res, 400, { ok: false, error: "invalid_request" });
      return;
    }
    try {
      const accessToken = await infisicalLogin(config);
      const name = `WEBHOOK__${eventKey}`;
      const existing = await readSecret(config, accessToken, name);
      if (existing) {
        json(res, 200, { ok: true, status: "duplicate" });
        return;
      }
      await writeSecret(config, accessToken, name, JSON.stringify({
        provider,
        received_at: Math.floor(Date.now() / 1000),
      }));
      json(res, 200, { ok: true, status: "accepted" });
    } catch (error) {
      json(res, 502, { ok: false, error: clean(error?.message) || "gateway_failed" });
    }
    return;
  }

  if (!operation || !ownerLumosId) {
    json(res, 400, { ok: false, error: "invalid_request" });
    return;
  }

  try {
    const accessToken = await infisicalLogin(config);

    if (operation === "credential.upsert") {
      if (!vaultRef || !provider || !clean(body?.credential?.access_token)) {
        json(res, 400, { ok: false, error: "invalid_request" });
        return;
      }
      const record = encodeCredentialRecord(body, Math.floor(Date.now() / 1000));
      await writeSecret(config, accessToken, secretNameForRef(vaultRef), record);
      json(res, 200, { ok: true, vault_ref: vaultRef });
      return;
    }

    if (operation === "credential.list") {
      const { records, unparsed } = await scanForOwner(config, accessToken, ownerLumosId);
      const filtered = provider
        ? records.filter((record) => record.provider === provider)
        : records;
      json(res, 200, {
        ok: true,
        credentials: newestFirst(filtered).map(publicRow),
        unparsed_records: unparsed,
      });
      return;
    }

    if (operation === "credential.metadata") {
      if (!provider) {
        json(res, 400, { ok: false, error: "invalid_request" });
        return;
      }
      const { records } = await scanForOwner(config, accessToken, ownerLumosId);
      const match = newestFirst(records.filter((record) => record.provider === provider))[0];
      if (!match) {
        json(res, 200, { ok: true, configured: false, vault_ref: "", expires_at: 0 });
        return;
      }
      json(res, 200, {
        ok: true,
        configured: true,
        vault_ref: match.vault_ref,
        expires_at: Number(match.credential.expires_at || 0),
      });
      return;
    }

    if (operation === "credential.resolve") {
      if (vaultRef) {
        // Hızlı yol: v2 adlandırmasıyla doğrudan oku; bulunamazsa tarama.
        const direct = parseCredentialRecord(
          await readSecret(config, accessToken, secretNameForRef(vaultRef)),
        );
        const record = direct && direct.owner_lumos_id === ownerLumosId && direct.vault_ref === vaultRef
          ? direct
          : (await scanForOwner(config, accessToken, ownerLumosId)).records
              .find((row) => row.vault_ref === vaultRef);
        if (!record || !record.credential.access_token) {
          json(res, 404, { ok: false, error: "credential_not_found" });
          return;
        }
        json(res, 200, resolveBody(record));
        return;
      }
      if (!provider) {
        json(res, 400, { ok: false, error: "invalid_request" });
        return;
      }
      const { records } = await scanForOwner(config, accessToken, ownerLumosId);
      const match = newestFirst(records.filter(
        (record) => record.provider === provider && record.credential.access_token,
      ))[0];
      if (!match) {
        json(res, 404, { ok: false, error: "credential_not_found" });
        return;
      }
      json(res, 200, resolveBody(match));
      return;
    }

    if (operation === "credential.delete") {
      if (!vaultRef) {
        json(res, 400, { ok: false, error: "invalid_request" });
        return;
      }
      const { records } = await scanForOwner(config, accessToken, ownerLumosId);
      const match = records.find((record) => record.vault_ref === vaultRef);
      if (match) await deleteSecret(config, accessToken, match.secret_name);
      else await deleteSecret(config, accessToken, secretNameForRef(vaultRef));
      json(res, 200, { ok: true, vault_ref: vaultRef });
      return;
    }

    json(res, 400, { ok: false, error: "unsupported_operation" });
  } catch (error) {
    json(res, 502, { ok: false, error: clean(error?.message) || "gateway_failed" });
  }
}
