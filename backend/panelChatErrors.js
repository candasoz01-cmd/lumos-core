/**
 * Panel /chat hata sınıflandırması ve kullanıcıya gösterilecek mesajlar.
 * Metinler panel.modules.chat.errors.* ile hizalı (TR/EN).
 * @typedef {'network_error'|'timeout'|'unauthorized'|'server_error'|'model_error'|'unknown_error'} PanelChatErrorKind
 */

/** @type {Record<PanelChatErrorKind, string>} */
export const PANEL_CHAT_ERROR_MESSAGES_TR = {
  network_error: "İletim tamamlanamadı. Bağlantıyı kontrol edip tekrar dene.",
  timeout: "Yanıt süresi doldu. Biraz sonra tekrar dene.",
  unauthorized: "Bağlantı doğrulanamadı. Cihaz ayarlarını kontrol edip tekrar dene.",
  server_error: "Sohbet geçici olarak yanıt veremedi. Biraz sonra tekrar dene.",
  model_error: "Yanıt üretilemedi. Biraz sonra tekrar dene.",
  unknown_error: "Beklenmeyen bir sorun oluştu. Biraz sonra tekrar dene.",
};

/** @type {Record<PanelChatErrorKind, string>} */
export const PANEL_CHAT_ERROR_MESSAGES_EN = {
  network_error: "Delivery failed. Check your connection and try again.",
  timeout: "Response timed out. Try again in a moment.",
  unauthorized: "Connection could not be verified. Check device settings and try again.",
  server_error: "Chat is temporarily unavailable. Try again in a moment.",
  model_error: "Could not produce a reply. Try again in a moment.",
  unknown_error: "Something unexpected happened. Try again in a moment.",
};

/**
 * @param {string} [locale]
 * @returns {'tr'|'en'}
 */
export function normalizePanelChatErrorLocale(locale) {
  return String(locale || "").trim().toLowerCase() === "en" ? "en" : "tr";
}

/**
 * @param {PanelChatErrorKind} kind
 * @param {string} [locale]
 * @returns {string}
 */
export function userMessageForPanelChatError(kind, locale = "tr") {
  const loc = normalizePanelChatErrorLocale(locale);
  const catalog = loc === "en" ? PANEL_CHAT_ERROR_MESSAGES_EN : PANEL_CHAT_ERROR_MESSAGES_TR;
  return catalog[kind] ?? catalog.unknown_error;
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
 * @param {{ detail?: string; locale?: string }} [opts]
 * @returns {{ errorKind: PanelChatErrorKind; error: string; reply: string }}
 */
export function panelChatErrorPayload(kind, opts = {}) {
  const base = userMessageForPanelChatError(kind, opts.locale);
  const detail = opts.detail && String(opts.detail).trim();
  const error = detail ? `${base} (${detail})` : base;
  return { errorKind: kind, error, reply: base };
}
