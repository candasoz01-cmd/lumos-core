#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

if [ -d .venv ]; then
  PY=".venv/bin/python"
else
  PY="python3"
fi

PORT=28765
export PORT

"$PY" web/app.py &
PID=$!
trap 'kill $PID 2>/dev/null || true' EXIT

sleep 1
curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/health" | grep -q 200
curl -s "http://127.0.0.1:$PORT/health" | grep -q '"ok":\s*true'
curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/status" | grep -q 200
curl -s "http://127.0.0.1:$PORT/status" | grep -qE '"mode"|"lock_status"|"presence'

echo "OK: smoke_web passed"
