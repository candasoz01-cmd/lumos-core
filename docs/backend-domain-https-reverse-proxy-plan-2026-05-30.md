# Backend Domain + HTTPS + Reverse Proxy Geçiş Planı (2026-05-30)

Bu doküman, Lumos canlı backend'inin IP tabanlı test erişiminden domain + HTTPS + reverse proxy mimarisine geçişi için planı tanımlar. Sadece plandır; bu adımda kod veya altyapı değişikliği yapılmaz.

## Mevcut durum

- Canlı backend test URL'i: `http://167.99.253.148:3000`
- Bu test bağlantısı çalışıyor, ancak üretim için uygun değil:
  - HTTP üzerinden, şifreleme yok (HTTPS değil).
  - Ham IP + açık port (`3000`) ile erişiliyor; doğrudan public expose edilmiş durumda.
  - Domain/subdomain üzerinden erişilemiyor.
- Şu an için açık şekilde bir **test sunucusu** olarak değerlendirilmelidir; üretim gibi davranılmamalıdır.

## Hedef yapı

- **Domain/subdomain:** `api.welockai.com` veya `lumos-api.welockai.com`
- **Reverse proxy:** Nginx
- **Backend iç port:** `127.0.0.1:3000` (yalnızca local loopback üzerinden dinler)
- **Public erişim:** HTTPS `443`
- **Port `3000` public erişimi:** Daha sonra kapatılacak (HTTPS doğrulandıktan sonra).

Akış özeti:

```
İstemci  --HTTPS 443-->  Nginx (reverse proxy)  --HTTP-->  127.0.0.1:3000 (backend)
```

## Cloudflare DNS

Cloudflare DNS tarafında bir A record planlanacak:

- `api` veya `lumos-api` -> `167.99.253.148`

Subdomain kararı (bkz. Hedef yapı) bu kaydı belirler:

| Subdomain | A record hedefi |
|-----------|-----------------|
| `api.welockai.com` | `167.99.253.148` |
| `lumos-api.welockai.com` | `167.99.253.148` |

## SSL

HTTPS sertifikası için iki seçenek değerlendirilecek:

- **Certbot (Let's Encrypt):** Sunucuda Nginx ile entegre, otomatik yenilenen ücretsiz sertifika. Cloudflare proxy kapalıyken (DNS only / gri bulut) doğrudan origin üzerinde TLS sonlandırması.
- **Cloudflare proxy:** Trafik Cloudflare üzerinden (turuncu bulut) geçer; edge'de TLS sonlandırması. Origin tarafında Cloudflare Origin Certificate veya Full (strict) modu ayrıca değerlendirilmeli.

Karar, Cloudflare aboneliği durumu ve istenen TLS sonlandırma noktasına göre verilecektir (bkz. Riskler).

## Öncelik

- **Önce** DNS ve Nginx planı netleştirilecek.
- **Sonra** uygulama (kurulum ve cutover) yapılacak.

## Riskler

- **Cloudflare Business aboneliği iptal sürecinde** olduğu için DNS/SSL tarafı dikkatli yönetilmeli; proxy/SSL davranışında abonelik değişikliğine bağlı sürprizler olabilir.
- **Üretim gibi davranmadan önce** bunun bir test sunucusu olduğu açık tutulmalı; üretim garantileri verilmemeli.
- **Port `3000` hemen kapatılmamalı;** HTTPS uçtan uca doğrulanınca kapatılmalı. Aksi halde erişim tamamen kesilebilir.

## Sonraki teknik adımlar

1. Hangi subdomain kullanılacak karar ver (`api.welockai.com` veya `lumos-api.welockai.com`).
2. Cloudflare DNS kaydı ekle (seçilen subdomain -> `167.99.253.148`).
3. Sunucuda Nginx kur.
4. Nginx reverse proxy ile `/` -> `127.0.0.1:3000` yönlendir.
5. HTTPS doğrula (sertifika geçerli, `https://<subdomain>` üzerinden backend yanıt veriyor).
6. Panel base URL'i HTTPS domain'e al.
7. Public `3000` erişimini kapat.

## Mevcut DNS durumu (2026-05-30, salt okuma)

Bu bölüm, Cloudflare DNS tarafında yalnızca okuma amaçlı yapılan inceleme sonucunu kaydeder. Herhangi bir değişiklik uygulanmamıştır.

- Cloudflare bağlantısı okuma amaçlı doğrulandı.
- `welockai.com` mevcut public DNS kayıtları incelendi.
- `api` ve `lumos-api` subdomainleri boş/çakışmasız görünüyor.
- **Önerilen subdomain:** `api.welockai.com`
- **Planlanan kayıt:** `api` -> `A` -> `167.99.253.148`
- Başlangıçta DNS only / gri bulut önerilir; Nginx + HTTPS doğrulandıktan sonra proxy/SSL modu değerlendirilecek.
- Apex `welockai.com` mevcut hosting/landing sağlayıcıya bağlı görünüyor; apex kaydına dokunulmayacak.
- Billing, ödeme, abonelik veya satın alma işlemi yapılmadı.
- DNS kaydı henüz eklenmedi; yalnızca okuma ve planlama yapıldı.
