set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

LUMOS_LOG=".lumos/log.txt"
: > "$LUMOS_LOG"

printf "kamera aç\nevet\n10\nkamera kapat\nçık\n" | PYTHONPATH=src python src/main.py >/dev/null 2>&1 || true

echo "--- Last 80 log lines ---"
tail -n 80 "$LUMOS_LOG" || true

LOG_CONTENT="$(cat "$LUMOS_LOG")"

# Must contain required events (logfmt: event=...)
for ev in presence_enabled presence_started presence_disabled; do
  if ! grep -q "event=$ev" <<<"$LOG_CONTENT"; then
    echo "FAIL: log missing event=$ev"
    exit 1
  fi
done

# Line numbers (default 0 if not found)
START_AT="$(grep -n "event=presence_started" "$LUMOS_LOG" | head -1 | cut -d: -f1 || true)"
DIS_AT="$(grep -n "event=presence_disabled" "$LUMOS_LOG" | head -1 | cut -d: -f1 || true)"

START_AT="${START_AT:-0}"
DIS_AT="${DIS_AT:-0}"

# Ensure started happens before disabled
if (( START_AT > 0 && DIS_AT > 0 && START_AT > DIS_AT )); then
  echo "FAIL: presence_disabled before presence_started"
  exit 1
fi

# Option B rule: presence_stopped must not appear
if grep -q "event=presence_stopped" "$LUMOS_LOG"; then
  echo "FAIL: event=presence_stopped must not appear (disable uses silent=True)"
  exit 1
fi

echo "OK: smoke_presence passed"
