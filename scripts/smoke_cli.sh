#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

if [ -d .venv ]; then
  PY=".venv/bin/python"
else
  PY="python3"
fi

if command -v lumos >/dev/null 2>&1; then
  RUNNER="lumos"
else
  RUNNER="$PY -m lumos_core"
fi

OUT="$("$RUNNER" <<'EOT'
HELP
durum
exit
EOT
)"

echo "$OUT" | grep -q "Komutlar:"
echo "$OUT" | grep -q "LOCKED"
echo "OK: smoke_cli passed"
