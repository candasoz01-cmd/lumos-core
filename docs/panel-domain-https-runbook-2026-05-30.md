# panel.welockai.com — Domain + HTTPS + Erişim Kontrolü Runbook (2026-05-30)

Bu doküman, panelin `panel.welockai.com` üzerinden HTTPS ile servis edilmesi ve erişim kontrolü için **sıralı uygulama planı + her adımın doğrulama komutudur**. Bu doküman yalnızca plandır; komutlar bu adımda **çalıştırılmadı**.

## Çalışma modu

- **Mod C:** Adım adım ilerlenir; **her riskli adımda durulur ve kullanıcı onayı alınır**, sonra devam edilir.
- **Erişim kontrolü:** Öncelik **Cloudflare Access**. **Nginx basic auth yalnızca geçici yedek** seçenektir (Access kurulamazsa kısa süreli köprü).
- Her uygulama adımı **ayrı onayla** yapılır; bu runbook tek başına uygulama yetkisi vermez.

İlgili planlar: `docs/panel-domain-https-plan-2026-05-30.md`, `docs/backend-domain-https-reverse-proxy-plan-2026-05-30.md`, `docs/panel-live-backend-config-2026-05-30.md`.

## Sabitler

- Sunucu IP: `167.99.253.148`
- SSH: `ssh -p 443 root@167.99.253.148` (port 22 Mac ağında timeout veriyordu)
- API (hazır, doğrulandı): `https://api.welockai.com`
- Panel API base default: `https://api.welockai.com`

## Riskli adım işareti

Aşağıda **[RİSKLİ — DUR/ONAY]** ile işaretli adımlar canlı/dış etkili değişikliklerdir; mod C gereği önce onay alınır.

---

## Adım 1 — DNS: `panel` kaydı  [RİSKLİ — DUR/ONAY]

**Amaç:** `panel.welockai.com` → sunucu IP.

**Uygulama (Cloudflare panelinden, elle):**
- A record: `panel` -> `167.99.253.148`
- Başlangıçta **DNS only (gri bulut)** önerilir; Nginx + panel doğrulandıktan sonra proxied (turuncu) açılır.

**Doğrulama:**

```bash
dig +short panel.welockai.com
```

Beklenen: `167.99.253.148` döner.

---

## Adım 2 — Nginx panel server block + statik servis

**Amaç:** Panel statik dosyaları `panel.welockai.com` için ayrı server block ile servis edilir (API server block'undan ayrı).

**Ön koşul / açık konu:** Panel statik dosyalarının (`panel/` içeriği) sunucuda hangi dizinde duracağı belirlenmeli (ör. `/var/www/panel`). Dosyaların sunucuya nasıl deploy edileceği (git pull / rsync / scp) ayrı kararlaştırılmalı. Şu an panel lokalde `python3 -m http.server 8080` ile servis ediliyor; production'da bu Nginx statik servise çevrilmeli.

**Uygulama (sunucuda, `/etc/nginx/sites-available/panel.welockai.com`):**

```nginx
server {
    listen 80;
    server_name panel.welockai.com;

    root /var/www/panel;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Site'ı enable et:

```bash
ln -s /etc/nginx/sites-available/panel.welockai.com /etc/nginx/sites-enabled/panel.welockai.com
```

**Doğrulama:**

```bash
nginx -t
```

```bash
curl -s -H "Host: panel.welockai.com" http://127.0.0.1/ | head -c 200
```

Beklenen: panel `index.html` içeriği döner (HTML).

> **[RİSKLİ — DUR/ONAY]** `systemctl reload nginx` mevcut API server block'unu da etkileyebileceği için reload öncesi onay alınır:
>
> ```bash
> systemctl reload nginx
> ```

---

## Adım 3 — Panel HTTPS (Cloudflare proxied)  [RİSKLİ — DUR/ONAY]

**Amaç:** `https://panel.welockai.com` çalışır hale gelir.

**Uygulama:** Adım 1'deki `panel` kaydı Cloudflare'de **proxied (turuncu bulut)** yapılır. SSL/TLS modu API ile tutarlı olmalı (şu an geçici Flexible; kalıcı hedef Full strict — bkz. Adım 5).

**Doğrulama:**

```bash
curl -sI https://panel.welockai.com/ | head -n 1
```

Beklenen: `HTTP/2 200` (veya Access aktifse 302 → Access login, bkz. Adım 4).

---

## Adım 4 — Erişim kontrolü: Cloudflare Access (öncelik)  [RİSKLİ — DUR/ONAY]

**Amaç:** `panel.welockai.com` herkese açık olmamalı; yalnızca yetkili kişiler erişebilmeli.

**Açık konu (karar gerekli):** Kimler erişecek (e-posta listesi / SSO / domain) ve hangi kimlik sağlayıcı kullanılacak. Bu netleşmeden Access policy yazılmaz.

**Uygulama (Cloudflare Zero Trust → Access):**
- Application: `panel.welockai.com` (Self-hosted).
- Policy: Allow → yetkili e-posta/identity grubu.
- Session süresi ve kimlik sağlayıcı seçilir.

**Doğrulama:**

```bash
curl -sI https://panel.welockai.com/ | head -n 5
```

Beklenen: yetkisiz istek Cloudflare Access login'e yönlenir (302 / Access sayfası); yalnızca yetkili oturum panel'e ulaşır.

**Geçici yedek (yalnızca Access kurulamazsa, kısa süreli):** Nginx basic auth.

```bash
htpasswd -c /etc/nginx/.htpasswd-panel <kullanici>
```

panel server block `location /` içine:

```nginx
auth_basic "Lumos Panel";
auth_basic_user_file /etc/nginx/.htpasswd-panel;
```

Doğrulama: parolasız istek `401`, doğru parola ile `200`. Access devreye girince basic auth kaldırılır.

---

## Adım 5 — API origin sertifikası + Cloudflare Full (strict)  [RİSKLİ — DUR/ONAY]

**Amaç:** API tarafındaki geçici **Flexible** kaldırılıp uçtan uca gerçek TLS (**Full strict**) sağlanır. (Sıra notu: bu adım, 3000 kapatmadan **önce** tamamlanmalı.)

**Uygulama:**
- Cloudflare → API zonunda **Origin Certificate** oluştur.
- Sertifikayı sunucuya koy; `api.welockai.com` Nginx server block'una `listen 443 ssl` + sertifika satırları ekle.
- Cloudflare SSL/TLS modunu **Full (strict)** yap.

**Doğrulama:**

```bash
curl -sI https://api.welockai.com/health | head -n 1
```

```bash
curl -s https://api.welockai.com/health
```

Beklenen: `HTTP/2 200` ve `{"status":"ok"}`; Cloudflare SSL/TLS modu Full (strict)'te ve hata yok.

---

## Adım 6 — `3000/tcp` public erişimini kapatma  [RİSKLİ — DUR/ONAY]

**Amaç:** Backend artık yalnızca Nginx reverse proxy üzerinden erişilir; ham public `3000` kapanır.

**Ön koşul:** Adım 5 doğrulanmış olmalı; `https://api.welockai.com` uçtan uca çalışıyor olmalı (bu doğrulanmadan port kapatılmaz).

**Uygulama (sunucuda):**

```bash
ufw delete allow 3000/tcp
```

**Doğrulama:**

```bash
ufw status
```

Dışarıdan ham port artık kapalı olmalı:

```bash
curl -s --max-time 8 http://167.99.253.148:3000/health || echo "3000 kapali (beklenen)"
```

API hâlâ HTTPS üzerinden çalışmalı:

```bash
curl -s https://api.welockai.com/health
```

Beklenen: ham `:3000` dışarıdan erişilemez; `https://api.welockai.com/health` → `{"status":"ok"}`.

---

## Özet sıra ve bağımlılık

1. DNS `panel` kaydı → 2. Nginx panel server block → 3. Panel HTTPS (proxied) → 4. Cloudflare Access (öncelik; basic auth geçici yedek).
5. API origin cert + Full strict → 6. `3000/tcp` kapatma (yalnızca 5 doğrulandıktan sonra).

Her **[RİSKLİ — DUR/ONAY]** adımında: uygula → doğrula → bir sonraki adıma geçmeden onay al.

---

## Adım 2 doğrulama sonucu (2026-05-30)

- Nginx server block aktif: `server_name panel.welockai.com`.
- Root: `/opt/lumos/panel`.
- Local Host-header testi `HTTP/1.1 200 OK` döndü.
- Domain üzerinden panel HTML geldi: `<title>Lumos Panel v1</title>`.
- API bozulmadı: `https://api.welockai.com/health` -> `{"status":"ok"}`.
- **Açık risk:** `panel.welockai.com` şu an erişim kontrolü olmadan dışarıya açık olabilir.
- **Sonraki zorunlu adım:** Cloudflare Access veya geçici basic auth ile panel erişimini sınırlamak.

---

## Adım 3 — Erişim kontrolü planı: Cloudflare Access (2026-05-30)

> Yalnızca plan; bu adımda uygulama/sunucu/Cloudflare değişikliği yapılmadı. Öncelik **Cloudflare Access**; basic auth yalnızca geçici yedek.

### Karar notu
- Öncelik: **Cloudflare Access**.
- Başlangıç IdP: **One-time PIN** (e-posta OTP).
- Erişecek e-posta(lar): **şimdilik manuel karar bekliyor.**
- Basic auth: yalnızca **geçici yedek** (Access gelince kaldırılır).
- **Gate:** Access doğrulanmadan **3000 port kapatma** ve **Full strict** geçişi yapılmayacak.

### A. Cloudflare Access ile uygulama/policy oluşturma
Ön koşul: `panel.welockai.com` DNS proxied (sağlandı); Cloudflare Zero Trust etkin ve team domain (`<isim>.cloudflareaccess.com`) tanımlı.
1. **IdP seç:** Başlangıç **One-time PIN (e-posta OTP)**. (Zero Trust → Settings → Authentication.)
2. **Access Application (Self-hosted):** Zero Trust → Access → Applications → Add an application → Self-hosted. Name: `Lumos Panel`; Application domain: `panel.welockai.com` (path `/`); Session duration karara bağlı; en az 1 IdP (OTP).
3. **Policy (Allow):** Action Allow; Include = kararlaştırılan e-postalar (veya domain/IdP grubu).
4. Kaydet. Cloudflare edge'de panel önüne Access korumasını koyar; origin/Nginx değişmez.

### B. Manuel karar gerektiren nokta
- Kimler erişecek (tam e-posta listesi / `@<domain>` kuralı / IdP grubu) — manuel karar; netleşmeden policy yazılmaz.

### C. Doğrulama
- Yetkisiz (gizli sekme): `https://panel.welockai.com` → Cloudflare Access giriş ekranı; panel görünmez. `curl -I https://panel.welockai.com` → `302` + `location: .../cdn-cgi/access/login/...`.
- Yetkili: OTP/SSO sonrası panel HTML (`<title>Lumos Panel v1</title>`) görünür.

### D. Risk
- Açık kalma: Include yanlış/çok geniş ("Everyone") veya domain/path hatalı → panel erişim kontrolsüz açık kalır.
- Kilitlenme: Include çok dar/yanlış → kimse giremez. Önlem: önce kendi e-postanı ekle, gizli sekmede doğrula.
- IdP doğrulanmadan policy → giriş çalışmaz.

### E. Basic auth yedek planı (yalnızca geçici)
- `htpasswd -c /etc/nginx/.htpasswd-panel <kullanici>` ve panel server block `location /` içine `auth_basic "Lumos Panel";` + `auth_basic_user_file /etc/nginx/.htpasswd-panel;`.
- Doğrulama: parolasız `401`, doğru parola `200`. Kalıcı bırakılmaz; Access gelince satırlar kaldırılır.

### F. Uygulanacak sıra
1. IdP belirle + Zero Trust team domain hazır.
2. Erişecek e-posta/grup kararı (manuel).
3. Access Application (panel.welockai.com, self-hosted) oluştur.
4. Allow policy (Include = kararlaştırılan e-postalar).
5. Doğrula: gizli sekme → login; yetkili → panel.
6. (Gerekirse) geçici basic auth yedeği; Access gelince kaldır.
7. Ancak bundan sonra → Adım 5 (origin cert + Full strict) → Adım 6 (3000 kapatma).

---

## Adım 3B — Nginx basic auth geçici koruma doğrulama sonucu (2026-05-30)

- Cloudflare Access kurulumu **ödeme/kart yetkisi** istediği için **uygulanmadı**.
- Geçici koruma olarak **Nginx basic auth** kullanıldı.
- Kullanıcı adı: `cando`.
- htpasswd dosyası: `/etc/nginx/.htpasswd-panel`.
- Nginx config testi başarılı: `nginx -t` → OK.
- Kimliksiz istek **HTTP 401** döndü.
- Local Host-header testi **HTTP 401** döndü.
- Doğru kullanıcı/şifre ile `https://panel.welockai.com` açıldı ve **Lumos Panel v1** göründü.
- Basic auth **geçici çözümdür**; kalıcı hedef **Cloudflare Access** veya eşdeğer kimlik tabanlı erişim kontrolüdür.
- Bu doğrulama yapılmadan önce **3000 portu kapatılmadı** ve **Full strict geçişi yapılmadı**.
- **Sonraki adım:** origin sertifikası + Cloudflare Full/Full strict geçişini **ayrı dur-onay adımı** olarak planlamak.

---

## Adım 5 (detay) — Origin cert + Cloudflare Full (strict) geçiş planı (2026-05-30)

> Yalnızca plan; bu adımda kod / sunucu / Nginx / DNS / Cloudflare / SSL mode değişikliği **yapılmadı**. Her **[RİSKLİ — DUR/ONAY]** adımında: uygula → doğrula → sonraki adıma geçmeden onay.

### Önemli ön tespit
- Cloudflare **SSL/TLS modu zone genelindedir** (`welockai.com`). Full (strict)'e geçince **proxied tüm origin'ler** geçerli TLS sunmalı — yalnızca `api` değil, `panel.welockai.com` origin'i de 443/SSL ile geçerli sertifika sunmalı. Aksi halde Full strict panel'i de kırar. Plan bu yüzden **iki origin'i de** kapsar.
- Mevcut geçici mod: **Flexible**. Hedef: **Full** ara durak → **Full (strict)**.
- `3000/tcp` bu plan boyunca **açık kalır**; Adım 6 (port kapatma) bu plan doğrulanmadan yapılmaz.

### 5.0 — Mevcut durum tespiti (risksiz, okuma)
```bash
ssh -p 443 root@167.99.253.148 'nginx -T 2>/dev/null | grep -E "server_name|listen|ssl_certificate"'
```
Beklenen: `api.welockai.com` ve `panel.welockai.com` server block'ları şu an yalnızca `listen 80`.

### 5.1 — Cloudflare Origin CA sertifikası oluşturma planı (Cloudflare panel, elle)  [RİSKLİ — DUR/ONAY]
- Cloudflare → `welockai.com` zonu → SSL/TLS → **Origin Server → Create Certificate**.
- Hostnames: `welockai.com`, `*.welockai.com` (api + panel tek sertifikayla kapsanır).
- Key type: RSA 2048 (veya ECDSA). Süre: 15 yıl.
- Çıktı: **Origin Certificate (PEM)** + **Private Key**. Private key yalnızca bu ekranda görünür — güvenli kaydet.

### 5.2 — Sertifikayı sunucuya koyma planı  [RİSKLİ — DUR/ONAY]
```bash
sudo mkdir -p /etc/nginx/ssl
sudo nano /etc/nginx/ssl/welockai-origin.pem   # 5.1'deki certificate
sudo nano /etc/nginx/ssl/welockai-origin.key   # 5.1'deki private key
sudo chmod 600 /etc/nginx/ssl/welockai-origin.key
```
(Authenticated Origin Pull / Origin CA root güveni ayrı karar — bu plana dahil değil.)

### 5.3 — Nginx 443 server block planı (api + panel)  [RİSKLİ — DUR/ONAY]
Her iki server block'a, mevcut `location` mantığını koruyarak:
```nginx
listen 443 ssl;
ssl_certificate     /etc/nginx/ssl/welockai-origin.pem;
ssl_certificate_key /etc/nginx/ssl/welockai-origin.key;
```
- `api.welockai.com`: `proxy_pass http://127.0.0.1:3000;` korunur.
- `panel.welockai.com`: root + `auth_basic` (Adım 3B koruması) korunur.
- `listen 80` blokları şimdilik kalır (redirect ayrı karar).

```bash
sudo nginx -t
```

### 5.4 — Reload + origin TLS doğrulama (mod DEĞİŞTİRMEDEN)  [RİSKLİ — DUR/ONAY]
```bash
sudo systemctl reload nginx
curl -sI --resolve api.welockai.com:443:127.0.0.1   https://api.welockai.com/health | head -n1
curl -sI --resolve panel.welockai.com:443:127.0.0.1 https://panel.welockai.com/   | head -n1
```
Beklenen: origin 443 üzerinden TLS el sıkışması başarılı; `api` → 200, `panel` → 401 (basic auth). Bu adım Flexible modda da çalışır; mod değişmeden önce origin'in 443'te sağlam olduğunu kanıtlar (kritik gate).

### 5.5 — Önce Full modda doğrulama (ara durak)  [RİSKLİ — DUR/ONAY]
- Cloudflare → SSL/TLS → Overview → **Full**.
- Doğrulama:
```bash
curl -sI https://api.welockai.com/health | head -n1
curl -s  https://api.welockai.com/health
curl -sI https://panel.welockai.com/ | head -n1
```
Beklenen: `api` 200 + `{"status":"ok"}`, `panel` 401; her ikisi de hatasız.

### 5.6 — Sonra Full (strict)'e geçiş  [RİSKLİ — DUR/ONAY]
- Cloudflare → SSL/TLS → **Full (strict)** (origin sertifikası Cloudflare Origin CA olduğundan strict doğrulanır).
- Doğrulama (5.5 ile aynı):
```bash
curl -sI https://api.welockai.com/health | head -n1
curl -s  https://api.welockai.com/health
curl -sI https://panel.welockai.com/ | head -n1
```
Beklenen: `api` 200 + `{"status":"ok"}`, `panel` 401; **526/525 (SSL handshake) hatası YOK**.

### Rollback
- Sorun çıkarsa: Cloudflare SSL/TLS modunu **Full (strict) → Flexible**'a geri al (anında etki).
- Nginx tarafı: `listen 80` blokları korunduğu için 443 eklentisi geri alınsa bile servis düşmez; gerekirse 443 satırlarını kaldırıp `nginx -t && systemctl reload nginx`.

### Bağımlılık ve sıra notu
- **Bu adım doğrulanmadan `3000/tcp` kapatılmayacak** (Adım 6 yalnızca 5 doğrulandıktan sonra).
- 526/525 görülürse kök neden genelde: panel origin'inde 443/SSL eksik veya sertifika yolu/izin hatası (5.2–5.4'e dön).

---

## Adım 5.0 — Mevcut durum kontrolü sonucu (2026-05-30)

> Yalnızca salt-okuma kontrolü; kod / sunucu / Nginx / DNS / Cloudflare / UFW / SSL mode **değiştirilmedi**.

- `api.welockai.com` ve `panel.welockai.com` için Nginx server block'ları yalnızca `listen 80` kullanıyor.
- `panel.welockai.com` basic auth aktif; kimliksiz HTTPS istek **HTTP 401** dönüyor.
- `api.welockai.com` HTTPS health **HTTP 200** ve `{"status":"ok"}` dönüyor.
- `/etc/ssl/cloudflare` yok; Origin CA sertifikası henüz sunucuda **yok**.
- **443 portu Nginx tarafından değil `sshd` tarafından dinleniyor.**
- Bu yüzden Nginx 443 SSL geçişi öncesinde **SSH port stratejisi netleşmeli**.
- `3000` portu hâlâ **açık** ve bu aşamada kapatılmadı.
- Full / Full strict canlı uygulamasına **geçilmedi**.

### Sonraki karar notu
Cloudflare Full / Full strict için origin'in 443'te geçerli TLS sunması gerekir; ancak 443 şu an SSH (`sshd`) tarafından kullanıldığı için, önce **SSH erişim yolu korunarak** 443'ün Nginx'e ayrılıp ayrılamayacağı planlanmalı. (Örn. SSH'ı farklı bir porta taşıma veya alternatif erişim, 443'ü Nginx'e bırakma — bu netleşmeden Adım 5.3 Nginx 443 server block uygulanmaz.)

---

## Adım 5.1 (ön koşul) — SSH port stratejisi notu (2026-05-30)

> Yalnızca plan/not; bu adımda kod / sunucu / Nginx / DNS / Cloudflare / UFW / SSH / SSL mode **değiştirilmedi**. Canlı SSH değişikliği ayrı bir **[RİSKLİ — DUR/ONAY]** adımdır.

- `443` portu şu an `sshd` tarafından kullanılıyor (Adım 5.0 bulgusu).
- Cloudflare Full / Full strict öncesinde **443'ün Nginx'e ayrılması** gerekir (origin'in 443'te geçerli TLS sunması için).
- **22 erişimi doğrulanmadan 443 SSH kapatılmayacak.**
- Web Console erişimi mevcut olduğu için canlı SSH değişikliği **ayrı, dur-onay adımı** olarak yapılacak.
- `3000` portu bu aşamada **kapatılmayacak**.

### Uygulanacak sıra (özet)
1. SSH 22 erişimi doğrula (gate). 22 sağlanmadan hiçbir değişiklik yok.
2. `sshd_config`'te 443 dinlemesinin kaynağını tespit et (salt-okuma).
3. 22 sağlamsa: rollback planı (sshd_config yedeği + açık 22 oturumu) yazıldıktan sonra 443'ü SSH'tan boşalt (Port satırını kaldır veya SSH'ı alternatif porta taşı), `sshd` reload — ayrı dur-onay.
4. 443 boşalınca Nginx 443 SSL hazırlığı (Adım 5.2 → 5.3 → 5.4).
5. Cloudflare Full → Full strict (5.5 → 5.6) yalnızca yukarısı doğrulandıktan sonra.
6. `3000` kapatma (Adım 6) yalnızca 5 tamamen doğrulandıktan sonra.

### Açık blocker
SSH anahtar erişimi henüz yok; 22 erişim testi bile bunsuz yapılamaz. Web Console üzerinden `authorized_keys`'e anahtar eklenmesi veya 22 testinin Web Console'dan teyidi gerekiyor.

---

## Adım 5.1 — SSH erişim durumu uyarısı (2026-05-31)

> Yalnızca durum notu; bu adımda kod / sunucu / Nginx / DNS / Cloudflare / UFW / SSH / SSL mode **değiştirilmedi**.

- **SSH 443 bağlantısı kopuyor** (kararsız; oturum düşüyor).
- **22 portu dış erişim timeout** veriyor (dışarıdan SSH 22 ile bağlanılamıyor).
- Mevcut **API ve panel çalışıyor** (servis tarafında sorun yok; yalnızca yönetim/SSH erişimi sorunlu).
- Cloudflare **Full / Full strict uygulanmadı** (hâlâ Flexible).
- `3000` portu **kapatılmadı** (açık).

### Etki / blocker
SSH 443 kararsız ve 22 dışarıdan timeout olduğundan, güvenilir yönetim erişimi şu an yalnızca **DigitalOcean Web Console** üzerinden. 443'ü Nginx'e ayırma (Adım 5.2/5.3) ve Full/Full strict geçişi, **güvenilir bir SSH/erişim yolu netleşmeden** uygulanmayacak. 443 SSH'tan alınırsa mevcut tek SSH yolu (443) da kaybolacağından, önce 22 dış erişimi veya alternatif port düzeltilmeli.

---

## Adım 5.1 — Yönetim erişimi ek durum notu (2026-05-31)

> Yalnızca durum notu; kod / sunucu / Nginx / DNS / Cloudflare / UFW / SSH / SSL mode **değiştirilmedi**.

- Mac Terminal'den **22 port SSH** denemesi `Operation timed out` verdi.
- Mac Terminal'den **443 port SSH** denemesi root login ekranına ulaştı ve giriş yaptı, ancak kısa süre sonra **`Connection reset by peer` / `Broken pipe`** ile kapandı.
- Web Console üzerinden **ssh servisi active/running** görüldü.
- Web Console çıktısında **sshd 22 ve 443 portlarını dinliyor** göründü.
- `api.welockai.com/health` hâlâ `{"status":"ok"}` dönüyor.
- `panel.welockai.com` kimliksiz istek **HTTP 401** dönüyor.
- Bu nedenle **Full / Full strict ve Nginx 443 uygulamasına geçilmedi**.
- `3000` portu **kapatılmadı**.

### Sonraki güvenli adım
Yönetim erişimini kalıcı hale getirmek için **DigitalOcean firewall / ağ / SSH oturum kopma sebebi ayrı incelenecek** (22 timeout + 443 reset kök nedeni). **SSL değişikliği (Full/Full strict, Nginx 443) ancak bundan sonra** yapılacak.

---

## Adım 5.1 — Ek doğrulama notu: SSH 2222 yedek yönetim kapısı (2026-06-01)

> Bu notta yalnızca **yedek SSH yönetim kapısı (2222)** eklendi ve doğrulandı; **kod / Nginx / DNS / Cloudflare / SSL mode / `3000` port ayarı değiştirilmedi**.

- DigitalOcean firewall `test-ssh` içine **inbound TCP 2222 — All IPv4** eklendi.
- Sunucuda `sshd` **2222 portunda da dinleyecek** şekilde ek config dosyası oluşturuldu.
- UFW'ye **`2222/tcp allow`** eklendi.
- Mac Terminal'den giriş doğrulandı:

```bash
ssh -i ~/.ssh/id_ed25519 -p 2222 root@167.99.253.148
```

- Doğrulama çıktısı: **OK / root / project-lumos-test**.
- **443 henüz SSH'tan çıkarılmadı** (mevcut 443 SSH yolu hâlâ duruyor).
- **Nginx 443, Origin cert, Cloudflare Full strict ve `3000` kapatma yapılmadı.**

### Sonraki canlı adım
2222 açık SSH oturumu **elde tutulurken**, 443'ü `sshd`'den çıkarıp **Nginx için boşaltma** ([RİSKLİ — DUR/ONAY]; ayrı dur-onay adımı). 2222 doğrulanmış yedek kapı olduğundan, 443 SSH yolu kaybolsa bile yönetim erişimi 2222 üzerinden korunur.

---

## Adım 5.1 — Doğrulama notu: 443 `sshd`'den çıkarıldı (2026-06-01)

> Bu adımda yalnızca **443'ün `sshd`'den boşaltılması** yapıldı; **kod / DNS / Cloudflare / SSL mode / `3000` port ayarı değiştirilmedi**.

- 2222 SSH oturumu **açık tutulurken** `/etc/ssh/sshd_config.d/99-lumos-ssh-port.conf` yedeklendi.
- `Port 443` satırı sshd config'ten kaldırıldı.
- `sshd -t` **başarılı** geçti.
- `systemctl reload ssh` uygulandı.
- Doğrulama sonrası `ss` çıktısında **22 ve 2222** `sshd` olarak kaldı; **443 artık `sshd` tarafından dinlenmiyor**.
- API doğrulaması: `https://api.welockai.com/health` → `{"status":"ok"}`.
- Panel doğrulaması: `https://panel.welockai.com/` → **HTTP 401**.
- **Nginx 443, Origin cert, Cloudflare Full strict ve `3000` kapatma henüz yapılmadı.**

### Sonraki canlı adım
**Origin certificate** oluşturma (Adım 5.1 — Origin CA) ve **Nginx 443 SSL hazırlığı** (Adım 5.2 → 5.3 → 5.4). 443 artık boşta olduğundan Nginx `listen 443 ssl` çakışmadan eklenebilir; yönetim erişimi 2222 üzerinden korunur.

---

## Adım 5.2–5.4 — Doğrulama notu: Origin cert kuruldu + Nginx 443 SSL aktif (2026-06-01)

> Bu adımda **Origin sertifikası sunucuya kuruldu** ve **Nginx 443 SSL** etkinleştirildi; **kod / DNS / Cloudflare SSL mode / `3000` port ayarı değiştirilmedi**. (Private key yalnızca sunucuda; repoya alınmadı.)

- Cloudflare **Origin Certificate** ve **Private Key** sunucuda `/etc/nginx/ssl/cloudflare-origin.crt` ve `/etc/nginx/ssl/cloudflare-origin.key` olarak oluşturuldu.
- İzinler: **key `600`**, **cert `644`**.
- `api.welockai.com` ve `panel.welockai.com` Nginx config'lerinde **`listen 80` blokları korunarak** `listen 443 ssl` server block eklendi.
- `nginx -t` **başarılı** geçti.
- `systemctl reload nginx` uygulandı.
- `ss` çıktısında **443 artık `nginx` tarafından** dinleniyor; **2222** `sshd` yönetim kapısı olarak dinlemeye devam ediyor.
- Local origin HTTPS testleri:

```bash
curl -sk --resolve api.welockai.com:443:127.0.0.1   https://api.welockai.com/health   # {"status":"ok"}
curl -sk --resolve panel.welockai.com:443:127.0.0.1 https://panel.welockai.com/        # HTTP 401
```

- Public testler: `https://api.welockai.com/health` → `{"status":"ok"}`; `https://panel.welockai.com/` → **HTTP 401**.
- **Cloudflare SSL/TLS mode hâlâ değiştirilmedi** (Flexible).
- **`3000` portu kapatılmadı.**

### Sonraki canlı adım
Cloudflare SSL/TLS mode **önce Full** (ara durak); doğrulama başarılıysa **Full (strict)** (Adım 5.5 → 5.6). Origin 443'te geçerli TLS sunduğundan strict doğrulanır; sorun çıkarsa rollback Flexible'a geri dönüş.

---

## Adım 5.5–5.6 — Doğrulama notu: Cloudflare Full → Full (strict) geçişi (2026-06-01)

> Bu adımda **Cloudflare SSL/TLS modu Full üzerinden Full (strict)'e** geçirildi; **kod / DNS / Nginx config / `3000` port ayarı değiştirilmedi**.

- Cloudflare SSL/TLS Overview ekranında **Current encryption mode: Full (strict)** görünüyor.
- Önce **Full** modda API ve panel doğrulandı.
- Sonra **Full (strict)** seçildi.
- Full (strict) sonrası doğrulama:

```bash
curl -s https://api.welockai.com/health                                            # {"status":"ok"}
curl -s -o /dev/null -w "PANEL HTTP %{http_code}\n" https://panel.welockai.com/     # PANEL HTTP 401
```

- **525/526 SSL handshake / origin certificate hatası görülmedi.**
- **2222** SSH yönetim kapısı korunuyor.
- **443** Nginx tarafından kullanılıyor.
- **`3000` portu henüz kapatılmadı.**

### Sonraki canlı adım
**`3000/tcp` public erişimini kapatma** (Adım 6) ve sonrasında api/panel doğrulaması. Uçtan uca HTTPS (Full strict) doğrulandığı için artık ham `3000` kapatılabilir; yönetim 2222 üzerinden korunur.

---

## Adım 6 — Doğrulama notu: `3000/tcp` public erişimi kapatıldı (2026-06-01)

> Bu adımda yalnızca **`3000/tcp` public erişimi kapatıldı**; **kod / DNS / Nginx config / Cloudflare SSL mode / SSH ayarı değiştirilmedi**.

- `ufw delete allow 3000/tcp` çalıştırıldı.
- **`3000/tcp` ve `3000/tcp (v6)`** kuralları silindi.
- `ufw status` çıktısında artık **`3000` görünmüyor**.
- **`22/tcp`, `80/tcp`, `443/tcp` ve `2222/tcp`** açık kalıyor.
- **2222** SSH yönetim kapısı korunuyor.
- **443** Nginx tarafından kullanılmaya devam ediyor.
- Doğrulama:

```bash
curl -s https://api.welockai.com/health                                            # {"status":"ok"}
curl -s -o /dev/null -w "PANEL HTTP %{http_code}\n" https://panel.welockai.com/     # PANEL HTTP 401
```

- Full strict sonrası **uçtan uca HTTPS çalışıyor**.

### Sonuç
**Bu adımla runbook'taki canlı geçiş tamamlandı.** Backend artık yalnızca Nginx reverse proxy (443, Full strict) üzerinden erişilir; ham public `3000` kapalı, yönetim erişimi 2222 üzerinden korunuyor.
