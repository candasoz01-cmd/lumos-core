"""
Minimal persistent user memory for Lumos v1: local file only.
Stores only a small list of user-approved preferences. No automatic learning or profiling.
"""
from __future__ import annotations

import json
from pathlib import Path

# Reuse base_dir from user_identity to keep .lumos in one place
_USER_MEMORY_FILENAME = "user_memory.json"
_MAX_APPROVED_PREFERENCES = 20


def _base_dir() -> str:
    if Path("src/.lumos").exists():
        return "src/.lumos"
    if Path(".lumos").exists():
        return ".lumos"
    return "src/.lumos"


def _user_memory_path(base_dir: str | Path | None = None) -> Path:
    base = Path(base_dir) if base_dir else Path(_base_dir())
    base.mkdir(parents=True, exist_ok=True)
    return base / _USER_MEMORY_FILENAME


def load_approved_preferences(base_dir: str | Path | None = None) -> list[dict[str, str]]:
    """
    Load the list of approved preferences from .lumos/user_memory.json.
    Returns a list of {"key": str, "value": str}. Empty list if missing or invalid.
    """
    path = _user_memory_path(base_dir)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        prefs = data.get("approved_preferences", [])
        if not isinstance(prefs, list):
            return []
        out: list[dict[str, str]] = []
        for p in prefs[: _MAX_APPROVED_PREFERENCES]:
            if isinstance(p, dict) and isinstance(p.get("key"), str) and isinstance(p.get("value"), str):
                out.append({"key": p["key"], "value": p["value"]})
        return out
    except Exception:
        return []


def save_approved_preferences(
    preferences: list[dict[str, str]],
    base_dir: str | Path | None = None,
) -> None:
    """
    Save the list of approved preferences. Overwrites the file.
    Call only when the user has explicitly approved what is being saved.
    """
    path = _user_memory_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    capped = preferences[:_MAX_APPROVED_PREFERENCES]
    data = {"approved_preferences": [{"key": p["key"], "value": p["value"]} for p in capped]}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def add_approved_preference(
    key: str,
    value: str,
    base_dir: str | Path | None = None,
) -> None:
    """
    Add or update one user-approved preference. Explicit-only: call only after user approval.
    Replaces existing entry with same key. Enforces max size.
    """
    key = (key or "").strip()
    value = (value or "").strip()
    if not key:
        return
    prefs = load_approved_preferences(base_dir)
    prefs = [p for p in prefs if p.get("key") != key]
    prefs.append({"key": key, "value": value})
    save_approved_preferences(prefs, base_dir)


def remove_approved_preference(key: str, base_dir: str | Path | None = None) -> None:
    """Remove one approved preference by key."""
    key = (key or "").strip()
    if not key:
        return
    prefs = [p for p in load_approved_preferences(base_dir) if p.get("key") != key]
    save_approved_preferences(prefs, base_dir)
