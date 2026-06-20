"""
Başlangıç sağlık kontrolü: consent, lock, presence, macOS izinleri.
Tek satır operasyon özeti + gerekiyorsa bir sonraki adım.
"""
from __future__ import annotations

import platform
from pathlib import Path
from typing import Any


def _consent_ok(base_dir: str | Path) -> bool:
    p = Path(base_dir) / "consent.json"
    return p.exists()


def effective_consent(base_dir: str | Path, session_consent: bool) -> bool:
    """
    Single source of truth for consent: file-based consent OR session (genel onay aç).
    Use this for durum, hazır, şu an güvenli miyim, bir sonraki adım ne, and task gate.
    """
    return _consent_ok(base_dir) or session_consent


def keystore_ready(keystore_initialized: bool) -> bool:
    """ADR-011: keystore init signal — FileKeyStore.is_initialized() or equivalent."""
    return bool(keystore_initialized)


def _presence_ok(presence_module: Any, base_dir: str | Path) -> tuple[bool, bool]:
    """Returns (config_ok, enabled). Config ok = loadable without error."""
    try:
        cfg = presence_module.load_presence_cfg(Path(base_dir))
        enabled = bool(getattr(cfg, "enabled", False))
        return True, enabled
    except Exception:
        return False, False


def _macos_permissions_ok() -> bool | None:
    """On Darwin, we don't have a direct API for accessibility/screen recording.
    Returns True if we can open camera (presence-relevant), False if we tried and failed, None if unknown/skipped.
    """
    if platform.system() != "Darwin":
        return None
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        ok = cap.isOpened()
        if cap:
            cap.release()
        return ok
    except Exception:
        return None


def get_startup_summary(
    base_dir: str | Path,
    keystore_initialized: bool,
    presence_module: Any,
    session_consent: bool = False,
    *,
    session_unlocked: bool | None = None,
) -> str:
    """
    Tek satır hazır olma özeti. Öncelik: consent > lock > presence > macOS.
    Sorun varsa yalnızca en kritik eksik; mümkünse bir sonraki adım.
    session_consent: when True (e.g. genel onay aç), consent is treated as given for this session.
    session_unlocked: when set (CLI hazir), runtime session signal is used instead of keystore_ready.
    """
    consent = effective_consent(base_dir, session_consent)
    if session_unlocked is not None:
        lock_ready = bool(session_unlocked)
        lock_missing = "Oturum kilitli"
        lock_ok_label = "Oturum açık"
    else:
        lock_ready = keystore_ready(keystore_initialized)
        lock_missing = "Keystore hazır değil"
        lock_ok_label = "Keystore hazır"
    pres_ok, pres_enabled = _presence_ok(presence_module, base_dir)
    macos = _macos_permissions_ok()

    if not consent:
        return "Hazır değil. Consent alınmadı."

    if not lock_ready:
        return f"Kısmen hazır. {lock_missing}, consent kayıtlı."

    if not pres_ok:
        return "Kısmen hazır. Presence yapılandırması yüklenemedi."

    if pres_enabled and platform.system() == "Darwin" and macos is False:
        return "Kısmen hazır. Presence açık, kamera izni yok."

    if pres_enabled and platform.system() == "Darwin" and macos is None:
        return "Kısmen hazır. Presence açık, kamera izni bilinmiyor."

    pres_label = "presence hazır" if pres_enabled else "presence kapalı"
    return f"Hazır. {lock_ok_label}, {pres_label}, consent kayıtlı."


def consent_ok(base_dir: str | Path) -> bool:
    """Consent dosyası var mı (durum komutu için)."""
    return _consent_ok(base_dir)


def get_durum_parts(
    base_dir: str | Path,
    keystore_initialized: bool,
    presence_module: Any,
    session_consent: bool = False,
) -> dict[str, Any]:
    """
    Durum komutu için etiket ve not. Öncelik: consent > keystore > presence > macOS.
    Döner: consent_ok, keystore_ready, durum_label ("güvenli" | "kısmen hazır"), not_line.
    session_consent: when True (e.g. genel onay aç), consent is treated as given for this session.
    """
    consent = effective_consent(base_dir, session_consent)
    ks_ready = keystore_ready(keystore_initialized)
    pres_ok, pres_enabled = _presence_ok(presence_module, base_dir)
    macos = _macos_permissions_ok()

    if not consent:
        return {"consent_ok": False, "keystore_ready": ks_ready, "durum_label": "kısmen hazır", "not_line": "consent alınmadı"}
    if not ks_ready:
        return {"consent_ok": True, "keystore_ready": False, "durum_label": "kısmen hazır", "not_line": "keystore hazır değil"}
    if not pres_ok:
        return {"consent_ok": True, "keystore_ready": True, "durum_label": "kısmen hazır", "not_line": "presence yapılandırması yok"}
    if pres_enabled and platform.system() == "Darwin" and macos is False:
        return {"consent_ok": True, "keystore_ready": True, "durum_label": "kısmen hazır", "not_line": "kamera izni yok"}
    if pres_enabled and platform.system() == "Darwin" and macos is None:
        return {"consent_ok": True, "keystore_ready": True, "durum_label": "kısmen hazır", "not_line": "kamera izni bilinmiyor"}

    return {"consent_ok": True, "keystore_ready": True, "durum_label": "güvenli", "not_line": "kritik eksik yok"}
