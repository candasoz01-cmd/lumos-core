# Lumos Ticari Ürün Paketleme Belgesi

| Alan | Değer |
|------|--------|
| **Durum** | `planlama` — banka incelemesi ve ilk müşteri dönüşümü için ticari katman tamamlayıcı belge |
| **Kapsam** | Ürün paketleri, özellik karşılaştırması, abonelik çerçevesi, iptal/iade, destek |
| **Dil** | Türkçe (birincil); teknik referanslar İngilizce kalabilir |
| **Üst sınır** | [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu belgeyi gevşetemez |
| **Public sınır** | [`docs/memory/public-repo-boundary.md`](../memory/public-repo-boundary.md), [`NOTICE`](../../NOTICE) — production secret, PSP credential, gerçek ödeme altyapısı public repoda yok |
| **Ödeme kararı** | OD-011 — [`payment-scope-decision.md`](../memory/payment-scope-decision.md) |
| **Son güncelleme** | 2026-06-21 |
| **Hukuk notu** | Bu belge ticari çerçeve ve planlama metnidir; nihai sözleşme, fiyat listesi ve iade metinleri için **hukuk onayı gerekir**. |

---

## Amaç

Bu belge, Lumos ürününün **banka incelemesi** ve **ilk müşteri dönüşümü** için eksik kalan ticari katmanı tamamlar. Ürün henüz erken geliştirme aşamasındadır; buradaki paketler, fiyatlar ve SLA değerleri **planlanan** çerçevedir. Mevcut durumda yalnızca açık kaynak geliştirme build'i ve demo-safe foundation kodu **mevcuttur**; resmi / ücretli hizmet henüz yayınlanmamıştır.

**Kaynak hizası:** [`README.md`](../../README.md) Release Tracks, [`docs/PRODUCT_SUMMARY.md`](../PRODUCT_SUMMARY.md), [`docs/memory/commercial-domain-payments.md`](../memory/commercial-domain-payments.md), [`docs/subscription-payment-control.md`](../subscription-payment-control.md).

---

## Paketleme modeli — mevcut repo ile ilişki

Repoda **Starter / Pro / Business** adlı fiyatlandırma katmanları **tanımlı değildir**. README'de iki iz vardır:

| Repo izi | Açıklama |
|----------|----------|
| **Open-source development build** | Kaynak kod; yerel inceleme, çalıştırma ve kontrollü deneme |
| **Official / professional release** | We Lock AI çatısında resmi Lumos; panel, servis bağlantıları, güvenli API, entegrasyonlar — **henüz yayınlanmadı** |

Bu belgedeki **Starter / Pro / Business** adlandırması, yukarıdaki iki izi banka ve müşteri diline taşıyan **paketleme önerisidir** (Business = kurumsal uzantı). OD-011 kapsamında fiyat, PSP ve abonelik motoru **henüz onaylı uygulama paketine alınmadı**; aşağıdaki tablolar planlama çerçevesidir.

---

## 1. Ne satıyoruz?

### 1.1 Ürün özü

**Lumos**, kullanıcının cihazları, dijital iş akışları ve bağlı sistemler üzerinde **anlaşılır, şeffaf ve onaylı** bir yapay zekâ kontrol ve asistan katmanıdır. Kullanıcı adına kalıcı, maliyetli veya geri dönüşü zor kararlar **sessizce alınmaz**; son onay kullanıcıdadır.

**Tek cümlelik vaat** ([`PRODUCT_SUMMARY.md`](../PRODUCT_SUMMARY.md)): *Lumos yardım eder ve yönlendirir; kalıcı veya riskli adım kullanıcı onayı olmadan atmaz.*

### 1.2 Satılan değer (ticari katman)

| Değer | Açıklama | Durum |
|-------|----------|--------|
| **Resmi Lumos paneli ve barındırılan hizmet** | We Lock AI markası altında güvenli panel, kimlik, onay akışları ve tanımlı kullanım sınırları | **Planlanan** |
| **Kontrollü entegrasyonlar** | Posta, takvim, kişiler, çalışma araçları (GitHub, Slack vb.) — granüler izin ve işlem bazlı onay | **Planlanan** (foundation stub **mevcut**; prod entegrasyon yok) |
| **Güvenlik ve vault geçidi** | Secret'ların Lumos yüzeyinde tutulmaması; amaçlı, onaylı erişim | **Planlanan** (ilke **onaylı**; uygulama kısmi) |
| **Abonelik ve kullanım yönetimi** | Tanımlı plan, fair use, faturalama döngüsü | **Planlanan** (OD-011 — uygulama bekliyor) |
| **Kurumsal destek ve SLA** | Business paketi kapsamında öncelikli destek | **Planlanan** |

### 1.3 Satılmayan / ayrı lisanslanan

Aşağıdakiler Apache-2.0 kapsamındaki **açık kaynak kod** ile karıştırılmamalıdır ([`NOTICE`](../../NOTICE)):

- Lumos ve We Lock AI **marka, logo ve görsel kimlik** kullanım hakkı
- Resmi barındırılan **production API** erişimi
- Resmi hizmetlerdeki **kullanıcı verisi**
- Özel / professional katman orchestration, cihaz kontrolü ve operasyonel backend

Kaynak kodu klonlayıp self-host etmek, resmi marka veya production API kullanım hakkı **vermez**.

### 1.4 Lumos'un bilinçli olarak yapmadığı (ticari vaat sınırı)

- Onaysız ödeme, satın alma, abonelik aktivasyonu veya domain işlemi başlatma ([`commercial-domain-payments.md`](../memory/commercial-domain-payments.md))
- Otomatik kalıcı silme veya sessiz dış yazma ([`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md))
- Kart / banka / PSP ayarlarını kullanıcı onayı olmadan değiştirme ([`subscription-payment-control.md`](../subscription-payment-control.md))

---

## 2. Kimler için?

| Segment | Profil | Birincil ihtiyaç | Önerilen paket |
|---------|--------|------------------|----------------|
| **Geliştirici / erken benimseyen** | Teknik kullanıcı, yerel kurulum ve kaynak incelemesi | Deneme, katkı, kendi ortamında çalıştırma | **Starter** (açık kaynak izi) |
| **Bireysel profesyonel / KOBİ** | Günlük iş akışı, görev, posta, entegrasyon; kontrollü otomasyon | Resmi panel, güvenli bağlantılar, düşük operasyon yükü | **Pro** |
| **Ekip / kurum** | Çok kullanıcı, uyumluluk, SLA, özel entegrasyon | Merkezi yönetim, öncelikli destek, kurumsal sözleşme | **Business** |
| **Banka / uyumluluk incelemesi** | Ürün sınırları, onay modeli, veri sahipliği | Şeffaf sınır: OSS foundation vs resmi hizmet ayrımı | Bu belge + [`payment-scope-decision.md`](../memory/payment-scope-decision.md) |

**Erken faz notu:** Ürün bugün **erken aktif geliştirmededir** ([`README.md`](../../README.md)); modüllerin çoğu görünür iskelet düzeyindedir. İlk müşteri dönüşümü **sınırlı erken erişim** veya **pilots** çerçevesinde planlanmalıdır; tam özellik vaadi bu belgede "planlanan" olarak işaretlenmiştir.

---

## 3. Paketler

### 3.1 Özet tablo

| Paket | Repo hizası | Hedef | Faturalama (planlanan) | Durum |
|-------|-------------|-------|------------------------|--------|
| **Starter** | Open-source development build | Yerel geliştirme, deneme, kontrollü self-host | **Ücretsiz** (kaynak lisansı Apache-2.0) | **Mevcut** (kaynak erişimi) |
| **Pro** | Official / professional release | Bireysel / küçük ekip; resmi panel ve barındırılan hizmet | Aylık / yıllık abonelik *(fiyat TBD — OD-011)* | **Planlanan** |
| **Business** | Professional + kurumsal uzantı | SLA, çok kullanıcı, uyumluluk, özel destek | Yıllık sözleşme + kullanıcı/koltuk *(TBD)* | **Planlanan** (paketleme önerisi) |

### 3.2 Starter — Açık Kaynak Geliştirme

**Ne içerir (mevcut):**

- `lumos-core` kaynak koduna erişim (Apache-2.0)
- Yerel UI build ve geliştirme (`ui/`, isteğe bağlı `backend/`, köprü script'leri)
- Demo-safe foundation: görev/plan iskeleti, panel yapısı, güvenlik ilkeleri dokümantasyonu
- Kontrollü dış katkı incelemesi (proje henüz tam OSS katkıya hazır değil)

**Ne içermez:**

- Resmi We Lock AI markası altında barındırılan hizmet
- Production API, resmi entegrasyon credential'ları
- Ticari destek SLA'si (topluluk / dokümantasyon düzeyi)

### 3.3 Pro — Resmi Lumos (Bireysel / Profesyonel)

**Planlanan kapsam** (README "Official / professional release" ile hizalı):

- Resmi Lumos paneli (birincil yüzey: `ui/` — [`primary-user-surface-decision.md`](../memory/primary-user-surface-decision.md))
- Kimlik, oturum ve tanımlı kullanım limitleri ile barındırılan erişim
- Onaylı servis bağlantıları (posta, takvim, çalışma araçları — kademeli açılış)
- Güvenli köprü / API erişimi (self-host token yerine resmi auth)
- Abonelik durumu ve plan limitleri (uygulama OD-011 sonrası)

**Erken erişim:** İlk müşteriler için sınırlı modül seti ve açık "beta / early access" etiketi önerilir.

### 3.4 Business — Kurumsal

**Paketleme önerisi** (repoda ayrı tier yok; banka / B2B ihtiyacı için):

- Pro kapsamının tamamı
- Çok kullanıcı / ekip yönetimi (planlanan)
- Öncelikli destek ve tanımlı SLA (Bölüm 7)
- Uyumluluk ve veri işleme ekleri (sözleşme eki — hukuk onayı)
- İsteğe bağlı: özel entegrasyon veya dedicated deployment *(private katman — public repoda detay yok)*

---

## 4. Özellik karşılaştırması

**Lejant:** ✅ Mevcut · 🔶 Kısmi / iskelet · 📋 Planlanan · ⛔ Paket dışı / ayrı sözleşme

| Özellik | Starter | Pro | Business |
|---------|:-------:|:---:|:--------:|
| Kaynak kod (Apache-2.0) | ✅ | ⛔ | ⛔ |
| Yerel panel / UI build | ✅ | 📋 (resmi barındırma) | 📋 |
| Resmi barındırılan panel | ⛔ | 📋 | 📋 |
| Görev ve plan (Faz A) | 🔶 | 📋 | 📋 |
| Sohbet modülü | 🔶 | 📋 | 📋 |
| Ses / medya modülleri | 🔶 | 📋 | 📋 |
| Posta entegrasyonu (onaylı) | ⛔ | 📋 | 📋 |
| Takvim / kişiler (OD-032) | ⛔ | 📋 | 📋 |
| Çalışma araçları connector'ları (OD-033) | ⛔ | 📋 | 📋 |
| Yetki profilleri (rapor / güvenli_yürüt / kısıtlı_otonom) | 🔶 | 📋 | 📋 |
| İşlem bazlı ticari onay (OD-041) | 📋 (ilke onaylı) | 📋 | 📋 |
| Vault / secret geçidi (OD-001–005) | 🔶 stub | 📋 | 📋 |
| Quantum Readiness tarayıcı (ADR-013) | 🔶 yerel | 📋 | 📋 |
| Abonelik / faturalama self-servis | ⛔ | 📋 | 📋 |
| Çok kullanıcı / ekip | ⛔ | ⛔ | 📋 |
| Öncelikli destek SLA | ⛔ | 📋 (standart) | 📋 (yükseltilmiş) |
| Özel deployment / private katman | ⛔ | ⛔ | ⛔ *(ayrı sözleşme)* |
| Marka / logo kullanım hakkı | ⛔ | ⛔ | ⛔ *(ayrı marka lisansı)* |

**Modül durumu kaynağı:** [`ROADMAP.md`](../../ROADMAP.md), [`README.md`](../../README.md) Modules.

**Abonelik izleme (Lumos içi):** Kullanıcının *kendi* harici aboneliklerini takip etme notu [`subscription-payment-control.md`](../subscription-payment-control.md) — otomatik ödeme **yok**; Pro/Business'ta "planlanan" ürün özelliği olarak konumlandırılabilir.

---

## 5. Abonelik koşulları

> **OD-011 durumu:** Ödeme ürün modeli, PSP seçimi, vergi/fatura akışı ve abonelik motoru **decision-approved / implementation-pending**. Aşağıdaki maddeler standart SaaS **planlama çerçevesidir**; checkout, webhook ve gerçek tahsilat **henüz uygulanmadı**. Nihai metinler PSP ve hukuk/mali paket onayı sonrası güncellenir — **hukuk onayı gerekir**.

### 5.1 Faturalama döngüsü (planlanan)

| Konu | Starter | Pro | Business |
|------|---------|-----|----------|
| Döngü | — | Aylık veya yıllık (yıllıkta indirim — oran TBD) | Yıllık sözleşme (tercihen) |
| Para birimi | — | TRY / EUR / USD *(PSP kararına bağlı — TBD)* | Sözleşme bazlı |
| Fatura | — | e-Fatura / e-arşiv *(vergi akışı TBD)* | Kurumsal fatura + PO |
| Ödeme yöntemi | — | Kart / banka *(PSP TBD)* | Havale + kart; vade *(TBD)* |

### 5.2 Deneme süresi (planlanan)

| Paket | Deneme | Not |
|-------|--------|-----|
| Starter | Süresiz (kaynak) | Ücret yok; resmi hizmet yok |
| Pro | **14 gün** *(öneri — TBD)* | Kredi kartı zorunluluğu ve otomatik yenileme metni hukuk onayına tabi |
| Business | **Pilot / POC** *(öneri)* | Teklif ve sözleşme ile; standart self-serve checkout dışı |

### 5.3 Plan limitleri ve fair use (planlanan)

Resmi hizmetlerde **tanımlı kullanım limitleri** uygulanır ([`README.md`](../../README.md): *authentication, user consent, and defined usage limits*).

| Limit türü | Örnek çerçeve (TBD) |
|------------|---------------------|
| API / köprü çağrısı | Aylık kota; aşımda yumuşak throttle veya plan yükseltme |
| Entegrasyon sayısı | Pro: sınırlı connector; Business: genişletilmiş |
| Depolama / görev hacmi | Makul kullanım; kötüye kullanımda bildirim |
| AI / model kullanımı | Harici model maliyeti kullanıcı onayı ve plan kotası ile |

**Fair use:** Otomasyon, scraping veya paylaşımlı hesap kötüye kullanımı hesap askıya alma veya plan sonlandırma gerekçesi olabilir — prosedür ve bildirim süresi sözleşmede tanımlanır *(hukuk onayı)*.

### 5.4 Yenileme ve yükseltme / düşürme

- **Otomatik yenileme:** Pro için planlanan varsayılan; iptal edilene kadar döngü sonunda ücretlendirme *(PSP entegrasyonu OD-011 sonrası)*.
- **Yükseltme:** Anında orantılı (pro-rata) ücretlendirme *(TBD)*.
- **Düşürme:** Mevcut dönem sonunda geçerli *(standart SaaS)*.
- **Onay ilkesi:** Lumos, kullanıcı **açık onayı olmadan** abonelik aktivasyonu veya ücretli işlem başlatmaz (OD-041 hibrit model: ticari işlemler işlem bazlı onay).

### 5.5 Bekleyen kararlar (OD-011 ve ilişkili)

| Konu | OD | Durum |
|------|-----|--------|
| PSP seçimi ve sözleşme modeli | OD-011 | needs-review |
| Abonelik ürün modeli | OD-011 | needs-review |
| Vergi / fatura / mevzuat | OD-011 | needs-review |
| Maliyet paylaşımı (QR / tek link) | OD-040 | needs-review |
| Ticari onay UX | OD-041 | decision-approved / implementation-pending |

---

## 6. İptal ve iade yaklaşımı

> Bu bölüm **politika çerçevesidir**, hukuki tavsiye değildir. Yürürlükteki tüketici mevzuatı, PSP kuralları ve şirket sözleşmeleri **hukuk onayı** ile nihai hale getirilmelidir.

### 6.1 İptal

| Paket | İptal yolu | Etki |
|-------|------------|------|
| Starter | Lisans sonlandırma (kullanım durdurma) | Yerel kopya kalır; resmi hizmet yok |
| Pro | Self-servis hesap ayarları veya destek talebi | Dönem sonuna kadar erişim; otomatik yenileme kapatılır |
| Business | Sözleşme fesih maddeleri | Bildirim süresi sözleşmede (ör. 30–90 gün — TBD) |

**Ilke:** İptal sonrası Lumos, onaysız yeni ücret veya yenileme başlatmaz.

### 6.2 İade (planlanan çerçeve)

| Senaryo | Önerilen yaklaşım | Not |
|---------|-------------------|-----|
| Yasal cayma hakkı süresi | Tam iade *(mevzuata uygun)* | Süre ve istisnalar hukuk tarafından netleştirilir |
| Pro — deneme içi iptal | Ücret alınmaz | Deneme bitmeden iptal |
| Pro — dönem içi erken iptal | **Orantılı iade yok** *(standart SaaS önerisi)* veya **kullanılmayan gün iadesi** *(alternatif — TBD)* | Banka/PSP chargeback politikası ile hizalanmalı |
| Hizmet kesintisi (Lumos kaynaklı) | Kredi veya orantılı iade | SLA ihlali Business'ta sözleşme eki |
| Yanlış / mükerrer tahsilat | Tam iade | PSP dispute süreci |

### 6.3 Chargeback ve anlaşmazlık

- Müşteriye önce **destek kanalı** (Bölüm 7) ile çözüm önerilir.
- Lumos adına otomatik chargeback veya banka itirazı **başlatılmaz**; kullanıcı kendi bankasıyla iletişime geçer, Lumos kanıt (fatura, kullanım kaydı) sağlar *(planlanan)*.

### 6.4 Veri ve hesap kapatma

- Hesap kapatma sonrası veri saklama / silme süreleri **gizlilik politikası** ve mevzuatla tanımlanır *(ayrı belge — TBD)*.
- Kalıcı silme yalnızca **açık kullanıcı komutu** ile; otomatik kalıcı silme yok ([`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md)).

---

## 7. Destek kanalları

> SLA süreleri ve iletişim adresleri **planlanan** placeholder değerlerdir; operasyonel kurulum sonrası güncellenir. Production URL, destek paneli credential'ı veya iç operasyon detayı **public repoda yer almaz**.

### 7.1 Kanallar

| Kanal | Starter | Pro | Business | Durum |
|-------|---------|-----|----------|--------|
| Dokümantasyon (`docs/`, README) | ✅ | ✅ | ✅ | **Mevcut** |
| GitHub Issues (kontrollü) | ✅ | 🔶 | 🔶 | **Mevcut** (katkı sınırlı) |
| E-posta destek | ⛔ | 📋 `support@<TBD_DOMAIN>` | 📋 + öncelik kuyruğu | **Planlanan** |
| Uygulama içi yardım / durum sayfası | ⛔ | 📋 | 📋 | **Planlanan** |
| Telefon / dedicated CSM | ⛔ | ⛔ | 📋 *(isteğe bağlı)* | **Planlanan** |

Birincil marka domain hedefi: **welockai.com** ([`commercial-domain-payments.md`](../memory/commercial-domain-payments.md)) — destek adresi ve durum sayfası bu çatı altında tanımlanacaktır.

### 7.2 SLA placeholder (planlanan)

| Metrik | Pro (standart) | Business |
|--------|----------------|----------|
| İlk yanıt | 2 iş günü *(TBD)* | 1 iş günü / 4 saat *(TBD)* |
| Kritik kesinti bildirimi | E-posta + durum sayfası | + telefon / dedicated kanal |
| Hedef uptime | %99,5 *(TBD)* | %99,9 *(sözleşme eki)* |
| Planlı bakım bildirimi | 48 saat önceden | 72 saat + müzakere |

**Erken faz:** Resmi SLA yürürlüğe girmeden önce "best effort" destek ve açık erken erişim sınırları müşteriye yazılı bildirilir.

### 7.3 Destek kapsamı sınırları

- Lumos, **üçüncü taraf** (PSP, domain registrar, OpenAI vb.) kesintilerinden sorumlu tutulmaz; yönlendirme ve kanıt toplama sağlanabilir.
- Güvenlik olaylarında vault / credential içeriği destek ticket'ına **yapıştırılmamalıdır** ([`public-repo-boundary.md`](../memory/public-repo-boundary.md)).
- Ödeme kartı verisi Lumos yüzeyinde tutulmaz; PCI kapsamı PSP tarafında kalacak şekilde tasarlanır *(OD-011 uygulama paketi)*.

---

## 8. Banka ve uyumluluk özeti

| Soru | Yanıt |
|------|--------|
| Şirket / vergi kaydı | **Mevcut** — OD-011 ertelemesinin nedeni şirket yokluğu değildir |
| Aktif ödeme altyapısı | **Yok** — PSP, merchant, checkout uygulanmadı |
| Gelir modeli | Planlanan SaaS abonelik (Pro / Business); Starter ücretsiz OSS |
| Kullanıcı onayı | Ticari işlemlerde işlem bazlı açık onay (OD-041) |
| Public vs private | Foundation OSS public; prod orchestration, credential, operasyon private |
| Açık karar | Fiyat, PSP, vergi/fatura, abonelik motoru → **OD-011 needs-review (uygulama)** |

---

## 9. Sonraki adımlar (ticari katman)

1. OD-011 uygulama paketi: PSP, fiyat listesi, vergi/fatura, abonelik motoru — **hukuk + mali onay**
2. Pro erken erişim sözleşmesi ve GAP-12 release checklist ile hizalama ([`release-roadmap.md`](./release-roadmap.md))
3. Destek e-postası, durum sayfası ve SLA — operasyonel kurulum *(private ops vault)*
4. Gizlilik politikası, KVKK/GDPR metinleri ve nihai iade şartları — **hukuk onayı**
5. Landing / vitrin metni (OD-048) — paket isimleri ve iddia seviyesi ile senkron

---

## Çapraz referanslar

| Belge | İlişki |
|-------|--------|
| [`payment-scope-decision.md`](../memory/payment-scope-decision.md) | OD-011 ödeme kapsam kararı |
| [`commercial-domain-payments.md`](../memory/commercial-domain-payments.md) | Ticari dış aksiyon sınırları |
| [`commercial-approval-model-decision.md`](../memory/commercial-approval-model-decision.md) | OD-041 hibrit onay |
| [`subscription-payment-control.md`](../subscription-payment-control.md) | Abonelik izleme modülü (plan) |
| [`open-decisions-needs-review.md`](../memory/open-decisions-needs-review.md) | Açık karar indeksi |
| [`public-repo-boundary.md`](../memory/public-repo-boundary.md) | Public / private sınır |
| [`release-readiness-gap-analysis.md`](./release-readiness-gap-analysis.md) | Release boşluk analizi |

---

*Bu belge yalnızca planlama ve banka/müşteri yüzeyi içindir; kod, ödeme entegrasyonu veya production credential içermez.*
