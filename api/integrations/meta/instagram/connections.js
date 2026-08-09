/** ADR-021 Instagram dilimi — GET /api/integrations/meta/instagram/connections
 *
 * Instagram credential'ları üzerinden hesap enumerasyonu (Instagram Login'de
 * credential başına bir profesyonel hesap; iki auth modu da meta_sync ile
 * çözülür). Her hesap kalıcı connection_id'li ayrı satır; credential'a
 * sunucu tarafında vault_ref REFERANSI ile bağlanır (kopya yok), gövdeye
 * secret/vault_ref sızmaz.
 *
 * Kurucu sınırı: boş/eksik enumeration satır uydurmaz (`gaps` görünür);
 * tüm credential'lar düşerse depodaki gerçek geçmiş kayıtlar `unverified`
 * döner, depo da boşsa 502.
 */
import {
  COOKIE,
  openSession,
  readCookie,
  sessionLumosId,
} from "../../../_lib/lumos_session.js";
import { instagramConnectionId } from "../../../_lib/meta_connections.js";
import { metaProviderConfig } from "../../../_lib/meta_oauth.js";
import { syncMetaReadOnly } from "../../../_lib/meta_sync.js";
import {
  listMetaConnections,
  listMetaCredentials,
  resolveMetaCredentialByRef,
  upsertMetaConnection,
} from "../../../_lib/meta_vault.js";
import { captureError, logEvent } from "../../../_lib/observability.js";

const ROUTE = "meta_instagram_connections";

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
    credentials = await listMetaCredentials(lumosId, "instagram");
  } catch (error) {
    await captureError(error, { route: ROUTE, errorCode: "credential_list_failed" });
    json(res, 503, { ok: false, error: "credential_list_unavailable" });
    return;
  }
  if (credentials.length === 0) {
    json(res, 200, {
      ok: true,
      connections: [],
      gaps: [{ reason: "no_instagram_credential" }],
      checked_at: new Date().toISOString(),
    });
    return;
  }

  const requestedScopes = metaProviderConfig("instagram")?.scopes || [];
  const nowSeconds = Math.floor(Date.now() / 1000);
  const connections = [];
  const gaps = [];
  let failures = 0;
  for (const row of credentials) {
    try {
      const credential = await resolveMetaCredentialByRef(lumosId, row.vaultRef);
      const snapshot = await syncMetaReadOnly("instagram", credential);
      const accounts = Array.isArray(snapshot?.accounts) ? snapshot.accounts : [];
      if (accounts.length === 0) {
        gaps.push({ reason: "accounts_empty", credential_account_id: row.providerAccountId });
        continue;
      }
      for (const account of accounts) {
        const connectionId = instagramConnectionId(lumosId, account.id);
        connections.push({
          connection_id: connectionId,
          provider: "instagram",
          ig_account_id: account.id,
          username: account.username || "",
          account_type: account.account_type || "",
          credential_account_id: row.providerAccountId,
          requested_scopes: requestedScopes,
          status: "verified",
          last_verified_at: nowSeconds,
        });
        try {
          await upsertMetaConnection(lumosId, {
            connectionId,
            provider: "instagram",
            credentialRef: row.vaultRef,
            // Gateway kaydında kullanıcı adı generic verified_name alanında
            // taşınır; ig hesap kimliği page_id gibi ayrı alan açmadan
            // provider+connection_id ile zaten tekilleşir.
            verifiedName: account.username || "",
            lastVerifiedAt: nowSeconds,
          });
        } catch (persistError) {
          await captureError(persistError, { route: ROUTE, errorCode: "connection_persist_failed" });
          gaps.push({ reason: "persist_failed", connection_id: connectionId });
        }
      }
    } catch (error) {
      failures += 1;
      const errorCode = String(error?.message || "instagram_enumeration_failed");
      await captureError(new Error(errorCode), { route: ROUTE, errorCode });
      gaps.push({
        reason: "enumeration_failed",
        error: errorCode,
        credential_account_id: row.providerAccountId,
      });
    }
  }

  if (connections.length === 0 && failures === credentials.length) {
    try {
      const stored = await listMetaConnections(lumosId, "instagram");
      if (stored.length > 0) {
        json(res, 200, {
          ok: true,
          mode: "stored_last_known",
          connections: stored.map((item) => ({
            connection_id: item.connectionId,
            provider: item.provider,
            username: item.verifiedName,
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
    json(res, 502, { ok: false, error: "instagram_enumeration_unavailable", gaps });
    return;
  }

  await logEvent("integration.instagram_connections", {
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
