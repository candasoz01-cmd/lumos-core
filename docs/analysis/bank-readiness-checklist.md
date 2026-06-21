# Lumos — KKTC Banka / Sanal POS Hazırlık Kontrol Listesi

| Alan | Değer |
|------|--------|
| **Belge ID** | `bank-readiness-checklist` |
| **Durum** | `analiz` — banka incelemesi öncesi boşluk envanteri |
| **Tarih** | 2026-06-21 |
| **Amaç** | KKTC banka incelemesi ve sanal POS / merchant hesabı onayı için **eksik ve kısmi** maddeleri tespit etmek |
| **Yargı yetkisi** | **KKTC (Kuzey Kıbrıs Türk Cumhuriyeti)** — genel SaaS kontrol listesi KKTC mevzuatı, banka prosedürü ve vergi uygulaması için **yerel danışmanlık** gerektirebilir; bu belgede KKTC'ye özgü maddeler `[KKTC]` ile işaretlenir |
| **Kapsam** | Ticari katman, müşteri yüzeyi ve dış operasyon; **kod veya credential içermez** |
| **Birincil kaynak** | [`commercial-product-packaging.md`](./commercial-product-packaging.md) |
| **İlgili kayıtlar** | [`commercial-domain-payments.md`](../memory/commercial-domain-payments.md), [`payment-scope-decision.md`](../memory/payment-scope-decision.md) (OD-011), [`public-repo-boundary.md`](../memory/public-repo-boundary.md), [`open-decisions-needs-review.md`](../memory/open-decisions-needs-review.md) |
| **Public sınır** | Production secret, PSP credential, banka/merchant detayı ve operasyonel endpoint **public repoda ve bu belgede yer almaz** |

---

## Yönetici özeti

Bu kontrol listesi, Lumos'un **planlanan SaaS abonelik modeli** (Pro / Business) için KKTC banka / sanal POS incelemesinde sorulabilecek maddeleri repo kanıtlarına göre sınıflandırır.

| Durum | Adet | Açıklama |
|-------|------|----------|
| **Hazır** | 11 | Şirket kaydı onayı, ürün çerçevesi, onay ilkeleri, OSS/prod ayrımı, panel deploy izi, PCI ilkesi vb. |
| **Kısmi** | 20 | Planlama metni var; müşteri yüzeyi, operasyon veya hukuk onayı eksik |
| **Eksik** | 22 | Banka incelemesi için kritik boşluk (PSP, checkout, hukuki sayfalar, fiyat, fatura akışı vb.) |
| **TBD** | 13 | Karar veya dış danışmanlık bekliyor (KYC evrakları, para birimi, KKTC vergi detayı vb.) |

*Toplam checklist maddesi: 66 (§1–§5 tabloları).*

**Genel değerlendirme:** Şirket / vergi kaydı **mevcut** ([`commercial-product-packaging.md` §8](./commercial-product-packaging.md#8-banka-ve-uyumluluk-özeti)); ancak **aktif ödeme altyapısı, PSP seçimi, checkout, hukuki müşteri sayfaları ve nihai fiyat/fatura metinleri eksik**. OD-011 ilke kararları onaylı olsa da **uygulama paketi başlamadı**; bu nedenle sanal POS başvurusu şu an **hazır değil**.

**Yüzey etiketleri (tablolarda):**

| Etiket | Anlam |
|--------|--------|
| **Repo-içi** | `lumos-core` veya bağlı canonical belgelerde kanıt |
| **Müşteri-yüzeyi** | `welockai.com` veya resmi panelde son kullanıcıya görünür olması gerekir |
| **Dış-only** | Banka, PSP, mali müşavir, hukuk veya private ops vault — repoda tutulmaz |

---

## Çapraz referans — `commercial-product-packaging.md`

| Bu belge bölümü | Packaging referansı |
|-----------------|---------------------|
| §1 Sanal POS başvurusu | Packaging §8 (Banka özeti), §5 (Abonelik), OD-011 notları |
| §2 Şirket evrakları | Packaging §8 (şirket kaydı), §2 (segment) |
| §3 Site gereksinimleri | Packaging §7 (Destek), §9 (Sonraki adımlar), OD-048 landing |
| §4 Hukuki sayfalar | Packaging §6 (İptal/iade), §9 madde 4 |
| §5 Abonelik ve faturalama | Packaging §3–§5, §6.2–6.4 |

---

## 1. Sanal POS başvurusu

> **Packaging:** §8, §5 · **OD-011:** ödeme/PSP aktif geliştirme kapsamı **dışı** ([`payment-scope-decision.md`](../memory/payment-scope-decision.md))

| Madde | Durum | Kaynak / kanıt | Not / aksiyon |
|-------|--------|----------------|---------------|
| İş modeli tanımı (SaaS abonelik — yazılım hizmeti) | **Hazır** | **Repo-içi:** [`commercial-product-packaging.md` §1–§3](./commercial-product-packaging.md#1-ne-satıyoruz) | Banka formunda MCC / faaliyet kodu **[KKTC]** yerel danışmanla netleştirilmeli |
| Gelir modeli özeti (Pro/Business ücretli; Starter ücretsiz OSS) | **Hazır** | **Repo-içi:** Packaging §3.1, §8 | Başvuru formuna kısa Türkçe özet eklenmeli (**Dış-only**) |
| PSP / ödeme sağlayıcı seçimi | **Eksik** | **Repo-içi:** OD-011 `needs-review` — [`payment-scope-decision.md` §11](../memory/payment-scope-decision.md#11-açık-kararlar) | KKTC'de sanal POS genelde **banka + PSP/gateway** birlikteliği; aday listesi ve sözleşme modeli **Dış-only** |
| Merchant / sanal POS hesabı başvurusu | **Eksik** | **Repo-içi:** [`commercial-domain-payments.md`](../memory/commercial-domain-payments.md) — kurulum yok | Banka başvuru paketi **henüz oluşturulmadı** (**Dış-only**) |
| Checkout / ödeme sayfası (hosted veya embedded) | **Eksik** | **Repo-içi:** OD-011 — checkout uygulanmadı | PCI kapsamı PSP tarafında kalacak şekilde tasarlanır (Packaging §7.3); **Müşteri-yüzeyi** |
| Webhook, settlement, reconciliation | **Eksik** | **Repo-içi:** [`payment-scope-decision.md` §6](../memory/payment-scope-decision.md#6-pspbankamerchant-kapsamı) | Uygulama paketi onayı sonrası **private** katman |
| Kart verisi Lumos yüzeyinde tutulmaz (PCI ilkesi) | **Hazır** | **Repo-içi:** Packaging §7.3, OD-011 ilkeleri | Banka/PSP'ye mimari özet olarak sunulabilir |
| KYC / AML ve banka risk soru formu | **TBD** | **Dış-only** | **[KKTC]** banka ve mevzuat gereksinimleri; repo kapsamı dışı |
| Chargeback / itiraz prosedürü taslağı | **Kısmi** | **Repo-içi:** Packaging §6.3 | Nihai metin PSP kuralları + hukuk onayı (**Dış-only** form eki) |
| 3D Secure / güvenli ödeme akışı | **TBD** | **Dış-only** | Seçilen banka/PSP'ye bağlı **[KKTC]** |
| Test ortamı / sandbox merchant | **Eksik** | **Repo-içi:** Aktif entegrasyon yok | PSP seçimi sonrası **Dış-only** |
| Başvuru öncesi canlı tahsilat yok (kapsam dışı ilke) | **Hazır** | **Repo-içi:** OD-011 `decision-approved` | Bilinçli erteleme; banka görüşmesinde "henüz tahsilat yok" şeffaf anlatılmalı |

---

## 2. Şirket evrakları

> **Packaging:** §8 · **Not:** Şirket/vergi kaydı **mevcut**; evrakların fiziksel/dijital kopyaları repoda **tutulmaz** ([`public-repo-boundary.md`](../memory/public-repo-boundary.md))

| Madde | Durum | Kaynak / kanıt | Not / aksiyon |
|-------|--------|----------------|---------------|
| Tüzel kişilik / şirket kaydı | **Hazır** | **Repo-içi:** Packaging §8, [`payment-scope-decision.md` §5](../memory/payment-scope-decision.md#5-uygulama-paketi-önkoşulu) | Asıl belgeler **Dış-only** (şirket dosyası) |
| Vergi kaydı / vergi numarası | **Hazır** | **Repo-içi:** OD-011 — erteleme nedeni şirket yokluğu **değil** | Güncel vergi levhası banka paketine eklenmeli **[KKTC]** (**Dış-only**) |
| Ticaret sicil / şirket kuruluş belgesi | **TBD** | **Dış-only** | **[KKTC]** evrak adları bankaya göre değişir; yerel danışman doğrulasın |
| İmza sirküleri / yetkili imza | **TBD** | **Dış-only** | Sanal POS sözleşmesi için zorunlu **[KKTC]** |
| Faaliyet konusu (yazılım / SaaS / danışmanlık uyumu) | **Kısmi** | **Repo-içi:** Packaging §1.1–§1.2 | Ana sözleşme faaliyet kodu ile Packaging'deki "AI kontrol katmanı / SaaS" hizası doğrulanmalı (**Dış-only**) |
| Ortaklık / UBO beyanı (varsa) | **TBD** | **Dış-only** | Banka KYC **[KKTC]** |
| Banka hesabı (TL / döviz — işletme hesabı) | **TBD** | **Dış-only** | Settlement hesabı; repoda **asla** tutulmaz |
| Son 3–6 ay hesap özeti / mali tablo (talebe bağlı) | **TBD** | **Dış-only** | Yeni şirket / düşük hacim senaryosunda banka alternatif ister **[KKTC]** |
| Ticari marka / We Lock AI — Lumos ilişkisi açıklaması | **Kısmi** | **Repo-içi:** [`NOTICE`](../../NOTICE), Packaging §1.3 | Marka lisansı ayrı konu; banka için kısa org chart veya marka sahipliği yazısı **Dış-only** |
| Apache-2.0 OSS vs ücretli resmi hizmet ayrımı | **Hazır** | **Repo-içi:** Packaging §1.3, §3.2–§3.3 | Banka "ne satılıyor" sorusuna net cevap |
| Resmi adres, telefon, e-posta (şirket) | **TBD** | **Dış-only** | Destek adresi Packaging §7.1'de `support@<TBD_DOMAIN>` — henüz sabitlenmedi |
| e-İmza / mühür (başvuru formatına bağlı) | **TBD** | **Dış-only** | **[KKTC]** banka prosedürü |

---

## 3. Site gereksinimleri

> **Packaging:** §7, §9 · **Mevcut iz:** `https://welockai.com/panel` ([`LUMOS_V1_READINESS.md`](../LUMOS_V1_READINESS.md))

| Madde | Durum | Kaynak / kanıt | Not / aksiyon |
|-------|--------|----------------|---------------|
| Birincil domain (`welockai.com`) | **Kısmi** | **Repo-içi:** [`commercial-domain-payments.md`](../memory/commercial-domain-payments.md) — hedef domain | Canlı panel `/panel`; tam ticari vitrin **eksik** (OD-048 `needs-review`) |
| HTTPS / geçerli SSL | **Hazır** | **Müşteri-yüzeyi:** [`LUMOS_V1_READINESS.md`](../LUMOS_V1_READINESS.md) prod smoke | Banka kontrolünde URL listesi verilmeli |
| Şirket / ürün tanıtım sayfası (landing) | **Eksik** | **Repo-içi:** OD-048 `needs-review`; Packaging §9 madde 5 | Paket isimleri ve iddia seviyesi ile senkron landing gerekli (**Müşteri-yüzeyi**) |
| İletişim sayfası (adres, e-posta, form) | **Eksik** | **Repo-içi:** Packaging §7.1 — destek e-postası TBD | **[KKTC]** bankalar genelde **fiziksel adres + ulaşılabilir iletişim** ister |
| Hakkımızda / şirket bilgisi | **Eksik** | **Müşteri-yüzeyi** | We Lock AI / Lumos ilişkisi; repoda hazır müşteri metni yok |
| Fiyatlandırma sayfası (Pro/Business) | **Eksik** | **Repo-içi:** Packaging §3.1 — fiyat TBD (OD-011) | Banka "ne kadar tahsil edilecek" sorusu için en az **planlanan** fiyat aralığı veya "teklif usulü" (**Müşteri-yüzeyi**) |
| Ürün / hizmet açıklaması (satılan değer) | **Kısmi** | **Repo-içi:** [`PRODUCT_SUMMARY.md`](../PRODUCT_SUMMARY.md), Packaging §1 | Teknik README banka diline çevrilmeli (**Müşteri-yüzeyi**) |
| Destek kanalı (e-posta / ticket) | **Eksik** | **Repo-içi:** Packaging §7.1 — planlanan | `support@welockai.com` veya eşdeğeri operasyonel kurulum **Dış-only** |
| Durum sayfası (uptime / kesinti) | **Eksik** | **Repo-içi:** Packaging §7.1 | SLA öncesi "best effort" metni Packaging §7.2 |
| Erişilebilir kayıt / giriş (Pro müşteri) | **Eksik** | **Repo-içi:** Packaging §3.3 — resmi barındırma planlanan | Panel teknik olarak var; **ücretli müşteri onboarding** yok |
| Domain varyasyon redirect (marka) | **Kısmi** | **Repo-içi:** OD-039 `implementation-pending` | Banka için zorunlu değil; marka bütünlüğü için önerilir |
| Production API / backend ayrımı açıklaması | **Kısmi** | **Repo-içi:** [`public-repo-boundary.md`](../memory/public-repo-boundary.md) | Banka risk ekibine "OSS foundation vs resmi hizmet" özeti (**Repo-içi** → sunum **Dış-only**) |
| Çalışan olmayan / placeholder sayfa yok | **TBD** | **Müşteri-yüzeyi** | Landing yayınlanınca 404 ve "yakında" sayfaları denetlenmeli |

---

## 4. Hukuki sayfalar

> **Packaging:** §6, §9 madde 4 · **Repo taraması:** `legal/`, `privacy`, KVKK metni **bulunamadı**

| Madde | Durum | Kaynak / kanıt | Not / aksiyon |
|-------|--------|----------------|---------------|
| Gizlilik politikası | **Eksik** | **Müşteri-yüzeyi** — Packaging §9.4, §6.4 | KVKK / GDPR uyumlu metin **hukuk onayı** gerekir **[KKTC]** |
| Kullanım koşulları / hizmet şartları | **Eksik** | **Müşteri-yüzeyi** | SaaS abonelik, fair use, hesap askıya alma — Packaging §5.3 |
| Mesafeli satış / elektronik sözleşme (varsa) | **TBD** | **Dış-only** | **[KKTC]** tüketici ve e-ticaret mevzuatı; yerel avukat |
| Cayma hakkı ve iade politikası (yayınlanmış) | **Kısmi** | **Repo-içi:** Packaging §6.2 — çerçeve only | Müşteri yüzeyinde **ayrı sayfa** yok; banka ve PSP ister |
| Çerez politikası | **Eksik** | **Müşteri-yüzeyi** | Panel analytics / oturum çerezleri için **[KKTC]** |
| Veri işleme / DPA (B2B Business) | **Eksik** | **Repo-içi:** Packaging §3.4 — sözleşme eki planlanan | Kurumsal paket için **Dış-only** şablon |
| Marka / logo kullanım koşulları | **Kısmi** | **Repo-içi:** [`NOTICE`](../../NOTICE), Packaging §1.3 | Ayrı marka lisansı; banka için doğrudan gerekli olmayabilir |
| Onaysız otomatik ödeme yapılmaz ilkesi (şeffaflık) | **Hazır** | **Repo-içi:** OD-041, [`commercial-domain-payments.md`](../memory/commercial-domain-payments.md) | Hukuki sayfada **sadeleştirilmiş** müşteri dili gerekli |
| Kalıcı silme / veri saklama süreleri | **Kısmi** | **Repo-içi:** Packaging §6.4, [`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) | Gizlilik politikasında gün sayısı **TBD** — hukuk |
| Üçüncü taraf / alt işleyici listesi (PSP, hosting, AI) | **Eksik** | **Müşteri-yüzeyi** | PSP seçimi sonrası güncellenmeli |
| Yaş / coğrafi kısıt beyanı | **TBD** | **Dış-only** | **[KKTC]** ve hedef pazar için hukuk |
| Hukuki sayfaların Türkçe birincil sürümü | **Eksik** | **Müşteri-yüzeyi** | Packaging birincil dil Türkçe; İngilizce opsiyonel |

---

## 5. Abonelik ve faturalama açıklamaları

> **Packaging:** §3, §5, §6 · **OD-011:** abonelik motoru uygulanmadı

| Madde | Durum | Kaynak / kanıt | Not / aksiyon |
|-------|--------|----------------|---------------|
| Paket tanımları (Starter / Pro / Business) | **Kısmi** | **Repo-içi:** Packaging §3 | Repoda tier **yok**; paketleme **önerisi** — müşteri yüzeyine taşınmalı |
| Aylık / yıllık faturalama döngüsü açıklaması | **Kısmi** | **Repo-içi:** Packaging §5.1 | Oran ve para birimi **TBD** |
| Fiyat listesi (TRY / EUR / USD) | **Eksik** | **Repo-içi:** Packaging §5.1 — OD-011 | Banka başvurusunda en az **taslak fiyat** veya Business "teklif usulü" (**Müşteri-yüzeyi** + **Dış-only**) |
| Deneme süresi (Pro 14 gün önerisi) | **Kısmi** | **Repo-içi:** Packaging §5.2 | Kart zorunluluğu ve otomatik yenileme metni **hukuk onayı** |
| Otomatik yenileme bildirimi | **Kısmi** | **Repo-içi:** Packaging §5.4 | Checkout ve e-posta akışı **eksik** (OD-011) |
| İptal prosedürü (self-servis) | **Kısmi** | **Repo-içi:** Packaging §6.1 | Hesap ayarları UI **planlanan** — henüz yok |
| İade koşulları (yayınlanmış) | **Kısmi** | **Repo-içi:** Packaging §6.2 | Chargeback hizası PSP ile **Dış-only** |
| e-Fatura / e-arşiv süreci | **Eksik** | **Repo-içi:** Packaging §5.1, OD-011 `needs-review` | **[KKTC]** vergi ve fatura mevzuatı — mali müşavir (**Dış-only**) |
| Kurumsal fatura + PO (Business) | **Kısmi** | **Repo-içi:** Packaging §5.1 | Operasyonel süreç tanımsız |
| Vergi dahil / hariç fiyat gösterimi | **TBD** | **Dış-only** | **[KKTC]** KDV veya eşdeğer uygulama |
| Abonelik limitleri / fair use | **Kısmi** | **Repo-içi:** Packaging §5.3 | Kota değerleri **TBD** |
| Pro-rata yükseltme / dönem sonu düşürme | **Kısmi** | **Repo-içi:** Packaging §5.4 | Teknik uygulama OD-011 sonrası |
| Fatura / makbuz e-posta şablonu | **Eksik** | **Dış-only** | PSP veya muhasebe yazılımı entegrasyonu |
| Abonelik durumu self-servis görünürlüğü | **Eksik** | **Repo-içi:** Packaging §4 — planlanan | Panelde faturalama modülü yok |
| PCI — kart Lumos'ta saklanmaz | **Hazır** | **Repo-içi:** Packaging §7.3, OD-011 | Müşteri SSS'sine eklenebilir |
| Ticari işlemde işlem bazlı onay (OD-041) | **Kısmi** | **Repo-içi:** [`commercial-approval-model-decision.md`](../memory/commercial-approval-model-decision.md) | Karar onaylı; UX **implementation-pending** |
| Harici abonelik *izleme* vs Lumos *satışı* ayrımı | **Hazır** | **Repo-içi:** Packaging §4 dipnot, [`subscription-payment-control.md`](../subscription-payment-control.md) | Banka karışıklığını önlemek için SSS'de vurgula |

---

## Boşluk özeti

### Kritik blockers (banka / sanal POS onayı için)

| # | Boşluk | Etki | Yüzey |
|---|--------|------|--------|
| B1 | **PSP seçimi ve merchant/sanal POS başvuru paketi yok** | Tahsilat altyapısı tanımsız | Dış-only |
| B2 | **Checkout / ödeme akışı uygulanmadı** (OD-011 `implementation-pending`) | Canlı satış ve banka test işlemi yok | Müşteri-yüzeyi + private |
| B3 | **Yayınlanmış hukuki sayfalar yok** (gizlilik, kullanım, iade) | Banka ve PSP uyumluluk red riski | Müşteri-yüzeyi |
| B4 | **Fiyat listesi ve vergi/fatura akışı TBD** | Gelir tahmini ve mali izlenebilirlik belirsiz | Dış-only + müşteri-yüzeyi |
| B5 | **Ticari landing + iletişim + destek kanalı eksik** | "Faaliyet kanıtı" ve müşteri erişilebilirliği zayıf | Müşteri-yüzeyi |

### Nice-to-have (ilk başvuru sonrası veya erken erişim döneminde)

| # | Madde | Not |
|---|--------|-----|
| N1 | Durum sayfası / SLA metrikleri | Packaging §7.2 — erken fazda "best effort" yeterli olabilir |
| N2 | Domain varyasyon redirect (OD-039) | Marka; banka zorunluluğu değil |
| N3 | Business DPA / kurumsal sözleşme eki | İlk B2C Pro lansmanında ertelenebilir |
| N4 | Çok para birimi | PSP kararına bağlı |
| N5 | Uygulama içi yardım merkezi | Self-servis destek artırır; başvuru için zorunlu değil |
| N6 | OD-040 maliyet paylaşımı QR/link | `needs-review`; sanal POS kapsamı dışı |

---

## OD-011 durumunun kontrol listesine etkisi

| OD-011 katmanı | Durum | Checklist etkisi |
|----------------|--------|------------------|
| İlke kararları | `decision-approved` | Onaysız ödeme yasağı, public boundary, PCI ilkesi maddeleri **hazır** sayılır |
| Uygulama | `implementation-pending` | PSP, checkout, webhook, abonelik motoru, fatura entegrasyonu maddeleri **eksik** |
| Needs-review | PSP, vergi/fatura, abonelik modeli, maliyet paylaşımı | İlgili satırlar **TBD** veya **eksik** |
| Şirket kaydı | **Mevcut** (erteleme nedeni değil) | §2 şirket evrakları **kısmi hazır** — fiziksel paket **Dış-only** |
| Public repo | Credential/endpoint yasağı | Banka detayları repoya **yazılmaz**; checklist kanıt olarak yalnızca belge referansı |

**Sonuç:** OD-011, banka hazırlığını **bloklayan** ana karar değil; ancak **uygulama paketi tamamlanmadan** sanal POS canlıya alınamaz. Banka görüşmesi "hazırlık / ön onay" için yapılabilir; **canlı tahsilat** için OD-011 uygulama + hukuk/mali paket şart.

**Önerilen sıra (Packaging §9 ile hizalı):**

1. Hukuk: gizlilik, kullanım, iade (**§4**)
2. Müşteri yüzeyi: landing, fiyat, iletişim (**§3**)
3. OD-011 uygulama paketi: PSP, fiyat, vergi/fatura (**§1, §5**)
4. Banka merchant / sanal POS başvurusu (**§1**)
5. Sandbox test → canlı tahsilat

---

## Sorumluluk matrisi (özet)

| Alan | Repo-içi (belge/karar) | Müşteri-yüzeyi | Dış-only |
|------|------------------------|----------------|----------|
| Ürün / paket çerçevesi | ✅ Packaging | Landing/fiyat gerekli | — |
| Ödeme altyapısı | ✅ OD-011 ilke | Checkout sayfası | PSP, banka, merchant |
| Şirket evrakları | ✅ "mevcut" kaydı | — | Asıl belgeler |
| Hukuki metinler | ✅ çerçeve | Yayınlanmış sayfalar | Hukuk onayı |
| Faturalama | ✅ plan | Fiyat sayfası | e-Fatura, muhasebe |

---

## Feragat

Bu belge **hukuki, vergi veya mali tavsiye değildir**. KKTC banka prosedürleri, vergi uygulaması ve tüketici mevzuatı **yerel avukat ve mali müşavir** ile doğrulanmalıdır. `[KKTC]` ile işaretli maddeler genel SaaS kontrol listesinden türetilmiş olup, banka veya düzenleyici özel format isteyebilir.

Public `lumos-core` deposu açık kaynak **foundation** katmanıdır; production ödeme credential'ı, banka hesap numarası, merchant ID ve operasyonel URL **bu repoda tutulmaz** ([`public-repo-boundary.md`](../memory/public-repo-boundary.md)).

---

## Çapraz referanslar

| Belge | İlişki |
|-------|--------|
| [`commercial-product-packaging.md`](./commercial-product-packaging.md) | Birincil ticari çerçeve |
| [`commercial-domain-payments.md`](../memory/commercial-domain-payments.md) | Ödeme/domain canonical |
| [`payment-scope-decision.md`](../memory/payment-scope-decision.md) | OD-011 onaylı karar |
| [`public-repo-boundary.md`](../memory/public-repo-boundary.md) | Public / private sınır |
| [`open-decisions-needs-review.md`](../memory/open-decisions-needs-review.md) | OD-011 indeks |
| [`release-readiness-gap-analysis.md`](./release-readiness-gap-analysis.md) | Teknik release boşlukları (ayrı eksen) |

---

*Son güncelleme: 2026-06-21 — kod değişikliği yok; banka credential veya hesap bilgisi içermez.*
