# Panel Feed API Base URL Yapılandırması (2026-05-30)

Panel feed API tabanı artık yapılandırılabilir. Yalnızca `panel/js/feed-api.js` içindeki base URL çözümlemesi güncellendi; UI ve endpoint davranışı değişmedi.

## Base URL çözüm sırası

1. `window.LUMOS_POSTS_API_BASE` varsa onu kullan.
2. `localStorage` içindeki `LUMOS_POSTS_API_BASE` (geriye dönük: `lumos_posts_api_base`) varsa onu kullan.
3. Yoksa varsayılan lokal taban kalır: `http://127.0.0.1:3000`.

Feed endpoint değişmedi: `GET /posts?order=feed`. Deprecated `/posts/feed` kullanılmıyor.

## Canlı test (tarayıcı konsolu)

Lokal geliştirme için varsayılan `http://127.0.0.1:3000` kullanılır. Uzak/staging API için ortam değişkeni veya tarayıcı konsolundan override:

```js
localStorage.setItem("LUMOS_POSTS_API_BASE", "https://api.example.com")
```

Ardından sayfayı yenile (taban oturum başında bir kez çözümlenir).

## Geri alma

```js
localStorage.removeItem("LUMOS_POSTS_API_BASE")
```

Tekrar varsayılan lokal tabana (`http://127.0.0.1:3000`) döner.

## Canlı feed doğrulaması (2026-05-30)

- Panel lokal olarak `http://127.0.0.1:8080` üzerinde çalıştırıldı.
- Akış ekranı uzak backend base URL ile doğrulandı (`LUMOS_POSTS_API_BASE` override ile).
- Feed endpoint: `/posts?order=feed`
- Panelde test gönderisi görüldü.
- Bu doğrulama panel -> uzak backend -> DB hattının çalıştığını gösterir.
- Not: Üretim için domain + HTTPS + reverse proxy gerekir; operasyonel detaylar bkz. `docs/ops-runbooks-private-notice.md`.

## HTTPS domain ile feed doğrulaması (2026-05-30)

- Panel lokal olarak `127.0.0.1:8080` üzerinde çalıştırıldı.
- `LUMOS_POSTS_API_BASE` değeri `https://api.welockai.com` olarak ayarlandı.
- `#feed` ekranı yeni HTTPS API domaininden veri çekti.
- Doğrulanan endpoint: `https://api.welockai.com/posts?order=feed&limit=20`
- Panelde "1 gönderi · Feed" ve "@test-user — Lumos backend test post" görüldü.
- CORS/fetch hatası görülmedi.
- Doğrulanmış canlı API tabanı `https://api.welockai.com` olarak kullanılabilir.

### Açık konu

- Panel HTTP origin (`http://127.0.0.1:8080`) üzerinde çalışıyor; HTTPS backend ile mixed-content/CORS hatası görülmedi.
- Kalıcı üretim için panelin de domain/HTTPS üzerinden servis edilmesi planlanmalı.
