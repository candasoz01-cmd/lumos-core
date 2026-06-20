"""Panel /chat hata sınıflandırması ve kullanıcıya gösterilecek mesajlar."""

from __future__ import annotations

import re
from typing import Literal

PanelChatErrorKind = Literal[
    "network_error",
    "timeout",
    "unauthorized",
    "server_error",
    "model_error",
    "unknown_error",
]

PanelChatErrorLocale = Literal["tr", "en"]

PANEL_CHAT_ERROR_MESSAGES_TR: dict[PanelChatErrorKind, str] = {
    "network_error": "İletim tamamlanamadı. Bağlantıyı kontrol edip tekrar dene.",
    "timeout": "Yanıt süresi doldu. Biraz sonra tekrar dene.",
    "unauthorized": "Bağlantı doğrulanamadı. Cihaz ayarlarını kontrol edip tekrar dene.",
    "server_error": "Sohbet geçici olarak yanıt veremedi. Biraz sonra tekrar dene.",
    "model_error": "Yanıt üretilemedi. Biraz sonra tekrar dene.",
    "unknown_error": "Beklenmeyen bir sorun oluştu. Biraz sonra tekrar dene.",
}

PANEL_CHAT_ERROR_MESSAGES_EN: dict[PanelChatErrorKind, str] = {
    "network_error": "Delivery failed. Check your connection and try again.",
    "timeout": "Response timed out. Try again in a moment.",
    "unauthorized": "Connection could not be verified. Check device settings and try again.",
    "server_error": "Chat is temporarily unavailable. Try again in a moment.",
    "model_error": "Could not produce a reply. Try again in a moment.",
    "unknown_error": "Something unexpected happened. Try again in a moment.",
}


def normalize_panel_chat_error_locale(locale: str = "") -> PanelChatErrorLocale:
    return "en" if str(locale or "").strip().lower() == "en" else "tr"


def user_message_for_panel_chat_error(
    kind: PanelChatErrorKind,
    locale: str = "tr",
) -> str:
    loc = normalize_panel_chat_error_locale(locale)
    catalog = PANEL_CHAT_ERROR_MESSAGES_EN if loc == "en" else PANEL_CHAT_ERROR_MESSAGES_TR
    return catalog.get(kind, catalog["unknown_error"])


def classify_panel_chat_error(
    *,
    http_status: int | None = None,
    err_name: str = "",
    err_message: str = "",
    upstream_text: str = "",
) -> PanelChatErrorKind:
    name = (err_name or "").lower()
    msg = (err_message or upstream_text or "").lower()

    if http_status in (401, 403):
        return "unauthorized"
    if http_status is not None and http_status >= 500:
        return "server_error"
    if http_status == 503 and re.search(r"openai_api_key|api.?key", msg, re.I):
        return "server_error"
    if http_status == 429:
        return "model_error"

    blob = f"{name} {msg}"
    if re.search(r"timeout|timed\s*out|etimedout|aborterror|deadline", blob, re.I):
        return "timeout"
    if re.search(
        r"failed to fetch|networkerror|network\s*error|econnrefused|enotfound|fetch failed|dns",
        blob,
        re.I,
    ) or (http_status is None and re.search(r"ulaşılamadı|network|cors", msg, re.I)):
        return "network_error"
    if re.search(r"unauthorized|forbidden|401|403|invalid.*token|api.?key", msg, re.I):
        return "unauthorized"
    if re.search(
        r"openai|chat\s*llm\s*error|model|responses\.create|rate.?limit|content.?policy",
        msg,
        re.I,
    ):
        return "model_error"
    if re.search(r"internal server|500|502|503|504|sunucu", msg, re.I):
        return "server_error"
    return "unknown_error"


def panel_chat_error_payload(
    kind: PanelChatErrorKind,
    *,
    detail: str = "",
    locale: str = "tr",
) -> dict[str, str]:
    base = user_message_for_panel_chat_error(kind, locale)
    detail = (detail or "").strip()
    error = f"{base} ({detail})" if detail else base
    return {"errorKind": kind, "error": error, "reply": base}
