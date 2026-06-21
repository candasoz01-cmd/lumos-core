"""Structured relay / bridge client errors with TR + EN messages."""
from __future__ import annotations

from typing import Any

_MESSAGES: dict[str, tuple[str, str]] = {
    "bridge_unreachable": (
        "Köprüye ulaşılamıyor — PC bridge çalışıyor mu?",
        "Bridge unreachable — is the PC bridge running?",
    ),
    "relay_unreachable": (
        "Relay sunucusuna ulaşılamıyor",
        "LAN relay server unreachable",
    ),
    "connection_failed": (
        "Bağlantı kurulamadı",
        "Connection failed",
    ),
    "request_failed": (
        "İstek başarısız",
        "Request failed",
    ),
    "invalid_relay_token": (
        "Geçersiz relay token — yeniden eşleştirin / Re-pair",
        "Invalid relay token — re-pair required",
    ),
    "relay_token_required": (
        "Relay token gerekli — önce POST /relay/pair",
        "Relay token required — pair first via POST /relay/pair",
    ),
    "relay_token_expired": (
        "Relay token süresi doldu — yeniden eşleştirin",
        "Relay token expired — re-pair required",
    ),
    "invalid_pairing_code": (
        "Geçersiz eşleştirme kodu",
        "Invalid pairing code",
    ),
    "pairing_expired": (
        "Eşleştirme kodunun süresi doldu",
        "Pairing code expired",
    ),
    "invalid_response": (
        "Geçersiz köprü yanıtı",
        "Invalid bridge response",
    ),
}


def enrich_error_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Add ``message_tr`` / ``message_en`` when ``error`` code is known."""
    code = str(payload.get("error") or "").strip()
    if not code:
        return payload
    pair = _MESSAGES.get(code)
    if pair is None:
        return payload
    out = dict(payload)
    out.setdefault("message_tr", pair[0])
    out.setdefault("message_en", pair[1])
    return out
