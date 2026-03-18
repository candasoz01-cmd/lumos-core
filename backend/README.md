# Backend (Express + Prisma + SQLite)

## HTTP güvenlik başlıkları (Helmet)

- **[helmet](https://github.com/helmetjs/helmet)** (MIT): `X-Content-Type-Options`, `X-DNS-Prefetch-Control`, `X-Download-Options`, `X-Frame-Options`, `X-Permitted-Cross-Domain-Policies`, `Strict-Transport-Security` (HTTPS’te), `Origin-Agent-Cluster` vb.
- **CSP kapalı:** API yalnızca JSON döndürür; CSP HTML sayfaları içindir.
- **Cross-Origin-Resource-Policy: cross-origin:** Mevcut `Access-Control-Allow-Origin: *` ile panel/tarayıcı çapraz köken isteklerinin bozulmaması için (varsayılan `same-origin` bazı istemcilerde çakışabilir).

## Setup

```bash
cd backend
npm install
echo 'DATABASE_URL="file:./prisma/dev.db"' > .env
npx prisma generate
npx prisma db push
npm start
```

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | /users | Create user `{ "username": "alice" }` |
| POST | /posts | Create post `{ "content": "...", "userId": "..." }` |
| GET | /posts | List non-deleted posts, **createdAt desc** (+ rating özetleri) |
| GET | /posts/feed | **feedScore** = `ratingAvg×1.2 + ln(ratingCount+1)` + taze (**+3** / 2 saat) − `ageInHours×0.4`. Env: `FEED_AVG_MULTIPLIER`, `FEED_TIME_DECAY_PER_H` (eski ad: `FEED_AGE_PENALTY_PER_H`), `FEED_FRESH_BOOST`, `FEED_FRESH_HOURS`. |
| GET | /posts/rated-high | İyi postlar: yüksek ortalama (`minVotes`, `limit`) |
| GET | /posts/rated-low | Kötü postlar: 1–2 yıldız oranı yüksek (`minVotes`≥2, `limit`) |
| DELETE | /posts/:id | Soft delete post |
| GET | /posts/trash | Deleted posts |
| PATCH | /posts/:id/restore | Restore post |
| POST | /posts/:id/rate | Header `Authorization: Bearer <ratingToken>` (POST /users yanıtındaki `ratingToken`) + body `{ "value": 1–5 }`. Body’de `userId` **kabul edilmez**. Aynı kullanıcı aynı postta **günceller** (yeni satır yok). |

**Güvenlik / abuse (küçük ölçek):** Geçersiz veya eksik Bearer → 401. Aynı kullanıcı + aynı post için varsayılan **10 saniyede en fazla 3** başarılı yazma → 429 (`RATING_BURST_WINDOW_MS`, `RATING_BURST_MAX`).

### Post cevabında rating alanları

- **ratingCount** — oy sayısı  
- **ratingAvg** — ortalama (1 ondalık, oy yoksa `null`)  
- **lowRatingCount** — 1 ve 2 yıldız  
- **highRatingCount** — 4 ve 5 yıldız  

UI örneği: `⭐ 4.3` + `(27 oy)` → `ratingAvg` + `ratingCount`.

Ürün kartı ↔ API alan eşlemesi: **`docs/kando-post-feed-contract.md`** (`pickPostCardProps` → `examples/kando-post-card.jsx`).

### POST /posts/:id/rate cevabı

`rating` satırı + güncel `ratingCount`, `ratingAvg`, `lowRatingCount`, `highRatingCount` (o post için).

Server: http://localhost:3000 (veya `PORT`).

## API smoke test

Repo kökünden; **önce** `backend` içinde `npm start` (veya `PORT` ile). İsteğe bağlı: `BASE_URL=http://127.0.0.1:3000 ./test_api.sh`.

Adım **13b** (yaş çürümesi) Prisma ile `createdAt` günceller; `backend/.env` içindeki `DATABASE_URL` ile aynı DB’ye yazılır (varsayılan `file:./prisma/dev.db`).

```bash
./test_api.sh
# veya: make test-api
```
