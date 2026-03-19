#!/usr/bin/env bash
# Gerçek CF senaryosu: userA↔userB COMMON’da örtüşür; userB’nin SPECIAL_B beğenisi userA feed’inde SPECIAL_B’yi yükseltir.
# Gereksinim: backend ayakta (örn. cd backend && npm run dev). Kişiselleştirme + CF için mutlaka Bearer gerekir — GET /posts/feed değil, GET /posts?order=feed.
set -euo pipefail
BASE="${BASE_URL:-http://127.0.0.1:3000}"
SUFFIX="$(date +%s)"

UA_JSON=$(curl -s -X POST "$BASE/users" -H 'Content-Type: application/json' -d "{\"username\":\"cf_userA_$SUFFIX\"}")
UB_JSON=$(curl -s -X POST "$BASE/users" -H 'Content-Type: application/json' -d "{\"username\":\"cf_userB_$SUFFIX\"}")
TA=$(echo "$UA_JSON" | jq -r '.ratingToken')
TB=$(echo "$UB_JSON" | jq -r '.ratingToken')
AUTH="cf_auth_$SUFFIX"

PC=$(curl -s -X POST "$BASE/posts" -H 'Content-Type: application/json' -d "{\"content\":\"COMMON\",\"username\":\"$AUTH\"}" | jq -r '.id')
PS=$(curl -s -X POST "$BASE/posts" -H 'Content-Type: application/json' -d "{\"content\":\"SPECIAL_B\",\"username\":\"$AUTH\"}" | jq -r '.id')
PR=$(curl -s -X POST "$BASE/posts" -H 'Content-Type: application/json' -d "{\"content\":\"RANDOM\",\"username\":\"$AUTH\"}" | jq -r '.id')

curl -s -X POST "$BASE/posts/$PC/rate" -H "Authorization: Bearer $TA" -H 'Content-Type: application/json' -d '{"value":5}' >/dev/null
curl -s -X POST "$BASE/posts/$PC/rate" -H "Authorization: Bearer $TB" -H 'Content-Type: application/json' -d '{"value":5}' >/dev/null
curl -s -X POST "$BASE/posts/$PS/rate" -H "Authorization: Bearer $TB" -H 'Content-Type: application/json' -d '{"value":5}' >/dev/null

echo "--- Sadece bu üç postun userA (Bearer) feed sırası (ilk = en üst) ---"
curl -s "$BASE/posts?order=feed&limit=500" -H "Authorization: Bearer $TA" \
  | jq --arg a "$PC" --arg b "$PS" --arg c "$PR" '
    [.[] | select(.id == $a or .id == $b or .id == $c) | {content, ratingAvg, ratingCount}]
  '
echo "--- Beklenti: SPECIAL_B, COMMON’dan üstte; RANDOM en altta (oy yok) ---"
