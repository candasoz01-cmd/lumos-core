/**
 * Panel /chat hata sınıflandırması ve kullanıcıya gösterilecek Türkçe mesajlar.
 * @typedef {'network_error'|'timeout'|'unauthorized'|'server_error'|'model_error'|'unknown_error'} PanelChatErrorKind
 */

/** @type {Record<PanelChatErrorKind, string>} */
export const PANEL_CHAT_ERROR_MESSAGES_TR = {
  network_error:
    "Sunucuya ulaşılamadı. İnternet bağlantınızı ve sohbet adresini kontrol edip tekrar deneyin.",
  timeout: "Yanıt süresi doldu. Biraz sonra tekrar deneyin.",
  unauthorized:
    "Yetkilendirme hatası. Oturum veya API anahtar ayarlarınızı kontrol edin.",
  server_error:
    "Sohbet sunucusu geçici bir sorun bildirdi. Biraz sonra tekrar deneyin.",
  model_error:
    "Yapay zekâ modeli yanıt üretemedi. Biraz sonra tekrar deneyin.",
  unknown_error: "Beklenmeyen bir hata oluştu. Biraz sonra tekrar deneyin.",
};

/**
 * @param {PanelChatErrorKind} kind
 * @returns {string}
 */
export function userMessageForPanelChatError(kind) {
  return PANEL_CHAT_ERROR_MESSAGES_TR[kind] ?? PANEL_CHAT_ERROR_MESSAGES_TR.unknown_error;
}

/**
 * @param {{
 *   httpStatus?: number|null;
 *   errName?: string;
 *   errMessage?: string;
 *   upstreamText?: string;
 * }} ctx
 * @returns {PanelChatErrorKind}
 */
export function classifyPanelChatError(ctx = {}) {
  const status =
    typeof ctx.httpStatus === "number" && Number.isFinite(ctx.httpStatus)
      ? ctx.httpStatus
      : null;
  const name = String(ctx.errName ?? "").toLowerCase();
  const msg = String(ctx.errMessage ?? ctx.upstreamText ?? "").toLowerCase();

  if (status === 401 || status === 403) return "unauthorized";
  if (status != null && status >= 500) return "server_error";
  if (status === 503 && /openai_api_key|api.?key/i.test(msg)) return "server_error";
  if (status === 429) return "model_error";

  if (
    /timeout|timed\s*out|etimedout|aborterror|deadline/i.test(name)
    || /timeout|timed\s*out|etimedout|deadline/i.test(msg)
  ) {
    return "timeout";
  }

  if (
    /failed to fetch|networkerror|network\s*error|econnrefused|enotfound|fetch failed|dns/i.test(
      name + " " + msg,
    )
    || (status == null && /ulaşılamadı|network|cors/i.test(msg))
  ) {
    return "network_error";
  }

  if (/unauthorized|forbidden|401|403|invalid.*token|api.?key/i.test(msg)) {
    return "unauthorized";
  }

  if (
    /openai|chat\s*llm\s*error|model|responses\.create|rate.?limit|content.?policy/i.test(
      msg,
    )
  ) {
    return "model_error";
  }

  if (/internal server|500|502|503|504|sunucu/i.test(msg)) {
    return "server_error";
  }

  return "unknown_error";
}

/**
 * @param {PanelChatErrorKind} kind
 * @param {{ detail?: string }} [opts]
 * @returns {{ errorKind: PanelChatErrorKind; error: string; reply: string }}
 */
export function panelChatErrorPayload(kind, opts = {}) {
  const base = userMessageForPanelChatError(kind);
  const detail = opts.detail && String(opts.detail).trim();
  const error = detail ? `${base} (${detail})` : base;
  return { errorKind: kind, error, reply: base };
}
