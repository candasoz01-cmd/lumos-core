"""Legacy entry: run main CLI with src on path. Prefer: lumos or python -m lumos_core."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import main  # type: ignore

if __name__ == "__main__":
    raise SystemExit(main.main())
