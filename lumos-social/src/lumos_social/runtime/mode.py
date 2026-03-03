"""Mode system: PRIMARY, DEGRADED, REMOTE. Reasons and user-facing descriptions."""

from enum import Enum


class Mode(str, Enum):
    """Runtime mode: full capability vs limited vs remote."""

    PRIMARY = "primary"
    DEGRADED = "degraded"
    REMOTE = "remote"


class ModeReason(str, Enum):
    """Why the current mode is active."""

    NO_PRIMARY_ACCESS = "no_primary_access"
    NO_SESSION = "no_session"
    POLICY_LOCK = "policy_lock"
    UNKNOWN = "unknown"


_REASON_TEXTS: dict[ModeReason, str] = {
    ModeReason.NO_PRIMARY_ACCESS: "Birincil erişim yok",
    ModeReason.NO_SESSION: "Oturum yok",
    ModeReason.POLICY_LOCK: "İlke kilidi",
    ModeReason.UNKNOWN: "Bilinmeyen",
}

_MODE_TEXTS: dict[Mode, str] = {
    Mode.PRIMARY: "Tam yetki: mesaj okuyup gönderebilir.",
    Mode.DEGRADED: "Kısıtlı: mesajları okuyabilir, gönderim onay gerektirir veya kapalı.",
    Mode.REMOTE: "Uzak: sadece senkron ve sınırlı işlem.",
}


def describe_mode(mode: Mode, reason: ModeReason | None = None) -> str:
    """Kullanıcıya okunabilir açıklama üretir."""
    parts = [_MODE_TEXTS.get(mode, str(mode.value))]
    if reason is not None:
        parts.append(f"Sebep: {_REASON_TEXTS.get(reason, reason.value)}")
    return " ".join(parts)
