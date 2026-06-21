# WeChat ve Çin Pazarı — Teknik Hazırlık Analizi (Lumos)

| Alan | Değer |
|------|--------|
| **Belge ID** | `wechat-china-market-technical-readiness` |
| **Durum** | `analiz` — karar destek; ürün/lansman kararı değildir |
| **Tarih** | 2026-06-22 |
| **Dil** | Türkçe (birincil) |
| **Kapsam** | Çin pazarı giriş engelleri, yerel entegrasyon ihtiyaçları, Lumos mimarisinde şimdiden düşünülmesi gereken kancalar |
| **Varlık bağlamı** | We Lock AI / KKTC kayıtlı şirket (overseas entity — Tencent sınıflandırması `[doğrulanmalı]`) |
| **Üst sınır** | [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md), [`docs/memory/public-repo-boundary.md`](../memory/public-repo-boundary.md) |
| **İlgili belgeler** | [`wechat-integration-feasibility.md`](./wechat-integration-feasibility.md) (WeChat ekosistemi derinlemesi), [`device-connection-architecture-draft.md`](./device-connection-architecture-draft.md), [`device-connection-information-architecture.md`](./device-connection-information-architecture.md), [`lumos-mobile-approval-mvp-plan.md`](./lumos-mobile-approval-mvp-plan.md), [`device-pairing-strategy.md`](./device-pairing-strategy.md), [`external-integrations-permissions.md`](../memory/external-integrations-permissions.md) |
| **Okunamayan / eksik kaynaklar** | `commercial-product-packaging.md`, `ip-protection-landscape.md`, `pre-commercial-release-plan.md` — repoda yok; eşdeğer bağlam: [`payment-scope-decision.md`](../memory/payment-scope-decision.md), [`commercial-domain-payments.md`](../memory/commercial-domain-payments.md), [`wechat-integration-feasibility.md` §6–10](./wechat-integration-feasibility.md) |

> **Sorumluluk reddi:** Bu belge **hukuki tavsiye değildir**. Çin veri mevzuatı (PIPL, DSL, CSL), ICP filing, Tencent platform kuralları ve dağıtım politikaları **hızla değişebilir**. `[doğrulanmalı]` işaretli maddeler yerel Çin hukuk danışmanı + operasyon ortağı ile teyit edilmelidir.

---

## 1. Yönetici özet

**WeChat / Çin pazarı = ticari lansmanı ertele, mimari kancaları şimdi hazırla.**

Lumos'un mevcut omurgası — local-first köprü, poll tabanlı mobil onay, LAN relay, onay kapılı dış entegrasyon felsefesi — Çin'de **doğrudan taşınmaz**; ancak **aynı trust/onay ilkeleri** resmi WeChat işletme API'leri ve alternatif bildirim kanalları ile uyumludur. Kişisel WeChat otomasyonu, FCM/APNs'e bağımlı push ve Google/Apple OAuth varsayımları Çin'de **blokör veya ciddi boşluk** oluşturur.

| Strateji | Anlam |
|----------|--------|
| **Defer (ticari lansman)** | Mainland tam ürün lansmanı, WeChat Pay native, mainland barındırma + ICP, App Store Çin dağıtımı — **Phase 2+**; hukuk + operasyon paketi olmadan Proceed yok |
| **Prepare-now (mimari)** | Bildirim kanalı soyutlaması, kimlik sağlayıcı eklentisi, bölge/veri ikameti sınırı, onay cihaz kanalının LAN'dan ayrışması, i18n genişlemesi — **Phase 0**; kod minimal, arayüz/sözleşme dokümantasyonu |

**Özet karar çerçevesi:**

1. **Kişisel WeChat** hedefi varsa → **red / defer** ([`wechat-integration-feasibility.md` §3.5](./wechat-integration-feasibility.md)).
2. **İşletme API + Mini Program onay yüzeyi** hedefi → **Phase 1 private POC** uygun.
3. **Mainland kullanıcı PII** taşınacaksa → PIPL outbound compliance **Proceed öncesi zorunlu** `[doğrulanmalı]`.
4. **Public OSS** (`lumos-core`) yalnızca demo-safe stub + generic kanal ilkesi; prod WeChat credential, webhook, PIPL ops **private katman**.

**Cross-link:** WeChat ürün haritası, API matrisi, entegrasyon desenleri (webhook middleware, Mini Program sidecar, Open Platform auth) için ayrıntılı fizibilite → [`wechat-integration-feasibility.md`](./wechat-integration-feasibility.md). Bu belge **pazar girişi + Lumos mimari hazırlığı** ekseninde kalır; fizibilite belgesi ile **çelişmez**, onu üst seviye hazırlık çerçevesine bağlar.

---

## 2. Giriş engelleri

### 2.1 Regülasyon (yüksek seviye — hukuki tavsiye değil)

| Mekanizma | Lumos etkisi | Not |
|-----------|--------------|-----|
| **PIPL** (Kişisel Bilgi Koruma Kanunu) | Mainland kullanıcı openid, telefon, mesaj içeriği KKTC/EU/ABD sunucusuna giderse **sınır ötesi transfer yükümlülüğü** `[doğrulanmalı]` | SCC filing, PI Protection Certification, ayrı rıza — [`wechat-integration-feasibility.md` §6.1](./wechat-integration-feasibility.md) |
| **DSL / CSL** (Veri Güvenliği / Siber Güvenlik) | Kritik veri, güvenlik değerlendirmesi, yerel barındırma baskısı | Mainland ağır PII senaryosunda Çin içi veya onaylı mekanizma |
| **ICP filing / ICP lisansı** | Mainland sunucu + mainland Mini Program → **ICP gerekir**; overseas entity + overseas hosting → genelde **hayır** `[doğrulanmalı]` | Politika değişebilir |
| **Cross-border data transfer** | Audit log, onay kayıtları, kullanıcı mesaj özetleri | Veri minimizasyonu; audit residency ayrı karar |

**KKTC entity notu:** Tencent'te muhtemelen **overseas / non-Mainland** sınıfı; mainland hesap özellik setinden **dar** olabilir. KKTC ticaret sicil sınıflandırması başvuru öncesi teyit `[doğrulanmalı]`.

### 2.2 WeChat ekosistemi kısıtları

| Yüzey | Giriş engeli | Lumos ilişkisi |
|-------|--------------|----------------|
| **Subscription Account (订阅号)** | Yurtdışı kuruluşlar genelde **kayıt edemez** | Öncelik düşük |
| **Service Account (服务号)** | Overseas kayıt mümkün; Weixin Verification (~99 USD); webhook HTTPS | **Birincil resmi kanal** — bildirim + OAuth |
| **Mini Program (小程序)** | Overseas entity kayıt mümkün; ICP mainland için gerekir, overseas için muaf `[doğrulanmalı]` | **Mobil onay yüzeyi adayı** |
| **WeCom (企业微信)** | Kurumsal doğrulama (~700 RMB); B2B | Lumos B2B trust middleware |
| **Open Platform** | Developer certification (~300 RMB); resmi website zorunlu | Servis sağlayıcı / merchant auth modeli |
| **Kişisel WeChat** | Resmi API **yok**; bot/scraping **yasak** | Lumos kapsam **dışı** |

**API kısıtları (overseas vs mainland):** WeChat Pay native, WeChat Store, bazı template message'lar, rate limit farkları — erken feature matrix doğrulaması gerekir ([`wechat-integration-feasibility.md` §2.1](./wechat-integration-feasibility.md)).

### 2.3 Great Firewall, gecikme ve barındırma

| Konu | Engeller | Lumos etkisi |
|------|----------|--------------|
| **GFW / uluslararası latency** | KKTC/EU/ABD webhook sunucusuna Çin'den erişim yavaş veya kararsız olabilir | Server URL **Çin-edge veya mainland CDN** değerlendirmesi `[doğrulanmalı]` |
| **Tencent altyapısı** | Mesajlar Tencent'te işlenir; developer push payload alır | Webhook middleware tasarımı latency-tolerant olmalı |
| **Yerel bulut zorunluluğu** | Ağır PII senaryosunda Tencent Cloud / Alibaba Cloud baskısı | Region-aware deployment boundary (§4) |
| **HTTPS + domain erişilebilirliği** | WeChat server URL doğrulaması mainland'den erişilebilir olmalı | Prod domain + sertifika Çin erişim testi |

### 2.4 Ödeme (WeChat Pay) vs Lumos kapsamı

| Durum | Açıklama |
|-------|----------|
| **Lumos ödeme kapsamı** | OD-011: ödeme sistemi **aktif geliştirme dışı**; onaysız ödeme **yasak** ([`payment-scope-decision.md`](../memory/payment-scope-decision.md)) |
| **WeChat Pay native** | Mainland entity gerekir; overseas Service Account'ta **genelde yok** |
| **Cross-Border Pay** | Ayrı başvuru; finans lisansı / institution model `[doğrulanmalı]` |
| **Lumos için anlam** | WeChat Pay **Phase 2+ ticari paket**; trust/onay katmanı ödeme entegrasyonundan **ayrı** tutulmalı |

WeChat Pay, Lumos'un "trust and control layer" vaadinin **ön koşulu değildir**; ticari lansmanda ayrı compliance paketi.

### 2.5 Uygulama mağazası ve dağıtım

| Kanal | Engeller | Lumos alternatifi |
|-------|----------|-------------------|
| **iOS App Store (Çin)** | ICP + yerel entity baskısı; TestFlight mainland kullanıcıları için sınırlı | **Mini Program** veya **H5 + WeChat OAuth** |
| **Android** | Google Play Çin'de yok; Huawei/Xiaomi/Oppo store'lar ayrı süreç | APK sideload / marka store / Mini Program |
| **Mini Program** | WeChat içi dağıtım; review süreci | Onay yüzeyi + hafif UX — **Phase 1 aday** |
| **LAN relay (mevcut OSS)** | Aynı Wi-Fi gerektirir; internet üzerinden Çin'de **yetersiz** | Poll + WeChat bildirim veya Mini Program |

### 2.6 Dil, i18n ve uyum metinleri

| Konu | Mevcut durum | Çin gap |
|------|--------------|---------|
| **Panel locale** | `tr` \| `en` yalnızca ([`ui/src/i18n/runtime.ts`](../../ui/src/i18n/runtime.ts)) | **`zh-CN` zorunlu** — onay, consent, güvenlik uyarıları |
| **Uyum kopyası** | ADR-012, consent, SECURITY_NEVER_AUTO metinleri TR/EN | Yerel dilde açık rıza, veri işleme bildirimi `[doğrulanmalı]` |
| **WeChat UI dili** | — | Mini Program / SA menüleri Çince veya çift dil |
| **Hukuki metin** | Lumos sözleşmesi TR odaklı | Mainland kullanıcı için ayrı privacy policy / ToS `[doğrulanmalı]` |

---

## 3. Yerel entegrasyon ihtiyaçları

### 3.1 WeChat Login / OAuth

| İhtiyaç | Açıklama |
|---------|----------|
| **OAuth2 web auth (openid / unionid)** | Service Account veya Open Platform üzerinden kullanıcı kimliği |
| **Overseas entity** | KKTC/TR entity ile mümkün `[doğrulanmalı]` — Google/Apple Sign-In **Çin'de güvenilir değil** |
| **Lumos hizası** | Kimlik ≠ consent ≠ işlem onayı (ADR-010); WeChat openid vault'ta, panelde secret yok |
| **Grant modeli** | Mail stub pattern: `wechat_read`, `wechat_notify`, `wechat_send_with_approval` — demo-safe public; impl private |

### 3.2 WeChat mesajlaşma bildirimleri (push alternatifi)

| Mevcut Lumos | Çin gerçeği |
|--------------|-------------|
| FCM/APNs **yok** ([`lumos-mobile-approval-mvp-plan.md` §1](./lumos-mobile-approval-mvp-plan.md)) | Google servisleri engelli; Apple push sınırlı |
| Poll-first MVP (3–30s gecikme) | Kabul edilebilir fallback; UX zayıf |
| LAN relay (RB-06) | Aynı LAN — Çin'de ev/ofis dışı **yetersiz** |

**WeChat alternatifleri:**

| Kanal | Kullanım | Kısıt |
|-------|----------|-------|
| **Service Account — Customer Service API** | 48 saat etkileşim penceresi; onay isteği mesajı | Kullanıcı SA'ya yazmış olmalı |
| **Template / subscription message** | Yapılandırılmış onay bildirimi | Sektör onayı, kategori kısıtı `[doğrulanmalı]` |
| **Mini Program — subscribe message** | Onay kartı + deep link | Mini Program aboneliği gerekir |
| **WeCom uygulama mesajı** | B2B onay | Kurumsal doğrulama |

**Sonuç:** Çin'de mobil onay için **WeChat resmi kanalları birincil aday**; FCM/APNs mimarisine hardcode **yapılmamalı**.

### 3.3 Mini Program — mobil onay yüzeyi?

| Artı | Eksi |
|------|------|
| WeChat içi dağıtım; App Store engeli aşılır | Ayrı frontend + backend; Tencent review |
| Onay kartı, approve/reject UX native WeChat dilinde | openid ↔ Lumos `lumos_id` eşlemesi gerekir |
| Poll yerine **kullanıcı tetiklemeli** veya subscribe message | Backend mainland latency / PIPL |

**Öneri:** Mini Program, Lumos Mobile native uygulamasının **Çin eşdeğeri** olarak Phase 1 POC'ta değerlendirilir — LAN relay'in internet-üzerinden karşılığı değil, **bölgesel onay yüzeyi**.

### 3.4 Yerel bulut vs mevcut mimari

| Katman | Mevcut (OSS / plan) | Çin ihtiyacı |
|--------|---------------------|--------------|
| **Kullanıcı cihazı + köprü** | Local-first; `127.0.0.1` kando_bridge | Değişmez — PC tarafı |
| **Pending onay** | `.lumos/pending_approvals/` disk | Değişmez — tek kaynak |
| **Relay** | LAN relay demo (private TLS) | **Internet relay** + mainland edge veya tünel `[doğrulanmalı]` |
| **Webhook ingress** | Yok (prod private) | Tencent → HTTPS endpoint (Çin-erişilebilir) |
| **Bulut** | KKTC/EU varsayımı | Tencent Cloud / Alibaba — **region-aware** config |

**Hibrit model (önerilen fizibilite):** PC + köprü local-first kalır; **bildirim + uzaktan onay yüzeyi** WeChat/Mini Program + opsiyonel mainland relay private katmanda.

### 3.5 SMS / OTP alternatifleri

| Senaryo | Alternatif |
|---------|------------|
| Push engelli | WeChat template message; Mini Program subscribe |
| OAuth / pairing | WeChat OAuth; 6 haneli pairing code (mevcut RB-06) **+** SMS OTP mainland operatör `[doğrulanmalı]` |
| 2FA / cihaz doğrulama | WeChat doğrulama; SMS (Aliyun/Tencent SMS API) — ayrı compliance |
| Lumos ilkesi | OTP credential vault'ta; onaysız SMS gönderimi yok |

### 3.6 Sosyal paylaşım ve deep link

| İhtiyaç | WeChat mekanizması |
|---------|-------------------|
| Onay linki paylaşımı | Mini Program path / SA menu link — **token link chat'te sızıntı riski** ([`device-pairing-strategy.md` §3.3](./device-pairing-strategy.md)) |
| Universal link | WeChat **dış URL kısıtları**; whitelist domain |
| QR | Pairing + Mini Program launch — Phase 1+ UX |
| Lumos kuralı | `relay_token` / onay token'ı kalıcı chat paylaşımına **uygun değil** |

---

## 4. Lumos mimarisinde şimdiden düşünülecekler

Aşağıdakiler **somut mimari kancalar**dır — Phase 0'da arayüz/sözleşme dokümantasyonu; **uygulama Phase 1+ private katman**.

### 4.1 Bildirim kanalı soyutlaması (push / WeChat / poll)

```
PendingApprovalCreated
       │
       ▼
┌──────────────────────────────────────┐
│  NotificationChannel (interface)      │
│  · deliver(context) → DeliveryResult  │
│  · channel_id: poll | fcm | wechat_sa │
│    | wechat_mp | sms | none           │
└──────────────────────────────────────┘
       │
       ├── PollChannel (OSS — mevcut MVP)
       ├── WeChatServiceAccountChannel (private)
       ├── WeChatMiniProgramSubscribeChannel (private)
       └── FcmApnsChannel (private — non-China)
```

**Kurallar:**

- Kanal seçimi **region + grant + kullanıcı tercihi** ile; hardcode FCM yok.
- Tüm kanallar aynı pending kaynağını tüketir (`.lumos/pending_approvals/`).
- Başarısız teslimat → poll fallback; kanıt/log provenance zorunlu.

### 4.2 Kimlik sağlayıcı eklentisi (Google/Apple hardcode yok)

| Bileşen | Mevcut | Hedef kanca |
|---------|--------|-------------|
| `DeviceIdentity` | Ed25519 local (`src/security/identity.py`) | Değişmez — cihaz kimliği |
| Harici IdP | Yok (demo) | `IdentityProvider` plugin: `local`, `wechat_oauth`, `apple`, `google` |
| Eşleme | — | `external_subject` (openid) ↔ `lumos_id` vault kaydı |
| Public OSS | Generic grant + interface stub | Provider adı/secret **private** |

### 4.3 Bölge-farkında deployment sınırı

| Config | Örnek |
|--------|-------|
| `deployment.region` | `global` \| `cn` \| `eu` \| `tr` |
| `deployment.data_residency` | PII sınıfı → bölge eşlemesi |
| `deployment.notification_channels` | `cn` → wechat_* ; `global` → fcm, poll |
| `deployment.webhook_ingress` | Bölgeye göre endpoint URL (public docs'ta prod URL yok) |

**İlke:** Tek binary/deployment ile tüm bölgeler **zorunlu değil**; config-driven boundary.

### 4.4 Veri ikameti (data residency) config

| Veri sınıfı | Varsayılan (non-CN) | CN senaryosu `[doğrulanmalı]` |
|-------------|---------------------|----------------------------------|
| WeChat AppSecret / token | Private vault | Aynı — asla public |
| Mainland user PII (openid, phone) | Minimize / EU-KKTC | Çin içi veya SCC |
| Pending approval metadata | Yerel disk (PC) | PC yerel; cloud sync **opsiyonel ayrı** |
| Audit log (redacted) | Müşteri sözleşmesi | CN residency veya cross-border onay |
| Policy kararları | Private professional | Private professional |

### 4.5 i18n / locale pipeline

| Adım | Phase 0 |
|------|---------|
| `Locale` tipi genişlemesi | `tr` \| `en` → `zh-CN` planlı |
| Mesaj katalog yapısı | Mevcut `ui/src/i18n/messages/` pattern korunur |
| Compliance copy | Consent, onay, SECURITY_NEVER_AUTO — ayrı `legal/` namespace |
| WeChat Mini Program | Panel i18n ile **paylaşılan anahtar sözlük** hedefi (DRY ilke; impl sonra) |

### 4.6 Onay cihaz kanalının LAN-only'den ayrışması

Mevcut RB-06 LAN relay **demo-safe OSS**; Çin ve internet senaryosu için:

| Kavram | Açıklama |
|--------|----------|
| `ApprovalTransport` | `lan_relay` \| `internet_relay` \| `wechat_surface` \| `direct_loopback` |
| `PairingStrategy` | `pairing_code`, `qr`, `wechat_oauth` — [`device-pairing-strategy.md`](./device-pairing-strategy.md) ile hizalı |
| Secret taşıma | `KANDO_BRIDGE_SECRET` Mobile'a **asla**; relay-scoped token (mevcut `relay_token` pattern) |
| LAN bağımlılığı | Transport seçimi runtime; onay **mantığı** transport'tan bağımsız |

### 4.7 Audit log residency

| Gereksinim | Kanca |
|------------|-------|
| Onay/red olayları | `audit_sink` plugin: `local_file`, `regional_cloud`, `wechat_callback_log` |
| Provenance | Kanal, cihaz, region, IdP — PII redaction |
| CN | Audit mainland'de tutulması gerekebilir `[doğrulanmalı]` |
| Public OSS | Audit **format/schema** demo; prod sink private |

### 4.8 OSS public vs Çin ticari private split

| Bileşen | `lumos-core` (public) | Private / professional |
|---------|-------------------------|-------------------------|
| NotificationChannel | Interface + poll demo | WeChat, FCM, SMS impl |
| IdentityProvider | Interface stub | WeChat OAuth, token exchange |
| Webhook handler | — | SA/WeCom XML/JSON, AES decrypt |
| Mini Program | — | Frontend + backend |
| PIPL / compliance ops | — | Strategy vault |
| Internet relay / TLS prod | LAN demo iskelet | Prod relay, mainland edge |
| AppSecret / merchant | **Asla** | Vault purpose_codes |

Detay: [`public-repo-boundary.md`](../memory/public-repo-boundary.md), [`wechat-integration-feasibility.md` §10](./wechat-integration-feasibility.md).

---

## 5. Lumos mevcut durum uyumu

### 5.1 Bugün çalışan (Çin'e kısmen uyarlanabilir)

| Bileşen | Durum | Çin uyumu |
|---------|-------|-----------|
| **Poll-first onay** | RB-04 + RB-06 doğrulandı | Gecikmeli ama **GFW'den bağımsız** fallback |
| **Pending disk sözleşmesi** | `lumos.pc_remote_pending_approval.v1` | Transport agnostic — **korunmalı** |
| **Onay kapısı / token tüketimi** | `validate_approval_token`, tek kullanımlık | Trust modeli WeChat ile **uyumlu** |
| **LAN relay + pairing code** | 6 hane, TTL, relay_token | Aynı LAN senaryosu; **internet/Çin için yetersiz tek başına** |
| **Entegrasyon felsefesi** | Resmi API, onaysız dış etki yok | WeChat işletme API ile **hizalı** |
| **Local-first köprü** | `127.0.0.1` kando_bridge | PC workspace modeli değişmez |
| **Grant modeli (mail stub)** | `read`, `notify`, send_with_approval | WeChat grant'larına **şablon** |

### 5.2 Çin gap'leri (blokör veya ciddi eksik)

| Gap | Etki | Öncelik |
|-----|------|---------|
| **FCM/APNs / push yok** | Anlık onay UX | Yüksek — WeChat kanalı gerekir |
| **Internet relay yok** | Uzaktan onay | Yüksek |
| **WeChat OAuth / webhook yok** | Kimlik + bildirim | Yüksek |
| **Mini Program yok** | Dağıtım + onay yüzeyi | Orta–yüksek |
| **zh-CN i18n yok** | Kullanılabilirlik + compliance copy | Orta |
| **Region / data residency config yok** | PIPL operasyonu | Orta–yüksek |
| **Google/Apple IdP varsayımı (gelecek)** | Login | Orta — plugin şart |
| **Multi-device registry (prod)** | Cihaz envanteri | Orta — IA taslak var, impl yok |
| **PIPL compliance paketi yok** | Hukuki Proceed engeli | **Blokör (mainland PII)** |
| **WeChat Pay** | Ticari gelir | Defer (OD-011) |

### 5.3 Cihaz bağlantı mimarisi — Çin lensi

[`device-connection-architecture-draft.md`](./device-connection-architecture-draft.md) ve [`device-connection-information-architecture.md`](./device-connection-information-architecture.md) v1 modeli:

- **Bağlı cihaz = aynı makinede köprü + panel** (public foundation).
- Çin'de **ikinci cihaz (telefon)** = WeChat Mini Program veya internet relay + WeChat bildirim; LAN discovery **tek başına yeterli değil**.
- Panel «Bağlantılar» IA'sı WeChat'i **Entegrasyonlar** kataloğunda gösterecek şekilde genişletilebilir (D3 açık karar).

---

## 6. Risk matrisi

| Alan | Risk | Erken hazırlık (Phase 0) | Defer |
|------|------|---------------------------|-------|
| **PIPL / cross-border PII** | Mainland veri KKTC/EU'ya — yüksek ceza riski `[doğrulanmalı]` | Data residency config; minimizasyon ilkesi; hukuk danışmanı brief | Mainland prod kullanıcı toplama |
| **Kişisel WeChat otomasyon** | Hesap kapatma; ToS ihlali | Kapsam dışı ilan; resmi API only docs | Scraping/bot POC |
| **Push (FCM/APNs) bağımlılığı** | Çin'de çalışmaz | NotificationChannel abstraction | FCM-first mobile stratejisi |
| **LAN-only onay** | Ev dışı/onay kaçırma | ApprovalTransport ayrımı; WeChat POC planı | LAN relay'i prod Çin çözümü sanma |
| **Overseas SA API limitleri** | Pay/store/template kısıt | Feature matrix erken doğrulama | Native WeChat Pay entegrasyonu |
| **ICP / mainland hosting** | Yanlış barındırma → servis kesintisi | Region deployment boundary doc | Mainland sunucu kurulumu |
| **i18n (zh-CN)** | UX + compliance copy eksik | Locale pipeline + key structure | Mainland marketing lansmanı |
| **App Store (iOS CN)** | Dağıtım engeli | Mini Program stratejisi | Native iOS Çin store |
| **Webhook latency / GFW** | Onay gecikmesi / timeout | Edge hosting değerlendirme; poll fallback | Tek bölge global webhook |
| **Public repo sızıntısı** | AppSecret, PIPL ops, prod URL | Boundary checklist; stub only | Prod credential commit |
| **Trust motoru (ADR-007 Faz 4)** | Parçalı enforcement | Dar policy gate; pending onay hattı | Birleşik trust motoru beklentisi |
| **WeChat Pay** | Finans lisansı | OD-011 defer kaydı | Ödeme entegrasyonu |

---

## 7. Önerilen fazlama

### Phase 0 — Şimdi (mimari dokümantasyon + arayüzler)

**Hedef:** Ticari lansman yok; **yanlış kilitlenmeyi önle**.

| Çıktı | Tür |
|-------|-----|
| `NotificationChannel` sözleşme taslağı | Doc / stub interface |
| `IdentityProvider` plugin taslağı | Doc / stub interface |
| `ApprovalTransport` ayrımı (LAN vs internet vs WeChat) | Doc — bu belge + device-pairing genişlemesi |
| `deployment.region` / `data_residency` config şeması | Doc |
| `zh-CN` i18n backlog maddesi | Doc / issue |
| Public vs private boundary checklist (WeChat) | Doc — [`wechat-integration-feasibility.md` §10](./wechat-integration-feasibility.md) ile hizalı |
| Hukuk danışmanı brief (PIPL, ICP, entity) | Ops — repo dışı |

**Kapsam dışı Phase 0:** Prod webhook, Mini Program kodu, mainland sunucu, WeChat Pay.

### Phase 1 — Mini Program onay POC (private katman)

**Önkoşullar:** Phase 0 arayüzleri; overseas SA veya MP kaydı `[doğrulanmalı]`; PIPL brief tamamlandı (mainland PII varsa).

| Adım | Açıklama |
|------|----------|
| 1 | Overseas Service Account veya Mini Program kaydı + verification |
| 2 | Webhook middleware (policy gate) — [`wechat-integration-feasibility.md` Desen A](./wechat-integration-feasibility.md) |
| 3 | Mini Program: pending listesi + approve/reject (poll veya subscribe message) |
| 4 | `openid` ↔ Lumos eşlemesi vault'ta |
| 5 | zh-CN onay metinleri |
| 6 | E2E: PC pending → WeChat bildirim → onay → köprü consume |

**Başarı ölçütü:** Mainland test kullanıcısı (sınırlı) ile uçtan uca onay; audit provenance; **public repoda secret yok**.

### Phase 2 — Ticari lansman Çin

**Önkoşullar:** Phase 1 POC; yerel hukuk onayı; ops runbook; vitrin (welockai.com — OD-048); isteğe bağlı mainland entity / ICP; Cross-Border Pay (ayrı karar).

| Alan | Kapsam |
|------|--------|
| Prod barındırma | Region-aware; mainland edge veya hybrid |
| Dağıtım | Mini Program prod + opsiyonel Android store |
| Ödeme | WeChat Pay / Cross-Border — OD-011 paketi sonrası |
| Compliance | SCC/Certification; privacy policy zh-CN |
| Operasyon | Tencent review, incident, key rotation runbook (private ops vault) |

---

## 8. Açık kararlar ve hukuki sorumluluk reddi

### 8.1 Açık kararlar

| # | Karar | Seçenekler | Not |
|---|-------|------------|-----|
| C1 | Çin birincil onay yüzeyi | Mini Program vs SA template message vs WeCom | Phase 1 POC öncesi |
| C2 | Mainland PII stratejisi | Minimize vs Çin içi barındırma vs SCC | **Hukuk review zorunlu** |
| C3 | Entity yapısı | KKTC overseas only vs mainland WFOE | Pay + ICP etkiler |
| C4 | Internet relay vs WeChat-only uzaktan onay | Hybrid | LAN relay Çin prod değil |
| C5 | zh-CN birincil mi çift dil mi | UX + legal | |
| C6 | Audit log residency (CN) | Local PC vs regional cloud | |
| C7 | WeChat entegrasyonu public stub'da mı | Generic `MessagingChannel` only | Boundary §9 |

### 8.2 Hukuki sorumluluk reddi

- Bu belge ve [`wechat-integration-feasibility.md`](./wechat-integration-feasibility.md) **hukuki tavsiye değildir**.
- ICP, PIPL, DSL, CSL, WeChat Pay lisansları ve sözleşmeler **yerel Çin hukuk danışmanı** ile değerlendirilmelidir.
- `[doğrulanmalı]` maddeler operasyonel başvuru veya resmi Tencent/partner teyidi olmadan **Proceed sayılmaz**.
- Lumos **onaysız dış etki yapmaz**; WeChat entegrasyonu da aynı çekirdek sözleşmeye tabidir.

---

## 9. Public repo boundary — Çin / WeChat özel

[`public-repo-boundary.md`](../memory/public-repo-boundary.md) ve workspace `public-github-boundary` kurallarına göre **`lumos-core` public deposuna GİRMEMESİ gerekenler:**

| Kategori | Örnekler |
|----------|----------|
| **Credential / secret** | WeChat AppID/AppSecret, EncodingAESKey, merchant key, relay prod token |
| **Prod endpoint** | Webhook URL, mainland API gateway, Tencent Cloud resource ID |
| **PIPL / compliance ops** | SCC filing, data processing agreement, mainland user list |
| **WeChat Pay** | Merchant ID, settlement, Cross-Border Pay credential |
| **Prod orchestration** | Webhook handler impl, token refresh, Mini Program prod backend |
| **Operasyonel runbook** | Canlı IP, SSH, mainland deploy komutları |
| **Tenant PII** | openid, mainland telefon, mesaj içeriği arşivi |
| **Private strateji** | Çin pazar GTM, fiyatlandırma, partner sözleşmeleri |

**Public'te kalabilecekler:**

| Kategori | Örnekler |
|----------|----------|
| Generic kanal ilkesi | Onaysız gönderim yok; grant modeli (mail stub pattern) |
| Trust / onay terminolojisi | ADR-007, ADR-010, ADR-012 |
| Demo-safe interface | `NotificationChannel`, `IdentityProvider` **tip iskeletleri** (secret yok) |
| LAN relay demo | RB-06 iskelet (prod TLS/ internet relay değil) |
| Analiz belgeleri | Bu belge, fizibilite özeti — operasyonel detay redakte |
| i18n altyapı | Locale pipeline; `zh-CN` mesaj dosyası **çeviri metni prod copy değilse** |

**Drift uyarısı:** Stub kod varlığı «WeChat entegrasyonu hazır» anlamına **gelmez** ([`public-repo-boundary.md` §C](../memory/public-repo-boundary.md)).

---

## 10. Kaynaklar ve çapraz referanslar

| Konu | Belge |
|------|-------|
| WeChat ekosistemi derinlemesi | [`wechat-integration-feasibility.md`](./wechat-integration-feasibility.md) |
| Mobil onay MVP | [`lumos-mobile-approval-mvp-plan.md`](./lumos-mobile-approval-mvp-plan.md) |
| LAN relay doğrulama | [`pr-rb-06-lan-relay-verification.md`](./pr-rb-06-lan-relay-verification.md) |
| Eşleştirme stratejileri | [`device-pairing-strategy.md`](./device-pairing-strategy.md) |
| Cihaz mimarisi | [`device-connection-architecture-draft.md`](./device-connection-architecture-draft.md) |
| Dış entegrasyon izinleri | [`external-integrations-permissions.md`](../memory/external-integrations-permissions.md) |
| Ödeme defer | [`payment-scope-decision.md`](../memory/payment-scope-decision.md) |
| Public sınır | [`public-repo-boundary.md`](../memory/public-repo-boundary.md) |
| Tencent — Service Account push | https://developers.weixin.qq.com/doc/service/en/guide/dev/push/ |
| Tencent — Overseas Mini Program | https://developers.weixin.qq.com/community/business/doc/000a86174e81f0836172539ce6140d |

---

*Belge sonu — `wechat-china-market-technical-readiness` v2026-06-22*
