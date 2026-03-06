"""
Minimal user identity for address preferences (name, address_mode, preferred_address).
Stored in .lumos/user_preferences.json. Distinct from device identity (security/identity.py).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

AddressMode = Literal["adaptive", "fixed"]
_USER_PREFS_FILENAME = "user_preferences.json"


def _base_dir() -> str:
    if Path("src/.lumos").exists():
        return "src/.lumos"
    if Path(".lumos").exists():
        return ".lumos"
    return "src/.lumos"


@dataclass
class UserIdentity:
    """User address preferences. name and preferred_address are optional."""
    name: str = ""
    address_mode: AddressMode = "adaptive"
    preferred_address: str | None = None

    def __post_init__(self) -> None:
        if self.address_mode not in ("adaptive", "fixed"):
            self.address_mode = "adaptive"


def _prefs_path(base_dir: str | Path | None = None) -> Path:
    base = Path(base_dir) if base_dir else Path(_base_dir())
    base.mkdir(parents=True, exist_ok=True)
    return base / _USER_PREFS_FILENAME


def load(base_dir: str | Path | None = None) -> UserIdentity:
    """Load user identity from .lumos/user_preferences.json. Returns defaults if missing/invalid."""
    path = _prefs_path(base_dir)
    if not path.exists():
        return UserIdentity()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return UserIdentity(
            name=str(data.get("name", "") or ""),
            address_mode=data.get("address_mode") or "adaptive",
            preferred_address=data.get("preferred_address"),
        )
    except Exception:
        return UserIdentity()


def save(user: UserIdentity, base_dir: str | Path | None = None) -> None:
    """Save user identity to .lumos/user_preferences.json."""
    path = _prefs_path(base_dir)
    data = {
        "name": user.name,
        "address_mode": user.address_mode,
        "preferred_address": user.preferred_address,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
