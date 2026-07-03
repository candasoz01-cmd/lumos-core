#!/usr/bin/env bash
# Compile anchorusb-touchid helper (macOS only, LocalAuthentication).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="${ROOT}/anchorusb-touchid.swift"
OUT="${ROOT}/bin/anchorusb-touchid"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "skip: Touch ID helper requires macOS" >&2
  exit 0
fi

mkdir -p "${ROOT}/bin"
swiftc -O -o "${OUT}" "${SRC}" -framework LocalAuthentication
chmod +x "${OUT}"
echo "built: ${OUT}"
