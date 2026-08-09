/** ADR-021 Pages dilimi — GET /api/integrations/meta/pages/connections
 *
 * Pages credential'ları üzerinden yönetilen Sayfa enumerasyonu; her Sayfa
 * kalıcı connection_id'li ayrı satır. Salt-okunur, secret dönmez, vault_ref
 * gövdeye sızmaz; satır credential'ına `credential_account_id` ile bağlanır,
 * sunucu tarafında çözümleme vault_ref REFERANSI ile yapılır (kopya yok).
 *
 * Kurucu sınırı: boş/eksik enumeration satır uydurmaz (`gaps` görünür);
 * tüm credential'lar düşerse depodaki gerçek geçmiş kayıtlar `unverified`
 * olarak döner, depo da boşsa 502.
 */
import {
  COOKIE,
  openSession,
  readCookie,
  sessionLumosId,
} from "../../../_lib/lumos_session.js";
import { enumeratePages } from "../../../_lib/meta_connections.js";
import { metaProviderConfig } from "../../../_lib/meta_oauth.js";
import {
  listMetaConnections,
  listMetaCredentials,
  resolveMetaCredentialByRef,
  upsertMetaConnection,
} from "../../../_lib/meta_vault.js";
import { captureError, logEvent } from "../../../_lib/observability.js";

const ROUTE = "meta_pages_connections";

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
    credentials = await listMetaCredentials(lumosId, "pages");
  } catch (error) {
    await captureError(error, { route: ROUTE, errorCode: "credential_list_failed" });
    json(res, 503, { ok: false, error: "credential_list_unavailable" });
    return;
  }
  if (credentials.length === 0) {
    json(res, 200, {
      ok: true,
      connections: [],
      gaps: [{ reason: "no_pages_credential" }],
      checked_at: new Date().toISOString(),
    });
    return;
  }

  const requestedScopes = metaProviderConfig("pages")?.scopes || [];
  const nowSeconds = Math.floor(Date.now() / 1000);
  const connections = [];
  const gaps = [];
  let failures = 0;
  for (const row of credentials) {
    try {
      const credential = await resolveMetaCredentialByRef(lumosId, row.vaultRef);
      const result = await enumeratePages(lumosId, credential);
      for (const page of result.pages) {
        connections.push({
          ...page,
          credential_account_id: row.providerAccountId,
          requested_scopes: requestedScopes,
          status: "verified",
          last_verified_at: nowSeconds,
        });
        try {
          await upsertMetaConnection(lumosId, {
            connectionId: page.connection_id,
            provider: "pages",
            credentialRef: row.vaultRef,
            pageId: page.page_id,
            pageName: page.page_name,
            lastVerifiedAt: nowSeconds,
          });
        } catch (persistError) {
          await captureError(persistError, { route: ROUTE, errorCode: "connection_persist_failed" });
          gaps.push({ reason: "persist_failed", connection_id: page.connection_id });
        }
      }
      for (const gap of result.gaps) {
        gaps.push({ ...gap, credential_account_id: row.providerAccountId });
      }
    } catch (error) {
      failures += 1;
      const errorCode = String(error?.message || "pages_enumeration_failed");
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
      const stored = await listMetaConnections(lumosId, "pages");
      if (stored.length > 0) {
        json(res, 200, {
          ok: true,
          mode: "stored_last_known",
          connections: stored.map((item) => ({
            connection_id: item.connectionId,
            provider: item.provider,
            page_id: item.pageId,
            page_name: item.pageName,
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
    json(res, 502, { ok: false, error: "pages_enumeration_unavailable", gaps });
    return;
  }

  await logEvent("integration.pages_connections", {
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
