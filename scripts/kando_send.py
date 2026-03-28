#!/usr/bin/env python3
"""CLI: görev metnini bridge POST /task ile yollar (request.txt kullanılmaz)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            'kullanım: python scripts/kando_send.py "görev metni"\n'
            "  veya: KANDO_BRIDGE_URL=http://127.0.0.1:8765/task python scripts/kando_send.py ...",
        )
    url = (os.environ.get("KANDO_BRIDGE_URL") or "http://127.0.0.1:8765/task").strip()
    token = (os.environ.get("KANDO_BRIDGE_SECRET") or "").strip()
    body = json.dumps({"text": sys.argv[1].strip()}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    if token:
        req.add_header("X-Kando-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        sys.stderr.write(f"HTTP {e.code}: {err_body}\n")
        raise SystemExit(1) from e
    except OSError as e:
        sys.stderr.write(f"bağlantı hatası ({url}): {e}\n")
        raise SystemExit(1) from e
    print(raw)


if __name__ == "__main__":
    main()
