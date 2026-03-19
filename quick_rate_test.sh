#!/usr/bin/env bash
set -e
BASE="http://127.0.0.1:3000"

echo "1) create post"
CREATE_RESP=$(curl -s -X POST "$BASE/posts" -H "Content-Type: application/json" -d '{"content":"RATE_TEST_POST","username":"kando_rate_test"}')
echo "$CREATE_RESP" | jq .
POST_ID=$(echo "$CREATE_RESP" | jq -r '.id')

echo
echo "2) get rating token"
TOKEN=$(curl -s -X POST "$BASE/users" -H "Content-Type: application/json" -d '{"username":"kando_rate_voter"}' | jq -r '.ratingToken')
echo "$TOKEN"

echo
echo "3) rate 5"
curl -s -X POST "$BASE/posts/$POST_ID/rate" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"value":5}' | jq .

echo
echo "4) rate 1"
curl -s -X POST "$BASE/posts/$POST_ID/rate" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"value":1}' | jq .

echo
echo "5) get by username"
curl -s "$BASE/posts?username=kando_rate_test&fields=id,content,user,ratingAvg,ratingCount&limit=5" | jq .

echo
echo "6) minRating=3"
curl -s "$BASE/posts?username=kando_rate_test&minRating=3&fields=id,content,ratingAvg,ratingCount" | jq .

echo
echo "DONE"
