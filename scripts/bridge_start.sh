#!/usr/bin/env bash
# Yerel köprüyü (kando_bridge HTTP) başlatır. Port meşgulse net mesajla çıkar.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PORT="${KANDO_BRIDGE_PORT:-8765}"
if command -v lsof >/dev/null 2>&1; then
  if lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "bridge_start: Port ${PORT} kullanımda. Boş port için örnek: KANDO_BRIDGE_PORT=8766 ./scripts/bridge_start.sh" >&2
    echo "bridge_start: Dinleyen süreç: lsof -nP -iTCP:${PORT} -sTCP:LISTEN" >&2
    exit 1
  fi
fi
export PYTHONPATH="${ROOT}/src:${ROOT}/packages/kando_bridge/src:${ROOT}/packages/kando_runtime/src${PYTHONPATH:+:${PYTHONPATH}}"
PYTHON="python3"
if [[ -x "${ROOT}/.venv/bin/python3" ]]; then
  PYTHON="${ROOT}/.venv/bin/python3"
fi
echo "bridge_start: Python: ${PYTHON}" >&2
exec "${PYTHON}" -m kando_bridge "$@"
