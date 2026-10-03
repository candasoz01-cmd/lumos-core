/**
 * Meta "User data deletion" geri çağrısı (KARAR-2, candasoz01-cmd/lumos-core#903).
 *
 * POST (Meta): `signed_request` doğrulanır; eşleşen kullanıcıya ait Meta
 * belirteçleri, bağlantı kayıtları ve bu bağlantıların WhatsApp zarf ve
 * gönderim kayıtları kimlik bilgisi geçidinde silinir. Yanıt, Meta'nın
 * beklediği { url, confirmation_code } biçimindedir. Geçit silmeyi
 * tamamlamazsa 503 döner; silinmiş gibi yanıt verilmez.
 *
 * GET ?code=: silme durumunu döner (kullanıcı kimliği yok, yalnız sayılar).
 */
import {
  isDeletionConfirmationCode,
  newDeletionConfirmationCode,
  signedRequestFromBody,
  verifyMetaSignedRequest,
} from "../_lib/meta_signed_request.js";
import { metaDeletionStatus, purgeMetaAccount } from "../_lib/meta_vault.js";
import { captureError, captureSecurityEvent, logEvent } from "../_lib/observability.js";

const ROUTE = "meta_data_deletion";

function json(res, status, payload) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(payload));
}

export function deletionStatusUrl(code) {
  return `https://welockai.com/legal/meta-deletion?code=${encodeURIComponent(code)}`;
}

async function handleStatus(req, res) {
  const url = new URL(req.url || "/", "https://welockai.com");
  const code = String(url.searchParams.get("code") || "").trim();
  if (!isDeletionConfirmationCode(code)) {
    json(res, 400, { ok: false, error: "confirmation_code_invalid" });
    return;
  }
  try {
    const status = await metaDeletionStatus(code);
    json(res, 200, {
      ok: true,
      confirmation_code: code,
      status: status.status,
      requested_at: status.requestedAt,
      completed_at: status.completedAt,
      counts: status.counts,
    });
  } catch (error) {
    const errorCode = String(error?.message || "meta_deletion_status_unavailable");
    // Geçit bulunamayan kodu ve arızayı aynı hata ile döner; ikisinde de
    // durum bilinmiyor demektir.
    json(res, 503, { ok: false, error: "deletion_status_unavailable" });
    await captureError(new Error(errorCode), { route: ROUTE, errorCode });
  }
}

export default async function handler(req, res) {
  if (req.method === "GET") {
    await handleStatus(req, res);
    return;
  }
  if (req.method !== "POST") {
    json(res, 405, { ok: false, error: "method_not_allowed" });
    return;
  }
  const verified = verifyMetaSignedRequest(signedRequestFromBody(req.body));
  if (!verified) {
    await captureSecurityEvent("meta_signed_request_invalid", { route: ROUTE });
    json(res, 400, { ok: false, error: "signed_request_invalid" });
    return;
  }
  const code = newDeletionConfirmationCode();
  try {
    const result = await purgeMetaAccount({
      providers: verified.providers,
      providerAccountId: verified.userId,
      confirmationCode: code,
    });
    json(res, 200, { url: deletionStatusUrl(code), confirmation_code: code });
    await logEvent("meta.data_deletion", {
      route: ROUTE,
      status: result.status,
      provider: verified.providers.join(","),
    });
  } catch (error) {
    const errorCode = String(error?.message || "meta_data_deletion_failed");
    await captureError(new Error(errorCode), { route: ROUTE, errorCode });
    json(res, 503, { ok: false, error: "meta_data_deletion_unavailable" });
  }
}
