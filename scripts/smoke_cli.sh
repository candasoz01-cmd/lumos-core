#!/usr/bin/env bash
set -euo pipefail

if [ -f ".venv/bin/activate" ]; then
  . ".venv/bin/activate"
fi

bash scripts/run.sh cli
echo "OK: smoke_cli passed"
