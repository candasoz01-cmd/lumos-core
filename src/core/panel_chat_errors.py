"""Panel /chat hata sınıflandırması ve kullanıcıya gösterilecek Türkçe mesajlar."""

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

PANEL_CHAT_ERROR_MESSAGES_TR: dict[PanelChatErrorKind, str] = {
    "network_error": (
        "Sunucuya ulaşılamadı. İnternet bağlantınızı ve sohbet adresini kontrol edip tekrar deneyin."
    ),
    "timeout": "Yanıt süresi doldu. Biraz sonra tekrar deneyin.",
    "unauthorized": "Yetkilendirme hatası. Oturum veya API anahtar ayarlarınızı kontrol edin.",
    "server_error": "Sohbet sunucusu geçici bir sorun bildirdi. Biraz sonra tekrar deneyin.",
    "model_error": "Yapay zekâ modeli yanıt üretemedi. Biraz sonra tekrar deneyin.",
    "unknown_error": "Beklenmeyen bir hata oluştu. Biraz sonra tekrar deneyin.",
}


def user_message_for_panel_chat_error(kind: PanelChatErrorKind) -> str:
    return PANEL_CHAT_ERROR_MESSAGES_TR.get(kind, PANEL_CHAT_ERROR_MESSAGES_TR["unknown_error"])


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
) -> dict[str, str]:
    base = user_message_for_panel_chat_error(kind)
    detail = (detail or "").strip()
    error = f"{base} ({detail})" if detail else base
    return {"errorKind": kind, "error": error, "reply": base}
