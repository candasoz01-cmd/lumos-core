#!/bin/bash
set -e

BASE_URL="${BASE_URL:-http://localhost:3000}"
RANDOM_USER="kando_$RANDOM"

die() { echo "FAIL: $*" >&2; exit 1; }

# Same-user rating UPDATE may hit 429 "Too fast" (RATE_ENDPOINT_COOLDOWN_MS); retry without weakening limits.
rate_post() {
  local post_id="$1" token="$2" value="$3"
  local attempt=1 max=12 delay=1
  while [[ $attempt -le $max ]]; do
    local resp code
    resp=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/posts/$post_id/rate" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $token" \
      -d "{\"value\":$value}")
    code=$(echo "$resp" | tail -1)
    if [[ "$code" == "200" ]]; then
      return 0
    fi
    if [[ "$code" == "429" ]]; then
      sleep "$delay"
      attempt=$((attempt + 1))
      continue
    fi
    die "rate failed HTTP $code (post=$post_id value=$value): $(echo "$resp" | sed '$d' | head -c 180)"
  done
  die "rate retry exhausted after 429 (post=$post_id value=$value)"
}

expect_http() {
  local code="$1"
  local got="$2"
  local msg="$3"
  [[ "$got" == "$code" ]] || die "$msg (beklenen HTTP $code, gelen: $got)"
}

echo "=== Sunucu: $BASE_URL (BASE_URL ile değiştirilebilir) ==="
echo ""

echo "=== 1) user1, user2 (+ ratingToken) ==="
U1=$(curl -sf -X POST "$BASE_URL/users" -H "Content-Type: application/json" \
  -d "{\"username\":\"${RANDOM_USER}_u1\"}") || die "user1 oluşturulamadı"
U2=$(curl -sf -X POST "$BASE_URL/users" -H "Content-Type: application/json" \
  -d "{\"username\":\"${RANDOM_USER}_u2\"}") || die "user2 oluşturulamadı"
USER1_ID=$(echo "$U1" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
USER2_ID=$(echo "$U2" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
USER1_TOKEN=$(echo "$U1" | grep -o '"ratingToken":"[^"]*"' | head -1 | cut -d'"' -f4)
USER2_TOKEN=$(echo "$U2" | grep -o '"ratingToken":"[^"]*"' | head -1 | cut -d'"' -f4)
[[ -n "$USER1_TOKEN" && -n "$USER2_TOKEN" ]] || die "ratingToken eksik (POST /users yanıtı)"
echo "USER1_ID=$USER1_ID USER2_ID=$USER2_ID"
echo ""

echo "=== 2) postA/postB (UPDATE zinciri) + liste A (yüksek) / liste B (düşük) ==="
echo "    → rated-high odağı: sadece A tipi (POST_LIST_A) | rated-low odağı: sadece B tipi (POST_LIST_B)"
PA=$(curl -sf -X POST "$BASE_URL/posts" -H "Content-Type: application/json" \
  -d "{\"content\":\"postA UPDATE zinciri\",\"userId\":\"$USER1_ID\"}") || die "postA"
PB=$(curl -sf -X POST "$BASE_URL/posts" -H "Content-Type: application/json" \
  -d "{\"content\":\"postB yardımcı\",\"userId\":\"$USER1_ID\"}") || die "postB"
PLA=$(curl -sf -X POST "$BASE_URL/posts" -H "Content-Type: application/json" \
  -d "{\"content\":\"LISTE A — yüksek puan (rated-high)\",\"userId\":\"$USER1_ID\"}") || die "listA"
PLB=$(curl -sf -X POST "$BASE_URL/posts" -H "Content-Type: application/json" \
  -d "{\"content\":\"LISTE B — düşük puan (rated-low)\",\"userId\":\"$USER1_ID\"}") || die "listB"
POST_A=$(echo "$PA" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
POST_B=$(echo "$PB" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
POST_LIST_A=$(echo "$PLA" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
POST_LIST_B=$(echo "$PLB" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "POST_A=$POST_A POST_B=$POST_B | LIST_A=$POST_LIST_A LIST_B=$POST_LIST_B"
echo ""

echo "=== 2b) LISTE A → 5+5 | LISTE B → 1+2 ==="
curl -sf -X POST "$BASE_URL/posts/$POST_LIST_A/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER1_TOKEN" -d "{\"value\":5}" >/dev/null
curl -sf -X POST "$BASE_URL/posts/$POST_LIST_A/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER2_TOKEN" -d "{\"value\":5}" >/dev/null
curl -sf -X POST "$BASE_URL/posts/$POST_LIST_B/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER1_TOKEN" -d "{\"value\":1}" >/dev/null
curl -sf -X POST "$BASE_URL/posts/$POST_LIST_B/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER2_TOKEN" -d "{\"value\":2}" >/dev/null
echo "OK A yüksek / B düşük (B tamamı 1–2★)"
echo ""

echo "=== 3) postA: user1 → 5, user2 → 1 (baz 3.0) ==="
curl -sf -X POST "$BASE_URL/posts/$POST_A/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER1_TOKEN" -d "{\"value\":5}" >/dev/null || die "rate u1→5"
curl -sf -X POST "$BASE_URL/posts/$POST_A/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER2_TOKEN" -d "{\"value\":1}" >/dev/null || die "rate u2→1"
echo "OK"
echo ""

echo "=== 3b) GET — postA ratingCount=2, ratingAvg=3.0 ==="
node <<NODE
(async () => {
  const posts = await (await fetch("${BASE_URL}/posts")).json();
  const a = posts.find((p) => p.id === "${POST_A}");
  if (!a || a.ratingCount !== 2 || Math.abs(a.ratingAvg - 3) > 0.01) process.exit(1);
  console.log("OK baz: 2 oy, ortalama 3.0");
})();
NODE
echo ""

echo "=== 3c) AYNI USER (user1: 5→4) — UPDATE ==="
rate_post "$POST_A" "$USER1_TOKEN" 4 || die "rate u1 UPDATE 5→4"
echo "OK"
echo ""

echo "=== 3d) GET — ratingCount=2, ratingAvg=2.5 ==="
node <<NODE
(async () => {
  const a = (await (await fetch("${BASE_URL}/posts")).json()).find((p) => p.id === "${POST_A}");
  if (a.ratingCount !== 2 || Math.abs(a.ratingAvg - 2.5) > 0.01) process.exit(1);
  console.log("OK UPDATE: count sabit 2, avg 2.5");
})();
NODE
echo ""

echo "=== 4) postB: her iki user → 5 ==="
curl -sf -X POST "$BASE_URL/posts/$POST_B/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER1_TOKEN" -d "{\"value\":5}" >/dev/null
curl -sf -X POST "$BASE_URL/posts/$POST_B/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER2_TOKEN" -d "{\"value\":5}" >/dev/null
echo "OK"
echo ""

echo "=== 5) GET — postA avg 2.5, postB avg 5 ==="
export BASE_URL POST_A POST_B
node <<'NODE'
const base = process.env.BASE_URL;
const POST_A = process.env.POST_A;
const POST_B = process.env.POST_B;
(async () => {
  const posts = await (await fetch(`${base}/posts`)).json();
  const a = posts.find((p) => p.id === POST_A);
  const b = posts.find((p) => p.id === POST_B);
  for (const k of ["ratingCount", "ratingAvg", "lowRatingCount", "highRatingCount"]) {
    if (!(k in a) || !(k in b)) throw new Error("eksik alan: " + k);
  }
  if (a.ratingCount !== 2 || Math.abs(a.ratingAvg - 2.5) > 0.01) process.exit(1);
  if (b.ratingCount !== 2 || Math.abs(b.ratingAvg - 5) > 0.01) process.exit(1);
  console.log("OK listeleme alanları + postA 2.5 / postB 5.0");
})();
NODE
echo ""

echo "=== 6) user2 postA: 1→4 (UPDATE, avg 4) ==="
rate_post "$POST_A" "$USER2_TOKEN" 4 || die "rate u2 UPDATE 1→4"
node <<NODE
(async () => {
  const a = (await (await fetch("${BASE_URL}/posts")).json()).find((p) => p.id === "${POST_A}");
  if (a.ratingCount !== 2 || Math.abs(a.ratingAvg - 4) > 0.01) process.exit(1);
  console.log("OK user2 UPDATE: count=2 avg=4");
})();
NODE
echo ""

echo "=== 7) Auth / validation ==="
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/posts/$POST_A/rate" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $USER1_TOKEN" \
  -d "{\"value\":6}")
expect_http 400 "$CODE" "value=6"
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/posts/$POST_A/rate" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $USER1_TOKEN" \
  -d "{\"value\":0}")
expect_http 400 "$CODE" "value=0"

echo "=== HATALI VALUE (string abc) ==="
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/posts/$POST_A/rate" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $USER1_TOKEN" \
  -d "{\"value\":\"abc\"}")
expect_http 400 "$CODE" 'value="abc"'

echo "=== Bearer yok → 401 ==="
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/posts/$POST_A/rate" \
  -H "Content-Type: application/json" -d "{}")
expect_http 401 "$CODE" "Bearer yok"

echo "=== body'de userId (manipülasyon) → 400 ==="
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/posts/$POST_A/rate" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $USER1_TOKEN" \
  -d "{\"userId\":\"$USER2_ID\",\"value\":5}")
expect_http 400 "$CODE" "userId body yasak"

echo "=== Bearer + value eksik → 400 ==="
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/posts/$POST_A/rate" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $USER1_TOKEN" \
  -d "{}")
expect_http 400 "$CODE" "value eksik"

echo "=== Geçersiz token → 401 ==="
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/posts/$POST_A/rate" \
  -H "Content-Type: application/json" -H "Authorization: Bearer invalidtokenxxxxxxxx" \
  -d "{\"value\":3}")
expect_http 401 "$CODE" "geçersiz token"

echo "OK auth + validation kodları"
echo ""

echo "=== 7b) Burst: aynı user+post 4 yazma / 10s → 4. 429 ==="
PBURST=$(curl -sf -X POST "$BASE_URL/posts" -H "Content-Type: application/json" \
  -d "{\"content\":\"burst test\",\"userId\":\"$USER1_ID\"}") || die "post burst"
POST_BURST=$(echo "$PBURST" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
rate_post "$POST_BURST" "$USER1_TOKEN" 1 || die "burst rate 1"
rate_post "$POST_BURST" "$USER1_TOKEN" 2 || die "burst rate 2"
rate_post "$POST_BURST" "$USER1_TOKEN" 3 || die "burst rate 3"
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/posts/$POST_BURST/rate" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $USER1_TOKEN" \
  -d "{\"value\":4}")
expect_http 429 "$CODE" "4. rating burst"

echo "OK burst 429"
echo ""

echo "=== 8) ÜRÜN: user1→5, user2→1, user2 tekrar→5 | count=2, ortalama yükselir ==="
PP=$(curl -sf -X POST "$BASE_URL/posts" -H "Content-Type: application/json" \
  -d "{\"content\":\"ürün senaryosu u2 puan değişimi\",\"userId\":\"$USER1_ID\"}") || die "post prod"
POST_P=$(echo "$PP" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
curl -sf -X POST "$BASE_URL/posts/$POST_P/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER1_TOKEN" -d "{\"value\":5}" >/dev/null
curl -sf -X POST "$BASE_URL/posts/$POST_P/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER2_TOKEN" -d "{\"value\":1}" >/dev/null
node <<NODE
(async () => {
  const p = (await (await fetch("${BASE_URL}/posts")).json()).find((x) => x.id === "${POST_P}");
  if (p.ratingCount !== 2 || Math.abs(p.ratingAvg - 3) > 0.01) process.exit(1);
  console.log("OK ara: 2 oy, avg 3.0");
})();
NODE
rate_post "$POST_P" "$USER2_TOKEN" 5 || die "rate u2 UPDATE 1→5"
node <<NODE
(async () => {
  const p = (await (await fetch("${BASE_URL}/posts")).json()).find((x) => x.id === "${POST_P}");
  if (p.ratingCount !== 2) {
    console.error("FAIL ratingCount beklenen 2, gelen", p.ratingCount);
    process.exit(1);
  }
  if (Math.abs(p.ratingAvg - 5) > 0.01) {
    console.error("FAIL ratingAvg beklenen 5.0 (5+5)/2, gelen", p.ratingAvg);
    process.exit(1);
  }
  console.log("OK ürün: ratingCount=2 (değişmedi), ratingAvg 3→5 (user2: 1→5 UPDATE)");
})();
NODE
echo ""

echo "=== 9) rated-high — A (yüksek) B’den önce; B bu listede anlamlı şekilde geride ==="
node <<NODE
(async () => {
  const base = "${BASE_URL}";
  const A = "${POST_LIST_A}";
  const B = "${POST_LIST_B}";
  const list = await (await fetch(base + "/posts/rated-high?minVotes=2&limit=100")).json();
  const iA = list.findIndex((p) => p.id === A);
  const iB = list.findIndex((p) => p.id === B);
  if (iA < 0) throw new Error("rated-high: A (yüksek) listede yok");
  if (iB < 0) throw new Error("rated-high: B referans için listede yok");
  if (iA >= iB) throw new Error("rated-high: A ortalaması B’den yüksek → A önce gelmeli");
  console.log("OK rated-high: A önde (yüksek puan odağı)");
})();
NODE
echo ""

echo "=== 10) rated-low — B (düşük yoğunluk) A’dan önce ==="
node <<NODE
(async () => {
  const base = "${BASE_URL}";
  const A = "${POST_LIST_A}";
  const B = "${POST_LIST_B}";
  const list = await (await fetch(base + "/posts/rated-low?minVotes=2&limit=100")).json();
  const iA = list.findIndex((p) => p.id === A);
  const iB = list.findIndex((p) => p.id === B);
  if (iA < 0 || iB < 0) throw new Error("rated-low: A veya B listede yok");
  if (iB >= iA) throw new Error("rated-low: B (1–2★ yoğun) A’dan önce gelmeli");
  console.log("OK rated-low: B önde (düşük puan odağı)");
})();
NODE
echo ""

echo "=== 11) DELETE + rating: silinen post rated-high / rated-low’da YOK ==="
PD=$(curl -sf -X POST "$BASE_URL/posts" -H "Content-Type: application/json" \
  -d "{\"content\":\"silinince listelerden düşmeli\",\"userId\":\"$USER1_ID\"}") || die "post del"
POST_DEL=$(echo "$PD" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
curl -sf -X POST "$BASE_URL/posts/$POST_DEL/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER1_TOKEN" -d "{\"value\":5}" >/dev/null
curl -sf -X POST "$BASE_URL/posts/$POST_DEL/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER2_TOKEN" -d "{\"value\":5}" >/dev/null
curl -sf -X DELETE "$BASE_URL/posts/$POST_DEL" >/dev/null || die "soft delete"
node <<NODE
(async () => {
  const base = "${BASE_URL}";
  const id = "${POST_DEL}";
  const high = await (await fetch(base + "/posts/rated-high?minVotes=1&limit=200")).json();
  const low = await (await fetch(base + "/posts/rated-low?minVotes=2&limit=200")).json();
  if (high.some((p) => p.id === id)) throw new Error("FAIL: silinen post rated-high’da göründü");
  if (low.some((p) => p.id === id)) throw new Error("FAIL: silinen post rated-low’da göründü");
  console.log("OK silinen post iki listede de yok (rated-high + rated-low)");
})();
NODE
echo ""

echo "=== 12) DELETE / TRASH / RESTORE (postA) ==="
curl -sf -X DELETE "$BASE_URL/posts/$POST_A" >/dev/null
curl -sf "$BASE_URL/posts/trash" >/dev/null
curl -sf -X PATCH "$BASE_URL/posts/$POST_A/restore" >/dev/null
echo "OK"
echo ""

echo "=== 13) GET /posts?order=feed — iyi puan üstte, kötü altta, yeni nötr üstte değil en alt ==="
PFEED_BAD=$(curl -sf -X POST "$BASE_URL/posts" -H "Content-Type: application/json" \
  -d "{\"content\":\"FEED_BAD düşük puan\",\"userId\":\"$USER1_ID\"}") || die "feed bad"
ID_BAD=$(echo "$PFEED_BAD" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
curl -sf -X POST "$BASE_URL/posts/$ID_BAD/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER1_TOKEN" -d "{\"value\":1}" >/dev/null
curl -sf -X POST "$BASE_URL/posts/$ID_BAD/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER2_TOKEN" -d "{\"value\":1}" >/dev/null
PFEED_GOOD=$(curl -sf -X POST "$BASE_URL/posts" -H "Content-Type: application/json" \
  -d "{\"content\":\"FEED_GOOD yüksek puan\",\"userId\":\"$USER1_ID\"}") || die "feed good"
ID_GOOD=$(echo "$PFEED_GOOD" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
curl -sf -X POST "$BASE_URL/posts/$ID_GOOD/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER1_TOKEN" -d "{\"value\":5}" >/dev/null
curl -sf -X POST "$BASE_URL/posts/$ID_GOOD/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER2_TOKEN" -d "{\"value\":5}" >/dev/null
PFEED_NEW=$(curl -sf -X POST "$BASE_URL/posts" -H "Content-Type: application/json" \
  -d "{\"content\":\"FEED_NEW oy yok\",\"userId\":\"$USER1_ID\"}") || die "feed new"
ID_NEW=$(echo "$PFEED_NEW" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
node <<NODE
(async () => {
  const base = "${BASE_URL}";
  const bad = "${ID_BAD}";
  const good = "${ID_GOOD}";
  const neu = "${ID_NEW}";
  const feed = await (await fetch(base + "/posts?order=feed&limit=500")).json();
  const idx = (id) => feed.findIndex((p) => p.id === id);
  const iBad = idx(bad);
  const iGood = idx(good);
  const iNeu = idx(neu);
  if (iBad < 0 || iGood < 0 || iNeu < 0) throw new Error("feed: üç posttan biri listede yok");
  if (iGood >= iBad) throw new Error("iyi puanlı, kötü puanlıdan üstte olmalı");
  if (iNeu >= iBad) throw new Error("yeni (nötr) kötü puanlıdan üstte olmalı");
  if (iGood >= iNeu) throw new Error("yüksek puanlı, yeni nötrden üstte olmalı");
  console.log("OK feed: GOOD > NEW > BAD (sıra)");
})();
NODE

echo "=== 13b) yaş çürümesi: 5★ ama ~4 gün eski, yeni 4★ üstte ==="
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
PDEC_OLD=$(curl -sf -X POST "$BASE_URL/posts" -H "Content-Type: application/json" \
  -d "{\"content\":\"DECAY eski süper yıldız\",\"userId\":\"$USER1_ID\"}") || die "decay old"
ID_DECAY_OLD=$(echo "$PDEC_OLD" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
curl -sf -X POST "$BASE_URL/posts/$ID_DECAY_OLD/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER1_TOKEN" -d "{\"value\":5}" >/dev/null
curl -sf -X POST "$BASE_URL/posts/$ID_DECAY_OLD/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER2_TOKEN" -d "{\"value\":5}" >/dev/null
( cd "$REPO_ROOT/backend" && DATABASE_URL="${DATABASE_URL:-file:./prisma/dev.db}" node -e "
const { PrismaClient } = require('@prisma/client');
(async () => {
  const id = process.argv[1];
  const prisma = new PrismaClient();
  await prisma.post.update({
    where: { id },
    data: { createdAt: new Date(Date.now() - 100 * 3600000) },
  });
  await prisma.\$disconnect();
})().catch((e) => { console.error(e); process.exit(1); });
" "$ID_DECAY_OLD" ) || die "Prisma createdAt geri alınamadı (backend/.env DATABASE_URL?)"
PDEC_NEW=$(curl -sf -X POST "$BASE_URL/posts" -H "Content-Type: application/json" \
  -d "{\"content\":\"DECAY taze 4 yıldız\",\"userId\":\"$USER1_ID\"}") || die "decay new"
ID_DECAY_NEW=$(echo "$PDEC_NEW" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
curl -sf -X POST "$BASE_URL/posts/$ID_DECAY_NEW/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER1_TOKEN" -d "{\"value\":4}" >/dev/null
curl -sf -X POST "$BASE_URL/posts/$ID_DECAY_NEW/rate" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER2_TOKEN" -d "{\"value\":4}" >/dev/null
node <<NODE
(async () => {
  const feed = await (await fetch("${BASE_URL}/posts?order=feed&limit=500")).json();
  const iOld = feed.findIndex((p) => p.id === "${ID_DECAY_OLD}");
  const iNew = feed.findIndex((p) => p.id === "${ID_DECAY_NEW}");
  if (iOld < 0 || iNew < 0) throw new Error("decay test: post feed'de yok");
  if (iNew >= iOld)
    throw new Error("yeni 4★, yaşlı 5★ üstünde olmalı (time decay)");
  console.log("OK decay: yeni 4★ > eski 5★ (sıra)");
})();
NODE

PFEED_DEL=$(curl -sf -X POST "$BASE_URL/posts" -H "Content-Type: application/json" \
  -d "{\"content\":\"FEED silinecek\",\"userId\":\"$USER1_ID\"}") || die "feed del"
ID_FEED_DEL=$(echo "$PFEED_DEL" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
curl -sf -X DELETE "$BASE_URL/posts/$ID_FEED_DEL" >/dev/null
node <<NODE
(async () => {
  const feed = await (await fetch("${BASE_URL}/posts?order=feed&limit=500")).json();
  if (feed.some((p) => p.id === "${ID_FEED_DEL}")) throw new Error("FAIL: silinen post feed'de");
  console.log("OK feed: soft delete yok");
})();
NODE
echo ""

echo "=== TÜM RATING DOĞRULAMALARI GEÇTİ ==="
echo "(Bearer; burst; feed; A/B listeleri; silinen post listelerde/feed'de yok)"
