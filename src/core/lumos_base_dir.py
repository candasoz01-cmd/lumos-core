"""Tek kaynak: LUMOS çalışma dizini (tasks, trash, bridge okumaları)."""
from __future__ import annotations

import os
from pathlib import Path


def lumos_base_dir() -> Path:
    return Path(os.environ.get("LUMOS_BASE_DIR", ".lumos")).resolve()
