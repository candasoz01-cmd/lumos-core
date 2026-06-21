#!/usr/bin/env python3
"""CLI wrapper: poll-based demo mobile approval client for kando_bridge."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_PKG = _REPO / "packages" / "kando_bridge" / "src"
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from kando_bridge.mobile_approval_client import main  # noqa: E402

if __name__ == "__main__":
    main()
