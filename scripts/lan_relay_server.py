#!/usr/bin/env python3
"""Start Lumos LAN relay (mobile approval MVP)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_BRIDGE_SRC = _ROOT / "packages" / "kando_bridge" / "src"
if str(_BRIDGE_SRC) not in sys.path:
    sys.path.insert(0, str(_BRIDGE_SRC))

from kando_bridge.lan_relay import main  # noqa: E402

if __name__ == "__main__":
    main()
