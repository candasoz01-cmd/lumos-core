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

function parseJson(value) {
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

const safeKey = (value) => clean(value).replace(/[^A-Za-z0-9_-]/g, "_");
const deletionKey = (code) => `DELETION__${safeKey(code)}`;

// Silme çekirdeği: verilen credential kayıtlarını, onlara credential_ref ile
// bağlı CONN__ kayıtlarını ve bu bağlantıların INBOUND__/LASTIN__/SEND__
// kayıtlarını siler. Silinen her ad sayılır; hiçbir şey "silindi" sayılmadan
// önce deleteSecret başarıyla dönmüş olmalıdır.
async function purgeCredentialTree(config, accessToken, secrets, credentialRecords, extraRefs = []) {
  const counts = { credentials: 0, connections: 0, inbound: 0, last_inbound: 0, send: 0 };
  const refs = new Set(extraRefs.map(clean).filter(Boolean));
  for (const record of credentialRecords) {
    await deleteSecret(config, accessToken, record.secret_name);
    counts.credentials += 1;
    refs.add(record.vault_ref);
  }
  const connectionIds = new Set();
  const phones = [];
  for (const secret of secrets) {
    if (!secret.name.startsWith("CONN__")) continue;
    const parsed = parseJson(secret.value);
    if (!parsed || !refs.has(clean(parsed.credential_ref))) continue;
    await deleteSecret(config, accessToken, secret.name);
    counts.connections += 1;
    connectionIds.add(clean(parsed.connection_id));
    if (clean(parsed.phone_number_id) && clean(parsed.waba_id)) {
      phones.push({ phone: clean(parsed.phone_number_id), waba: clean(parsed.waba_id) });
    }
  }
  for (const secret of secrets) {
    const parsed = secret.name.startsWith("LASTIN__") ? null : parseJson(secret.value);
    if (secret.name.startsWith("INBOUND__")) {
      if (!phones.some((p) => p.phone === clean(parsed?.phone_number_id) && p.waba === clean(parsed?.waba_id))) continue;
      await deleteSecret(config, accessToken, secret.name);
      counts.inbound += 1;
    } else if (secret.name.startsWith("LASTIN__")) {
      if (!phones.some((p) => secret.name.startsWith(`LASTIN__${safeKey(p.phone)}__`))) continue;
      await deleteSecret(config, accessToken, secret.name);
      counts.last_inbound += 1;
    } else if (secret.name.startsWith("SEND__")) {
      if (!connectionIds.has(clean(parsed?.connection_id))) continue;
      await deleteSecret(config, accessToken, secret.name);
      counts.send += 1;
    }
  }
  return counts;
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

  // ---------------------------------------------------------- ADR-022 D2
  // Inbound zarfı + gönderim rezervasyonu. Kurucu sınırları (2026-08-10):
  // mesaj GÖVDESİ saklanmaz (yalnız zarf + varsa içerik hash'i); SEND_INTENT
  // rezervasyonu yazılamazsa gönderim yapılmaz (gerçek fail-closed); bu
  // operasyonlar mesaj GÖNDERMEZ — yalnız kayıt düzlemi.
  const inboundKey = (messageId) => `INBOUND__${clean(messageId).replace(/[^A-Za-z0-9_-]/g, "_")}`;
  const lastInKey = (phoneNumberId, fromWaId) =>
    `LASTIN__${clean(phoneNumberId).replace(/[^A-Za-z0-9_-]/g, "_")}__${clean(fromWaId).replace(/[^A-Za-z0-9_-]/g, "_")}`;
  const sendKey = (inboundMessageId) => `SEND__${clean(inboundMessageId).replace(/[^A-Za-z0-9_-]/g, "_")}`;

  if (operation === "inbound.store") {
    const messageId = clean(body?.message_id);
    const fromWaId = clean(body?.from_wa_id);
    const phoneNumberId = clean(body?.phone_number_id);
    const wabaId = clean(body?.waba_id);
    if (!provider || !messageId || !fromWaId || !phoneNumberId || !wabaId) {
      json(res, 400, { ok: false, error: "invalid_request" });
      return;
    }
    try {
      const accessToken = await infisicalLogin(config);
      const existing = await readSecret(config, accessToken, inboundKey(messageId));
      if (existing) {
        json(res, 200, { ok: true, status: "duplicate" });
        return;
      }
      const receivedAt = Number(body?.timestamp || 0) || Math.floor(Date.now() / 1000);
      await writeSecret(config, accessToken, inboundKey(messageId), JSON.stringify({
        schema: "lumos-inbound-v1",
        provider,
        message_id: messageId,
        from_wa_id: fromWaId,
        phone_number_id: phoneNumberId,
        waba_id: wabaId,
        timestamp: receivedAt,
        message_type: clean(body?.message_type),
        content_hash: clean(body?.content_hash),
      }));
      await writeSecret(config, accessToken, lastInKey(phoneNumberId, fromWaId), JSON.stringify({
        last_inbound_at: receivedAt,
        message_id: messageId,
      }));
      json(res, 200, { ok: true, status: "stored" });
    } catch (error) {
      json(res, 502, { ok: false, error: clean(error?.message) || "gateway_failed" });
    }
    return;
  }

  if (operation === "inbound.last") {
    const fromWaId = clean(body?.from_wa_id);
    const phoneNumberId = clean(body?.phone_number_id);
    if (!fromWaId || !phoneNumberId) {
      json(res, 400, { ok: false, error: "invalid_request" });
      return;
    }
    try {
      const accessToken = await infisicalLogin(config);
      const raw = await readSecret(config, accessToken, lastInKey(phoneNumberId, fromWaId));
      if (!raw) {
        json(res, 200, { ok: true, last_inbound_at: 0 });
        return;
      }
      const parsed = JSON.parse(raw);
      json(res, 200, {
        ok: true,
        last_inbound_at: Number(parsed?.last_inbound_at || 0),
        message_id: clean(parsed?.message_id),
      });
    } catch (error) {
      json(res, 502, { ok: false, error: clean(error?.message) || "gateway_failed" });
    }
    return;
  }

  if (operation === "connection.lookup") {
    const phoneNumberId = clean(body?.phone_number_id);
    const wabaId = clean(body?.waba_id);
    if (!phoneNumberId || !wabaId) {
      json(res, 400, { ok: false, error: "invalid_request" });
      return;
    }
    try {
      const accessToken = await infisicalLogin(config);
      const secrets = await listSecrets(config, accessToken);
      // TAM eşleşme, fail-closed: phone_number_id VE waba_id birlikte.
      let match = null;
      for (const secret of secrets) {
        if (!secret.name.startsWith("CONN__")) continue;
        let parsed;
        try {
          parsed = JSON.parse(secret.value);
        } catch {
          continue;
        }
        if (clean(parsed?.phone_number_id) === phoneNumberId && clean(parsed?.waba_id) === wabaId) {
          match = parsed;
          break;
        }
      }
      if (!match) {
        json(res, 404, { ok: false, error: "connection_not_found" });
        return;
      }
      json(res, 200, {
        ok: true,
        connection_id: clean(match.connection_id),
        owner_lumos_id: clean(match.owner_lumos_id),
        provider: clean(match.provider),
      });
    } catch (error) {
      json(res, 502, { ok: false, error: clean(error?.message) || "gateway_failed" });
    }
    return;
  }

  if (operation === "send.reserve") {
    const inboundMessageId = clean(body?.inbound_message_id);
    const connectionId = clean(body?.connection_id);
    const domainId = clean(body?.domain_id);
    if (!inboundMessageId || !connectionId) {
      json(res, 400, { ok: false, error: "invalid_request" });
      return;
    }
    try {
      const accessToken = await infisicalLogin(config);
      const key = sendKey(inboundMessageId);
      const existing = await readSecret(config, accessToken, key);
      if (existing) {
        // İdempotency: aynı inbound için ikinci rezervasyon YOK — çağıran
        // göndermemelidir.
        json(res, 200, { ok: true, status: "duplicate" });
        return;
      }
      await writeSecret(config, accessToken, key, JSON.stringify({
        schema: "lumos-send-v1",
        inbound_message_id: inboundMessageId,
        connection_id: connectionId,
        domain_id: domainId,
        status: "intent",
        reserved_at: Math.floor(Date.now() / 1000),
      }));
      json(res, 200, { ok: true, status: "reserved" });
    } catch (error) {
      // Rezervasyon yazılamadı → çağıran GÖNDERMEZ (fail-closed).
      json(res, 502, { ok: false, error: clean(error?.message) || "gateway_failed" });
    }
    return;
  }

  if (operation === "send.finalize") {
    const inboundMessageId = clean(body?.inbound_message_id);
    const status = clean(body?.status);
    if (!inboundMessageId || !new Set(["sent", "failed"]).has(status)) {
      json(res, 400, { ok: false, error: "invalid_request" });
      return;
    }
    try {
      const accessToken = await infisicalLogin(config);
      const key = sendKey(inboundMessageId);
      const raw = await readSecret(config, accessToken, key);
      if (!raw) {
        json(res, 404, { ok: false, error: "send_intent_not_found" });
        return;
      }
      const record = JSON.parse(raw);
      await writeSecret(config, accessToken, key, JSON.stringify({
        ...record,
        status,
        provider_message_id: clean(body?.provider_message_id),
        finalized_at: Math.floor(Date.now() / 1000),
      }));
      json(res, 200, { ok: true, status });
    } catch (error) {
      json(res, 502, { ok: false, error: clean(error?.message) || "gateway_failed" });
    }
    return;
  }

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

  // Meta veri silme / yetki kaldırma geri çağrısı (KARAR-2, #903). Çağrı
  // Meta'nın imzalı isteğinden gelir; owner_lumos_id bilinmez. Eşleşme:
  // provider listesi + provider_account_id (Meta'nın uygulama kapsamlı
  // kullanıcı kimliği). Durum kaydı kullanıcı kimliği taşımaz.
  if (operation === "account.purge") {
    const providers = new Set(
      (Array.isArray(body?.providers) ? body.providers : []).map((item) => clean(item).toLowerCase()).filter(Boolean),
    );
    const providerAccountId = clean(body?.provider_account_id);
    const code = clean(body?.confirmation_code);
    if (!providers.size || !providerAccountId || !/^[A-Za-z0-9_-]{16,64}$/.test(code)) {
      json(res, 400, { ok: false, error: "invalid_request" });
      return;
    }
    const requestedAt = Math.floor(Date.now() / 1000);
    let accessToken;
    try {
      accessToken = await infisicalLogin(config);
      const secrets = await listSecrets(config, accessToken);
      const { records } = scanCredentialRecords(secrets);
      const matches = records.filter(
        (record) => providers.has(record.provider) && record.provider_account_id === providerAccountId,
      );
      const counts = await purgeCredentialTree(config, accessToken, secrets, matches);
      const status = {
        schema: "lumos-deletion-v1",
        status: "completed",
        providers: [...providers].sort(),
        requested_at: requestedAt,
        completed_at: Math.floor(Date.now() / 1000),
        counts,
      };
      await writeSecret(config, accessToken, deletionKey(code), JSON.stringify(status));
      json(res, 200, { ok: true, ...status });
    } catch (error) {
      if (accessToken) {
        try {
          await writeSecret(config, accessToken, deletionKey(code), JSON.stringify({
            schema: "lumos-deletion-v1",
            status: "failed",
            providers: [...providers].sort(),
            requested_at: requestedAt,
          }));
        } catch {
          // Durum kaydı da yazılamadı; çağıran başarısızlığı görür.
        }
      }
      json(res, 502, { ok: false, error: clean(error?.message) || "gateway_failed" });
    }
    return;
  }

  if (operation === "deletion.status") {
    const code = clean(body?.confirmation_code);
    if (!/^[A-Za-z0-9_-]{16,64}$/.test(code)) {
      json(res, 400, { ok: false, error: "invalid_request" });
      return;
    }
    try {
      const accessToken = await infisicalLogin(config);
      const record = parseJson(await readSecret(config, accessToken, deletionKey(code)));
      if (!record) {
        json(res, 404, { ok: false, error: "deletion_not_found" });
        return;
      }
      json(res, 200, { ok: true, ...record });
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

    // ADR-021 S5 — bağlantı kayıtları: connection_id kalıcı iç kimlik,
    // credential'a vault_ref REFERANSI ile bağlanır (kopya yok), sır içermez.
    if (operation === "connection.upsert") {
      const connectionId = clean(body?.connection_id);
      if (!connectionId || !provider) {
        json(res, 400, { ok: false, error: "invalid_request" });
        return;
      }
      const record = JSON.stringify({
        schema: "lumos-connection-v1",
        connection_id: connectionId,
        owner_lumos_id: ownerLumosId,
        provider,
        credential_ref: clean(body?.credential_ref),
        waba_id: clean(body?.waba_id),
        waba_name: clean(body?.waba_name),
        business_id: clean(body?.business_id),
        business_name: clean(body?.business_name),
        phone_number_id: clean(body?.phone_number_id),
        display_phone_number: clean(body?.display_phone_number),
        verified_name: clean(body?.verified_name),
        page_id: clean(body?.page_id),
        page_name: clean(body?.page_name),
        last_verified_at: Number(body?.last_verified_at || 0),
      });
      await writeSecret(config, accessToken, `CONN__${connectionId.replace(/[^A-Za-z0-9_-]/g, "_")}`, record);
      json(res, 200, { ok: true, connection_id: connectionId });
      return;
    }

    if (operation === "connection.list") {
      const secrets = await listSecrets(config, accessToken);
      const rows = [];
      for (const secret of secrets) {
        if (!secret.name.startsWith("CONN__")) continue;
        let parsed;
        try {
          parsed = JSON.parse(secret.value);
        } catch {
          continue;
        }
        if (clean(parsed?.owner_lumos_id) !== ownerLumosId) continue;
        if (provider && clean(parsed?.provider) !== provider) continue;
        // credential_ref iç referanstır; liste yanıtında dışarı verilmez.
        const { credential_ref: _internalRef, ...publicFields } = parsed;
        rows.push(publicFields);
      }
      json(res, 200, { ok: true, connections: rows });
      return;
    }

    // Kullanıcının "Bağlantıyı kaldır" eylemi: credential silindikten sonra
    // ona bağlı bağlantı kayıtları ve WhatsApp zarf/rezervasyon kayıtları.
    if (operation === "connection.delete") {
      const credentialRef = clean(body?.credential_ref);
      if (!credentialRef) {
        json(res, 400, { ok: false, error: "invalid_request" });
        return;
      }
      const secrets = await listSecrets(config, accessToken);
      const owned = secrets.filter((secret) => {
        if (!secret.name.startsWith("CONN__")) return true;
        return clean(parseJson(secret.value)?.owner_lumos_id) === ownerLumosId;
      });
      const counts = await purgeCredentialTree(config, accessToken, owned, [], [credentialRef]);
      json(res, 200, { ok: true, credential_ref: credentialRef, counts });
      return;
    }

    json(res, 400, { ok: false, error: "unsupported_operation" });
  } catch (error) {
    json(res, 502, { ok: false, error: clean(error?.message) || "gateway_failed" });
  }
}
