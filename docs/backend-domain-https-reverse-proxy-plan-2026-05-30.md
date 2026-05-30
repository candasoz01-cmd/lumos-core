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

## DNS kaydı eklendi (2026-05-30)

- A record eklendi: `api` → `167.99.253.148`, DNS only (gri bulut), TTL Auto.
- Cloudflare panelinden manuel olarak kaydedildi.
- DNS yayılımı bekleniyor; `dig +short api.welockai.com` ile doğrulanabilir.

## api.welockai.com Nginx reverse proxy — uygulama adımları (2026-05-30)

> **Uyarı:** Aşağıdakiler bir plan/komut listesidir. Bu komutlar bu agent tarafından sunucuda **çalıştırılmadı**; manuel olarak uygulanacaktır. Her komut tek amaçlıdır ve kopyalanıp yapıştırılabilir. Sıraya uyulması önerilir.

### 1. MANUEL DNS adımı (Cloudflare panelinden, elle)

Bu adım otomatik yapılmıyor; Cloudflare panelinden elle eklenmelidir:

- A record: `api` -> `167.99.253.148`
- **DNS only (gri bulut)** — proxy kapalı.

Doğrulama (DNS yayıldıktan sonra), `167.99.253.148` dönmeli:

```bash
dig +short api.welockai.com
```

### 2. Sunucuya SSH (root)

Port `22` Mac ağında timeout verdiği için SSH `443` üzerinden yapılır:

```bash
ssh -p 443 root@167.99.253.148
```

### 3. Nginx kurulumu (Ubuntu/Debian)

Paket listesini güncelle:

```bash
apt update
```

Nginx'i kur:

```bash
apt install -y nginx
```

### 4. Reverse proxy site config

Site config dosyasını oluştur: `/etc/nginx/sites-available/api.welockai.com` içeriği:

```bash
cat > /etc/nginx/sites-available/api.welockai.com <<'EOF'
server {
    listen 80;
    server_name api.welockai.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
```

Site'ı enable et (`sites-enabled` içine symlink):

```bash
ln -s /etc/nginx/sites-available/api.welockai.com /etc/nginx/sites-enabled/api.welockai.com
```

Config sözdizimini doğrula:

```bash
nginx -t
```

Nginx'i reload et:

```bash
systemctl reload nginx
```

### 5. Health doğrulama

Health endpoint beklenen yanıtı vermeli:

```bash
curl -s http://api.welockai.com/health
```

Feed endpoint beklenen yanıtı vermeli:

```bash
curl -s "http://api.welockai.com/posts?order=feed"
```

### 6. HTTPS (ayrı adım — bu bölümde sadece referans)

HTTPS bu bölümün kapsamı dışındadır; ayrı bir adım olarak ele alınacaktır. İki seçenek (bkz. yukarıdaki **SSL** bölümü):

- **Certbot (Let's Encrypt):** origin üzerinde TLS sonlandırması.
- **Cloudflare proxy/SSL:** edge'de TLS sonlandırması.

**Önemli:** HTTPS uçtan uca doğrulanmadan port `3000` **KAPATILMAZ**.

### 7. Port 3000 public erişimini kapatma (EN SON — sadece HTTPS doğrulandıktan sonra)

Bu adım **en sona** bırakılır ve **yalnızca HTTPS doğrulandıktan sonra** uygulanır.

Mevcut `3000/tcp` allow kuralını kaldır:

```bash
ufw delete allow 3000/tcp
```

Alternatif olarak açıkça reddet:

```bash
ufw deny 3000/tcp
```

UFW durumunu doğrula:

```bash
ufw status
```

## Nginx reverse proxy + Cloudflare Flexible HTTPS doğrulama sonucu (2026-05-30)

Bu bölüm, `api.welockai.com` için Nginx reverse proxy ve Cloudflare Flexible HTTPS kurulumunun **doğrulama sonucunu** kaydeder.

### Uygulanan durum

- DNS: `api.welockai.com` Cloudflare üzerinden **proxied** (turuncu bulut) olarak çalışıyor.
- Cloudflare SSL/TLS mode **geçici olarak Flexible** yapıldı.
- Sunucuda Nginx kuruldu; `api.welockai.com` istekleri `127.0.0.1:3000` backend'e proxy'lendi.
- UFW'de `80/tcp` açıldı.

### Doğrulama

| İstek | Sonuç |
|-------|-------|
| `http://localhost/health` | `{"status":"ok"}` |
| `http://api.welockai.com/health` | Cloudflare tarafından HTTPS'e `301` yönleniyor |
| `https://api.welockai.com/health` | `{"status":"ok"}` |

### Durum notları

- `3000/tcp` public erişimi şimdilik **açık** bırakıldı.
- **Not:** Flexible geçici çözümdür. Kalıcı hedef: origin sertifikası + Cloudflare **Full / Full (strict)** olmalı.
- **Sonraki teknik adım:** panel live backend base URL'i `http://167.99.253.148:3000` yerine `https://api.welockai.com` olarak doğrulamak.
