from enum import Enum


class Mode(str, Enum):
    PRIMARY = "primary"
    DEGRADED = "degraded"


class ModeReason(str, Enum):
    NO_PRIMARY_ACCESS = "no_primary_access"
    NO_SESSION = "no_session"
    POLICY_LOCK = "policy_lock"


def describe_mode(mode: Mode, reason: ModeReason | None = None) -> str:
    if mode == Mode.PRIMARY:
        return "Lumos tam kapasite çalışıyor."

    if mode == Mode.DEGRADED:
        base = "⚠️ Lumos sınırlı modda çalışıyor."
        if reason == ModeReason.NO_PRIMARY_ACCESS:
            return base + " Ana bağlama erişilemiyor."
        if reason == ModeReason.NO_SESSION:
            return base + " Telegram oturumu aktif değil."
        if reason == ModeReason.POLICY_LOCK:
            return base + " Politika nedeniyle otomatik aksiyon kapalı."
        return base

    return "Bilinmeyen mod."
