# Panel / Frontend — Canlı Backend Bağlantı Planı (2026-05-30)

> Sunucu IP, SSH ve deployment notları public repoda yok — bkz. [`ops-runbooks-private-notice.md`](ops-runbooks-private-notice.md).

Bu not, panel/frontend tarafının uzak (staging/production) backend'e bağlanması için plandır. Henüz kod değişikliği yapılmadı.

## Uzak Backend Bilgileri

- **Base URL:** `https://api.example.com` (veya ortam değişkeni ile tanımlanan `<API_BASE_URL>`)
- **Health endpoint:** `/health`
- **Feed endpoint:** `/posts?order=feed`
- **Deprecated (kullanılmayacak):** `/posts/feed`

## Yapılandırma İlkeleri

- Panel tarafında API base URL **sabit kodlanmadan** config/env üzerinden yönetilmeli.
- Lokal geliştirme için `127.0.0.1:3000` korunmalı.
- Uzak test için backend URL **ayrı bir ortam değişkeniyle** tanımlanmalı.
- UI değişikliği yapılmadan önce mevcut panel API çağrıları haritalanmalı.

## Risk

- Direkt IP veya HTTP üzerinden bağlanmak geçici çözümdür; domain/HTTPS/proxy olmadan üretim sayılmaz.

## Sonraki Teknik Adım

- Panel içindeki fetch/API helper dosyalarını bul ve hangi endpointlerin kullanıldığını listele.
