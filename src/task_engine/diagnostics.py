"""
Task validation diagnostics: exact blocking reasons when a task or step cannot run.

Reasons: missing_consent, lock_active, offline_mode, unsupported_action, policy_restriction.
Used in görev özeti, görev durumu, and execution feedback; does not change execution logic.
"""
from __future__ import annotations

from typing import Any

from task_engine.profiles import (
    DECISION_LAYER_NEVER,
    get_decision_layer,
    requires_explicit_approval,
)

# Canonical block reason codes (for display and logs)
BLOCK_MISSING_CONSENT = "missing_consent"
BLOCK_LOCK_ACTIVE = "lock_active"
BLOCK_OFFLINE_MODE = "offline_mode"
BLOCK_UNSUPPORTED_ACTION = "unsupported_action"
BLOCK_POLICY_RESTRICTION = "policy_restriction"

# Short labels for "Engel: ..." line
BLOCK_LABELS = {
    BLOCK_MISSING_CONSENT: "Consent yok",
    BLOCK_LOCK_ACTIVE: "Kilit aktif",
    BLOCK_OFFLINE_MODE: "Çevrimdışı mod",
    BLOCK_UNSUPPORTED_ACTION: "Desteklenmeyen adım",
    BLOCK_POLICY_RESTRICTION: "Yetki kısıtı",
}


def get_step_block_reason(
    profile: str, step_type: str, general_approval: bool
) -> tuple[str, str] | None:
    """
    When a step is not allowed at runtime, return (reason_code, user_message) or None if allowed.
    Caller uses this to set step.error, task.error_summary, and task.block_reason.
    """
    if get_decision_layer(step_type) == DECISION_LAYER_NEVER:
        return (
            BLOCK_UNSUPPORTED_ACTION,
            "Desteklenmeyen adım türü (bu adım güvenlik politikası gereği çalıştırılamaz).",
        )
    # Step type is allowed in some profile/approval combo; current (profile, general_approval) blocks it
    if requires_explicit_approval(profile, step_type, general_approval):
        return (
            BLOCK_POLICY_RESTRICTION,
            f"Yetki kısıtı — genel onay kapalı. Bu adım türü için «genel onay aç» gerekir.",
        )
    # Profil never allows this step type (e.g. rapor + safe_local)
    return (
        BLOCK_POLICY_RESTRICTION,
        f"Yetki kısıtı — mevcut profil bu adım türüne izin vermiyor.",
    )


def format_block_for_display(reason_code: str, detail_message: str | None = None) -> str:
    """Single line for görev durumu / görev özeti: Engel: <label> [— detail]."""
    label = BLOCK_LABELS.get(reason_code, reason_code)
    if detail_message and detail_message.strip():
        return f"Engel: {label} — {detail_message.strip()}"
    return f"Engel: {label}"


def format_task_block_line(task: Any) -> str | None:
    """
    If task has a blocking reason (policy/consent/unsupported/etc.), return one line for display; else None.
    Use in görev durumu and görev özeti. Execution errors (no block_reason) stay as "Hata: ...".
    """
    reason = getattr(task, "block_reason", "") or ""
    err = getattr(task, "error_summary", "") or ""
    if not reason:
        return None
    return format_block_for_display(reason, err if err and err != reason else None)
