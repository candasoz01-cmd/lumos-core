# Ödeme sistemi kapsam kararı — onaylı karar (OD-011)

> **Durum:** `decision-approved` — ilke kararları onaylandı; **uygulama başlamadı** (`implementation-pending`). Bu belge kod değişikliği değildir.
>
> **Üst sınır:** `docs/lumos-karar-sozlesmesi.md` — güvenlik, yetki, kalıcı silme ve onay kuralları bu kararı gevşetemez.

**Kaynak OD:** OD-011 (`commercial-domain-payments.md` — Ödeme sistemi kapsamı)

**Çelişki çözümü:** Bu dosya ile kaynak canonical dosyalar arasında çelişki varsa `docs/lumos-karar-sozlesmesi.md` ve ilgili kaynak `docs/memory/*.md` dosyaları esas alınır.

---

## 1. Amaç

OD-011 kapsamında ödeme sistemi, PSP (Payment Service Provider), banka/merchant hesabı ve ticari ödeme akışlarının **Lumos ürün sınırını** netleştirmek.

Bu belge:

- Ödeme ürün modeli, PSP seçimi, hukuk/mali ödeme akışı ve fatura/vergi işleme henüz **uygulama paketine** alınmadığı için ödeme altyapısının **aktif geliştirme kapsamı dışı** kalmasını kayıt altına alır (şirket/vergi kaydı mevcut; erteleme nedeni şirket yokluğu değildir).
- Onaysız ödeme, satın alma, abonelik ve domain işlemlerinin **yasak** olduğunu tekrarlar.
- QR / tek ödeme linki fikrini yalnızca **gelecek ürün notu** olarak konumlandırır.
- Vault, veri sahipliği ve public repo sınırlarıyla hizayı sabitler.

**Uygulama notu:** İlke kararları onaylandı; kod, test, panel, bridge, ödeme entegrasyonu, sağlayıcı seçimi, banka/PSP kurulumu veya credential/endpoint tanımı **henüz başlamadı**.

**Kuruluş yönü notu (2026-07-13):** [`ADR-015`](../decisions/ADR-015-regulated-service-entity-boundaries.md), Lumos Bank / Lumos Sepet / Lumos POS / Lumos Devlet çalışma adlarının gelecek sorumluluk sınırlarını tanımlar. Bu yön OD-011'i gevşetmez; banka/PSP/merchant/checkout/settlement ve gerçek kamu bağlantısı yine `implementation-pending` ve düzenleme kapılıdır.

---

## 1b. Onaylanan ilke vs bekleyen uygulama

| Katman | Durum | Kapsam |
|--------|--------|--------|
| **İlke kararları** | `decision-approved` | Ödeme ürün modeli + PSP/hukuk-mali ödeme akışı uygulama paketi hazır olana kadar ödeme sistemi, PSP, banka, merchant hesabı, checkout, webhook, settlement ve gerçek ödeme entegrasyonu **aktif geliştirme kapsamı dışı** (şirket/vergi kaydı mevcut). Lumos, kullanıcı **açık onayı olmadan** ödeme, satın alma, abonelik, domain satın alma/yenileme veya ödeme linki oluşturma **başlatmaz**. QR / tek ödeme linki yalnızca **gelecek ürün notu** — uygulama yok. Ödeme credential'ı, banka bilgisi, merchant detayı ve production endpoint public repoda ve Lumos yüzeyinde **tutulmaz/yazılmaz**. |
| **Uygulama / teknik detay** | `implementation-pending` | Ödeme altyapısı, checkout, webhook, settlement, PSP entegrasyonu — hiçbiri uygulanmadı; bu belge uygulama izni vermez. |
| **Needs-review (açık)** | `needs-review` | PSP seçimi, ödeme sağlayıcı entegrasyonu, vergi/fatura akışı, abonelik modeli, maliyet paylaşımı modeli, ödeme verisi vault entegrasyonu; OD-040 (maliyet paylaşımı QR/link) ve OD-041 (ticari onay modeli) detayları. |

---

## 2. Kapsam dışı olanlar

Aşağıdakiler **şu an ve ödeme modeli / PSP / hukuk-mali ödeme akışı uygulama paketi tamamlanana kadar** Lumos aktif geliştirme ve ürün kapsamı dışındadır:

| Alan | Kapsam dışı davranış |
|------|----------------------|
| Ödeme altyapısı | Ödeme sistemi özelliği, checkout akışı, fatura/abonelik motoru |
| Banka / PSP | Banka hesabı, PSP sözleşmesi, merchant hesabı, ödeme sağlayıcı kurulumu |
| Entegrasyon | Gerçek ödeme API entegrasyonu, webhook, settlement, reconciliation |
| Credential | Ödeme credential'ı, banka bilgisi, merchant detayı, production endpoint |
| Otomatik ticari aksiyon | Onaysız ödeme başlatma, domain satın alma/yenileme, abonelik aktivasyonu |
| Public repo | Yukarıdakilere ait operasyonel veya production verisi |

**Not:** Domain izleme ve bilgi sunumu (müsaitlik, fiyat, risk) `commercial-domain-payments.md` kapsamında ayrı tutulur; bu belge yalnızca **ödeme ve PSP** karar sınırına odaklanır.

---

## 3. Onaylanan ilkeler

Aşağıdaki ilkeler **onaylandı** (`decision-approved`); çekirdek sözleşme ve canonical memory kayıtlarıyla uyumludur:

| # | İlke | Kaynak hizası |
|---|------|---------------|
| 1 | Ödeme sistemi, **ödeme ürün modeli + PSP/hukuk-mali ödeme akışı uygulama paketi** hazır olana kadar **ertelenir** (şirket/vergi kaydı mevcut; erteleme nedeni şirket yokluğu değildir). | `commercial-domain-payments.md` |
| 2 | Bu sürede **banka, PSP, merchant hesabı veya ödeme sağlayıcı entegrasyonu** aktif geliştirme kapsamında **yapılmaz**. | `commercial-domain-payments.md` |
| 3 | Lumos, kullanıcı **açık onayı olmadan** ödeme, satın alma, abonelik, domain satın alma/yenileme **başlatmaz**. | `lumos-karar-sozlesmesi.md`, `security-architecture.md` |
| 4 | Ödeme bilgisi, kullanıcı verisi ve credential'lar Lumos **yüzeyinde** tutulmaz; vault ve sahiplik ilkeleri geçerlidir. | `data-vault-user-data.md` |
| 5 | Ticari dış aksiyonlar Lumos **güvenli geçidi** ve **açık kapsam + risk gösterimi** üzerinden tanımlanır. | `external-integrations-permissions.md` |
| 6 | Public `lumos-core` reposuna ödeme credential'ı, banka bilgisi, merchant detayı veya production endpoint **yazılmaz**. | `security-architecture.md`, public boundary kuralları |
| 7 | QR veya tek ödeme linki fikri **yalnızca gelecek ürün notu** olarak saklanır; **uygulama, tasarım veya entegrasyon yok**. | `commercial-domain-payments.md` |
| 8 | Gerçek ödeme entegrasyonu, webhook, settlement ve reconciliation **kapsam dışı**; uygulama paketi onaylanana kadar başlatılmaz. | `commercial-domain-payments.md` |
| 9 | Lumos, kullanıcı adına **ödeme linki oluşturma veya paylaşma** dahil onaysız ticari aksiyon başlatmaz. | `external-integrations-permissions.md` |

---

## 4. Ödeme sistemi karar sınırı

```
[ Ödeme modeli / PSP / hukuk-mali akış uygulama paketi yok ] → ödeme sistemi KAPSAM DIŞI
[ Kullanıcı açık onayı yok ]                                  → ödeme/domain/abonelik BAŞLATILMAZ
[ Lumos yüzeyi ]                                              → ödeme bilgisi / credential TUTULMAZ
[ Public repo ]                                               → operasyonel ödeme detayı YAZILMAZ
```

**Karar sınırı özeti:**

- **Onaylandı (şimdi):** Kapsam dışı sınır, onaysız ticari aksiyon yasağı, QR/link gelecek-notu konumu, public repo ve yüzey sınırı.
- **Uygulama (beklemede):** Ödeme altyapısı, entegrasyon, PSP/banka kurulumu — hiçbiri başlamadı; bu belge tek başına uygulama izni vermez.
- **Sonra (koşullu):** Ödeme ürün modeli, PSP seçimi, hukuk/mali ödeme akışı ve fatura/vergi işleme uygulama paketi netleşince ayrı karar turu ve OD güncellemesi gerekir.
- **Her zaman:** Kullanıcı onayı, gateway ilkesi ve çekirdek sözleşme üst sınırdır.

---

## 5. Uygulama paketi önkoşulu

| Konu | Durum |
|------|--------|
| Şirket / vergi kaydı | **Mevcut** — ödeme kapsamı ertelemesinin nedeni şirket yokluğu değildir |
| Ödeme özelliğine geçiş önkoşulu | Ödeme ürün modeli, PSP seçimi, hukuk/mali ödeme akışı ve fatura/vergi işleme **uygulama paketi** onaylanmadan ödeme sistemi aktif kapsama **alınmaz** |
| Vergi, fatura, mevzuat uyumu | `[needs-review]` — uygulama paketi içinde ayrı hukuk/mali değerlendirme gerekir |
| Domain ticari işlemleri | Domain izleme ayrı; satın alma/yenileme yine açık onaylı — bkz. `commercial-domain-payments.md` |

**Firm karar:** Ödeme sistemi, ödeme modeli / PSP / hukuk-mali ödeme akışı uygulama paketi hazır olana kadar **aktif geliştirme kapsamı dışında** kalır.

---

## 6. PSP/banka/merchant kapsamı

| Bileşen | Şu anki karar |
|---------|---------------|
| Banka hesabı | Kurulum yok; değerlendirme yok |
| PSP (ödeme sağlayıcı) | Kurulum yok; sağlayıcı seçimi yapılmadı |
| Merchant hesabı | Açılmaz; tanımsız |
| Checkout / ödeme gateway entegrasyonu | Uygulama yok |
| Webhook, settlement, iade akışı | Tanımsız; kapsam dışı |

**Firm karar:** Banka, PSP, merchant account veya payment provider **setup çalışması yapılmaz**.

**Needs-review (ileride, koşullu):** Hangi PSP modeli (doğrudan merchant, platform, marketplace), hangi ülke/para birimi, KYC/AML ve sözleşme gereksinimleri — ayrı karar turu.

---

## 7. QR / tek ödeme linki fikri

`commercial-domain-payments.md` migration #8'den taşınan gelecek fikir:

| Öğe | Karar |
|-----|--------|
| Kullanım senaryosu (taslak) | Kullanıcılar arası **maliyet paylaşımı** |
| Teknik biçim (taslak) | QR kod veya **tek ödeme linki** |
| Ürün durumu | **Gelecek ürün fikri** — uygulama, tasarım veya entegrasyon yok |
| Hukuk / PSP modeli | `[needs-review]` |
| Vergi ve dağıtım modeli | `[needs-review]` |

**Firm karar:** QR veya tek ödeme linki fikri yalnızca not olarak saklanır; Lumos şu an bu akışı **başlatmaz, üretmez veya dağıtmaz**.

---

## 8. Kullanıcı onayı ve ticari dış aksiyon sınırı

Tüm **ticari dış aksiyonlar** (ödeme, domain satın alma/yenileme, abonelik, üçüncü taraf checkout, ödeme linki oluşturma) için:

| Sınır | Kural |
|-------|--------|
| Onay | Kullanıcı **açık onayı** zorunlu |
| Kapsam | İşlem **açık kapsam** ile tanımlı (ne, nerede, ne kadar) |
| Risk | **Risk gösterimi** kullanıcıya sunulmalı |
| Gateway | Lumos güvenli geçidi; sessiz arka plan ödemesi yok |
| Varsayılan onay | Lumos, kullanıcı adına **sessiz** veya **varsayılan-onaylı** ticari işlem başlatmaz |

**Onay akışı (taslak — model needs-review):**

```
[ Bilgi: fiyat · risk · kapsam ] → [ Açık onay ] → [ İzinli aksiyon ]
```

**Yasak (onaysız):** ödeme başlatma, satın alma, yenileme, abonelik aktivasyonu, üçüncü taraf ödeme linki oluşturma/paylaşma (Lumos adına).

**Çapraz referans:** `external-integrations-permissions.md` genel yasak tablosu; `lumos-karar-sozlesmesi.md` karar katmanları (`SECURITY_NEVER_AUTO`, dış yazma).

---

## 9. Veri/vault ve ödeme bilgisi ilişkisi

| İlke | Açıklama |
|------|----------|
| Veri sahipliği | Kullanıcı verinin sahibidir; Lumos ayrı sahiplik kurmaz (`data-vault-user-data.md`) |
| Yüzey ayrımı | Ödeme bilgisi ve hassas kullanıcı verisi mümkün olduğunca Lumos **yüzeyinde** tutulmaz |
| Vault rolü | Lumos yetkili **geçit/orkestratör**; ham secret'ları yüzeyde biriktirmez |
| Credential | Token, banka ve ödeme credential'ları Lumos yüzeyinde açık tutulmaz |
| Onaysız veri | Onaysız dış veri çekme, kalıcı import veya kullanıcı adına silme yapılmaz |

**Ödeme bilgisi özelinde:** Kart, IBAN, merchant API anahtarı veya benzeri veriler — uygulama aşamasına geçilse bile — vault/katman ve amaç bazlı erişim modeli (`OD-001`–`OD-005`, needs-review) netleşmeden Lumos yüzeyine taşınmaz.

---

## 10. Public repo sınırı

Public `lumos-core` deposu açık kaynak **foundation** katmanıdır.

**Taşınmaz / yazılmaz:**

- Ödeme credential'ı, API anahtarı, token
- Banka hesabı veya merchant bilgisi
- Production ödeme endpoint'i veya operasyonel URL
- Kullanıcı ödeme verisi, PII, licensing/payment sistemleri (private katman)

**Taşınabilir (bu belge gibi):**

- Demo-safe politika ve karar notları
- Placeholder/stub açıklamalar
- Kapsam dışı ve onay ilkeleri

**Firm karar:** Public repoda ödeme entegrasyonu, gerçek sağlayıcı detayı veya operasyonel altyapı **bulunmaz**.

---

## 11. Açık kararlar

Aşağıdakiler **needs-review** olarak kalır; bu karar taslağı bunları kapatmaz:

| Konu | OD / kaynak | Not |
|------|-------------|-----|
| PSP seçimi ve sözleşme modeli | OD-011, OD-040 | Platform vs merchant; ülke/para birimi |
| Ödeme sağlayıcı entegrasyonu | OD-011 | Uygulama paketi içinde tanımlanacak |
| Vergi, fatura, mevzuat uyumu | OD-011 | Uygulama paketi içinde mali/hukuk değerlendirme |
| Abonelik modeli | OD-011 | Ürün + PSP birlikte |
| Maliyet paylaşımı modeli | OD-040 | Ürün + hukuk + PSP birlikte |
| Ödeme verisi vault entegrasyonu | OD-001, OD-003 | `data-vault-user-data.md` |
| QR / tek link maliyet paylaşımı ürün modeli | OD-040 | Ürün + hukuk + PSP birlikte |
| Ticari onay: hibrit model (oturum vs işlem) | OD-041 | [`commercial-approval-model-decision.md`](./commercial-approval-model-decision.md) — **decision-approved / implementation-pending** |
| Domain varyasyon redirect (ticari edinim sonrası) | OD-039 | [`domain-redirect-model-decision.md`](./domain-redirect-model-decision.md) — **decision-approved / implementation-pending** |

---

## 12. OD eşleme tablosu

| OD | Kaynak dosya | Konu | Bu belgedeki karar | Durum |
|----|--------------|------|-------------------|--------|
| **OD-011** | `commercial-domain-payments.md` | Ödeme sistemi kapsamı | Ödeme modeli/PSP/hukuk-mali akış uygulama paketi bekleniyor; ödeme/PSP aktif kapsam dışı | **decision-approved / implementation-pending** |
| OD-040 | `commercial-domain-payments.md` | Maliyet paylaşımı QR/link | Gelecek fikir only; ürün/hukuk/PSP belirsiz | needs-review |
| OD-041 | `commercial-domain-payments.md` | Ticari onay modeli | Hibrit model — [`commercial-approval-model-decision.md`](./commercial-approval-model-decision.md) | **decision-approved / implementation-pending** |
| OD-039 | `commercial-domain-payments.md` | Domain redirect | [`domain-redirect-model-decision.md`](./domain-redirect-model-decision.md) — ödeme kapsamı dışı | **decision-approved / implementation-pending** |
| OD-001–002 | `security-architecture.md` | Vault / token | Ödeme credential yüzeyde değil | decision-approved / implementation-pending |
| OD-003–005 | `data-vault-user-data.md` | Vault erişim / şifreleme | Ödeme verisi vault ilkesine tabi | decision-approved / implementation-pending |

**İndeks notu:** `open-decisions-needs-review.md` OD-011 satırı bu belgeyle senkron tutulur; canonical kaynak önce `commercial-domain-payments.md`, onaylı karar özeti bu dosyadır.

---

## 13. Sonraki adım

1. **Needs-review (devam):** PSP seçimi, ödeme sağlayıcı entegrasyonu, vergi/fatura akışı, abonelik modeli, maliyet paylaşımı modeli, ödeme verisi vault entegrasyonu — uygulama paketi değerlendirmesi (çoğu bu repo dışı).
2. **OD-040 / OD-041:** Maliyet paylaşımı QR/link ürün modeli ve ticari onay (tek seferlik vs oturum bazlı) detayları netleşene kadar uygulama yok.
3. Koşullar netleşince: `commercial-domain-payments.md` güncellenir; uygulama spesifikasyonu **yeni** belgede açılır (bu onaylı karar belgesi tek başına uygulama izni vermez).
4. Ödeme kapsamına geçilmeden önce: vault modeli (OD-001–005), ticari onay modeli (OD-041) ve public boundary tekrar doğrulanmalı.

**Yasak (bu aşamada):** kod, test, ödeme entegrasyonu, sağlayıcı seçimi, banka/PSP kurulumu, credential, endpoint, secret.

---

## Çapraz referanslar

- [`commercial-domain-payments.md`](./commercial-domain-payments.md) — canonical ödeme/domain kaydı
- [`external-integrations-permissions.md`](./external-integrations-permissions.md) — onaysız ödeme/domain yasağı
- [`data-vault-user-data.md`](./data-vault-user-data.md) — veri sahipliği ve vault
- [`security-architecture.md`](./security-architecture.md) — güvenlik ilkeleri ve public sınır
- [`open-decisions-needs-review.md`](./open-decisions-needs-review.md) — OD-011 indeks
- [`../lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — çekirdek sözleşme

---

*Son güncelleme: 2026-06-20 (OD-041/039 tablo sync — envanter ab791c14 §13)*
