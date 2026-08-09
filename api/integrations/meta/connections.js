/** ADR-021 S2 — Meta bağlantı listesi (salt-okunur; secret asla dönmez).
 *
 * Çoklu yol: vault `credential.list` (S1 adapter'ı) → bağlantı satırları.
 * FALLBACK (GEÇİŞ UYUMLULUĞU — kalıcı mimari DEĞİL): private gateway henüz
 * `credential.list` desteklemiyorsa provider başına tekil metadata okunur ve
 * yanıt `mode: "single_credential_fallback"` ile AÇIKÇA işaretlenir; çoklu
 * bağlantı çalışıyormuş gibi gösterilmez (kurucu sınırı, 2026-08-09).
 * Gateway kaynağı bulunup private taraf tamamlanınca fallback kaldırılabilir.
 *
 * connection_id: fallback ve liste modunda deterministik türetilir
 * (`conn_<provider>_<provider_account_id>`); kalıcı ULID kaydı, bağlantı
 * deposu dilimiyle gelir (ADR-021 §1 kalıcı kimlik şartının deterministik
 * geçiş karşılığı — provider kimliği değişmedikçe id değişmez).
 */
import {
  COOKIE,
  openSession,
  readCookie,
  sessionLumosId,
} from "../../_lib/lumos_session.js";
import { META_PROVIDERS } from "../../_lib/meta_oauth.js";
import {
  listMetaCredentials,
  metaCredentialMetadata,
} from "../../_lib/meta_vault.js";
import { captureError, logEvent } from "../../_lib/observability.js";

const ROUTE = "meta_connections";

function json(res, status, payload) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(payload));
}

function authenticatedLumosId(req) {
  const claims = openSession(readCookie(req, COOKIE));
  return claims?.sid ? sessionLumosId(claims) : "";
}

function connectionId(provider, providerAccountId) {
  return `conn_${provider}_${providerAccountId}`;
}

function statusFor(expiresAt, nowSeconds) {
  if (Number(expiresAt) > 0 && Number(expiresAt) <= nowSeconds) return "expired";
  return "authorized";
}

function connectionRow(provider, providerAccountId, expiresAt, authMode, nowSeconds) {
  return {
    connection_id: connectionId(provider, providerAccountId),
    provider,
    provider_account_id: providerAccountId,
    status: statusFor(expiresAt, nowSeconds),
    expires_at: Number(expiresAt || 0),
    auth_mode: String(authMode || ""),
  };
}

async function multiConnectionRows(lumosId, nowSeconds) {
  const rows = await listMetaCredentials(lumosId);
  return rows
    .filter((row) => META_PROVIDERS.includes(row.provider))
    .map((row) => connectionRow(
      row.provider, row.providerAccountId, row.expiresAt, row.authMode, nowSeconds,
    ));
}

async function fallbackRows(lumosId, nowSeconds) {
  const rows = [];
  let failures = 0;
  for (const provider of META_PROVIDERS) {
    try {
      const metadata = await metaCredentialMetadata(lumosId, provider);
      if (!metadata.configured) continue;
      // Tekil metadata provider_account_id taşımaz; vault_ref opak kalır.
      // Fallback satırı hesap kimliği yerine "current" yer tutucusu kullanır
      // ve mode alanı bu kısıtı açıkça duyurur.
      rows.push(connectionRow(provider, "current", metadata.expiresAt, "", nowSeconds));
    } catch (error) {
      failures += 1;
      await captureError(error, { route: ROUTE, provider, errorCode: "fallback_metadata_failed" });
    }
  }
  // "Servis çöktü" ile "bağlantı yok" karıştırılmaz: hiç satır üretemedik ve
  // en az bir provider sorgusu HATAYLA düştüyse bu boş liste değil, kesintidir.
  if (rows.length === 0 && failures > 0) {
    throw new Error("meta_vault_fallback_unavailable");
  }
  return rows;
}

export default async function handler(req, res) {
  if (req.method !== "GET") {
    json(res, 405, { ok: false, error: "method_not_allowed" });
    return;
  }
  const lumosId = authenticatedLumosId(req);
  if (!lumosId) {
    json(res, 401, { ok: false, error: "unauthorized" });
    return;
  }
  const nowSeconds = Math.floor(Date.now() / 1000);
  try {
    const connections = await multiConnectionRows(lumosId, nowSeconds);
    await logEvent("integration.connections_list", { route: ROUTE, lumosId, mode: "multi", count: connections.length });
    json(res, 200, { ok: true, mode: "multi", connections });
  } catch (error) {
    // GEÇİŞ UYUMLULUĞU: gateway credential.list bilmiyor olabilir → tekil moda
    // düş, ama bunu AÇIKÇA raporla (degraded görünürlüğü kurucu şartı).
    await captureError(error, { route: ROUTE, errorCode: "credential_list_unavailable" });
    try {
      const connections = await fallbackRows(lumosId, nowSeconds);
      await logEvent("integration.connections_list", { route: ROUTE, lumosId, mode: "single_credential_fallback", count: connections.length });
      json(res, 200, {
        ok: true,
        mode: "single_credential_fallback",
        note: "gateway credential.list bekleniyor; provider başına tek bağlantı gösteriliyor",
        connections,
      });
    } catch (fallbackError) {
      await captureError(fallbackError, { route: ROUTE, errorCode: "connections_unavailable" });
      json(res, 503, { ok: false, error: "connections_unavailable" });
    }
  }
}
