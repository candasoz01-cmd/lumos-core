#!/usr/bin/env python3
"""Kontrollü köprü file_rw smoke testi (bridge çalışıyor olmalı)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kando.controlled_bridge_client import ping, read_file, write_file  # noqa: E402


def main() -> None:
    test_path = "lumos-controlled-test.txt"
    content = "lumos controlled bridge ok\n"

    steps = [
        ("ping", ping()),
        ("write", write_file(test_path, content)),
        ("read", read_file(test_path)),
    ]
    failed = False
    for name, out in steps:
        ok = bool(out.get("ok"))
        print(f"[{name}] ok={ok} {out}")
        if not ok:
            failed = True
    if failed:
        raise SystemExit(1)
    read_out = steps[2][1]
    if read_out.get("content") != content:
        print("read content mismatch")
        raise SystemExit(1)
    print("controlled bridge file_rw test passed")


if __name__ == "__main__":
    main()
