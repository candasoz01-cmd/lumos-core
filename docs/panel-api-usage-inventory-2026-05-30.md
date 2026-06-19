# Panel / Frontend Backend API Kullanım Envanteri (2026-05-30)

Salt okuma taraması. Kodda değişiklik yapılmadı. Aranan kalıplar: `fetch(`, `axios`, `localhost:3000`, `/posts`, `/health`, `API_BASE`, `BASE_URL`, `/posts/feed`, `order=feed`. `node_modules` ve `dist` hariç tutuldu.

## Özet: Backend grupları

Panel üç ayrı backend tabanına konuşuyor:

1. **Posts/Feed API (port 3000)** — `panel/js/feed-api.js` (uzak backend bunu hedefliyor).
2. **Tasks / Trash action API (port 8766)** — `panel/js/app.js`, `frontend/index.html` (yerel köprü/görev sunucusu).
3. **Chat / Bridge / Upload / Health / Status** — `ui/src/pages/panel.astro` (Astro `import.meta.env` ile).

---

## 1. panel/js/feed-api.js — Posts/Feed API (port 3000)

Base çözümü (satır 9-29):

- `window.LUMOS_POSTS_API_BASE` → varsa
- `localStorage.lumos_posts_api_base` → varsa
- aksi halde `DEFAULT_BASE = "http://127.0.0.1:3000"`

Kullanılan endpointler:

| Endpoint | Metot | Satır |
|---|---|---|
| `/posts?order=feed&limit=N` | GET | 274 |
| `/posts/rated-high?limit=N` | GET | 286 |
| `/posts/rated-low?limit=N` | GET | 292 |
| `/posts/{id}/rate-high` | POST | 295 |
| `/posts/{id}/rate-low` | POST | 298 |
| `/posts/{id}/trash` | POST | 301, 304 |
| `/posts/{id}/restore` | POST | 307 |
| `/posts/{id}` | DELETE | 310 |
| `/posts/trash` | GET | 318, 345 |

Feed için **doğru** kullanım (`/posts?order=feed`) mevcut. Deprecated `/posts/feed` çağrısı **yok**.

## 2. panel/js/app.js — Tasks / Trash / Feed tüketimi

- `TASKS_API_BASE = "http://127.0.0.1:8766"` (satır 419); override: `window.LUMOS_PANEL_TASKS_API_BASE` (satır 443-461). `=== false` ise tam çevrimdışı.
- Tasks endpointleri: `/tasks` (607), `/tasks.json` (474-475), `/tasks/complete` (4668), `/tasks/delete` (4710), `/tasks/restore` & `/tasks/delete-permanent` (3580-3590).
- Trash action base: `window.LUMOS_PANEL_TRASH_ACTION_API_BASE`, varsayılan `http://127.0.0.1:8766` (satır 3516-3520).
- Feed sekmesi `feed-api.js` (F.*) üzerinden okur (satır 5093-5120); posts tabanını ayrıca sabit kodlamaz.

## 3. ui/src/pages/panel.astro — env tabanlı (zaten config)

Tümü `import.meta.env` üzerinden, sabit kodlama yok (satır 8-25):

- `CHAT_URL` ← `PUBLIC_LUMOS_CHAT_URL` (varsayılan `https://lumos-core-1.onrender.com/chat`)
- `UPLOAD_URL` ← `PUBLIC_LUMOS_PANEL_UPLOAD_URL`
- `HEALTH_URL` ← `PUBLIC_LUMOS_PANEL_HEALTH_URL` / `PUBLIC_LUMOS_BRIDGE_HEALTH_URL` → `/health`
- `STATUS_URL` ← `PUBLIC_LUMOS_PANEL_STATUS_URL` → `/status`
- `TASKS_API_URL` ← `PUBLIC_LUMOS_PANEL_TASKS_API_BASE`
- `BRIDGE_BASE_URL` + `/controlled` (7149), `/task` (7555), `/last-result` (7859), `/health` (7817)

## 4. ui/.env.local — mevcut değerler

- `PUBLIC_LUMOS_PANEL_UPLOAD_URL=http://127.0.0.1:8765/panel/upload`
- `PUBLIC_LUMOS_PANEL_HEALTH_URL=http://127.0.0.1:8765/health`
- `PUBLIC_KANDO_TOKEN=test123`

Not: Posts API (3000) bu env dosyasında temsil edilmiyor; `feed-api.js` kendi global/localStorage tabanını kullanıyor.

## 5. frontend/index.html — Bridge UI

- Bridge URL input varsayılanı `http://127.0.0.1:8766` (satır 1757); `getBase()` (6556).
- `bridgeFetch("/health")` (6674).

---

## Deprecated endpoint işareti

- `/posts/feed` **çağrı olarak kullanılmıyor**. Tek geçiş: `panel/css/app.css:920` içinde eski bir yorum satırı (`/* ——— Akış (GET /posts/feed) ——— */`). Yalnızca yorum; davranışı etkilemez ama yanıltıcı, ileride güncellenebilir.

## Canlı backend bağlantısı için değiştirilmesi gereken dosyalar (sadece not)

- `panel/js/feed-api.js`: Uzak test için posts tabanı `window.LUMOS_POSTS_API_BASE` veya `localStorage.lumos_posts_api_base` ile verilebilir (ör. `https://api.example.com`). Lokal varsayılan `http://127.0.0.1:3000` korunmalı. Kalıcı/varsayılan istenirse `DEFAULT_BASE` (satır 9) tek dokunma noktasıdır — env tabanlı yapılması önerilir.
- `ui/.env.local`: Canlı doğrulama için ayrı bir değişken (ör. `PUBLIC_LUMOS_POSTS_API_BASE`) tanımlanıp panel.astro'da feed tabanına bağlanması değerlendirilebilir (şu an feed tabanı astro env'inden gelmiyor).
- `frontend/index.html` (satır 1757) ve `panel/js/app.js` (satır 419/3516): bunlar 8766 köprü/görev sunucusu içindir; posts/feed canlı bağlantısı için **değiştirilmemeli**.
- `panel/css/app.css:920`: yalnızca yanıltıcı yorum; istenirse `/posts?order=feed` olarak güncellenir.

> İlke: posts API tabanı tek noktadan (env/global) yönetilmeli, lokal `127.0.0.1:3000` korunmalı, uzak URL ayrı değişkenle verilmeli. Düz IP + HTTP geçici çözümdür; domain/HTTPS/proxy olmadan üretim sayılmaz.
