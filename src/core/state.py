"""
Core state: single source for lock/presence and mode.
CLI/TUI read from CoreState only.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


class CoreState:
    """Read-only view over lumos lock state, presence status, and mode."""

    def __init__(self, lumos: Any, presence_lock_module: Any, mode: str) -> None:
        self._lumos = lumos
        self._pl = presence_lock_module
        self._mode = (mode or "offline").strip().lower()

    def lock_status(self) -> str:
        """LOCKED or UNLOCKED."""
        try:
            return "UNLOCKED" if getattr(self._lumos, "lock_state", None) and getattr(self._lumos.lock_state, "unlocked", False) else "LOCKED"
        except Exception:
            return "LOCKED"

    def is_locked(self) -> bool:
        """True when device is locked (for presence is_already_locked)."""
        return not self.lock_status().startswith("UNLOCKED")

    def presence_display(self) -> str:
        """ON (running) | ON (stopped) | OFF."""
        try:
            ps = self._pl.presence_status()
            if ps == "ON":
                return "ON (running)" if self._pl.is_running() else "ON (stopped)"
            return "OFF"
        except Exception:
            return "OFF"

    def mode_str(self) -> str:
        """offline | online."""
        return "offline" if self._mode == "offline" else "online"

    def log_event(self, message: str) -> None:
        self._pl.log_event(message)

    def snapshot(
        self,
        base_dir: str | Path | None = None,
        log_path: Path | None = None,
    ) -> dict[str, Any]:
        """Single source snapshot: lock_status, presence_enabled, presence_running, mode, last_log_ts."""
        lock = self.lock_status()
        try:
            presence_enabled = False
            if base_dir is not None:
                cfg = self._pl.load_presence_cfg(Path(base_dir))
                presence_enabled = bool(getattr(cfg, "enabled", False))
        except Exception:
            presence_enabled = False
        try:
            presence_running = bool(self._pl.is_running())
        except Exception:
            presence_running = False
        mode = self.mode_str()
        last_log_ts = ""
        try:
            lp = log_path if log_path is not None else Path.cwd() / ".lumos" / "logs" / "log.txt"
            if lp.exists():
                lines = lp.read_text(encoding="utf-8", errors="replace").strip().splitlines()
                if lines:
                    first_part = lines[-1].strip().split(" | ")[0].strip()
                    if first_part:
                        last_log_ts = first_part
        except Exception:
            pass
        return {
            "lock_status": lock,
            "presence_enabled": presence_enabled,
            "presence_running": presence_running,
            "mode": mode,
            "last_log_ts": last_log_ts,
        }


def format_status_line(snapshot: dict[str, Any]) -> str:
    """Single formatter for 'LOCKED | Presence: ... | Mode: ... | Log: ...' from snapshot."""
    lock = (snapshot.get("lock_status") or "LOCKED").strip()
    enabled = bool(snapshot.get("presence_enabled", False))
    running = bool(snapshot.get("presence_running", False))
    if not enabled:
        pres = "OFF"
    else:
        pres = "ON (running)" if running else "ON (stopped)"
    mode = (snapshot.get("mode") or "offline").strip()
    log_ts = (snapshot.get("last_log_ts") or "").strip()
    return f"{lock} | Presence: {pres} | Mode: {mode} | Log: {log_ts}"


def format_durum(
    snapshot: dict[str, Any],
    consent_ok: bool,
    lock_ok: bool,
    durum_label: str,
    not_line: str,
) -> str:
    """
    Durum komutu için okunur çıktı: Durum, Lock, Presence, Consent, Mod, Not.
    consent_ok/lock_ok/durum_label/not_line get_durum_parts ile alınır.
    """
    lock_label = "aktif" if lock_ok else "pasif"
    enabled = bool(snapshot.get("presence_enabled", False))
    pres_label = "açık" if enabled else "kapalı"
    consent_label = "kayıtlı" if consent_ok else "yok"
    mode = (snapshot.get("mode") or "offline").strip()

    lines = [
        f"Durum: {durum_label}",
        f"Lock: {lock_label}",
        f"Presence: {pres_label}",
        f"Consent: {consent_label}",
        f"Mod: {mode}",
        f"Not: {not_line}",
    ]
    return "\n".join(lines)
