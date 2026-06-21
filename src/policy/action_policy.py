"""
Minimal task / surface policy (hardcoded rules).

check_policy(action, context) — context: online, koruma_active (kilit), consent.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from core.logfmt import logfmt

# Actions used by CLI and (mirror) panel naming
CREATE_TASK = "create_task"
COMPLETE_TASK = "complete_task"
DELETE_TASK = "delete_task"
CANCEL_TASK = "cancel_task"
ACCESS_IDENTITY = "access_identity"
ACCESS_KEYSTORE = "access_keystore"

# Panel delete-permanent yolu — confirmation_policy.DELETE_PERMANENT_ACTION ile aynı token.
DELETE_PERMANENT = "delete_permanent"


@dataclass(frozen=True)
class PolicyContext:
    """Runtime snapshot for one check."""

    online: bool
    koruma_active: bool
    consent: bool
    general_approval: bool = False


@dataclass(frozen=True)
class PolicyResult:
    allowed: bool
    reason: str = ""


def is_never_auto_policy_action(action: str) -> bool:
    """Policy yüzey action SECURITY_NEVER_AUTO tablosunda mı? (Option B tek kaynak)."""
    from task_engine.profiles import resolve_never_auto_member_for_policy_action

    return resolve_never_auto_member_for_policy_action(action) is not None


def never_auto_member_for_policy_action(action: str) -> str | None:
    """Policy action → canonical küme üyesi; yoksa None."""
    from task_engine.profiles import resolve_never_auto_member_for_policy_action

    return resolve_never_auto_member_for_policy_action(action)


def check_policy(action: str, context: PolicyContext | Mapping[str, Any]) -> PolicyResult:
    """
    Hardcoded rules:
    - Offline: create / complete / delete / cancel → deny
    - Koruma (kilit) active: delete_task → deny
    - No consent: identity / keystore access → deny
    """
    if isinstance(context, PolicyContext):
        ctx = context
    else:
        ctx = PolicyContext(
            online=bool(context.get("online")),
            koruma_active=bool(context.get("koruma_active")),
            consent=bool(context.get("consent")),
            general_approval=bool(context.get("general_approval")),
        )

    if not ctx.online:
        if action in (CREATE_TASK, COMPLETE_TASK, DELETE_TASK, CANCEL_TASK):
            return PolicyResult(False, "offline_mode")

    if ctx.koruma_active and action == DELETE_TASK:
        return PolicyResult(False, "koruma_aktif_delete")

    if not ctx.consent and action in (ACCESS_IDENTITY, ACCESS_KEYSTORE):
        return PolicyResult(False, "consent_required")

    return PolicyResult(True, "")


def _policy_reason_display(reason: str) -> str:
    if reason == "offline_mode":
        return "çevrimdışı"
    if reason == "koruma_aktif_delete":
        return "koruma aktif"
    if reason == "consent_required":
        return "izin yok"
    return reason or "bilinmiyor"


def policy_user_message(action: str, reason: str) -> str:
    """Tek format: [POLICY_BLOCKED] <action> → <reason> (Türkçe etiket)."""
    disp = _policy_reason_display(reason)
    return f"[POLICY_BLOCKED] {action} → {disp}"


def log_policy_blocked(base_dir: str, action: str, reason: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    line = logfmt("policy_blocked", action=action, reason=reason, ts=ts)
    p = Path(base_dir) / "logs" / "log.txt"
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
    try:
        from core.evidence_continuity import mirror_policy_blocked_to_evidence_journal

        mirror_policy_blocked_to_evidence_journal(base_dir, action, reason)
    except Exception:
        pass
