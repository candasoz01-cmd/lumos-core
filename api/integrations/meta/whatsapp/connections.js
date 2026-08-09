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
  listMetaCredentials,
  resolveMetaCredentialByRef,
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
        });
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

  // "Servis çöktü" ≠ "numara yok": hiç satır yok VE her credential hatayla
  // düştüyse kesinti raporla.
  if (connections.length === 0 && failures === credentials.length) {
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
