"""Policy engine: should_auto_send(message_context) -> Decision."""

import re
from dataclasses import dataclass
from enum import Enum


class Decision(str, Enum):
    """Auto-send kararı."""

    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


@dataclass
class MessageContext:
    """Mesaj ve bağlam (ilk sürümde sadece text)."""

    text: str
    platform: str = ""


# Kurallar (ilk sürüm)
_SORU_PATTERN = re.compile(r"\?|mı\s*$|mi\s*$|mu\s*$|mü\s*$|nasıl|ne zaman|neden|kim", re.I)
_PARA_PLAN_TARIH = re.compile(r"\b(para|plan|tarih|fiyat|ödeme|iban|kart)\b", re.I)
_HASSAS = re.compile(
    r"\b(şifre|password|parola|gizli|secret|token|api[_-]?key)\b",
    re.I,
)
_SELAM_TESEKKUR = re.compile(
    r"^(selam|merhaba|teşekkür|thanks|teşekkürler|sağol|eyvallah)\b",
    re.I,
)


def should_auto_send(message_context: MessageContext) -> Decision:
    """İlk sürüm kuralları: soru → REQUIRE_APPROVAL; para/plan/tarih → REQUIRE_APPROVAL; hassas → DENY; selam/teşekkür → ALLOW."""
    text = (message_context.text or "").strip()
    if not text:
        return Decision.DENY
    if _HASSAS.search(text):
        return Decision.DENY
    if _SORU_PATTERN.search(text):
        return Decision.REQUIRE_APPROVAL
    if _PARA_PLAN_TARIH.search(text):
        return Decision.REQUIRE_APPROVAL
    if _SELAM_TESEKKUR.search(text):
        return Decision.ALLOW
    return Decision.REQUIRE_APPROVAL  # default: onay gerek (autopilot kapalı varsayım)
