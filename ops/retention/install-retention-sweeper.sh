#!/bin/bash
# Prova kaydı metin katmanı saklama süpürücüsünü kurar (macOS launchd).
#
# Kurucu kararı (2026-08-25): metin katmanının 24 saatlik ömrü GERÇEK bir üst
# sınır olmalı. Sınırı uygulayan şey bu zamanlayıcı işidir; kurulu değilse rig
# fail-closed davranıp başlamaz (representative.retention.require_sweeper).
#
# Kullanım:  bash ops/retention/install-retention-sweeper.sh [sweep_dizini]
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SWEEP_DIR="$(cd "${1:-$REPO}" && pwd)"
PYTHON="${LUMOS_PYTHON:-$REPO/.venv/bin/python}"
LABEL="ai.lumos.representative.retention-sweep"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$HOME/Library/Logs/$LABEL.log"
INTERVAL="$("$PYTHON" -c 'import sys; sys.path.insert(0, "'"$REPO"'/src"); from representative.retention import SWEEP_INTERVAL_S; print(SWEEP_INTERVAL_S)')"

if [ ! -x "$PYTHON" ]; then
  echo "python bulunamadı: $PYTHON (LUMOS_PYTHON ile ver)" >&2
  exit 1
fi

echo "Süpürülecek dizin : $SWEEP_DIR"
echo "Aralık            : $INTERVAL sn"
echo
echo "İlk süpürme ŞUNLARI yapardı (kuru çalışma — hiçbir şey silinmedi):"
PYTHONPATH="$REPO/src" "$PYTHON" -m representative.retention --sweep --dir "$SWEEP_DIR" --dry-run
echo
read -r -p "Süpürücü kurulsun mu? Bu, süresi dolmuş metinleri KALICI olarak siler [e/H] " answer
case "$answer" in
  e|E|evet|y|Y|yes) ;;
  *) echo "vazgeçildi (hiçbir şey kurulmadı, hiçbir dosya değişmedi)"; exit 1 ;;
esac

mkdir -p "$(dirname "$PLIST")" "$(dirname "$LOG")"
sed -e "s|__LABEL__|$LABEL|g" \
    -e "s|__PYTHON__|$PYTHON|g" \
    -e "s|__SWEEP_DIR__|$SWEEP_DIR|g" \
    -e "s|__SRC__|$REPO/src|g" \
    -e "s|__INTERVAL__|$INTERVAL|g" \
    -e "s|__LOG__|$LOG|g" \
    "$REPO/ops/retention/$LABEL.plist.template" > "$PLIST"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

# RunAtLoad ilk süpürmeyi hemen tetikler; kalp atışı damgası düşene kadar bekle
sleep 3
PYTHONPATH="$REPO/src" "$PYTHON" -m representative.retention --sweeper-status --dir "$SWEEP_DIR"
echo "log: $LOG"
