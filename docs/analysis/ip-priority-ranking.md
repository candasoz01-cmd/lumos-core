# Lumos — IP Koruma Öncelik Sıralaması

| Alan | Değer |
|------|--------|
| **Belge ID** | `ip-priority-ranking` |
| **Durum** | `analiz` — önceliklendirme çerçevesi; hukuki tescil kararı bekliyor |
| **Tarih** | 2026-06-21 |
| **Dil** | Türkçe (birincil) |
| **Kapsam** | `lumos-core` public OSS foundation + We Lock AI ticari katman sınırı |
| **Birincil kaynak** | [`ip-protection-landscape.md`](./ip-protection-landscape.md) |
| **Üst sınır** | [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md), [`docs/memory/public-repo-boundary.md`](../memory/public-repo-boundary.md) |
| **İlgili ADR'ler** | [ADR-007](../decisions/ADR-007-trust-engine-layer.md), [ADR-011](../decisions/ADR-011-lock-semantics-decision.md), [ADR-012](../decisions/ADR-012-lumos-security-codex.md), [ADR-013](../decisions/ADR-013-lumos-quantum-security-readiness.md) |
| **Bölgesel referans** | KKTC, TR, AB, ABD, CN — [`ip-protection-landscape.md` §7](./ip-protection-landscape.md#7-bölgesel-koruma-stratejileri) |
| **Son güncelleme** | 2026-06-21 |

---

## Yönetici özeti

Bu belge, [`ip-protection-landscape.md`](./ip-protection-landscape.md) envanterindeki **tüm IP adaylarını** (10 marka, 13 ticari sır kategorisi, 10 patent alanı, 5 telif paketi) ticari değer, kopyalanma riski, tescil zorluğu ve koruma maliyeti eksenlerinde sıralar ve **P0 / P1 / P2** öncelik sınıflarına atar.

**Özet dağılım:** P0 = **8** · P1 = **17** · P2 = **13** (toplam **38** aday)

**En acil üç P0:**

1. **Lumos** marka tescili — birincil ürün adı; OSS klonları marka hakkı vermez ama isim çakışması riski yüksek.
2. **We Lock AI / welockai** marka tescili — çatı marka ve domain; banka/KKTC ticari unvan hizası için kritik.
3. **Private orchestration + Production API** ticari sır rejimi — rekabet avantajının çekirdeği; public sızıntı = sır kaybı.

---

## Metodoloji

### Öncelik formülü (çerçeve)

Her aday için beş boyut değerlendirilir:

| Boyut | Skala | Anlam |
|-------|-------|-------|
| **Ticari değer** | düşük / orta / yüksek | Gelir, marka, rekabet avantajı veya banka/ müşteri güvenine etkisi |
| **Kopyalanma riski** | düşük / orta / yüksek | Rakip veya üçüncü tarafın taklit / sızıntı / prior art oluşturma olasılığı |
| **Tescil zorluğu** | düşük / orta / yüksek / N/A | Yerel mevzuat, önceki haklar, jeneriklik; ticari sırlar için N/A |
| **Koruma maliyeti** | düşük / orta / yüksek | Kabaca büyüklük sırası (vekil, çoklu bölge, sürekli operasyonel maliyet) |
| **Koruma önceliği** | P0 / P1 / P2 | Aşağıdaki atama kuralları |

### P0 / P1 / P2 atama kuralları

```
Öncelik skoru ≈ (Ticari değer + Kopyalanma riski) − (Tescil zorluğu + Koruma maliyeti)
```

| Sınıf | Zaman | Atama kriteri |
|-------|-------|---------------|
| **P0 (hemen)** | 0–3 ay | Yüksek ticari değer **ve** yüksek kopyalanma/sızıntı riski; koruma uygulanabilir veya operasyonel zorunluluk (ticari sır, birincil marka) |
| **P1 (6 ay içinde)** | 3–6 ay | Orta–yüksek değer; ikincil marka, telif belgeleme, patent prior art taraması, kalan ticari sır kategorileri |
| **P2 (ileride)** | 6+ ay | Düşük değer veya yüksek zorluk/maliyet; savunma amaçlı; zaten Apache-2.0 / otomatik telif ile yeterli koruma; jenerik marka adları |

**Not:** Patent alanları için landscape belgesi **patent iddiası taşımaz**; öncelik yalnızca prior art taraması ve vekil değerlendirmesi zamanlaması içindir.

---

## Özet matris (tüm adaylar)

| # | Aday | Tür | Ticari değer | Kopyalanma riski | Tescil zorluğu | Koruma maliyeti | Öncelik |
|---|------|-----|--------------|------------------|----------------|-----------------|---------|
| M1 | Lumos | Marka | yüksek | yüksek | orta | orta | **P0** |
| M2 | We Lock AI / WeLock AI | Marka | yüksek | yüksek | orta | orta | **P0** |
| M3 | welockai | Marka | yüksek | yüksek | orta | orta | **P0** |
| M4 | Lumos Panel | Marka | orta | orta | orta | orta | P1 |
| M5 | Lumos Core | Marka | orta | orta | orta | orta | P1 |
| M6 | Lumos Quantum Readiness | Marka | orta | orta | orta | orta | P1 |
| M7 | Starter | Marka | düşük | orta | yüksek | orta | P2 |
| M8 | Pro | Marka | düşük | orta | yüksek | orta | P2 |
| M9 | Business | Marka | düşük | orta | yüksek | orta | P2 |
| M10 | Kando | Marka | düşük | düşük | orta | düşük | P2 |
| TS1 | Private orchestration katmanı | Ticari sır | yüksek | yüksek | N/A | düşük | **P0** |
| TS2 | Production API ve barındırılan hizmet | Ticari sır | yüksek | yüksek | N/A | düşük | **P0** |
| TS3 | Operasyonel altyapı | Ticari sır | yüksek | yüksek | N/A | düşük | **P0** |
| TS4 | Mail / iletişim otomasyon stratejisi | Ticari sır | orta | yüksek | N/A | düşük | P1 |
| TS5 | Vault / secret yönetimi (prod) | Ticari sır | yüksek | yüksek | N/A | düşük | **P0** |
| TS6 | Ödeme / abonelik altyapısı | Ticari sır | yüksek | yüksek | N/A | düşük | P1 |
| TS7 | Cihaz kontrolü ve prod entegrasyonlar | Ticari sır | orta | yüksek | N/A | düşük | P1 |
| TS8 | Kullanıcı verisi sistemleri | Ticari sır | yüksek | yüksek | N/A | düşük | P1 |
| TS9 | Private entegrasyon pilotları | Ticari sır | orta | yüksek | N/A | düşük | P1 |
| TS10 | Bridge prod güvenlik politikası | Ticari sır | orta | yüksek | N/A | düşük | P1 |
| TS11 | Entropy Lab prod konfigürasyonu | Ticari sır | düşük | orta | N/A | düşük | P2 |
| TS12 | Ticari fiyatlandırma ve sözleşme paketleri | Ticari sır | yüksek | orta | N/A | düşük | P1 |
| TS13 | İç iletişim protokolü (Bando / imzalama) | Ticari sır | orta | yüksek | N/A | düşük | P1 |
| P1 | Çok katmanlı onay zinciri | Patent alanı | orta | orta | yüksek | yüksek | P1 |
| P2 | İki sinyalli lock semantiği | Patent alanı | düşük | düşük | yüksek | yüksek | P2 |
| P3 | Trust durum hedef sözleşmesi (8 durum) | Patent alanı | düşük | düşük | yüksek | yüksek | P2 |
| P4 | SECURITY_NEVER_AUTO matrisi | Patent alanı | düşük | düşük | yüksek | yüksek | P2 |
| P5 | Tek dış kapı (facade) mimarisi | Patent alanı | düşük | düşük | yüksek | yüksek | P2 |
| P6 | Trash prensibi + onaysız kalıcı silme yasağı | Patent alanı | düşük | düşük | yüksek | yüksek | P2 |
| P7 | Quantum Readiness salt okunur tarayıcı | Patent alanı | orta | orta | yüksek | yüksek | P1 |
| P8 | Patch proposal + protected apply pipeline | Patent alanı | düşük | düşük | yüksek | yüksek | P2 |
| P9 | Offline-first policy engine | Patent alanı | düşük | düşük | yüksek | yüksek | P2 |
| P10 | Panel ↔ CLI trust görünürlük ayrımı | Patent alanı | düşük | düşük | yüksek | yüksek | P2 |
| C1 | Kaynak kodu (Apache-2.0) | Telif | yüksek | yüksek | düşük | düşük | **P0** |
| C2 | UI metinleri (TR/EN i18n) | Telif | orta | orta | düşük | düşük | P1 |
| C3 | Dokümantasyon (ADR, analiz) | Telif | orta | orta | düşük | düşük | P1 |
| C4 | Logo / görsel kimlik | Telif + marka | orta | orta | orta | orta | P1 |
| C5 | Landing / pazarlama kopyası | Telif | orta | orta | düşük | düşük | P1 |

---

## 1. Marka adayları (10)

Kaynak: [`ip-protection-landscape.md` §2.1, §5](./ip-protection-landscape.md#21-marka-tescil-adayı)

### M1 — Lumos

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **yüksek** | Birincil ürün adı; panel, README, i18n ve repo kimliğinin merkezi |
| Kopyalanma riski | **yüksek** | OSS klonları kodu alabilir; isim/domain çakışması ve marka karışıklığı riski |
| Tescil zorluğu | **orta** | Nice 9/42; önceki hak ve benzer marka araştırması gerekir (KKTC/TR/EU/US) |
| Koruma maliyeti | **orta** | Çoklu bölge marka başvurusu + vekil; kabaca birkaç bin–on bin USD bandı |
| Koruma önceliği | **P0** | |

### M2 — We Lock AI / WeLock AI

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **yüksek** | Çatı marka; NOTICE, README ve welockai.com vitrininin sahibi |
| Kopyalanma riski | **yüksek** | AI/güvenlik alanında benzer isimler; banka incelemesinde unvan hizası kritik |
| Tescil zorluğu | **orta** | Kelime birleşimi; yazım varyantları (We Lock / WeLock) ayrı başvuru gerekebilir |
| Koruma maliyeti | **orta** | M1 ile birlikte paketlenebilir; ayrı sınıf genişlemesi ek maliyet |
| Koruma önceliği | **P0** | |

### M3 — welockai

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **yüksek** | Domain ve ticari vitrin kelime markası |
| Kopyalanma riski | **yüksek** | Domain squatting ve benzer domain varyantları |
| Tescil zorluğu | **orta** | Domain sahipliği kanıtı güçlü; uluslararası sınıf seçimi vekil ile |
| Koruma maliyeti | **orta** | M1/M2 ile birlikte; CN savunma tescili ayrı bütçe (P1) |
| Koruma önceliği | **P0** | |

### M4 — Lumos Panel

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **orta** | Aktif UI yüzey adı; kullanıcıya görünür alt marka |
| Kopyalanma riski | **orta** | "Panel" jenerik; birleşik kullanım (Lumos Panel) daha savunulabilir |
| Tescil zorluğu | **orta** | Birleşik marka olarak daha güçlü; tek kelime zayıf |
| Koruma maliyeti | **orta** | Birincil marka paketine eklenebilir |
| Koruma önceliği | **P1** | |

### M5 — Lumos Core

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **orta** | GitHub public repo kimliği; OSS topluluk tanınırlığı |
| Kopyalanma riski | **orta** | Fork'larda isim kullanımı NOTICE ile sınırlı ama izleme gerekir |
| Tescil zorluğu | **orta** | "Core" jenerik bileşen; birleşik marka tercih edilmeli |
| Koruma maliyeti | **orta** | M1 paketine eklenebilir |
| Koruma önceliği | **P1** | |

### M6 — Lumos Quantum Readiness

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **orta** | ADR-013 alt ürün/modül adı; niş ama ayırt edici |
| Kopyalanma riski | **orta** | PQC/readiness alanında benzer isimler çıkabilir |
| Tescil zorluğu | **orta** | Uzun birleşik marka; abartılı kuantum iddiası yasağı ile tutarlı kullanım şart |
| Koruma maliyeti | **orta** | Modül lansmanına yakın tescil yeterli |
| Koruma önceliği | **P1** | |

### M7 — Starter

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **düşük** | Jenerik tier adı; tek başına zayıf marka değeri |
| Kopyalanma riski | **orta** | Rakipler aynı tier ismini kullanabilir; "Lumos Starter" birleşik gerekir |
| Tescil zorluğu | **yüksek** | Aşırı jenerik; tescil reddi veya dar koruma olasılığı yüksek |
| Koruma maliyeti | **orta** | Birleşik marka başvurusu yine vekil gerektirir |
| Koruma önceliği | **P2** | |

### M8 — Pro

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **düşük** | Çok jenerik; repoda tier henüz yok |
| Kopyalanma riski | **orta** | Sektörde yaygın kullanım; ayırt edicilik düşük |
| Tescil zorluğu | **yüksek** | Tek başına tescil pratikte anlamsız |
| Koruma maliyeti | **orta** | "Lumos Pro" birleşik değerlendirme — öncelik düşük |
| Koruma önceliği | **P2** | |

### M9 — Business

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **düşük** | Jenerik kurumsal tier adı |
| Kopyalanma riski | **orta** | "Lumos Business" birleşik kullanım kanıtı zayıf (henüz tier yok) |
| Tescil zorluğu | **yüksek** | Jenerik kelime; tescil öncesi kullanım kanıtı yetersiz |
| Koruma maliyeti | **orta** | Tier lansmanına kadar ertelenebilir |
| Koruma önceliği | **P2** | |

### M10 — Kando

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **düşük** | İç katman; kullanıcıya yansımaz |
| Kopyalanma riski | **düşük** | Dış pazarda görünürlük minimal |
| Tescil zorluğu | **orta** | Savunma amaçlı değerlendirme; öncelik düşük |
| Koruma maliyeti | **düşük** | Tek bölge savunma tescili yeterli |
| Koruma önceliği | **P2** | |

---

## 2. Ticari sır kategorileri (13)

Kaynak: [`ip-protection-landscape.md` §3](./ip-protection-landscape.md#3-ticari-sır-olarak-korunacak-alanlar)

> Tüm ticari sırlar için **tescil zorluğu = N/A** (resmi tescil yok; gizlilik + erişim kontrolü + sözleşme).

### TS1 — Private orchestration katmanı

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **yüksek** | Görev dağılımı, iç ajan koordinasyonu, prod akış — rekabet çekirdeği |
| Kopyalanma riski | **yüksek** | Public commit veya sızıntı = sır kaybı ve prior art benzeri avantaj erimesi |
| Tescil zorluğu | **N/A** | |
| Koruma maliyeti | **düşük** | Private repo, NDA, erişim listesi — operasyonel disiplin |
| Koruma önceliği | **P0** | |

### TS2 — Production API ve barındırılan hizmet

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **yüksek** | Resmi panel backend, auth, rate limit — ticari hizmet omurgası |
| Kopyalanma riski | **yüksek** | Canlı API, credential, tenant modeli sızıntısı kritik |
| Tescil zorluğu | **N/A** | |
| Koruma maliyeti | **düşük** | Public boundary + vault ayrımı |
| Koruma önceliği | **P0** | |

### TS3 — Operasyonel altyapı

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **yüksek** | Deploy, firewall, DNS, smoke — operasyonel süreklilik |
| Kopyalanma riski | **yüksek** | `.lumos/internal/ops-vault/` sızıntısı güvenlik ve rekabet riski |
| Tescil zorluğu | **N/A** | |
| Koruma maliyeti | **düşük** | Vault erişim kontrolü, commit guard |
| Koruma önceliği | **P0** | |

### TS4 — Mail / iletişim otomasyon stratejisi

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **orta** | Kural motoru, granüler izin matrisi — Pro/Business farklılaştırıcı |
| Kopyalanma riski | **yüksek** | Tam spec ve provider seçimi public'te olmamalı |
| Tescil zorluğu | **N/A** | |
| Koruma maliyeti | **düşük** | Strategy-vault erişim sınırı |
| Koruma önceliği | **P1** | |

### TS5 — Vault / secret yönetimi (prod)

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **yüksek** | Credential şeması, rotation — güvenlik ve uyum temeli |
| Kopyalanma riski | **yüksek** | Prod secret sızıntısı hem hukuki hem operasyonel felaket |
| Tescil zorluğu | **N/A** | |
| Koruma maliyeti | **düşük** | Infisical/vault operasyonel erişim politikası |
| Koruma önceliği | **P0** | |

### TS6 — Ödeme / abonelik altyapısı

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **yüksek** | PSP, checkout, webhook — gelir akışı |
| Kopyalanma riski | **yüksek** | Merchant ID ve canlı entegrasyon credential'ları |
| Tescil zorluğu | **N/A** | |
| Koruma maliyeti | **düşük** | Private katman + sözleşme |
| Koruma önceliği | **P1** | Henüz canlı PSP yok; boundary şimdi, detay lansman öncesi |

### TS7 — Cihaz kontrolü ve prod entegrasyonlar

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **orta** | IoT/ev otomasyon prod bağlantıları — gelecek tier farklılaştırıcı |
| Kopyalanma riski | **yüksek** | Canlı connector ve cihaz protokolleri |
| Tescil zorluğu | **N/A** | |
| Koruma maliyeti | **düşük** | Modül iskeleti public; impl private |
| Koruma önceliği | **P1** | |

### TS8 — Kullanıcı verisi sistemleri

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **yüksek** | Resmi hizmette PII/tenant data — GDPR/PIPL uyumu |
| Kopyalanma riski | **yüksek** | Veri modeli ve saklama mimarisi sızıntısı |
| Tescil zorluğu | **N/A** | |
| Koruma maliyeti | **düşük** | Tamamen private katman |
| Koruma önceliği | **P1** | Resmi hizmet lansmanına kadar P0'ya yükseltilebilir |

### TS9 — Private entegrasyon pilotları

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **orta** | Gmail/Slack/GitHub prod OAuth — entegrasyon moat |
| Kopyalanma riski | **yüksek** | Token exchange ve canlı handler detayları |
| Tescil zorluğu | **N/A** | |
| Koruma maliyeti | **düşük** | Contract tipleri public; handler private |
| Koruma önceliği | **P1** | |

### TS10 — Bridge prod güvenlik politikası

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **orta** | Uzak köprü token, IP allowlist — prod hosting güvenliği |
| Kopyalanma riski | **yüksek** | Dev script public; prod policy ayrımı kritik |
| Tescil zorluğu | **N/A** | |
| Koruma maliyeti | **düşük** | ADR-012 boundary ile hizalı |
| Koruma önceliği | **P1** | |

### TS11 — Entropy Lab prod konfigürasyonu

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **düşük** | Deneysel modül; IBM Runtime prod yolu erken aşama |
| Kopyalanma riski | **orta** | Prod credential ve maliyet/onay akışı |
| Tescil zorluğu | **N/A** | |
| Koruma maliyeti | **düşük** | Sağlayıcı kodu zaten public |
| Koruma önceliği | **P2** | |

### TS12 — Ticari fiyatlandırma ve sözleşme paketleri

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **yüksek** | Pro/Business nihai fiyat, kurumsal ekler — marj ve müzakere |
| Kopyalanma riski | **orta** | Planlama çerçevesi public; nihai rakamlar private |
| Tescil zorluğu | **N/A** | |
| Koruma maliyeti | **düşük** | İç erişim sınırı |
| Koruma önceliği | **P1** | |

### TS13 — İç iletişim protokolü (Bando / imzalama)

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **orta** | Lumos → Kando/Cando kanal bütünlüğü — güven zinciri |
| Kopyalanma riski | **yüksek** | Protokol implementasyonu henüz pending (OD-006) |
| Tescil zorluğu | **N/A** | |
| Koruma maliyeti | **düşük** | Karar özeti public; impl private |
| Koruma önceliği | **P1** | |

---

## 3. Patent alanları (10)

Kaynak: [`ip-protection-landscape.md` §4](./ip-protection-landscape.md#4-patent-potansiyeli-taşıyan-alanlar)

> **Uyarı:** Patentlenebilirlik değerlendirilmemiştir. Public OSS yayını prior art oluşturur.

### P1 — Çok katmanlı onay zinciri

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **orta** | Profil × policy × confirmation × consent birleşimi — farklılaştırıcı UX/güvenlik |
| Kopyalanma riski | **orta** | Kod public; davranış kopyalanabilir ama birleşik model nadir |
| Tescil zorluğu | **yüksek** | Önceki sanat yoğun; Alice/Mayo/EPO yazılım sınırları |
| Koruma maliyeti | **yüksek** | Prior art taraması + vekil + çoklu bölge başvurusu |
| Koruma önceliği | **P1** | Prior art taraması önce; başvuru zamanlaması vekil kararı |

### P2 — İki sinyalli lock semantiği

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **düşük** | Dar uygulama (keystore_ready vs session_unlocked) |
| Kopyalanma riski | **düşük** | Genel kilit kavramları prior art |
| Tescil zorluğu | **yüksek** | ADR-011 zayıf/spesifik değerlendirmesi |
| Koruma maliyeti | **yüksek** | Düşük getiri / yüksek maliyet |
| Koruma önceliği | **P2** | |

### P3 — Trust durum hedef sözleşmesi (8 durum)

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **düşük** | Dokümantasyon hedefi; birleşik motor henüz yok |
| Kopyalanma riski | **düşük** | State machine pattern yaygın |
| Tescil zorluğu | **yüksek** | ADR-007 zayıf değerlendirmesi |
| Koruma maliyeti | **yüksek** | |
| Koruma önceliği | **P2** | |

### P4 — SECURITY_NEVER_AUTO matrisi

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **düşük** | Politika tablosu; güvenlik best practice sınıfı |
| Kopyalanma riski | **düşük** | Genel bilgi niteliğinde |
| Tescil zorluğu | **yüksek** | Patentlenebilir teknik etki zayıf |
| Koruma maliyeti | **yüksek** | |
| Koruma önceliği | **P2** | |

### P5 — Tek dış kapı (facade) mimarisi

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **düşük** | Gateway pattern — yaygın mimari |
| Kopyalanma riski | **düşük** | Bilinen pattern |
| Tescil zorluğu | **yüksek** | Genel bilgi |
| Koruma maliyeti | **yüksek** | |
| Koruma önceliği | **P2** | |

### P6 — Trash prensibi + onaysız kalıcı silme yasağı

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **düşük** | Soft-delete + onay UX — bilinen UX pattern |
| Kopyalanma riski | **düşük** | Workspace sözleşmesi dokümantasyon odaklı |
| Tescil zorluğu | **yüksek** | Genel bilgi |
| Koruma maliyeti | **yüksek** | |
| Koruma önceliği | **P2** | |

### P7 — Quantum Readiness salt okunur tarayıcı

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **orta** | Envanter + kanıt etiketli rapor — niş PQC hazırlık aracı |
| Kopyalanma riski | **orta** | Kod public; birleşik raporlama yaklaşımı dar alan |
| Tescil zorluğu | **yüksek** | PQC uygulaması yok; tarayıcı sınıfı prior art yoğun |
| Koruma maliyeti | **yüksek** | P1 alanı ile birlikte prior art taraması |
| Koruma önceliği | **P1** | P1 (onay zinciri) ile birleşik değerlendirme önerilir |

### P8 — Patch proposal + protected apply pipeline

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **düşük** | Code review / patch workflow — bilinen süreç |
| Kopyalanma riski | **düşük** | |
| Tescil zorluğu | **yüksek** | Zayıf değerlendirme |
| Koruma maliyeti | **yüksek** | |
| Koruma önceliği | **P2** | |

### P9 — Offline-first policy engine

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **düşük** | Offline gate — bilinen pattern |
| Kopyalanma riski | **düşük** | |
| Tescil zorluğu | **yüksek** | Genel bilgi |
| Koruma maliyeti | **yüksek** | |
| Koruma önceliği | **P2** | |

### P10 — Panel ↔ CLI trust görünürlük ayrımı

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **düşük** | UX/enforcement ayrımı — dar uygulama |
| Kopyalanma riski | **düşük** | |
| Tescil zorluğu | **yüksek** | Zayıf değerlendirme |
| Koruma maliyeti | **yüksek** | |
| Koruma önceliği | **P2** | |

---

## 4. Telif paketleri (5)

Kaynak: [`ip-protection-landscape.md` §2.2, §6](./ip-protection-landscape.md#22-telif-kayıt-belgeleme)

### C1 — Kaynak kodu (Apache-2.0)

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **yüksek** | `src/`, `task_engine/`, `panel/`, `ui/` — OSS foundation |
| Kopyalanma riski | **yüksek** | Apache-2.0 kasıtlı paylaşım; marka/resmi hizmet hariç |
| Tescil zorluğu | **düşük** | Otomatik telif; lisans NOTICE ile zaten aktif |
| Koruma maliyeti | **düşük** | Mevcut LICENSE + NOTICE yeterli; CLA eksik (P1) |
| Koruma önceliği | **P0** | NOTICE/marka ayrımının sürdürülmesi ve CLA planı |

### C2 — UI metinleri (TR/EN i18n)

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **orta** | Uzun form ürün metinleri — kullanıcı deneyimi |
| Kopyalanma riski | **orta** | Metin kopyalama kolay; telif ihlali izleme gerekir |
| Tescil zorluğu | **düşük** | Otomatik telif; gönüllü kayıt delil gücü artırır |
| Koruma maliyeti | **düşük** | Repo tarihçesi + opsiyonel kayıt |
| Koruma önceliği | **P1** | |

### C3 — Dokümantasyon (ADR, analiz)

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **orta** | Mimari know-how belgesi; karar sözleşmesi |
| Kopyalanma riski | **orta** | Public repo — kasıtlı açık; atıf olmadan kopya riski |
| Tescil zorluğu | **düşük** | Commit kanıtı mevcut |
| Koruma maliyeti | **düşük** | |
| Koruma önceliği | **P1** | |

### C4 — Logo / görsel kimlik

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **orta** | Marka tanınırlığı; OD-050/051 kararı pending |
| Kopyalanma riski | **orta** | Görsel kopyalama kolay |
| Tescil zorluğu | **orta** | Henüz public commit yok; tescil öncesi final tasarım |
| Koruma maliyeti | **orta** | Telif + marka çift koruma |
| Koruma önceliği | **P1** | Logo finalizasyonu sonrası |

### C5 — Landing / pazarlama kopyası

| Boyut | Değer | Gerekçe (tek satır) |
|-------|-------|---------------------|
| Ticari değer | **orta** | OD-048 `needs-review`; vitrin dönüşümü |
| Kopyalanma riski | **orta** | Pazarlama metni kopyalanabilir |
| Tescil zorluğu | **düşük** | Otomatik telif; final metin sonrası kayıt |
| Koruma maliyeti | **düşük** | |
| Koruma önceliği | **P1** | OD-048 onayı sonrası |

---

## 5. Öncelik sınıflandırması

### P0 (hemen) — 8 aday

| ID | Aday | Gerekçe |
|----|------|---------|
| M1 | Lumos | Birincil ürün markası; yüksek ticari değer + yüksek isim çakışması riski; banka/KKTC unvan hizası |
| M2 | We Lock AI / WeLock AI | Çatı marka; NOTICE sahibi; ticari vitrin ve sözleşme omurgası |
| M3 | welockai | Domain kelime markası; squatting riski; M1/M2 ile birlikte paket tescil |
| TS1 | Private orchestration | Rekabet moat çekirdeği; public sızıntı = sır kaybı |
| TS2 | Production API | Ticari hizmet omurgası; credential/tenant sızıntısı kritik |
| TS3 | Operasyonel altyapı | Ops-vault güvenliği; operasyonel süreklilik |
| TS5 | Vault / secret yönetimi (prod) | Güvenlik temeli; sızıntı felaket senaryosu |
| C1 | Kaynak kodu (Apache-2.0) | NOTICE/marka ayrımı sürdürülmeli; katkı IP'si için CLA planı (landscape §10 adım 4) |

**Operasyonel P0 (tüm ticari sırlar için):** Public boundary commit guard, NDA, erişim listesi — [`ip-protection-landscape.md` §3.1](./ip-protection-landscape.md#31-ticari-sır-koruma-uygulamaları-önerilen-çerçeve)

### P1 (6 ay içinde) — 17 aday

| ID | Aday | Gerekçe |
|----|------|---------|
| M4 | Lumos Panel | İkincil marka; birincil pakete eklenebilir |
| M5 | Lumos Core | OSS repo kimliği; fork izleme |
| M6 | Lumos Quantum Readiness | Modül lansmanına yakın alt marka |
| TS4 | Mail / iletişim otomasyon | Pro/Business farklılaştırıcı; strategy-vault |
| TS6 | Ödeme / abonelik | Gelir akışı; canlı PSP öncesi boundary |
| TS7 | Cihaz kontrolü prod | Gelecek tier; impl private |
| TS8 | Kullanıcı verisi sistemleri | Resmi hizmet lansmanında P0'ya yükselt |
| TS9 | Private entegrasyon pilotları | OAuth handler detayları |
| TS10 | Bridge prod güvenlik politikası | Prod hosting ayrımı |
| TS12 | Ticari fiyatlandırma | Nihai rakamlar private |
| TS13 | İç iletişim protokolü (Bando) | OD-006 implementasyonu pending |
| P1 | Çok katmanlı onay zinciri | Potansiyel patent alanı; prior art taraması zorunlu |
| P7 | Quantum Readiness tarayıcı | Potansiyel (dar); P1 ile birleşik değerlendirme |
| C2 | UI metinleri (i18n) | Gönüllü telif kaydı delil gücü |
| C3 | Dokümantasyon (ADR) | Commit kanıtı + opsiyonel kayıt |
| C4 | Logo / görsel kimlik | OD-050/051 finalizasyonu sonrası |
| C5 | Landing / pazarlama kopyası | OD-048 onayı sonrası |

**Çapraz P1 operasyonel adımlar (landscape §10):** NOTICE/sözleşme hizası (adım 2), CONTRIBUTING+CLA (adım 4), CN savunma markası (§7.5)

### P2 (ileride) — 13 aday

| ID | Aday | Gerekçe |
|----|------|---------|
| M7 | Starter | Jenerik; "Lumos Starter" birleşik — tier lansmanına kadar bekle |
| M8 | Pro | Aşırı jenerik; kullanım kanıtı zayıf |
| M9 | Business | Jenerik; tier henüz repoda yok |
| M10 | Kando | İç katman; savunma amaçlı düşük öncelik |
| TS11 | Entropy Lab prod | Deneysel; düşük ticari değer şimdilik |
| P2, P3, P4, P5, P6, P8, P9, P10 | Zayıf patent alanları (8 adet) | Yüksek maliyet / düşük getiri; prior art yoğun |

---

## 6. Bölgesel koruma notu (özet)

Detay: [`ip-protection-landscape.md` §7](./ip-protection-landscape.md#7-bölgesel-koruma-stratejileri)

| Bölge | P0 odak | P1 genişleme |
|-------|---------|--------------|
| **KKTC** | Lumos + We Lock AI (banka/unvan hizası) | Telif kayıt opsiyonel |
| **Türkiye** | Nice 9/42 marka (TÜRİKPATENT) | Madrid genişlemesi |
| **AB** | EUIPO veya ulusal (CY) | Ticari sır direktifi uyumu |
| **ABD** | USPTO use-based (GitHub/welockai.com kanıtı) | Copyright Office gönüllü kayıt |
| **Çin** | — (P2 savunma) | CNIPA savunma tescili vekil ile |

---

## 7. Çapraz referanslar

| Belge | İlişki |
|-------|--------|
| [`ip-protection-landscape.md`](./ip-protection-landscape.md) | **Birincil kaynak** — tüm aday envanteri, bölgesel strateji, ticari sır kategorileri |
| [`commercial-product-packaging.md`](./commercial-product-packaging.md) | Starter/Pro/Business tier marka adayları |
| [`bank-readiness-checklist.md`](./bank-readiness-checklist.md) | KKTC marka/şirket tutarlılığı — P0 marka gerekçesi |
| [`public-repo-boundary.md`](../memory/public-repo-boundary.md) | Ticari sır kategori kaynağı; P0 boundary |
| [`NOTICE`](../../NOTICE) | Marka/hizmet lisans dışılığı — P0 C1 |
| ADR-007, ADR-011, ADR-012, ADR-013 | Patent ve teknik IP envanter kaynağı |

---

## 8. Sorumluluk reddi

**Bu belge hukuk danışmanlığı değildir.** Önceliklendirme çerçevesi, ticari değer ve risk değerlendirmesi içerir; tescil onayı, patent verilmesi, ticari sır statüsü veya ihlal koruması **taahhüt edilmez**.

**Ücretler yargı alanına göre değişir.** Kabaca maliyet sıralaması (düşük / orta / yüksek) kesin ücret değildir. KKTC, Türkiye (TÜRİKPATENT), AB (EUIPO/EPO), ABD (USPTO) ve Çin (CNIPA) rejimleri için [`ip-protection-landscape.md` §7](./ip-protection-landscape.md#7-bölgesel-koruma-stratejileri) ve **yerel vekil** şarttır.

**Garanti yoktur:** P0/P1/P2 atamaları uygulandığında belirli hukuki sonuç garantisi verilmez.

---

*Belge sonu — `ip-priority-ranking` v2026-06-21 · Kaynak: `ip-protection-landscape` v2026-06-21*
