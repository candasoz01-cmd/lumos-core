/** ADR-021 S4c — GET /api/integrations/meta/whatsapp/connections
 *
 * WhatsApp credential'ları üzerinden WABA + telefon numarası enumerasyonu;
 * her numara kalıcı connection_id'li ayrı satır. Salt-okunur, secret dönmez,
 * vault_ref gövdeye sızmaz (S2 leak-guard çizgisi): satır, credential'ına
 * `credential_account_id` (provider_account_id) ile bağlanır; sunucu tarafında
 * çözümleme vault_ref REFERANSI ile yapılır, credential kopyalanmaz.
 *
 * Kurucu sınırı: enumeration 0/eksik dönerse satır uydurulmaz; boşluklar
 * `gaps`'te görünür. Tüm credential'lar hatayla düşerse bu boş liste değil
 * kesintidir → 502.
 */
import {
  COOKIE,
  openSession,
  readCookie,
  sessionLumosId,
} from "../../../_lib/lumos_session.js";
import { enumerateWhatsappNumbers } from "../../../_lib/meta_connections.js";
import { metaProviderConfig } from "../../../_lib/meta_oauth.js";
import {
  listMetaConnections,
  listMetaCredentials,
  resolveMetaCredentialByRef,
  upsertMetaConnection,
} from "../../../_lib/meta_vault.js";
import { captureError, logEvent } from "../../../_lib/observability.js";

const ROUTE = "meta_whatsapp_connections";

function json(res, status, payload) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(payload));
}

export default async function handler(req, res) {
  if (req.method !== "GET") {
    json(res, 405, { ok: false, error: "method_not_allowed" });
    return;
  }
  const claims = openSession(readCookie(req, COOKIE));
  const lumosId = claims?.sid ? sessionLumosId(claims) : "";
  if (!lumosId) {
    json(res, 401, { ok: false, error: "unauthorized" });
    return;
  }

  let credentials;
  try {
    credentials = await listMetaCredentials(lumosId, "whatsapp");
  } catch (error) {
    await captureError(error, { route: ROUTE, errorCode: "credential_list_failed" });
    json(res, 503, { ok: false, error: "credential_list_unavailable" });
    return;
  }
  if (credentials.length === 0) {
    json(res, 200, {
      ok: true,
      connections: [],
      gaps: [{ reason: "no_whatsapp_credential" }],
      checked_at: new Date().toISOString(),
    });
    return;
  }

  const requestedScopes = metaProviderConfig("whatsapp")?.scopes || [];
  const nowSeconds = Math.floor(Date.now() / 1000);
  const connections = [];
  const gaps = [];
  let failures = 0;
  for (const row of credentials) {
    try {
      const credential = await resolveMetaCredentialByRef(lumosId, row.vaultRef);
      const result = await enumerateWhatsappNumbers(lumosId, credential);
      for (const number of result.numbers) {
        connections.push({
          ...number,
          credential_account_id: row.providerAccountId,
          requested_scopes: requestedScopes,
          status: "verified",
          last_verified_at: nowSeconds,
        });
        // ADR-021 S5: başarılı doğrulama kalıcı kayda yazılır. Yazım hatası
        // canlı sonucu düşürmez ama görünür raporlanır.
        try {
          await upsertMetaConnection(lumosId, {
            connectionId: number.connection_id,
            provider: "whatsapp",
            credentialRef: row.vaultRef,
            wabaId: number.waba_id,
            wabaName: number.waba_name,
            businessId: number.business_id,
            businessName: number.business_name,
            phoneNumberId: number.phone_number_id,
            displayPhoneNumber: number.display_phone_number,
            verifiedName: number.verified_name,
            lastVerifiedAt: nowSeconds,
          });
        } catch (persistError) {
          await captureError(persistError, { route: ROUTE, errorCode: "connection_persist_failed" });
          gaps.push({ reason: "persist_failed", connection_id: number.connection_id });
        }
      }
      for (const gap of result.gaps) {
        gaps.push({ ...gap, credential_account_id: row.providerAccountId });
      }
    } catch (error) {
      failures += 1;
      const errorCode = String(error?.message || "whatsapp_enumeration_failed");
      await captureError(new Error(errorCode), { route: ROUTE, errorCode });
      gaps.push({
        reason: "enumeration_failed",
        error: errorCode,
        credential_account_id: row.providerAccountId,
      });
    }
  }

  // "Servis çöktü" ≠ "numara yok": canlı satır yok ve her credential düştüyse,
  // depodaki GERÇEK geçmiş kayıtlar (uydurma değil) eski last_verified_at ile
  // "doğrulanamadı" durumunda gösterilir; depo da boşsa kesinti raporlanır.
  if (connections.length === 0 && failures === credentials.length) {
    try {
      const stored = await listMetaConnections(lumosId, "whatsapp");
      if (stored.length > 0) {
        json(res, 200, {
          ok: true,
          mode: "stored_last_known",
          connections: stored.map((item) => ({
            connection_id: item.connectionId,
            provider: item.provider,
            business_id: item.businessId,
            business_name: item.businessName,
            waba_id: item.wabaId,
            waba_name: item.wabaName,
            phone_number_id: item.phoneNumberId,
            display_phone_number: item.displayPhoneNumber,
            verified_name: item.verifiedName,
            requested_scopes: requestedScopes,
            status: "unverified",
            last_verified_at: item.lastVerifiedAt,
          })),
          gaps,
          checked_at: new Date().toISOString(),
        });
        return;
      }
    } catch (storeError) {
      await captureError(storeError, { route: ROUTE, errorCode: "connection_store_unavailable" });
    }
    json(res, 502, { ok: false, error: "whatsapp_enumeration_unavailable", gaps });
    return;
  }

  await logEvent("integration.whatsapp_connections", {
    route: ROUTE,
    lumosId,
    count: connections.length,
    gapCount: gaps.length,
  });
  json(res, 200, {
    ok: true,
    connections,
    gaps,
    checked_at: new Date().toISOString(),
  });
}
