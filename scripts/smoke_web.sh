#!/usr/bin/env bash
set -euo pipefail

if [ -f ".venv/bin/activate" ]; then
  . ".venv/bin/activate"
fi

bash scripts/run.sh web
echo "OK: smoke_web passed"
