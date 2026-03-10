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

# Consent may consume first line in CI; main CLI gets durum then exit. We only require status line + clean exit.
OUT="$("$RUN" <<'EOT'
HELP
durum
exit
EOT
)"

echo "$OUT" | grep -q "LOCKED"
echo "$OUT" | grep -q "OK"
echo "OK: smoke_cli passed"
