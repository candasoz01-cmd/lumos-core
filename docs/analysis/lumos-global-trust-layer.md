# Küresel katkıcı / ödeme-uyum katmanı — güven mimarisi kaydı

| Alan | Değer |
|------|-------|
| Durum | **FİKİR** — tarihli çalışma notu; yeni yön değil |
| Tarih | 2026-08-28 kullanıcı kilidi |
| Kanıt merdiveni | Kayıt: **FİKİR**. Uygulama: yok ([scope-accounting](./scope-accounting.md)) |
| Üst sınır | [`CONSTITUTION.md`](../CONSTITUTION.md) §1/§5, [`ROADMAP.md`](../ROADMAP.md) STOP LIST, [`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) |
| Hiza | [ADR-017](../decisions/ADR-017-regulated-service-entity-boundaries.md), [DL-E04](../decision-log.md), [OD-011](../memory/payment-scope-decision.md), [`public-repo-boundary.md`](../memory/public-repo-boundary.md) |
| Bu PR | **#809 değildir.** #809 kapsamı değişmez |

**Sınır notu:** Bu kayıt yeni ürün, yeni rota, yeni orchestration katmanı veya STOP LIST istisnası **açmaz**. FAZ-1 kapanmadan uygulama yok.

---

## Kilit cümle

> **Ülke, fırsata duvar olmamalı; ödeme, kur, vergi ve uyum ise güven mimarisinin parçasıdır.**

---

## Kullanıcı kilidi (2026-08-28)

> Global ekip, ödeme, kur, vergi ve uyum katmanı Lumos’un güven mimarisinin parçası olarak değerlendirilecek; ancak FAZ-1 kapanmadan uygulama yok.
> #809’un kapsamı değişmesin: önce FAZ-1 kapanış onayı, sonra panel bağlantısı.

---

## Ne kaydedilir

1. **Küresel ekip / katkıcı modeli ülke sınırında durmaz.** Fırsat, katkı ve çalışma ülkeden ülkeye duvarlanmaz. Bu, ADR-017 Lumos Dünya yüzeyinin «küresel insan katılımı» rolüyle aynı omurgadır; ülke sistemi entegrasyonu (markasız, private, sözleşmeli) ayrı kalır.
2. **Ödeme, kur, vergi ve uyum ürün dışına atılmaz.** Güven mimarisinin parçası olarak değerlendirilir — «başka birinin sorunu» değildir.
3. **FAZ-1’de inşa edilmez.** İlke kaydı uygulama izni değildir. OD-011 `decision-approved` / `implementation-pending` durur: canlı PSP, checkout, webhook, settlement yok.
4. **Üretim faturalama public OSS’te yoktur.** ADR-017 public/private ayrımı ve OD-011 ilke 6: production billing, merchant, banka/PSP credential ve endpoint `lumos-core` public deposuna yazılmaz; private ve yetkili katmanda kalır.

## Mevcut kararlarla hiza

Çelişki yok; mevcut kararlar gevşetilmez.

| Kayıt | Bu notun okunuşu | Gevşeme |
|-------|------------------|---------|
| **ADR-017** | Ticari birimler, Lumos Dünya ve ülke entegrasyonu ayrı sorumluluk. Ortak omurga: kimlik, onay, politika, audit — güven sözleşmeleri. Canlı ödeme / ülke bağlantısı foundation-only. | Yok |
| **DL-E04** | Lumos Bank/Sepet/POS + Lumos Dünya + markasız ülke katmanı. Canlı ödeme ve ülke sistemi bağlantısı bekliyor. | Yok |
| **OD-011** | Ödeme modeli + PSP/hukuk-mali paket gelene kadar aktif geliştirme dışı. Onaysız ödeme yasak. Credential public’te yok. | Yok |

Bu kayıt ADR-017’yi, OD-011’i veya DL-E04’ü yeniden yazmaz. Üretim tahsilatı, lisans ve ülke adaptörü yine `implementation-pending` ve düzenleme kapılıdır.

## Bu kayıt ≠ PR #809

`candasoz01-cmd/lumos-core#809` (dal: `cursor/self-governance-surface-3c61`) **aynı kalır:**

1. önce insan **FAZ-1 kapanış onayı**;
2. sonra mevcut parçaların **panel bağlantısı** (yeni parça yok).

Ajan FAZ-1’i kapatmaz. Bu dosya o PR’ın dosyalarına (`lumos-self-governance-surface.md`, `ROADMAP.md`, `PRODUCT_SUMMARY.md`, `decision-log.md`, `security-architecture.md`) yazmaz.

## Ne değildir

- Yeni bordro / maaş ürünü
- Ülke seçici UI veya yeni panel sayfası
- FAZ-1 kapanış ilanı
- Panel kodu, yeni rota, yeni mercek
- STOP LIST istisnası (`yeni özellik`, `yeni sayfa`, `yeni agent / orchestration katmanı`)
- PSP seçimi, checkout, canlı tahsilat veya public repo’ya production billing

## Sonraki adım (uygulama değil)

FAZ-1 kapanış onayı insan işidir. Onaydan sonra #809 sırası (panel bağlama) yürür. Küresel katkıcı ve ödeme/kur/vergi/uyum katmanının uygulama paketi **ayrı, sonraki** kullanıcı kararı ister; bu not o paketi açmaz.
