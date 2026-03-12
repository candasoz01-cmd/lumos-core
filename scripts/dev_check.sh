#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  echo "FAIL: .venv yok. Önce venv kur."
  exit 1
fi

source .venv/bin/activate

if [ ! -f "pytest.ini" ]; then
  echo "FAIL: pytest.ini yok (pythonpath=src gerekiyor)."
  exit 1
fi

echo "== make check =="
if make check; then
  echo "OK: dev_check passed"
  exit 0
fi

echo "--- tail .lumos/logs/log.txt (last 30) ---"
tail -n 30 .lumos/logs/log.txt 2>/dev/null || true
exit 1
