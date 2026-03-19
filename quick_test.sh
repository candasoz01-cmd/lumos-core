#!/usr/bin/env bash
set -e
BASE="http://127.0.0.1:3000"
echo "1) health"
curl -s "$BASE/health" | jq .
echo
echo "2) create post with username"
CREATE_RESP=$(curl -s -X POST "$BASE/posts" -H "Content-Type: application/json" -d '{"content":"OTOMATIK_TEST_POST","username":"kando_otomatik"}')
echo "$CREATE_RESP" | jq .
POST_ID=$(echo "$CREATE_RESP" | jq -r '.id')
echo
echo "3) list by username"
curl -s "$BASE/posts?username=kando_otomatik&order=desc&limit=5" | jq .
echo
echo "4) delete post"
curl -s -X DELETE "$BASE/posts/$POST_ID" | jq .
echo
echo "5) restore post"
curl -s -X PATCH "$BASE/posts/$POST_ID/restore" | jq .
echo
echo "6) filtered list"
curl -s "$BASE/posts?username=kando_otomatik&fields=id,content,user,createdAt,ratingAvg,ratingCount&limit=5" | jq .
echo
echo "DONE"
