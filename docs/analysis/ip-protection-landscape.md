# Lumos — Fikri Mülkiyet Koruma Manzarası

| Alan | Değer |
|------|--------|
| **Belge ID** | `ip-protection-landscape` |
| **Durum** | `analiz` — koruma çerçevesi envanteri; hukuki tescil kararı bekliyor |
| **Tarih** | 2026-06-21 |
| **Dil** | Türkçe (birincil) |
| **Kapsam** | `lumos-core` public OSS foundation + We Lock AI ticari katman sınırı |
| **Üst sınır** | [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md), [`docs/memory/public-repo-boundary.md`](../memory/public-repo-boundary.md), [`NOTICE`](../../NOTICE) |
| **İlgili ADR'ler** | [ADR-007](../decisions/ADR-007-trust-engine-layer.md), [ADR-011](../decisions/ADR-011-lock-semantics-decision.md), [ADR-012](../decisions/ADR-012-lumos-security-codex.md), [ADR-013](../decisions/ADR-013-lumos-quantum-security-readiness.md) |
| **Ticari referans** | [`commercial-product-packaging.md`](./commercial-product-packaging.md) (Starter / Pro / Business) |
| **Marka / vitrin** | OD-048/049/052 — [`od-048-landing-vitrin-decision.md`](../memory/od-048-landing-vitrin-decision.md) (`needs-review`) |
| **Public OSS lisansı** | Apache License 2.0 — [`LICENSE`](../../LICENSE) |
| **Son güncelleme** | 2026-06-21 |

---

## Yönetici özeti

Lumos fikri mülkiyet portföyü **iki katmanlıdır**: (1) **public `lumos-core`** — Apache-2.0 altında açık kaynak foundation kodu, dokümantasyon ve demo-safe stub'lar; (2) **private / professional katman** — ticari hizmet, production orchestration, operasyonel altyapı ve kullanıcı verisi — public repoda **bilerek yoktur** ([`public-repo-boundary.md`](../memory/public-repo-boundary.md)).

**Ana koruma stratejisi (önerilen çerçeve):**

| Katman | Birincil koruma aracı | Not |
|--------|----------------------|-----|
| Açık kaynak kod + docs | Telif (Apache-2.0) + NOTICE ayrımı | Marka ve resmi hizmet lisans dışı |
| Marka (Lumos, We Lock AI) | Marka tescili + lisans sözleşmesi | OSS klonu marka hakkı vermez |
| Private orchestration / prod | Ticari sır + sözleşme + erişim kontrolü | Public yayın = sır kaybı riski |
| Güvenlik mimarisi (codex, trust) | Telif (public kısım) + patent *değerlendirmesi* (seçili alanlar) | Patent iddiası yok — potansiyel envanter |
| UI / panel metinleri | Telif + marka | i18n içerik telif kapsamında |

**Durum:** Ürün erken geliştirme aşamasındadır; resmi / ücretli hizmet henüz yayınlanmamıştır ([`README.md`](../../README.md)). Bu belge **koruma yol haritasıdır**; tescil başvurusu veya hukuki sonuç garantisi içermez.

---

## 1. Mevcut IP varlıkları

### 1.1 Envanter özeti

| Kategori | Varlık | Konum / kanıt | Koruma durumu | Public / Private |
|----------|--------|---------------|---------------|------------------|
| **Yazılım (OSS)** | Lumos çekirdek kodu | `src/`, `task_engine/`, `panel/`, `ui/` | Apache-2.0 | Public |
| **Lisans metni** | LICENSE + NOTICE | Repo kökü | Hukuki metin | Public |
| **ADR / karar kayıtları** | Güvenlik codex, trust, lock, quantum readiness | `docs/decisions/` | Telif (belge) | Public |
| **Analiz / planlama** | Ticari paketleme, banka checklist, bu belge | `docs/analysis/` | Telif (belge) | Public (strateji özeti) |
| **UI / panel** | Astro/React panel, i18n metinleri | `ui/`, `panel/` | Telif | Public |
| **Marka metinleri** | Lumos, We Lock AI, welockai.com referansları | README, NOTICE, UI i18n | Marka + telif ayrımı | Public (isim); logo ayrı |
| **Güvenlik ilkeleri** | Karar sözleşmesi, confirmation policy | `docs/`, `src/policy/` | Telif + uygulama | Public (ilke); prod detay private |
| **Demo stub entegrasyonlar** | Mail/vault adapter iskeletleri | `src/integrations/` | Apache-2.0 | Public (demo-safe) |
| **İç katman persona** | Core, Local, Sentinel tanımları | `docs/lumos-persona-layers.md` | Telif (dok); uygulama private | Public (yüksek seviye) |
| **Resmi hizmet / prod API** | Barındırılan panel, auth, entegrasyonlar | Private katman | Ticari sır + sözleşme | **Private** |
| **Operasyonel runbook'lar** | Infra, deploy, smoke | `.lumos/internal/ops-vault/` | Ticari sır | **Private** |
| **Mail / kanal stratejisi** | Otomasyon spec, vault seçimi | `.lumos/internal/strategy-vault/` | Ticari sır | **Private** |

### 1.2 Kod tabanı IP bileşenleri (public)

| Bileşen | IP türü | Not |
|---------|---------|-----|
| Task engine + profil matrisi (`rapor`, `guvenli_yurut`, `kisitli_otonom`) | Telif (kod) | `SECURITY_NEVER_AUTO` sözleşmesi |
| Security codex uygulama izleri | Telif + süreç know-how | ADR-012; enforcement haritası |
| Trust / lock / consent parçaları | Telif (kod) | Birleşik trust motoru henüz yok (ADR-007) |
| Confirmation policy (CU4) | Telif (kod) | Opt-in; işlem bazlı onay |
| Quantum Readiness tarayıcı | Telif (kod) | Salt okunur; PQC iddiası yok (ADR-013) |
| Panel köprüsü + bridge script'leri | Telif (kod) | Dev köprü; prod policy private |
| Workspace sözleşmesi (`.lumos/` omurgası) | Telif (kod + docs) | Trash, config, tasks yapısı |

### 1.3 Dokümantasyon IP bileşenleri

| Belge grubu | İçerik değeri |
|-------------|---------------|
| ADR serisi (001–013+) | Mimari karar, terminoloji, güvenlik sözleşmesi |
| `lumos-karar-sozlesmesi.md` | Çekirdek davranış sözleşmesi — dokunulmaz alan tanımı |
| `security-architecture.md` | Canonical güvenlik ilkeleri (secret içermez) |
| `commercial-product-packaging.md` | Starter / Pro / Business paketleme önerisi |
| `public-repo-boundary.md` | OSS vs private ayrımının tek kaynağı |

---

## 2. Tescile uygun IP'ler

> **Not:** Tescil uygunluğu yerel mevzuat, önceki haklar ve somut kullanım kanıtına bağlıdır. Aşağıdaki tablo **değerlendirme çerçevesidir**.

### 2.1 Marka (tescil adayı)

| Aday | Sınıf önerisi (yüksek seviye) | Öncelik | Gerekçe |
|------|-------------------------------|---------|---------|
| **Lumos** | Yazılım / SaaS / AI asistan (Nice 9, 42) | **Yüksek** | Birincil ürün adı; panel, README, i18n |
| **We Lock AI** / **WeLock AI** | Yazılım / teknoloji hizmetleri (9, 42) | **Yüksek** | Çatı marka; NOTICE, welockai.com |
| **welockai** (kelime) | 9, 42, 35 (hizmet) | **Yüksek** | Domain ve ticari vitrin |
| **Lumos Panel** | 9, 42 | Orta | UI yüzey adı |
| **Lumos Core** | 9, 42 | Orta | OSS repo adı; açık kaynak ile birlikte |
| **Lumos Quantum Readiness** | 9, 42 | Orta | Alt ürün / modül adı (ADR-013) |
| **Starter** | 9, 42 | Düşük / koşullu | Jenerik; birleşik kullanım gerekir ("Lumos Starter") |
| **Pro** | 9, 42 | Düşük / koşullu | Çok jenerik; tek başına zayıf |
| **Business** | 9, 42 | Düşük / koşullu | Jenerik; "Lumos Business" birleşik düşünülmeli |
| **Core** | 9, 42 | Düşük (savunma) | İç katman; kullanıcıya yansıtılmaz — savunma amaçlı |

**Marka adayı sayısı (envanter):** **10** (Lumos, We Lock AI, welockai, Lumos Panel, Lumos Core, Lumos Quantum Readiness, Starter, Pro, Business, Core).

### 2.2 Telif (kayıt / belgeleme)

| Varlık | Tescil / kayıt türü | Uygulanabilirlik |
|--------|---------------------|------------------|
| Kaynak kodu (Apache-2.0) | Otomatik telif; lisans NOTICE ile | Zaten lisanslı; ek kayıt opsiyonel |
| UI metinleri (TR/EN i18n) | Telif; bazı ülkelerde gönüllü kayıt | AB/TR/ABD'de kayıt delil gücü artırır |
| Dokümantasyon (ADR, analiz) | Telif | Repo tarihçesi + commit kanıtı |
| Logo / görsel kimlik | Telif + marka | OD-050/051 logo kararı ayrı; henüz public commit yok |
| Landing / pazarlama kopyası | Telif | OD-048 `needs-review` |

### 2.3 Patent (başvuru değerlendirmesi — iddia yok)

Patent başvurusu **önerilmez veya reddedilmez** bu belgede; yalnızca teknik alan envanteri yapılır (Bölüm 4).

### 2.4 Ticari sır (tescil değil — koruma rejimi)

Ticari sırlar resmi tescile tabi değildir; **gizlilik, erişim kontrolü ve sözleşme** ile korunur (Bölüm 3).

---

## 3. Ticari sır olarak korunacak alanlar

Public GitHub boundary ([`public-repo-boundary.md`](../memory/public-repo-boundary.md), workspace `public-github-boundary` kuralları) ile hizalı **kategori düzeyinde** liste:

| # | Kategori | İçerik (kategori düzeyi) | Public'te olan | Public'te olmayan |
|---|----------|---------------------------|----------------|-------------------|
| 1 | **Private orchestration katmanı** | Görev dağılımı, iç ajan koordinasyonu, prod akış | Persona tanımı (yüksek seviye) | Uygulama, endpoint, kural motoru |
| 2 | **Production API ve barındırılan hizmet** | Resmi panel backend, auth, rate limit | Stub / demo | Canlı API, credential, tenant modeli |
| 3 | **Operasyonel altyapı** | Sunucu, deploy, firewall, DNS, smoke | Placeholder notice | `.lumos/internal/ops-vault/` |
| 4 | **Mail / iletişim otomasyon stratejisi** | Kural motoru, granüler izin matrisi, kanal roadmap | Demo-safe stub (`src/integrations/mail/`) | Tam spec, pilot sırası, provider seçimi |
| 5 | **Vault / secret yönetimi (prod)** | Credential şeması, Infisical/vault operasyonu | Adapter arayüzü iskeleti | Prod yazma, rotation, purpose kodları |
| 6 | **Ödeme / abonelik altyapısı** | PSP, checkout, webhook, fatura | OD-011 ilke kararı | Credential, merchant ID, canlı entegrasyon |
| 7 | **Cihaz kontrolü ve prod entegrasyonlar** | IoT, araç, ev otomasyon prod bağlantıları | Modül iskeleti / dil | Canlı connector, cihaz protokolleri |
| 8 | **Kullanıcı verisi sistemleri** | Resmi hizmette saklanan PII / tenant data | — | Tamamen private |
| 9 | **Private entegrasyon pilotları** | Gmail/Slack/GitHub prod OAuth akışları | Contract tipleri | Token exchange, canlı handler |
| 10 | **Bridge prod güvenlik politikası** | Uzak köprü token, IP allowlist, prod secret | Dev loopback script | Prod hosting policy |
| 11 | **Entropy Lab prod konfigürasyonu** | IBM Runtime, ücretli API, prod entropy yolu | Deneysel sağlayıcı kodu (public) | Prod credential ve maliyet/onay akışı |
| 12 | **Ticari fiyatlandırma ve sözleşme paketleri** | Pro/Business nihai fiyat, kurumsal ekler | Planlama çerçevesi | Müzakere edilen sözleşmeler |
| 13 | **İç iletişim protokolü (Sentinel / imzalama)** | Lumos → Core / Local kanal bütünlüğü | OD-006/007 karar özeti | Protokol implementasyonu |

**Ticari sır kategori sayısı:** **13**

### 3.1 Ticari sır koruma uygulamaları (önerilen çerçeve)

| Uygulama | Açıklama |
|----------|----------|
| **Erişim listesi** | Strategy-vault ve ops-vault yalnızca yetkili operatör |
| **NDA / çalışan sözleşmesi** | Private katmana erişen tüm taraflar |
| **Commit öncesi tarama** | Public `docs/` altında IP/SSH/secret/provider detayı yasağı |
| **Ayrı repo / private paket** | Prod impl public repoya merge edilmez |
| **OSS lisans ayrımı** | NOTICE: marka ve resmi hizmet Apache-2.0 dışı |

---

## 4. Patent potansiyeli taşıyan alanlar

> **Uyarı:** Aşağıdaki liste **teknik alan envanteridir**. Patentlenebilirlik, yenilik, buluş basamağı ve önceki sanat (prior art) **değerlendirilmemiştir**. Hukuki patent iddiası veya garantisi **yoktur**.

| Teknik alan | Repo izi | Potansiyel değerlendirme | Gerekçe |
|-------------|----------|--------------------------|---------|
| **Çok katmanlı onay zinciri** (profil × policy × confirmation × consent) | ADR-012, `profiles.py`, `confirmation_policy.py` | **Potansiyel** | Birleşik "dur-kanıt-onay" modeli; önceki sanat yoğun alan |
| **İki sinyalli lock semantiği** (keystore_ready vs session_unlocked) | ADR-011 | **Zayıf / spesifik** | Dar uygulama; genel kilit kavramları prior art |
| **Trust durum hedef sözleşmesi** (8 durum) | ADR-007 | **Zayıf** | Dokümantasyon hedefi; birleşik motor yok |
| **SECURITY_NEVER_AUTO matrisi** | `task_engine/profiles.py` | **Zayıf / genel bilgi** | Politika tablosu; güvenlik best practice sınıfı |
| **Tek dış kapı (facade) mimarisi** | ADR-012 §1 | **Zayıf / genel bilgi** | Gateway pattern — yaygın mimari |
| **Trash prensibi + onaysız kalıcı silme yasağı** | Workspace sözleşmesi | **Zayıf / genel bilgi** | Soft-delete + onay UX |
| **Quantum Readiness salt okunur tarayıcı** | ADR-013, `scanner.py` | **Potansiyel (dar)** | Envanter + kanıt etiketli rapor; PQC uygulaması yok |
| **Patch proposal + protected apply pipeline** | `docs/ARCHITECTURE.md` | **Zayıf** | Code review / patch workflow |
| **Offline-first policy engine** | `offline_engine.py` | **Zayıf / genel bilgi** | Offline gate — bilinen pattern |
| **Panel ↔ CLI trust görünürlük ayrımı** | `panel_bridge_state.py` | **Zayıf** | UX/enforcement ayrımı |

**Önerilen çerçeve:** Patent başvurusu düşünülmeden önce **prior art taraması** ve **yerel patent vekili** ile dar alan seçimi (varsa: onay zinciri + readiness raporlama birleşimi). Public OSS yayını **prior art oluşturur** — başvuru zamanlaması kritiktir.

---

## 5. Marka koruması gereken alanlar

### 5.1 Birincil markalar

| Marka | Kullanım | Kaynak | Koruma önerisi |
|-------|----------|--------|----------------|
| **Lumos** | Ürün adı, panel, CLI, repo | README, NOTICE, UI i18n | Çoklu sınıf marka tescili; domain (lumos.*) savunması |
| **We Lock AI** | Çatı marka, telif sahibi | NOTICE, README, welockai.com | Tescil + OSS NOTICE ile lisans ayrımı |
| **welockai** | Domain, vitrin | README link | Domain + kelime markası |

### 5.2 İkincil / birleşik markalar

| Marka | Durum | Not |
|-------|-------|-----|
| **Lumos Panel** | Aktif UI | Panel başlığı i18n |
| **Lumos Core** | Repo adı | GitHub public identity |
| **Lumos Quantum Readiness** | ADR-013 alt marka | Abartılı kuantum iddiası yasağı ile tutarlı kullanım |
| **Starter / Pro / Business** | Planlama | Repoda tier yok; tescil öncesi kullanım kanıtı zayıf (Pro/Business jenerik) |

### 5.3 İç katman adları (düşük öncelik / savunma)

| Ad | Kullanıcıya görünür mü | Öneri |
|----|------------------------|-------|
| **Core** | Hayır (iç katman) | Savunma amaçlı tescil değerlendirmesi; README'de dev aracı olarak geçer |
| **Local** | Hayır | Tescil önceliği düşük |
| **Sentinel** | Hayır | Henüz uygulama pending (OD-006) |

### 5.4 Marka — OSS etkileşimi

[`NOTICE`](../../NOTICE) açıkça belirtir:

- Lumos ve We Lock AI **isim, logo, görsel kimlik** Apache-2.0 kapsamında **değildir**.
- Kaynak klonlama **marka kullanım hakkı vermez**.
- Resmi hizmet ve production API **ayrı sözleşme** gerektirir.

**OD-048 durumu:** Landing vitrin kopyası ve görsel ton `needs-review`; tescil öncesi nihai marka kullanım kılavuzu onaylanmalıdır.

---

## 6. Telif koruması gereken alanlar

### 6.1 Kod

| Varlık | Lisans | Koruma mekanizması |
|--------|--------|-------------------|
| `src/`, `task_engine/`, `panel/`, `ui/` kaynak kodu | Apache-2.0 | Lisans + telif bildirimi; katkı sözleşmesi (CONTRIBUTING — henüz yok) |
| Test kodu | Apache-2.0 | Ana repo ile birlikte |
| Script'ler (`scripts/`) | Apache-2.0 | Dev aracı; bridge README |

**Apache-2.0 etkisi:** Üçüncü taraflar kodu kullanabilir; **marka ve resmi hizmet hariç**. Patent grant clause (Apache §3) — patent ihtilaflarında lisans koşulları geçerli olabilir; **hukuk danışmanlığı gerekir**.

### 6.2 Dokümantasyon

| Varlık | Koruma |
|--------|--------|
| ADR'ler, analiz belgeleri, karar sözleşmesi | Telif — We Lock AI / Lumos |
| README, PRODUCT_SUMMARY, ROADMAP | Telif |
| Güvenlik / trust / codex belgeleri | Telif — mimari know-how belgesi |

### 6.3 UI ve pazarlama

| Varlık | Konum | Not |
|--------|-------|-----|
| Panel i18n (TR/EN) | `ui/src/i18n/messages/panel/` | Uzun form ürün metinleri |
| Landing / vitrin kopyası | Planlanan (OD-048) | Henüz final değil |
| Logo / görsel varlıklar | Public repo sınırlı | Marka + telif çift koruma |

### 6.4 Üçüncü taraf ve bağımlılıklar

- Bağımlılık lisansları `package.json`, `requirements` vb. ile uyumlu tutulmalı.
- Apache-2.0 uyumlu lisans tercihi korunmalı; copyleft zorunluluğu oluşturan bileşenler **IP stratejisini etkiler** — bağımlılık denetimi ayrı süreç.

---

## 7. Bölgesel koruma stratejileri

> **Genel uyarı:** Aşağıdaki alt bölümler **pratik koruma çerçevesidir**; yerel mevzuat, süre, maliyet ve başarı garantisi içermez. **KKTC ve Türkiye için yerel vekil şarttır** (Bölüm 9).

### 7.1 KKTC (Kuzey Kıbrıs Türk Cumhuriyeti)

| IP türü | Önerilen çerçeve | Kurum / not (yüksek seviye) |
|---------|------------------|----------------------------|
| **Marka** | Lumos + We Lock AI — KKTC'de kullanım ve banka incelemesi ([`bank-readiness-checklist.md`](./bank-readiness-checklist.md)) | KKTC marka rejimi — **yerel vekil**; TR tescili tek başına yeterli olmayabilir |
| **Telif** | Kod/docs otomatik koruma; kayıt opsiyonel | Yerel noter / meslek birliği pratiği — vekil |
| **Ticari sır** | Şirket KKTC kayıtlı; strategy/ops vault erişimi KKTC operasyon ekibi ile sınırlı | NDA + iç politika |
| **Patent** | Erken aşama — öncelik düşük | KKTC/TR patent vekili değerlendirmesi |
| **OSS** | Apache-2.0 geçerli; NOTICE Türkçe/İngilizce | Public repo boundary aynen uygulanır |

**KKTC özel not:** Banka / sanal POS hazırlığı ([`commercial-product-packaging.md` §8](./commercial-product-packaging.md)) marka ve şirket unvanı tutarlılığı gerektirir; marka tescili ile ticari unvan hizası vekil ile doğrulanmalıdır.

### 7.2 Türkiye

| IP türü | Önerilen çerçeve | Kurum / not |
|---------|------------------|-------------|
| **Marka** | Lumos, We Lock AI, welockai — Nice 9, 42 (ve gerekirse 35) | **TÜRİKPATENT** — ulusal marka; Madrid Protokolü ile genişleme |
| **Telif** | Kaynak kod + docs: depo tarihçesi; gönüllü kayıt delil gücü | **TÜRKPATENT** telif kayıt; e-serbest / noter uygulamaları |
| **Ticari sır** | 6769 sayılı SMK kapsamında gizlilik önlemleri | Erişim kontrolü, NDA, private repo |
| **Patent** | Dar alan prior art sonrası | **TÜRİKPATENT** — araştırma raporu |
| **OSS** | Apache-2.0 Türkiye'de geçerli lisans; marka ayrımı NOTICE'ta | Self-host ≠ marka lisansı |

### 7.3 AB (Avrupa Birliği)

| IP türü | Önerilen çerçeve | Kurum / not |
|---------|------------------|-------------|
| **Marka** | EU trade mark (tek başvuru, 27 üye) veya ulusal (ör. DE, CY) | **EUIPO** (Alicante); Kıbrıs için ulusal/EU kombinasyonu vekil ile |
| **Telif** | Yazılım telif otomatik; isteğe bağlı kayıt | AB Telif Direktifi; sınır ötesi delil için kayıt faydalı |
| **Ticari sır** | AB Ticari Sır Direktifi (2016/943) — makul gizlilik önlemleri | GDPR ile birlikte kullanıcı verisi private katmanda |
| **Patent** | Yazılım "olarak such" patenti sınırlı; teknik etki gerekir | **EPO** — Avrupa patent başvurusu (ulusal aşama ayrı) |
| **OSS** | Apache-2.0 AB uyumlu; marka ihlali NOTICE ile ayrılır | Public boundary — GDPR hassas veri public repoda yok |

### 7.4 ABD (USA)

| IP türü | Önerilen çerçeve | Kurum / not |
|---------|------------------|-------------|
| **Marka** | Lumos, We Lock AI — US kullanım kanıtı (welockai.com, GitHub) | **USPTO** — Intent-to-use veya use-based başvuru |
| **Telif** | Gönüllü kayıt — tazminat ve delil avantajı | **US Copyright Office** — yazılım kaydı |
| **Ticari sır** | UTSA (Uniform Trade Secrets Act) — makul gizlilik | Private katman ABD'de barındırılıyorsa yerel hukuk |
| **Patent** | Alice/Mayo sonrası yazılım patenti dar | **USPTO** — prior art taraması zorunlu |
| **OSS** | Apache-2.0 + patent grant; marka NOTICE dışı | GitHub public = ABD prior art |

### 7.5 Çin (China)

| IP türü | Önerilen çerçeve | Kurum / not |
|---------|------------------|-------------|
| **Marka** | Lumos Çince pazarda bilinen marka riski — savunma tescili | **CNIPA** — yerel vekil zorunlu pratikte |
| **Telif** | Otomatik koruma; kayıt önerilir | **NCAC** / telif merkezi uygulamaları |
| **Ticari sır** | Anti-Unfair Competition Law — gizlilik önlemleri | Veri lokalizasyonu (PIPL) — prod verisi Çin'de ise ayrı uyum |
| **Patent** | Yazılım + teknik etki | **CNIPA** — hızlı artan başvuru hacmi; prior art yoğun |
| **OSS** | Apache-2.0 geçerli; marka ayrımı | Public repo Çin'de prior art; tescil zamanlaması kritik |

---

## 8. Açık kaynak yayını vs ticari sır kaybı riski

### 8.1 Risk matrisi

| Risk | Tetikleyici | Etki | Azaltma (önerilen çerçeve) |
|------|-------------|------|----------------------------|
| **Ticari sır kaybı** | Prod spec, credential, runbook public commit | Rekabet avantajı kaybı; hukuki "gizli bilgi" statüsü zayıflar | Public boundary; pre-commit tarama; vault ayrımı |
| **Marka serbest bırakma algısı** | NOTICE olmadan marka kullanımına izin sanılması | Marka değeri erimesi | NOTICE + README açık ayrım |
| **Patent prior art** | Public GitHub commit tarihi | Patent başvuru alanı daralır | Başvuru *önce* mi yayın *sonra* mı — vekil kararı |
| **OSS lisans kalıcılığı** | Apache-2.0 altında yayınlanan kod geri alınamaz | Ticari exclusivity yok | Dual-license veya private fork *yayın öncesi* planlanmalı |
| **Katkı sahipliği** | Dış katkı CLA yok | IP sahipliği belirsiz | CONTRIBUTING + CLA (henüz yok) |
| **Drift: stub = prod sanılması** | Demo stub public'te | Müşteri / banka yanlış anlama | ADR-002, public-repo-boundary §C |

### 8.2 Public / private ayrım özeti

```
┌─────────────────────────────────────────────────────────────┐
│  PUBLIC (lumos-core, Apache-2.0)                            │
│  • Foundation kod, demo stub, ADR, güvenlik ilkeleri      │
│  • UI iskelet, i18n, quantum readiness tarayıcı (salt oku)  │
│  • NOTICE: marka + resmi hizmet LİSANSA DAHİL DEĞİL         │
└─────────────────────────────────────────────────────────────┘
                              │
                    Lumos tek dış kapı (ADR-012)
                              │
┌─────────────────────────────────────────────────────────────┐
│  PRIVATE / PROFESSIONAL                                     │
│  • Prod orchestration, API, auth, entegrasyon impl          │
│  • Ops vault, strategy vault, PSP, kullanıcı verisi         │
│  • Ticari sır + sözleşme + erişim kontrolü                  │
└─────────────────────────────────────────────────────────────┘
```

### 8.3 Çapraz referanslar

| Belge | IP ilişkisi |
|-------|-------------|
| [`commercial-product-packaging.md`](./commercial-product-packaging.md) | Starter/Pro/Business; marka lisansı ayrı |
| [`public-repo-boundary.md`](../memory/public-repo-boundary.md) | Ticari sır kategori kaynağı |
| [`NOTICE`](../../NOTICE) | Marka / hizmet lisans dışılığı |
| [`bank-readiness-checklist.md`](./bank-readiness-checklist.md) | KKTC marka / şirket tutarlılığı |
| [`security-architecture.md`](../memory/security-architecture.md) | Public repo güvenlik sınırı |
| ADR-012, ADR-007, ADR-011, ADR-013 | Teknik IP envanter kaynağı |

---

## 9. Sorumluluk reddi

**Bu belge hukuk danışmanlığı değildir.** Fikri mülkiyet tescili, patentlenebilirlik, ticari sır statüsü, lisans yorumu ve bölgesel uygulama **yetkili yerel vekil** veya patent/marka vekili gerektirir.

**KKTC ve Türkiye özelinde yerel vekil şarttır** — marka sınıfları, tescil süresi, OSS ile marka ayrımı, banka incelemesi için unvan/marka hizası ve vergi/şirket kaydı birlikte değerlendirilmelidir.

**Garanti yoktur:** "Önerilen çerçeve" maddeleri uygulandığında belirli bir hukuki sonuç (tescil onayı, ihlal koruması, patent verilmesi) **taahhüt edilmez**.

**Gizlilik:** Bu belge production secret, credential, gerçek algoritma detayı veya operasyonel endpoint **içermez** — yalnızca kategori düzeyinde envanter sunar.

---

## 10. Sonraki adımlar (önerilen çerçeve — öncelik sırası)

| Öncelik | Adım | Sorumlu |
|---------|------|---------|
| 1 | Lumos + We Lock AI marka tescil ön araştırması (KKTC + TR + EU/US hedef pazar) | Yerel vekil |
| 2 | NOTICE ve README marka ayrımının ticari sözleşme şablonları ile hizalanması | Hukuk |
| 3 | Public boundary commit guard — strategy/ops sızıntı kontrolü | Geliştirme |
| 4 | CONTRIBUTING + CLA taslağı (katkı IP sahipliği) | Hukuk + geliştirme |
| 5 | Patent prior art taraması (dar alan — onay zinciri / readiness) | Patent vekili |
| 6 | OD-048 landing onayı sonrası marka kullanım kılavuzu | Ürün + hukuk |

---

*Belge sonu — `ip-protection-landscape` v2026-06-21*
