"""Legacy entry: run interactive CLI. Prefer: lumos or python -m lumos_core."""
from __future__ import annotations

from lumos_core.interactive_cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
