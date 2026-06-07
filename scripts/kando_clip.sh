#!/usr/bin/env bash
# macOS: panodaki metni kando_send.py ile bridge'e yollar (hata/secret: kando_send.py).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec pbpaste | python3 "$ROOT/scripts/kando_send.py"
