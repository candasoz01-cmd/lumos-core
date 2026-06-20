"""Tek kaynak: LUMOS çalışma dizini (tasks, trash, bridge okumaları)."""
from __future__ import annotations

import os
from pathlib import Path


def lumos_base_dir() -> Path:
    # Boş veya yalnızca boşluk: get(..., ".lumos") devreye girmez (env anahtarı vardır);
    # Path("") resolve edilince cwd olur — bunu engelle.
    raw = (os.environ.get("LUMOS_BASE_DIR") or ".lumos").strip()
    if not raw:
        raw = ".lumos"
    return Path(raw).expanduser().resolve()
