#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
UI_DIR="$REPO_DIR/ui"
PORT="${1:-4173}"

if ! [[ "$PORT" =~ ^[0-9]+$ ]] || ((PORT < 1024 || PORT > 65535)); then
  echo "Hata: port 1024-65535 arasında bir sayı olmalı." >&2
  exit 2
fi

if [[ ! -x "$UI_DIR/node_modules/.bin/astro" ]]; then
  echo "Hata: UI bağımlılıkları eksik. Önce: npm --prefix ui install" >&2
  exit 3
fi

LAN_IP=""
if command -v ipconfig >/dev/null 2>&1; then
  LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
  if [[ -z "$LAN_IP" ]]; then
    LAN_IP="$(ipconfig getifaddr en1 2>/dev/null || true)"
  fi
fi

echo "Elektronik Uzmanı telefon önizlemesi hazırlanıyor..."
npm --prefix "$UI_DIR" run build

if [[ -n "$LAN_IP" ]]; then
  echo "Telefondan aç: http://$LAN_IP:$PORT/panel/"
else
  echo "Telefondan aç: http://<bu-bilgisayarin-yerel-ip-adresi>:$PORT/panel/"
fi
echo "Bilgisayar ve telefon aynı Wi-Fi ağında olmalı."
echo "Bu production deploy değildir. Terminali kapatınca önizleme sona erer."
echo "Pilot kayıtları telefon tarayıcısında yerel kalır."

exec python3 -m http.server "$PORT" --bind 0.0.0.0 --directory "$UI_DIR/dist"
