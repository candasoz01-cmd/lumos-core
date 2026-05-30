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
