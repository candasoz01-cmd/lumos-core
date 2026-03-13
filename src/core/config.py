"""
Config load + validation. Single source for .lumos config.
Safe defaults when missing/invalid; log config_invalid once.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.workspace_contract import config_file_path

# Presence defaults (aligned with presence_lock.PresenceLockConfig)
PRESENCE_DEFAULTS = {
    "enabled": False,
    "timeout_sec": 30,
    "poll_sec": 1.0,
    "camera_index": 0,
    "require_face": True,
    "lock_mode": "mac",
}

PRESENCE_TIMEOUT_MIN, PRESENCE_TIMEOUT_MAX = 5, 600
PRESENCE_POLL_MIN, PRESENCE_POLL_MAX = 0.2, 10.0


def _validate_presence(data: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    """Validate presence section. Return (cleaned dict, error_msg or None)."""
    out = dict(PRESENCE_DEFAULTS)
    if not isinstance(data, dict):
        return (out, "not a dict")
    enabled = data.get("enabled")
    if enabled is not None:
        out["enabled"] = bool(enabled)
    try:
        t = data.get("timeout_sec")
        if t is not None:
            t = int(t)
            if PRESENCE_TIMEOUT_MIN <= t <= PRESENCE_TIMEOUT_MAX:
                out["timeout_sec"] = t
            else:
                out["timeout_sec"] = max(PRESENCE_TIMEOUT_MIN, min(PRESENCE_TIMEOUT_MAX, t))
    except (TypeError, ValueError):
        pass
    try:
        p = data.get("poll_sec")
        if p is not None:
            p = float(p)
            if PRESENCE_POLL_MIN <= p <= PRESENCE_POLL_MAX:
                out["poll_sec"] = p
    except (TypeError, ValueError):
        pass
    try:
        c = data.get("camera_index")
        if c is not None:
            out["camera_index"] = int(c)
    except (TypeError, ValueError):
        pass
    if "require_face" in data:
        out["require_face"] = bool(data["require_face"])
    if isinstance(data.get("lock_mode"), str):
        out["lock_mode"] = data["lock_mode"]
    return (out, None)


def load_config(base_dir: str | Path) -> dict[str, Any]:
    """Load .lumos/config.json (or presence.json for presence). Safe defaults on missing/invalid."""
    base = Path(base_dir)
    config_path = config_file_path(base)
    out: dict[str, Any] = {"presence": dict(PRESENCE_DEFAULTS)}
    if not config_path.exists():
        return out
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "presence" in data:
            pres, err = _validate_presence(data["presence"])
            out["presence"] = pres
    except Exception:
        pass
    return out


def load_presence_from_config(base_dir: str | Path) -> dict[str, Any]:
    """Load presence config: prefer config.json presence section, else presence.json (legacy)."""
    base = Path(base_dir)
    cfg = load_config(base)
    pres = cfg.get("presence") or dict(PRESENCE_DEFAULTS)
    # Legacy: if presence.json exists, it overrides for backward compat
    legacy = base / "presence.json"
    if legacy.exists():
        try:
            data = json.loads(legacy.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                pres, _ = _validate_presence(data)
        except Exception:
            pass
    return pres


_report_invalid_done = False


def report_config_invalid_once(log_event: Any, err: str) -> None:
    """Log config_invalid | err=... at most once per process."""
    global _report_invalid_done
    if _report_invalid_done:
        return
    _report_invalid_done = True
    try:
        log_event(f"config_invalid | err={err}")
    except Exception:
        pass
