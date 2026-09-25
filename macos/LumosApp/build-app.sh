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

# Translation.framework macOS 14.0–14.3'te yok; güçlü bağlıysa uygulama bu
# sürümlerde açılmaz. Package.swift zayıf bağlar; burada kanıtlanır.
if ! otool -l "${OUTPUT}/Contents/MacOS/Lumos" | grep -A2 "cmd LC_LOAD_WEAK_DYLIB" \
  | grep -q "Translation.framework"; then
  echo "HATA: Translation.framework zayıf bağlı değil (LC_LOAD_WEAK_DYLIB yok)" >&2
  exit 1
fi
if otool -l "${OUTPUT}/Contents/MacOS/Lumos" | grep -A2 "cmd LC_LOAD_DYLIB" \
  | grep -q "Translation"; then
  echo "HATA: Translation (veya SwiftUI overlay'i) güçlü bağlı; macOS 14.0–14.3'te açılmaz" >&2
  exit 1
fi

ENTITLEMENTS="${APP_DIR}/Lumos.entitlements"
if [[ "${SIGNING_IDENTITY}" == "-" ]]; then
  # Ad-hoc (yerel test / CI) imza: `com.apple.developer.associated-domains`
  # kısıtlı bir entitlement'tır, provisioning profile ister; profilsiz imzada
  # macOS uygulamayı açılışta öldürür. Yerel build'de çıkarılır; yayın imzasında
  # (aşağıdaki dal) applinks:welockai.com aynen korunur.
  ADHOC_ENTITLEMENTS="${APP_DIR}/.build/Lumos.adhoc.entitlements"
  cp "${ENTITLEMENTS}" "${ADHOC_ENTITLEMENTS}"
  /usr/libexec/PlistBuddy -c "Delete :com.apple.developer.associated-domains" \
    "${ADHOC_ENTITLEMENTS}" >/dev/null 2>&1 || true
  codesign --force --deep --entitlements "${ADHOC_ENTITLEMENTS}" \
    --sign - "${OUTPUT}" >/dev/null
  if codesign -d --entitlements - --xml "${OUTPUT}" 2>/dev/null \
    | grep -q "com.apple.developer.associated-domains"; then
    echo "HATA: ad-hoc imzada associated-domains kaldı; uygulama açılmaz" >&2
    exit 1
  fi
else
  codesign --force --deep --options runtime --timestamp \
    --entitlements "${ENTITLEMENTS}" \
    --sign "${SIGNING_IDENTITY}" "${OUTPUT}" >/dev/null
  if ! codesign -d --entitlements - --xml "${OUTPUT}" 2>/dev/null \
    | grep -q "applinks:welockai.com"; then
    echo "HATA: yayın imzasında applinks:welockai.com yok" >&2
    exit 1
  fi
fi
codesign --verify --deep --strict "${OUTPUT}"
echo "Lumos.app hazır: ${OUTPUT}"
