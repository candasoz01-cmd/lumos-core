from __future__ import annotations

from dataclasses import dataclass

# OD-031 dar v1 + OD-041 CA1 — yalnızca read + notify; draft_prep kapalı (A).
MAIL_GRANT_READ = "read"
MAIL_GRANT_NOTIFY = "notify"
MAIL_DAR_V1_GRANTS = frozenset({MAIL_GRANT_READ, MAIL_GRANT_NOTIFY})

# Dar v1 dışı — connector yüzeyinde desteklenmez.
MAIL_GRANT_SEND_REPLY = "send_reply"


@dataclass(frozen=True)
class MailGrantSession:
    """Oturum bazlı mail izin paketi (CA1 — düşük risk okuma/bildirim)."""

    grants: frozenset[str]
    account_id: str
    session_id: str


def _normalize_grants(grants: object) -> frozenset[str]:
    if not isinstance(grants, (list, tuple, set, frozenset)):
        return frozenset()
    out: set[str] = set()
    for item in grants:
        if isinstance(item, str) and item.strip():
            out.add(item.strip().lower())
    return frozenset(out)


def validate_mail_grants(session: MailGrantSession, *, require_notify: bool = False) -> str | None:
    """Grant doğrulama; hata kodu veya None (OK)."""
    grants = _normalize_grants(session.grants)
    unknown = grants - MAIL_DAR_V1_GRANTS
    if unknown:
        return "unsupported_mail_grant"
    if MAIL_GRANT_SEND_REPLY in grants:
        return "send_reply_not_in_dar_v1"
    if not grants or MAIL_GRANT_READ not in grants:
        return "read_grant_required"
    if require_notify and MAIL_GRANT_NOTIFY not in grants:
        return "notify_grant_required"
    if not session.account_id.strip():
        return "account_id_required"
    if not session.session_id.strip():
        return "session_id_required"
    return None


def session_from_payload(payload: dict) -> MailGrantSession:
    raw = payload.get("grants", [])
    account_id = payload.get("account_id", "")
    session_id = payload.get("session_id", "")
    return MailGrantSession(
        grants=_normalize_grants(raw),
        account_id=account_id if isinstance(account_id, str) else "",
        session_id=session_id if isinstance(session_id, str) else "",
    )
