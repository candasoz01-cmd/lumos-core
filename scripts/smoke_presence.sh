#!/usr/bin/env bash
set -euo pipefail

if [ -f ".venv/bin/activate" ]; then
  . ".venv/bin/activate"
fi

python -m pip --version >/dev/null 2>&1 || python3 -m pip --version >/dev/null 2>&1 || true

bash scripts/run.sh presence
echo "OK: smoke_presence passed"
