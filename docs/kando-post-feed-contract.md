# Post kartı ↔ backend akış veri sözleşmesi

**Amaç:** `KandoPostCard` ile `GET /posts`, `GET /posts/feed` (ve aynı `serializePost` şeklini kullanan `rated-high` / `rated-low`) cevabını hizalamak.

## Ortak post JSON şekli (liste / feed)

Backend her post için Prisma `Post` + rating özetlerini birleştirir (`serializePost`).

| Alan | Tip | Kartta kullanım |
|------|-----|-----------------|
| `id` | string | Liste anahtarı (`key`); kart içeriği değil |
| `content` | string | Gövde metni |
| `createdAt` | string (ISO 8601) | Göreli zaman |
| `userId` | string | Kartta kullanılmaz (isteğe bağlı üst katman) |
| `user` | `{ username }` | Kartta kullanılmaz |
| `deletedAt` | null \| string | Listelerde silinmişler yok; trash ayrı endpoint |
| `ratingCount` | number | Oy sayısı |
| `ratingAvg` | number \| null | Ortalama (1 ondalık); oy yoksa `null` |
| `lowRatingCount` | number | Kartta kullanılmaz |
| `highRatingCount` | number | Kartta kullanılmaz |

## Sadece `GET /posts/feed` ek alanı

| Alan | Tip | Not |
|------|-----|-----|
| `feedScore` | number | Sıralama skoru; **UI’da gösterilmez**, karta verilmez |

## Karta bağlama

Kart yalnızca şu dört alanı bekler: `content`, `ratingAvg`, `ratingCount`, `createdAt`.

Örnek kod: `pickPostCardProps(post)` → `examples/kando-post-card.jsx`.

```jsx
<KandoPostCard key={post.id} {...pickPostCardProps(post)} />
```

## Endpoint farkı (ürün kararı)

- **`GET /posts`** — `createdAt` azalan; kronolojik “tüm akış”.
- **`GET /posts/feed?limit=…`** — `feedScore` ile sıralı; ürün feed’i için tipik kaynak.

İkisi de aynı post nesnesi şeklini paylaşır (feed’de ekstra `feedScore`).

## Referans

- Serileştirme: `backend/index.js` — `serializePost`, `getRatingStatsMap`
- API özeti: `backend/README.md`
