#!/usr/bin/env bash
# Infisical self-host PoC — read-only health check (env-gated, no secrets in repo).
set -euo pipefail

cd "$(dirname "$0")/.."

URL="${LUMOS_VAULT_URL:-}"
TOKEN="${LUMOS_VAULT_TOKEN:-}"

if [ -z "$URL" ] || [ -z "$TOKEN" ]; then
  echo "FAIL: LUMOS_VAULT_URL and LUMOS_VAULT_TOKEN must be set in environment."
  echo "Hint: export from operator secret store — never commit values."
  exit 1
fi

BASE="${URL%/}"
STATUS_URL="${BASE}/api/status"

HTTP_CODE=$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${STATUS_URL}" || true)

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
  echo "OK: Infisical reachable at ${BASE} (HTTP ${HTTP_CODE})"
  exit 0
fi

echo "FAIL: Infisical health check returned HTTP ${HTTP_CODE} for ${STATUS_URL}"
exit 1
