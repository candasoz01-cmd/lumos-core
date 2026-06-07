#!/usr/bin/env python3
"""CLI: görev metnini bridge POST /task ile yollar."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

_DEFAULT_URL = "http://127.0.0.1:8765/task"


def resolve_message_text(argv: list[str], *, stdin_text: str | None = None) -> str:
    if argv:
        raw = " ".join(argv)
    else:
        raw = stdin_text if stdin_text is not None else sys.stdin.read()
    text = raw.rstrip()
    if not text.strip():
        msg = "boş görev metni (argüman, stdin veya pipe gerekli)"
        raise ValueError(msg)
    return text


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else list(argv)

    token = (os.environ.get("KANDO_BRIDGE_SECRET") or "").strip()
    if not token:
        sys.stderr.write(
            "Hata: KANDO_BRIDGE_SECRET tanımlı değil.\n"
            "  export KANDO_BRIDGE_SECRET='your-local-dev-secret'\n",
        )
        raise SystemExit(2)

    try:
        text = resolve_message_text(argv)
    except ValueError as e:
        sys.stderr.write(f"Hata: {e}\n")
        raise SystemExit(2) from e

    url = (os.environ.get("KANDO_BRIDGE_URL") or _DEFAULT_URL).strip()
    payload = {"text": text}

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-Kando-Token": token,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        sys.stderr.write(f"HTTP {e.code}: {err_body}\n")
        if e.code == 401:
            sys.stderr.write(
                "İpucu: export KANDO_BRIDGE_SECRET ve bridge'deki secret ile eşleşmeli.\n",
            )
        raise SystemExit(1) from e
    except OSError as e:
        sys.stderr.write(
            f"bağlantı hatası ({url}): {e}\n"
            "Bridge çalışmıyor olabilir; başlat: ./scripts/bridge_start.sh\n",
        )
        raise SystemExit(1) from e
    print(raw)


if __name__ == "__main__":
    main()
