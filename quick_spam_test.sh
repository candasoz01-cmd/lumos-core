#!/usr/bin/env bash
set -e
BASE="http://127.0.0.1:3000"
POST_ID=$(curl -s -X POST "$BASE/posts" -H "Content-Type: application/json" -d '{"content":"SPAM_TEST","username":"kando_spam"}' | jq -r '.id')
TOKEN=$(curl -s -X POST "$BASE/users" -H "Content-Type: application/json" -d '{"username":"kando_spam_voter"}' | jq -r '.ratingToken')
for i in 1 2 3 4 5; do
  curl -s -X POST "$BASE/posts/$POST_ID/rate" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"value":5}' | jq .
done
curl -s "$BASE/posts?username=kando_spam&fields=id,ratingAvg,ratingCount,highRatingCount,lowRatingCount" | jq .
