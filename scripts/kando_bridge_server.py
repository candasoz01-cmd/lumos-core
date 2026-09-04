#!/usr/bin/env python3
"""
Lumos Kando HTTP köprüsünü başlatır.

Uygulama kodu tek kaynakta: ``packages/kando_bridge/src/kando_bridge/server.py``
(import: ``kando_bridge.server``). Bu dosya yalnızca ``sys.path`` düzenler ve
``main()`` çağırır; eski 2k+ satırlık kopya kaldırıldı.

Önerilen çalıştırma (venv içinde paket kuruluysa): ``python -m kando_bridge``
"""
from __future__ import annotations

import os
import sys

_HOST = (os.environ.get("HOST") or "127.0.0.1").strip()
_PORT = int(os.environ.get("PORT") or os.environ.get("KANDO_BRIDGE_PORT") or "8765")

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

for _p in (
    os.path.join(_BASE, "src"),
    os.path.join(_BASE, "packages", "kando_bridge", "src"),
    os.path.join(_BASE, "packages", "kando_runtime", "src"),
):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

from kando_bridge.server import main  # noqa: E402

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "--host", _HOST, "--port", str(_PORT)]
    main()
