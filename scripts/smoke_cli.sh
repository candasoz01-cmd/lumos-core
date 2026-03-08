#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

if [ -f ".venv/bin/activate" ]; then
  . ".venv/bin/activate"
fi

if command -v lumos >/dev/null 2>&1; then
  RUN="lumos"
else
  RUN="python -m lumos_core"
fi

OUT="$("$RUN" <<'EOT'
HELP
durum
exit
EOT
)"

echo "$OUT" | grep -q "Komutlar:"
echo "$OUT" | grep -q "LOCKED"
echo "OK: smoke_cli passed"
