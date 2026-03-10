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


def _lock_ok(keystore_initialized: bool) -> bool:
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
) -> str:
    """
    Tek satır hazır olma özeti. Öncelik: consent > lock > presence > macOS.
    Sorun varsa yalnızca en kritik eksik; mümkünse bir sonraki adım.
    """
    consent = _consent_ok(base_dir)
    lock = _lock_ok(keystore_initialized)
    pres_ok, pres_enabled = _presence_ok(presence_module, base_dir)
    macos = _macos_permissions_ok()

    if not consent:
        return "Hazır değil. Consent alınmadı."

    if not lock:
        return "Kısmen hazır. Lock yok, consent kayıtlı."

    if not pres_ok:
        return "Kısmen hazır. Presence yapılandırması yüklenemedi."

    if pres_enabled and platform.system() == "Darwin" and macos is False:
        return "Kısmen hazır. Presence açık, kamera izni yok."

    if pres_enabled and platform.system() == "Darwin" and macos is None:
        return "Kısmen hazır. Presence açık, kamera izni bilinmiyor."

    pres_label = "presence hazır" if pres_enabled else "presence kapalı"
    return f"Hazır. Lock aktif, {pres_label}, consent kayıtlı."
