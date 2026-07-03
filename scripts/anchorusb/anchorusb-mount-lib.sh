# shellcheck shell=bash
# AnchorUSB mount helpers — source from poc watcher / tests.

anchorusb_default_volume_name() {
  printf '%s' "${ANCHORUSB_VOLUME_NAME:-NO NAME}"
}

anchorusb_mount_point() {
  printf '/Volumes/%s' "$(anchorusb_default_volume_name)"
}

anchorusb_project_dir_name() {
  printf '%s' "${ANCHORUSB_PROJECT_DIR:-Project_Lumos}"
}

anchorusb_vault_basename() {
  printf '%s' "${ANCHORUSB_VAULT_BASENAME:-AnchorUSB.vault}"
}

# Resolved vault path on the configured USB volume.
anchorusb_vault_path() {
  local mount project base
  mount="$(anchorusb_mount_point)"
  project="$(anchorusb_project_dir_name)"
  base="$(anchorusb_vault_basename)"
  if [[ -n "${ANCHORUSB_VAULT_PATH:-}" ]]; then
    printf '%s' "${ANCHORUSB_VAULT_PATH}"
    return 0
  fi
  printf '%s/%s/%s' "${mount}" "${project}" "${base}"
}

# True when the configured volume directory exists and is a mount point.
anchorusb_is_volume_mounted() {
  local mp
  mp="$(anchorusb_mount_point)"
  [[ -d "${mp}" ]] || return 1
  mount | grep -Fq " on ${mp} "
}

# Human-readable lock banner (terminal).
anchorusb_lock_banner() {
  local mp vault
  mp="$(anchorusb_mount_point)"
  vault="$(anchorusb_vault_path)"
  cat <<EOF

╔══════════════════════════════════════════════════════════════╗
║  AnchorUSB — LOCKED (USB detected)                           ║
║  Volume: ${mp}
║  Vault:  ${vault}
║  Authenticate with Touch ID, then enter vault passphrase.    ║
╚══════════════════════════════════════════════════════════════╝

EOF
}
