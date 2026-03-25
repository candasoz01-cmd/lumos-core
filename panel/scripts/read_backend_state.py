#!/usr/bin/env python3
"""
CLI: çekirdek `get_live_read_state()` çıktısını JSON basar veya `panel/js/state_inject.js` yazar.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent.parent
_src = _repo_root / "src"
if _src.is_dir():
    sys.path.insert(0, str(_src))


def main() -> None:
    from core.panel_runtime import get_live_read_state

    write_path = None
    if "--write" in sys.argv:
        write_path = _repo_root / "panel" / "js" / "state_inject.js"

    state = get_live_read_state(repo_root=_repo_root)
    payload = json.dumps(state, ensure_ascii=False, indent=2)

    if write_path is not None:
        content = (
            "// Read-only bridge state (set by panel/scripts/read_backend_state.py --write)\n"
            "window.__LUMOS_READ_STATE__ = "
            + payload
            + ";\n"
        )
        write_path.write_text(content, encoding="utf-8")
        print("Wrote", write_path, file=sys.stderr)
    else:
        print(payload)


if __name__ == "__main__":
    main()
