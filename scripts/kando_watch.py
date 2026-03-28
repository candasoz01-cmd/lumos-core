#!/usr/bin/env python3
"""
DEPRECATED: Direct patch ve agent akışı scripts/kando_bridge_server.py içinde çözülür.

Eski request.txt + .last_request + watcher zinciri kaldırıldı. Bu betiği çalıştırmayın.
"""
from __future__ import annotations

import sys


def main() -> None:
    sys.stderr.write(
        "kando_watch.py artık kullanılmıyor. "
        "Orkestratör: PYTHONPATH=src python scripts/kando_bridge_server.py\n",
    )
    raise SystemExit(2)


if __name__ == "__main__":
    main()
