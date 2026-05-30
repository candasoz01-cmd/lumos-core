# Panel / Frontend — Canlı DigitalOcean Backend Bağlantı Planı (2026-05-30)

Bu not, panel/frontend tarafının canlı DigitalOcean test backend'ine bağlanması için plandır. Henüz kod değişikliği yapılmadı.

## Canlı Backend Bilgileri

- **Base URL:** http://167.99.253.148:3000
- **Health endpoint:** `/health`
- **Feed endpoint:** `/posts?order=feed`
- **Deprecated (kullanılmayacak):** `/posts/feed`

## Yapılandırma İlkeleri

- Panel tarafında API base URL **sabit kodlanmadan** config/env üzerinden yönetilmeli.
- Lokal geliştirme için `localhost:3000` korunmalı.
- Canlı test için DigitalOcean backend URL **ayrı bir ortam değişkeniyle** tanımlanmalı.
- UI değişikliği yapılmadan önce mevcut panel API çağrıları haritalanmalı.

## Risk

- Direkt canlı IP'ye bağlanmak geçici çözümdür; domain/HTTPS/proxy olmadan üretim sayılmaz.

## Sonraki Teknik Adım

- Panel içindeki fetch/API helper dosyalarını bul ve hangi endpointlerin kullanıldığını listele.
