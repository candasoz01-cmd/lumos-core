# Panel Feed API Base URL Yapılandırması (2026-05-30)

Panel feed API tabanı artık yapılandırılabilir. Yalnızca `panel/js/feed-api.js` içindeki base URL çözümlemesi güncellendi; UI ve endpoint davranışı değişmedi.

## Base URL çözüm sırası

1. `window.LUMOS_POSTS_API_BASE` varsa onu kullan.
2. `localStorage` içindeki `LUMOS_POSTS_API_BASE` (geriye dönük: `lumos_posts_api_base`) varsa onu kullan.
3. Yoksa varsayılan lokal taban kalır: `http://127.0.0.1:3000`.

Feed endpoint değişmedi: `GET /posts?order=feed`. Deprecated `/posts/feed` kullanılmıyor.

## Canlı test (tarayıcı konsolu)

```js
localStorage.setItem("LUMOS_POSTS_API_BASE", "http://167.99.253.148:3000")
```

Ardından sayfayı yenile (taban oturum başında bir kez çözümlenir).

## Geri alma

```js
localStorage.removeItem("LUMOS_POSTS_API_BASE")
```

Tekrar varsayılan lokal tabana (`http://127.0.0.1:3000`) döner.

## Canlı feed doğrulaması (2026-05-30)

- Panel lokal olarak `http://127.0.0.1:8080` üzerinde çalıştırıldı.
- Akış ekranı canlı backend base URL ile doğrulandı: `http://167.99.253.148:3000`
- `localStorage` `LUMOS_POSTS_API_BASE` üzerinden canlı backend seçildi.
- Feed endpoint: `/posts?order=feed`
- Panelde "Lumos backend test post" görüldü.
- Bu doğrulama panel -> canlı backend -> Prisma SQLite DB hattının çalıştığını gösterir.
- Not: Bu bağlantı HTTP/IP üzerinden test içindir; üretim için domain + HTTPS + reverse proxy gerekir.
