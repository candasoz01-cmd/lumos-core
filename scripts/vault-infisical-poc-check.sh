#!/usr/bin/env bash
# Infisical self-host PoC — health check + optional env-gated secret read (no secrets in repo).
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

if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "204" ]; then
  echo "FAIL: Infisical health check returned HTTP ${HTTP_CODE} for ${STATUS_URL}"
  exit 1
fi

echo "OK: Infisical reachable at ${BASE} (HTTP ${HTTP_CODE})"

PROJECT="${LUMOS_VAULT_PROJECT:-}"
ENV_SLUG="${LUMOS_VAULT_ENV:-}"
TEST_REF="${LUMOS_VAULT_TEST_REF:-}"
SECRET_PATH="${LUMOS_VAULT_SECRET_PATH:-/integrations/mail}"

if [ -z "$PROJECT" ] || [ -z "$ENV_SLUG" ] || [ -z "$TEST_REF" ]; then
  echo "SKIP: secret read step (set LUMOS_VAULT_PROJECT, LUMOS_VAULT_ENV, LUMOS_VAULT_TEST_REF to enable)"
  exit 0
fi

ENCODED_REF=$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$TEST_REF")
SECRET_URL="${BASE}/api/v3/secrets/raw/${ENCODED_REF}?workspaceId=${PROJECT}&environment=${ENV_SLUG}&secretPath=${SECRET_PATH}"

SECRET_HTTP=$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${SECRET_URL}" || true)

if [ "$SECRET_HTTP" = "200" ]; then
  echo "OK: secret read probe succeeded for ref ${TEST_REF} (value not printed)"
  exit 0
fi

echo "FAIL: secret read probe returned HTTP ${SECRET_HTTP} for ref ${TEST_REF}"
exit 1
