# Backend (Express + Prisma + SQLite)

## HTTP güvenlik başlıkları (Helmet)

Helmet middleware eklendi (basic security headers).

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
| GET | /health | Sağlık: 200 + `{ ok, checkpoints }`. Tam kontrol için checkpoint’lere GET atılır — bkz. `docs/STABILIZASYON_LISTESI.md`. |
| POST | /users | Create user `{ "username": "alice" }` |
| POST | /posts | Create post `{ "content": "...", "userId": "..." }` |
| GET | /posts | List non-deleted posts (+ rating özetleri). **`order=feed`** → feed sıralaması (taban skor + isteğe bağlı kişisel/CF için **`Authorization: Bearer <ratingToken>`**). Kimlik yoksa yalnızca taban sıralama. `limit` / `offset` ile sayfalama. Env: `FEED_*`, `FEED_COLLAB_*`. |
| GET | /posts/feed | **Kullanımdan kaldırıldı:** **410** + `message: use /posts?order=feed` — bunun yerine **`GET /posts?order=feed`** kullanın. |
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

## Lark persistent connection

Lark bot ayrı bir süreç olarak çalışır; webhook, Redirect URL veya public callback gerektirmez.
App Secret repoya yazılmaz.

Gerekli Lark uygulama ayarları:

- Bot capability: etkin
- Event subscription: **Persistent Connection**
- Event: `im.message.receive_v1`
- Tenant scopes:
  - `im:message.p2p_msg:readonly`
  - `im:message.group_at_msg:readonly`
  - `im:message:send_as_bot`
- Redirect URLs: OAuth eklenene kadar boş

Çalıştırma:

```bash
export LARK_APP_ID="cli_..."
export LARK_APP_SECRET="..."
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-5.6-terra"
npm run lark:start
```

Hazır bir Lumos sohbet uç noktası varsa `OPENAI_API_KEY` yerine
`LUMOS_CHAT_URL="http://127.0.0.1:3000/chat"` kullanılabilir. İki değer birlikte
verilirse öncelik Lumos sohbet uç noktasındadır. Anahtarlar repoya veya loglara
yazılmaz.

IP allowlist isteğe bağlıdır. Etkinleştirilirse Lark API çağrılarının yapıldığı Lumos
sunucusunun sabit dış çıkış IP'si eklenir; Cloudflare proxy IP'leri eklenmez.

## API smoke test

Repo kökünden; **önce** `backend` içinde `npm start` (veya `PORT` ile). İsteğe bağlı: `BASE_URL=http://127.0.0.1:3000 ./test_api.sh`.

Adım **13b** (yaş çürümesi) Prisma ile `createdAt` günceller; `backend/.env` içindeki `DATABASE_URL` ile aynı DB’ye yazılır (varsayılan `file:./prisma/dev.db`).

```bash
./test_api.sh
# veya: make test-api
```
