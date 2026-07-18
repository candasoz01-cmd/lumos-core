#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${APP_DIR}/../.." && pwd)"
OUTPUT="${APP_DIR}/dist/Lumos.app"
ICONSET="${APP_DIR}/.build/Lumos.iconset"
ICON_SOURCE="${APP_DIR}/.build/chat-lumos-mark.png"
SIGNING_IDENTITY="${LUMOS_MAC_SIGNING_IDENTITY:--}"

swift build --package-path "${APP_DIR}" -c release

rm -rf "${OUTPUT}" "${ICONSET}"
mkdir -p "${OUTPUT}/Contents/MacOS" "${OUTPUT}/Contents/Resources" "${ICONSET}"
cp "${APP_DIR}/.build/release/Lumos" "${OUTPUT}/Contents/MacOS/Lumos"
cp "${APP_DIR}/Info.plist" "${OUTPUT}/Contents/Info.plist"

qlmanage -t -s 1024 -o "${APP_DIR}/.build" "${ROOT}/ui/public/chat-lumos-mark.svg" >/dev/null 2>&1
mv "${APP_DIR}/.build/chat-lumos-mark.svg.png" "${ICON_SOURCE}"
for size in 16 32 128 256 512; do
  sips -z "${size}" "${size}" "${ICON_SOURCE}" --out "${ICONSET}/icon_${size}x${size}.png" >/dev/null
  double=$((size * 2))
  sips -z "${double}" "${double}" "${ICON_SOURCE}" --out "${ICONSET}/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "${ICONSET}" -o "${OUTPUT}/Contents/Resources/Lumos.icns"

if [[ "${SIGNING_IDENTITY}" == "-" ]]; then
  codesign --force --deep --entitlements "${APP_DIR}/Lumos.entitlements" \
    --sign - "${OUTPUT}" >/dev/null
else
  codesign --force --deep --options runtime --timestamp \
    --entitlements "${APP_DIR}/Lumos.entitlements" \
    --sign "${SIGNING_IDENTITY}" "${OUTPUT}" >/dev/null
fi
codesign --verify --deep --strict "${OUTPUT}"
echo "Lumos.app hazır: ${OUTPUT}"
