/**
 * Meta "Deauthorize callback" (KARAR-2, candasoz01-cmd/lumos-core#903).
 *
 * Kullanıcı uygulamanın erişimini Meta tarafında kaldırdığında çağrılır.
 * `signed_request` doğrulanır; o kullanıcıya ait belirteçler ve bağlantı
 * kayıtları, veri silme geri çağrısıyla aynı yoldan silinir. Geçit silmeyi
 * tamamlamazsa 503 döner; Meta isteği yeniden deneyebilir.
 */
import {
  newDeletionConfirmationCode,
  signedRequestFromBody,
  verifyMetaSignedRequest,
} from "../_lib/meta_signed_request.js";
import { purgeMetaAccount } from "../_lib/meta_vault.js";
import { captureError, captureSecurityEvent, logEvent } from "../_lib/observability.js";

const ROUTE = "meta_deauthorize";

function json(res, status, payload) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(payload));
}

export default async function handler(req, res) {
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
  try {
    const result = await purgeMetaAccount({
      providers: verified.providers,
      providerAccountId: verified.userId,
      confirmationCode: newDeletionConfirmationCode(),
    });
    json(res, 200, { ok: true, status: result.status });
    await logEvent("meta.deauthorize", {
      route: ROUTE,
      status: result.status,
      provider: verified.providers.join(","),
    });
  } catch (error) {
    const errorCode = String(error?.message || "meta_deauthorize_failed");
    await captureError(new Error(errorCode), { route: ROUTE, errorCode });
    json(res, 503, { ok: false, error: "meta_deauthorize_unavailable" });
  }
}
