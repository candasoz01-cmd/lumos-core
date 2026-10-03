#!/bin/bash
# SessionStart: install the Claude Code Bash sandbox dependencies
# (bubblewrap, socat) in Claude Code on the web containers (#906, risk 1).
#
# Acts only when every condition holds; otherwise it is a no-op:
#   - Claude Code on the web (CLAUDE_CODE_REMOTE=true)
#   - Linux, running as root, apt-get available
#   - bwrap or socat missing
# Never fails the session: every path exits 0 and reports on stderr.

set -u

log() { echo "session_start_sandbox_deps: $*" >&2; }

main() {
  if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
    return 0
  fi
  if [ "$(uname -s)" != "Linux" ]; then
    return 0
  fi
  if [ "$(id -u)" != "0" ]; then
    log "not root; skipping bubblewrap/socat install"
    return 0
  fi
  if ! command -v apt-get >/dev/null 2>&1; then
    log "apt-get not found; skipping bubblewrap/socat install"
    return 0
  fi

  local missing=()
  command -v bwrap >/dev/null 2>&1 || missing+=(bubblewrap)
  command -v socat >/dev/null 2>&1 || missing+=(socat)
  if [ ${#missing[@]} -eq 0 ]; then
    return 0
  fi

  export DEBIAN_FRONTEND=noninteractive
  if ! timeout 120 apt-get install -y -q --no-install-recommends "${missing[@]}" >/dev/null 2>&1; then
    # Package lists can be empty in a fresh container; refresh once and retry.
    if ! { timeout 120 apt-get update -q >/dev/null 2>&1 \
        && timeout 120 apt-get install -y -q --no-install-recommends "${missing[@]}" >/dev/null 2>&1; }; then
      log "install of ${missing[*]} failed; the Bash sandbox stays unavailable"
      return 0
    fi
  fi

  if command -v bwrap >/dev/null 2>&1 && command -v socat >/dev/null 2>&1; then
    log "installed ${missing[*]}"
  else
    log "install reported success but bwrap/socat are still missing"
  fi
  return 0
}

main || true
exit 0
