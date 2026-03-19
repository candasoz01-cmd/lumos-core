#!/usr/bin/env bash
set -e
BASE="http://127.0.0.1:3000"
U="kando_feed_case_$(date +%s)"

P1=$(curl -s -X POST "$BASE/posts" -H 'Content-Type: application/json' -d "{\"content\":\"FEED_LOW\",\"username\":\"$U\"}" | jq -r '.id')
P2=$(curl -s -X POST "$BASE/posts" -H 'Content-Type: application/json' -d "{\"content\":\"FEED_HIGH\",\"username\":\"$U\"}" | jq -r '.id')

T1=$(curl -s -X POST "$BASE/users" -H 'Content-Type: application/json' -d "{\"username\":\"${U}_v1\"}" | jq -r '.ratingToken')
T2=$(curl -s -X POST "$BASE/users" -H 'Content-Type: application/json' -d "{\"username\":\"${U}_v2\"}" | jq -r '.ratingToken')

curl -s -X POST "$BASE/posts/$P1/rate" -H "Authorization: Bearer $T1" -H 'Content-Type: application/json' -d '{"value":1}' >/dev/null
curl -s -X POST "$BASE/posts/$P2/rate" -H "Authorization: Bearer $T1" -H 'Content-Type: application/json' -d '{"value":5}' >/dev/null
curl -s -X POST "$BASE/posts/$P2/rate" -H "Authorization: Bearer $T2" -H 'Content-Type: application/json' -d '{"value":5}' >/dev/null

echo "$U"
curl -s "$BASE/posts?username=$U&order=feed&fields=content,ratingAvg,ratingCount,highRatingCount,lowRatingCount" | jq .
#!/usr/bin/env bash
set -e
BASE="http://127.0.0.1:3000"
U="kando_feed_case_$(date +%s)"

P1=$(curl -s -X POST "$BASE/posts" -H 'Content-Type: application/json' -d "{\"content\":\"FEED_LOW\",\"username\":\"$U\"}" | jq -r '.id')
P2=$(curl -s -X POST "$BASE/posts" -H 'Content-Type: application/json' -d "{\"content\":\"FEED_HIGH\",\"username\":\"$U\"}" | jq -r '.id')

T1=$(curl -s -X POST "$BASE/users" -H 'Content-Type: application/json' -d "{\"username\":\"${U}_v1\"}" | jq -r '.ratingToken')
T2=$(curl -s -X POST "$BASE/users" -H 'Content-Type: application/json' -d "{\"username\":\"${U}_v2\"}" | jq -r '.ratingToken')

curl -s -X POST "$BASE/posts/$P1/rate" -H "Authorization: Bearer $T1" -H 'Content-Type: application/json' -d '{"value":1}' >/dev/null
curl -s -X POST "$BASE/posts/$P2/rate" -H "Authorization: Bearer $T1" -H 'Content-Type: application/json' -d '{"value":5}' >/dev/null
curl -s -X POST "$BASE/posts/$P2/rate" -H "Authorization: Bearer $T2" -H 'Content-Type: application/json' -d '{"value":5}' >/dev/null

echo "$U"
curl -s "$BASE/posts?username=$U&order=feed&fields=content,ratingAvg,ratingCount,highRatingCount,lowRatingCount" | jq .
