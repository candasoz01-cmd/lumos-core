# Ödeme sistemi kapsam kararı — OD-011 karar taslağı

**Durum:** `[decision-draft]` — uygulama başlamadı; bu belge kod değişikliği değildir.

**Kaynak OD:** OD-011 (`commercial-domain-payments.md` — Ödeme sistemi kapsamı)

**Çelişki çözümü:** Bu dosya ile kaynak canonical dosyalar arasında çelişki varsa `docs/lumos-karar-sozlesmesi.md` ve ilgili kaynak `docs/memory/*.md` dosyaları esas alınır.

---

## 1. Amaç

OD-011 kapsamında ödeme sistemi, PSP (Payment Service Provider), banka/merchant hesabı ve ticari ödeme akışlarının **Lumos ürün sınırını** netleştirmek.

Bu belge:

- Şirket/resmî iş yapısı netleşene kadar ödeme altyapısının **kapsam dışı** kalmasını kayıt altına alır.
- Onaysız ödeme, satın alma, abonelik ve domain işlemlerinin **yasak** olduğunu tekrarlar.
- QR / tek ödeme linki fikrini yalnızca **gelecek ürün notu** olarak konumlandırır.
- Vault, veri sahipliği ve public repo sınırlarıyla hizayı sabitler.

**Uygulama durumu:** Ödeme sistemi uygulaması **başlamadı**. Bu doküman politika/karar taslağıdır; kod, test, panel, bridge veya entegrasyon değişikliği içermez.

---

## 2. Kapsam dışı olanlar

Aşağıdakiler **şu an ve şirket/resmî yapı netleşene kadar** Lumos geliştirme ve ürün kapsamı dışındadır:

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

## 3. Netleşen ilkeler

Aşağıdaki ilkeler **firm** (sabit) kabul edilir; çekirdek sözleşme ve canonical memory kayıtlarıyla uyumludur:

| # | İlke | Kaynak hizası |
|---|------|---------------|
| 1 | Ödeme sistemi, **şirket/resmî bağımsız iş yapısı** netleşene kadar **ertelenir**. | `commercial-domain-payments.md` |
| 2 | Bu sürede **banka, PSP, merchant hesabı veya ödeme sağlayıcı kurulumu yapılmaz**. | `commercial-domain-payments.md` |
| 3 | Lumos, kullanıcı **açık onayı olmadan** ödeme, satın alma, abonelik, domain satın alma/yenileme **başlatmaz**. | `lumos-karar-sozlesmesi.md`, `security-architecture.md` |
| 4 | Ödeme bilgisi, kullanıcı verisi ve credential'lar Lumos **yüzeyinde** tutulmaz; vault ve sahiplik ilkeleri geçerlidir. | `data-vault-user-data.md` |
| 5 | Ticari dış aksiyonlar Lumos **güvenli geçidi** ve **açık kapsam + risk gösterimi** üzerinden tanımlanır. | `external-integrations-permissions.md` |
| 6 | Public `lumos-core` reposuna ödeme credential'ı, banka bilgisi, merchant detayı veya production endpoint **yazılmaz**. | `security-architecture.md`, public boundary kuralları |
| 7 | QR veya tek ödeme linki fikri **yalnızca gelecek ürün notu** olarak saklanır; uygulama yok. | `commercial-domain-payments.md` |

---

## 4. Ödeme sistemi karar sınırı

```
[ Şirket/resmî yapı belirsiz ] → ödeme sistemi KAPSAM DIŞI
[ Kullanıcı açık onayı yok ]   → ödeme/domain/abonelik BAŞLATILMAZ
[ Lumos yüzeyi ]               → ödeme bilgisi / credential TUTULMAZ
[ Public repo ]                → operasyonel ödeme detayı YAZILMAZ
```

**Karar sınırı özeti:**

- **Şimdi:** Politika notu ve karar taslağı; teknik uygulama yok.
- **Sonra (koşullu):** Şirket/resmî yapı + hukuk/vergi/PSP modeli netleşince ayrı karar belgesi ve OD güncellemesi gerekir; bu belge tek başına uygulama izni vermez.
- **Her zaman:** Kullanıcı onayı, gateway ilkesi ve çekirdek sözleşme üst sınırdır.

---

## 5. Şirket/resmî yapı şartı

| Konu | Durum |
|------|--------|
| Bağımsız şirket / resmî iş yapısı | `[needs-review]` — hukuk ve operasyonel detay bu belgede tanımlanmaz |
| Ödeme özelliğine geçiş önkoşulu | Resmî yapı netleşmeden ödeme sistemi kapsama **alınmaz** |
| Vergi, fatura, mevzuat uyumu | `[needs-review]` — ayrı hukuk/mali değerlendirme gerekir |
| Domain ticari işlemleri | Domain izleme ayrı; satın alma/yenileme yine açık onaylı — bkz. `commercial-domain-payments.md` |

**Firm karar:** Ödeme sistemi, şirket/resmî bağımsız iş yapısı açıklanana kadar **tamamen dışarıda** kalır.

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
| Şirket/resmî bağımsız iş yapısı zamanlaması ve formu | OD-011 | Hukuk/operasyon ayrı değerlendirme |
| PSP seçimi ve sözleşme modeli | OD-011, OD-040 | Platform vs merchant; ülke/para birimi |
| Vergi, fatura, mevzuat uyumu | — | Mali/hukuk danışmanlığı gerekir |
| QR / tek link maliyet paylaşımı ürün modeli | OD-040 | Ürün + hukuk + PSP birlikte |
| Ticari onay: tek seferlik vs oturum bazlı | OD-041 | Çekirdek sözleşme onay katmanları esas |
| Vault amaç bazlı erişim (ödeme verisi dahil) | OD-001, OD-003 | `security-architecture.md`, `data-vault-user-data.md` |
| Domain varyasyon redirect (ticari edinim sonrası) | OD-039 | Edinim zaten onaylı; teknik detay sonra |

---

## 12. OD eşleme tablosu

| OD | Kaynak dosya | Konu | Bu belgedeki karar | Durum |
|----|--------------|------|-------------------|--------|
| **OD-011** | `commercial-domain-payments.md` | Ödeme sistemi kapsamı | Şirket yapısı netleşene kadar ödeme/PSP tamamen dışarıda | **decision-draft** (needs-review devam) |
| OD-040 | `commercial-domain-payments.md` | Maliyet paylaşımı QR/link | Gelecek fikir only; ürün/hukuk/PSP belirsiz | needs-review |
| OD-041 | `commercial-domain-payments.md` | Ticari onay modeli | Açık onay zorunlu; tek/oturum modeli belirsiz | needs-review |
| OD-039 | `commercial-domain-payments.md` | Domain redirect | Ödeme belgesi kapsamı dışı; çapraz referans | needs-review |
| OD-001–002 | `security-architecture.md` | Vault / token | Ödeme credential yüzeyde değil | needs-review |
| OD-003–005 | `data-vault-user-data.md` | Vault erişim / şifreleme | Ödeme verisi vault ilkesine tabi | needs-review |

**İndeks notu:** `open-decisions-needs-review.md` OD-011 satırı, bu belge yayınlandıktan sonra manuel senkronize edilebilir; canonical kaynak önce `commercial-domain-payments.md`, karar özeti bu dosyadır.

---

## 13. Sonraki adım

1. **Şirket/resmî yapı** ve hukuk/mali çerçeve için ayrı değerlendirme (bu repo dışı; needs-review).
2. Koşullar netleşince: `commercial-domain-payments.md` ve `open-decisions-needs-review.md` içinde OD-011 durumunu güncelle; gerekirse uygulama spesifikasyonu **yeni** belgede aç (bu taslak uygulama izni vermez).
3. Ödeme kapsamına geçilmeden önce: vault modeli (OD-001–005), ticari onay modeli (OD-041) ve public boundary tekrar doğrulanmalı.

**Tek doğrulanabilir sonraki repo adımı (dokümantasyon):** OD-011 için `open-decisions-needs-review.md` indeks satırına bu belgeye referans eklenmesi — ayrı onaylı commit turu; bu dosya tek başına indeksi değiştirmez.

---

## Çapraz referanslar

- [`commercial-domain-payments.md`](./commercial-domain-payments.md) — canonical ödeme/domain kaydı
- [`external-integrations-permissions.md`](./external-integrations-permissions.md) — onaysız ödeme/domain yasağı
- [`data-vault-user-data.md`](./data-vault-user-data.md) — veri sahipliği ve vault
- [`security-architecture.md`](./security-architecture.md) — güvenlik ilkeleri ve public sınır
- [`open-decisions-needs-review.md`](./open-decisions-needs-review.md) — OD-011 indeks
- [`../lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — çekirdek sözleşme

---

*Son güncelleme: 2026-06-17*
