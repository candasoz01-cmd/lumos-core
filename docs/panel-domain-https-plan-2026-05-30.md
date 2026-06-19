# Panel Domain + HTTPS Servis Planı (2026-05-30)

Bu doküman, Lumos panelinin ileride `panel.welockai.com` veya `app.welockai.com` üzerinden HTTPS ile servis edilmesi planını tanımlar. Sadece plandır; bu adımda kod veya altyapı değişikliği yapılmaz.

## Mevcut durum

- Panel lokal olarak `http://127.0.0.1:8080` üzerinde çalışıyor.
- Panel şu anda canlı backend'e `https://api.welockai.com` üzerinden bağlanabiliyor (feed doğrulandı; bkz. `docs/panel-live-backend-config-2026-05-30.md`).

## Hedef seçenekler

| Subdomain | Kullanım | Not |
|-----------|----------|-----|
| `panel.welockai.com` | Yönetim / developer paneli | İç/operasyonel araç olarak daha net. |
| `app.welockai.com` | Son kullanıcı uygulaması | Ürün odaklı, kullanıcıya açık arayüz için daha uygun. |

## Öneri

- **Şimdilik `panel.welockai.com` kullan.**
- `app.welockai.com`, ileride kullanıcıya açık ürün arayüzü için ayrılabilir.

## DNS

- Planlanan kayıt: `panel` -> `A` -> `<SERVER_IP>`.
- Başlangıçta Cloudflare proxied (turuncu bulut) kullanılabilir; ancak origin / Nginx ayarı dikkatle doğrulanmalı.

## Nginx

- Panel için **ayrı bir server block** açılmalı.
- Bu server block panel statik dosyalarını servis etmeli; **veya** mevcut lokal panel serve süreci (`python3 -m http.server 8080`) production yapıya çevrilmeli.
- Backend reverse proxy ile karıştırılmamalı; `api.welockai.com` (backend) ve `panel.welockai.com` (statik panel) ayrı server block'larda yönetilmeli.

## Panel API base URL

- Panel API base URL varsayılanı `https://api.welockai.com` olmalı.

## Güvenlik notu

- Panel yönetim arayüzü **herkese açık bırakılmamalı.**
- En azından basic auth, Cloudflare Access veya başka bir erişim kontrolü planlanmalı.

## Açık konu

- `panel.welockai.com` canlıya alınmadan önce **kimlerin erişeceği** ve **hangi auth katmanının** kullanılacağı netleşmeli.

## Sonraki teknik adım

1. Önce doküman (bu dosya).
2. Sonra DNS (`panel` -> `A` -> `<SERVER_IP>`).
3. Sonra Nginx statik panel servis testi.
