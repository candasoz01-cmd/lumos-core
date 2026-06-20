"""Minimal next-step planner: when an action is blocked, suggest a concrete next step.

Used by live_brain and callers to return: what blocked, why, and what to do next.
No tools or filesystem; intent routing and guidance only.
"""
from __future__ import annotations

from typing import Any

# Supported block reasons (caller passes one of these)
REASON_LOCKED = "locked"
REASON_CONSENT_MISSING = "consent_missing"
REASON_TOOL_UNAVAILABLE = "tool_unavailable"
REASON_CLARIFICATION_NEEDED = "clarification_needed"


def suggest_next_step(
    intent: str | None,
    state: Any,
    reason: str,
    missing_param: str | None = None,
) -> dict[str, Any]:
    """
    Return a small dict with blocked, reason, next_step, and message.

    reason must be one of: locked, consent_missing, tool_unavailable, clarification_needed.
    """
    blocked = True
    next_step = ""
    message = ""

    if reason == REASON_LOCKED:
        next_step = "kilit aç"
        message = "Bu işlem şu anda kilit yüzünden yapılamıyor. Sonraki adım: kilit aç"
    elif reason == REASON_CONSENT_MISSING:
        next_step = "onaylıyorum"
        message = "Bu işlem genel onay gerektiriyor. Sonraki adım: onaylıyorum"
    elif reason == REASON_TOOL_UNAVAILABLE:
        next_step = "Bu özelliği eklemek ya da terminal komutu kullanmak"
        message = "İsteği anladım ama bu özellik şu an mevcut değil. Sonraki adım: bu özelliği eklemek ya da terminal komutu kullanmak."
    elif reason == REASON_CLARIFICATION_NEEDED:
        if missing_param == "folder":
            next_step = "klasör adını yaz"
            message = "Hangi klasör? Sonraki adım: klasör adını yaz"
        else:
            next_step = "eksik parametreyi yaz"
            message = "Eksik bilgi var. Sonraki adım: eksik parametreyi yaz"
    else:
        next_step = "durumu kontrol et"
        message = "İşlem şu an yapılamadı. Sonraki adım: durumu kontrol et"

    return {
        "blocked": blocked,
        "reason": reason,
        "next_step": next_step,
        "message": message,
    }
