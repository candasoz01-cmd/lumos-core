#!/usr/bin/env bash
# Non-interactive checks for anchorusb mount helper (no Touch ID / unlock).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=anchorusb-mount-lib.sh
source "${ROOT}/anchorusb-mount-lib.sh"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

pass() {
  echo "OK: $*"
}

# Defaults
[[ "$(anchorusb_default_volume_name)" == "NO NAME" ]] || fail "default volume name"
[[ "$(anchorusb_project_dir_name)" == "Project_Lumos" ]] || fail "default project dir"
[[ "$(anchorusb_vault_basename)" == "AnchorUSB.vault" ]] || fail "default vault basename"

export ANCHORUSB_VOLUME_NAME="TestVol"
export ANCHORUSB_PROJECT_DIR="Proj"
export ANCHORUSB_VAULT_BASENAME="demo.vault"
unset ANCHORUSB_VAULT_PATH || true
[[ "$(anchorusb_vault_path)" == "/Volumes/TestVol/Proj/demo.vault" ]] || fail "vault path composition"

export ANCHORUSB_VAULT_PATH="/tmp/custom.vault"
[[ "$(anchorusb_vault_path)" == "/tmp/custom.vault" ]] || fail "vault path override"

unset ANCHORUSB_VOLUME_NAME ANCHORUSB_PROJECT_DIR ANCHORUSB_VAULT_BASENAME ANCHORUSB_VAULT_PATH

# Live mount probe (informational — does not fail if USB absent)
mp="$(anchorusb_mount_point)"
if anchorusb_is_volume_mounted; then
  pass "test USB volume mounted at ${mp}"
  vault="$(anchorusb_vault_path)"
  if [[ -f "${vault}" ]]; then
    pass "vault file exists at ${vault}"
  else
    pass "vault file missing at ${vault} (expected S0 until init)"
  fi
else
  pass "volume not mounted at ${mp} (plug USB to test live)"
fi

pass "mount-detect helper tests"
