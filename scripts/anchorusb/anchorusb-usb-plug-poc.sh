#!/usr/bin/env bash
# AnchorUSB USB-plug POC — mount detect → lock screen → Touch ID → anchorusb unlock.
# macOS experiment only. No network. Read-only on USB until user passphrase unlock.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${ROOT}/../.." && pwd)"
# shellcheck source=anchorusb-mount-lib.sh
source "${ROOT}/anchorusb-mount-lib.sh"

POLL_SECS="${ANCHORUSB_POLL_SECS:-1}"
STATE_FILE="${ANCHORUSB_STATE_FILE:-/tmp/anchorusb-mount-state}"
TOUCHID_BIN="${ANCHORUSB_TOUCHID_BIN:-${ROOT}/bin/anchorusb-touchid}"
ANCHORUSB_CLI="${ANCHORUSB_CLI:-}"

usage() {
  cat <<'EOF'
AnchorUSB USB-plug POC (macOS)

Watches for USB volume mount → lock banner → Touch ID → anchorusb unlock.

Environment:
  ANCHORUSB_VOLUME_NAME   Volume label (default: NO NAME)
  ANCHORUSB_PROJECT_DIR   Subfolder on USB (default: Project_Lumos)
  ANCHORUSB_VAULT_BASENAME Vault file name (default: AnchorUSB.vault)
  ANCHORUSB_VAULT_PATH    Override full vault path
  ANCHORUSB_PASSPHRASE    Passphrase for unlock (else interactive prompt)
  ANCHORUSB_SKIP_TOUCHID  1 = skip biometric gate
  ANCHORUSB_POLL_SECS     Poll interval (default: 1)
  ANCHORUSB_TRIGGER_ON_START 1 = run flow if volume already mounted at start
  ANCHORUSB_CLI           Path to anchorusb binary (else cargo build)

Usage:
  ./scripts/anchorusb/anchorusb-usb-plug-poc.sh watch   # loop until Ctrl-C
  ./scripts/anchorusb/anchorusb-usb-plug-poc.sh once    # single flow if mounted
  ./scripts/anchorusb/anchorusb-usb-plug-poc.sh status  # mount + vault status

EOF
}

resolve_anchorusb_cli() {
  if [[ -n "${ANCHORUSB_CLI}" && -x "${ANCHORUSB_CLI}" ]]; then
    return 0
  fi
  if command -v anchorusb >/dev/null 2>&1; then
    ANCHORUSB_CLI="$(command -v anchorusb)"
    return 0
  fi
  local release="${REPO_ROOT}/target/release/anchorusb"
  local debug="${REPO_ROOT}/target/debug/anchorusb"
  if [[ -x "${release}" ]]; then
    ANCHORUSB_CLI="${release}"
    return 0
  fi
  if [[ -x "${debug}" ]]; then
    ANCHORUSB_CLI="${debug}"
    return 0
  fi
  echo "building anchorusb-cli..." >&2
  (cd "${REPO_ROOT}" && cargo build -p anchorusb-cli -q)
  ANCHORUSB_CLI="${REPO_ROOT}/target/debug/anchorusb"
}

ensure_touchid_helper() {
  if [[ "${ANCHORUSB_SKIP_TOUCHID:-0}" == "1" ]]; then
    return 0
  fi
  if [[ -x "${TOUCHID_BIN}" ]]; then
    return 0
  fi
  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "note: Touch ID skipped (not macOS)" >&2
    export ANCHORUSB_SKIP_TOUCHID=1
    return 0
  fi
  echo "building Touch ID helper..." >&2
  "${ROOT}/build-touchid.sh"
}

show_lock_dialog() {
  local mp
  mp="$(anchorusb_mount_point)"
  if [[ "$(uname -s)" != "Darwin" ]]; then
    return 0
  fi
  osascript <<EOF 2>/dev/null || true
display alert "AnchorUSB Locked" message "USB volume detected: ${mp}

Place your finger on Touch ID when prompted, then enter your vault passphrase in the terminal." as critical buttons {"OK"} default button "OK"
EOF
}

run_touchid_gate() {
  if [[ "${ANCHORUSB_SKIP_TOUCHID:-0}" == "1" ]]; then
    echo "Touch ID: skipped (ANCHORUSB_SKIP_TOUCHID=1)" >&2
    return 0
  fi
  if [[ ! -x "${TOUCHID_BIN}" ]]; then
    echo "Touch ID: helper missing, continuing to passphrase" >&2
    return 0
  fi
  echo "Touch ID: waiting for biometric..." >&2
  if "${TOUCHID_BIN}" "AnchorUSB: USB plugged in — authenticate to unlock"; then
    echo "Touch ID: OK" >&2
    return 0
  fi
  local rc=$?
  if [[ "${rc}" -eq 2 ]]; then
    echo "Touch ID: unavailable on this Mac — continuing to passphrase" >&2
    return 0
  fi
  if [[ "${rc}" -eq 3 ]]; then
    echo "Touch ID: cancelled by user" >&2
    return 1
  fi
  echo "Touch ID: failed (exit ${rc})" >&2
  return 1
}

run_unlock_flow() {
  local vault
  vault="$(anchorusb_vault_path)"
  resolve_anchorusb_cli
  ensure_touchid_helper

  clear 2>/dev/null || true
  anchorusb_lock_banner
  show_lock_dialog

  if ! run_touchid_gate; then
    echo "unlock aborted (biometric gate)" >&2
    return 1
  fi

  if [[ ! -f "${vault}" ]]; then
    echo "S0: no vault at ${vault}" >&2
    echo "Create with:" >&2
    echo "  ANCHORUSB_PASSPHRASE='...' ${ANCHORUSB_CLI} init --path \"${vault}\"" >&2
    return 2
  fi

  echo "vault status:" >&2
  "${ANCHORUSB_CLI}" status --path "${vault}" || true

  echo "unlocking (passphrase required for crypto)..." >&2
  if [[ -n "${ANCHORUSB_PASSPHRASE:-}" ]]; then
    ANCHORUSB_PASSPHRASE="${ANCHORUSB_PASSPHRASE}" "${ANCHORUSB_CLI}" unlock --path "${vault}"
  else
    "${ANCHORUSB_CLI}" unlock --path "${vault}"
  fi
}

cmd_status() {
  local vault mp
  mp="$(anchorusb_mount_point)"
  vault="$(anchorusb_vault_path)"
  echo "mount_point: ${mp}"
  if anchorusb_is_volume_mounted; then
    echo "mounted: yes"
  else
    echo "mounted: no"
  fi
  echo "vault_path: ${vault}"
  if [[ -f "${vault}" ]]; then
    echo "vault_file: present"
    resolve_anchorusb_cli
    "${ANCHORUSB_CLI}" status --path "${vault}" || true
  else
    echo "vault_file: missing (S0)"
  fi
}

read_mount_state() {
  if [[ -f "${STATE_FILE}" ]]; then
    cat "${STATE_FILE}"
  else
    echo "unmounted"
  fi
}

write_mount_state() {
  printf '%s' "$1" >"${STATE_FILE}"
}

cmd_once() {
  if ! anchorusb_is_volume_mounted; then
    echo "volume not mounted: $(anchorusb_mount_point)" >&2
    return 1
  fi
  run_unlock_flow
}

cmd_watch() {
  echo "AnchorUSB mount watcher — volume=$(anchorusb_default_volume_name) poll=${POLL_SECS}s" >&2
  echo "Ctrl-C to stop. Unplug USB to reset trigger." >&2
  local state
  state="$(read_mount_state)"
  if [[ "${ANCHORUSB_TRIGGER_ON_START:-0}" == "1" ]] && anchorusb_is_volume_mounted; then
    run_unlock_flow || true
    state="mounted"
  fi
  while true; do
    if anchorusb_is_volume_mounted; then
      if [[ "${state}" != "mounted" ]]; then
        echo "event: USB mounted at $(anchorusb_mount_point)" >&2
        run_unlock_flow || true
        state="mounted"
        write_mount_state "mounted"
      fi
    else
      if [[ "${state}" == "mounted" ]]; then
        echo "event: USB unmounted" >&2
      fi
      state="unmounted"
      write_mount_state "unmounted"
    fi
    sleep "${POLL_SECS}"
  done
}

main() {
  local cmd="${1:-watch}"
  case "${cmd}" in
    watch) cmd_watch ;;
    once) cmd_once ;;
    status) cmd_status ;;
    -h | --help | help) usage ;;
    *)
      echo "unknown command: ${cmd}" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
