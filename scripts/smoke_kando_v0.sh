#!/usr/bin/env bash
# Kando v0 resmî smoke: help, durum, kamera alt menüsü, çıkış.
# docs/SMOKE_KANDO_V0.md ile uyumlu.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ -f ".venv/bin/activate" ]; then
  . ".venv/bin/activate"
fi
[ -d "src" ] && export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
OUT=$(mktemp)
trap 'rm -f "$OUT"' EXIT
printf '%s\n' help durum kamera durum cik exit | python -m lumos_core cli 2>&1 > "$OUT" || true
check() { grep -q "$1" "$OUT" || { echo "FAIL: beklenen çıktı yok: $1"; exit 1; }; }
check "Kando v0"
check "kilit | kamera | alias | durum"
check "LOCKED | Presence:"
check "Mode:"
check "Kamera: durum | ac | kapat"
check "enabled="
check "OK"
echo "PASS: Kando v0 smoke tamamlandı"
