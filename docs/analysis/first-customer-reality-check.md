# Lumos — İlk Müşteri Gerçeklik Kontrolü

| Alan | Değer |
|------|--------|
| **Belge ID** | `first-customer-reality-check` |
| **Durum** | `analiz` — satış öncesi müşteri/alıcı perspektifi; kod veya pazar araştırması değil |
| **Tarih** | 2026-06-21 |
| **Kapsam** | İlk ücretli veya resmi hizmet müşterisinin gerçek dünya beklentileri vs repo/doküman durumu |
| **Dil** | Türkçe (birincil) |
| **Persona odağı** | İlk müşteri — bireysel profesyonel / küçük işletme erken benimseyeni (Pro hedefi); teknik ekip değil |
| **Kaynaklar** | [`commercial-product-packaging.md`](./commercial-product-packaging.md), [`bank-readiness-checklist.md`](./bank-readiness-checklist.md), [`release-blockers.md`](./release-blockers.md) (yalnızca müşteri yüzü etkileri), [`README.md`](../../README.md), [`ROADMAP.md`](../../ROADMAP.md), [`PRODUCT_SUMMARY.md`](../PRODUCT_SUMMARY.md), [`LUMOS_V1_READINESS.md`](../LUMOS_V1_READINESS.md) |
| **Public sınır** | Bu analiz production credential, fiyat taahhüdü veya gelir iddiası içermez |

---

## Amaç

Bu belge, Lumos'un **ilk gerçek müşterisinin** (satın alan veya resmi hizmete geçen kişi/kurum) neye bakacağını teknik borç veya ADR dili olmadan sıralar. Amaç: erken erişim / pilot satış öncesi beklenti uyumu ve güven kaybı risklerini görmek.

**Bu bir pazar araştırması değildir.** Yalnızca 2026-06 itibarıyla repodaki ürün, panel ve ticari belgelerin dürüst özeti üzerine kuruludur.

---

## Persona: «İlk müşteri»

| Özellik | Tanım |
|---------|--------|
| **Kim** | Günlük işini toparlamak isteyen bireysel profesyonel veya 1–5 kişilik küçük işletme; erken benimseyen, «yeni nesil güvenli asistan» vaadine açık |
| **Teknik seviye** | GitHub klonlamak zorunda kalmak istemeyebilir; «hesap aç, kullan, gerekirse öde» bekler |
| **Ne arıyor** | Görev/sohbet/posta gibi günlük iş akışında yardım; riskli adımlarda kontrol; verilerinin nerede durduğuna dair netlik |
| **Ne aramıyor** | ADR kapanışı, köprü wiring, CI pipeline, vault mimarisi |
| **Paket hizası** | [`commercial-product-packaging.md`](./commercial-product-packaging.md) §2: **Pro** (resmi panel + barındırılan hizmet) — Starter (ücretsiz OSS) genelde aynı kişinin *önceki* adımı, ödeme anındaki hedef değil |

---

## Top 10 müşteri önceliği

Sıra, **satın alma ve günlük kullanım kararını** en çok etkileyenden başlar.

### 1. Bugün gerçekten işimi yapabilir miyim?

**Ne:** Panel açılınca sohbet, görev, dosya, posta vb. gerçekten çalışıyor mu; boş menü veya «yakında» duvarı var mı?

**Neden önemli:** Müşteri ürünü iş aracı olarak satın alır; iskelet menü değer hissi vermez.

**Mevcut durum:** **Kısmi.** Canlı panel (`welockai.com/panel`) yüklenir; üretimde çoğu kullanıcı **Sınırlı mod** görür — yerel görevler çalışır, sohbet ve köprü gerektiren işlemler beklemede kalır ([`LUMOS_V1_READINESS.md`](../LUMOS_V1_READINESS.md)). ROADMAP'te modüllerin çoğu «görünür temel iskelet»; posta, takvim, tam otomasyon **henüz vaat edilmemiş** ama menüde yerleri açık ([`ROADMAP.md`](../../ROADMAP.md)).

---

### 2. Nasıl kayıt olur, nasıl öderim?

**Ne:** Fiyat, deneme süresi, kartla ödeme, fatura — self-servis yol.

**Neden önemli:** «Nasıl satın alacağım?» sorusu cevapsız kalırsa keşif anında biter.

**Mevcut durum:** **Yok.** Resmi / ücretli hizmet «henüz yayınlanmadı» ([`README.md`](../../README.md) Release Tracks). Checkout, fiyat listesi, abonelik hesabı uygulanmadı ([`commercial-product-packaging.md`](./commercial-product-packaging.md) §5, [`bank-readiness-checklist.md`](./bank-readiness-checklist.md) §1, §5). OD-011 bilinçli erteleme — müşteri açısından «henüz satış yok».

---

### 3. Verim ve verilerim güvende mi — bunu anlayabiliyor muyum?

**Ne:** Gizlilik politikası, verinin nerede tutulduğu, kimlerin erişebileceği, silme/iptal sonrası ne olur.

**Neden önemli:** Asistan ürünleri kişisel ve iş verisi taşır; hukuki sayfa yoksa güven eksikliği satışı öldürür.

**Mevcut durum:** **Kısmi.** README ve ürün ilkeleri gizlilik/onay vurgular ([`README.md`](../../README.md) Principles). Yayınlanmış gizlilik politikası, kullanım koşulları, çerez metni **yok** ([`bank-readiness-checklist.md`](./bank-readiness-checklist.md) §4). Müşteri yüzünde «okudum, anladım» noktası eksik.

---

### 4. E-posta, takvim, Slack/GitHub gibi araçlarıma bağlanır mı?

**Ne:** Günlük işin geçtiği sistemlerle entegrasyon; tek panelden yönetim.

**Neden önemli:** KOBİ müşterisi «bir yer daha» değil, «mevcut iş yükünü hafifleten» aracı arar.

**Mevcut durum:** **Yok (planlanan).** Packaging tablosunda posta, takvim, çalışma araçları Pro için **planlanan**; foundation stub / menü iskeleti var, production connector yok ([`commercial-product-packaging.md`](./commercial-product-packaging.md) §4). v1 bilinçli olarak tam posta/takvim/ödeme otomasyonu dışında ([`LUMOS_V1_READINESS.md`](../LUMOS_V1_READINESS.md) §3).

---

### 5. Ücretsiz GitHub ile ücretli resmi hizmet arasındaki fark net mi?

**Ne:** Kaynak kodu klonlayınca ne kazandım; ödeme yapınca ne ekleniyor; marka ve resmi API hakkı var mı?

**Neden önemli:** Belirsizlik «zaten bedava varken neden para vereyim?» veya «aynı şeyi iki kez mi satıyorsunuz?» algısı yaratır.

**Mevcut durum:** **Kısmi.** README ve NOTICE ayrımı teknik olarak net: OSS ≠ resmi hizmet, marka, production API ([`README.md`](../../README.md), [`commercial-product-packaging.md`](./commercial-product-packaging.md) §1.3). Müşteri dilinde landing / fiyat / karşılaştırma sayfası **eksik** (bank checklist §3 — landing OD-048 `needs-review`).

---

### 6. Takılınca kime yazacağım, ne kadar sürede dönerler?

**Ne:** Destek e-postası, yardım merkezi, durum sayfası («şu an kesinti var mı?»).

**Neden önemli:** Erken üründe destek, özellikten sonra gelen ikinci satın alma nedeni; yoksa ilk sorunda churn.

**Mevcut durum:** **Kısmi / yok.** Dokümantasyon ve kontrollü GitHub Issues (Starter) var; Pro için planlanan `support@<TBD>` ve uygulama içi yardım **henüz yok** ([`commercial-product-packaging.md`](./commercial-product-packaging.md) §7). SLA placeholder — erken fazda «best effort» denmeli; müşteri yüzünde yazılı değil.

---

### 7. İptal ve iade nasıl işler?

**Ne:** Deneme bitmeden iptal, otomatik yenileme, cayma hakkı, para geri gelir mi.

**Neden önemli:** Ödeme öncesi son güven kapısı; belirsizlik kart girme kararını erteler.

**Mevcut durum:** **Kısmi (çerçeve only).** Packaging §6'da politika taslağı var; **yayınlanmış müşteri sayfası yok** ([`bank-readiness-checklist.md`](./bank-readiness-checklist.md) §4, §5). Self-servis iptal UI planlanan — uygulanmadı.

---

### 8. Riskli işlerde ben mi karar veriyorum — bunu panelde hissediyor muyum?

**Ne:** Silme, ödeme, dış gönderim gibi adımlarda durma, açıklama, onay; «sessizce yaptı» korkusu yok.

**Neden önemli:** Lumos'un ticari vaadi bu ([`PRODUCT_SUMMARY.md`](../PRODUCT_SUMMARY.md)); müşteri bunu satın alma gerekçesi yapar.

**Mevcut durum:** **Kısmi.** İlke ve panel metinleri onay vurgular (sohbet/görev alanlarında «kalıcı işlemler için onay»). Ticari işlem onay UX (OD-041) karar onaylı, uygulama bekliyor. Üretim panelinde tam otomasyon veya posta gönderimi olmadığı için müşteri «onay modelini» günlük işte sınamaz — daha çok **söz** düzeyinde.

---

### 9. Şirket gerçek mi, iletişim kurulabilir mi?

**Ne:** Hakkımızda, adres, iletişim formu, tutarlı marka (We Lock AI / Lumos).

**Neden önemli:** İlk müşteri «hayalet ürün» endişesi taşır; banka checklist'i de aynı boşlukları işaretler.

**Mevcut durum:** **Kısmi.** `welockai.com` ve `/panel` canlı ([`LUMOS_V1_READINESS.md`](../LUMOS_V1_READINESS.md)). Tam ticari vitrin, iletişim sayfası, hakkımızda **eksik** ([`bank-readiness-checklist.md`](./bank-readiness-checklist.md) §3). Şirket kaydı packaging'de mevcut denmiş; müşteri bunu repodan okumaz — **yayınlanmış kanıt** gerekir.

---

### 10. Fiyat öngörülebilir mi, sürpriz masraf var mı?

**Ne:** Aylık/yıllık net ücret, deneme sonrası ne olur, AI/kota aşımı, vergi dahil mi.

**Neden önemli:** Bütçesi olan KOBİ için belirsiz fiyat = «sonra konuşuruz» = genelde hayır.

**Mevcut durum:** **Yok.** Pro/Business fiyat TBD; fair use kotası TBD ([`commercial-product-packaging.md`](./commercial-product-packaging.md) §5). Fiyatlandırma sayfası eksik (bank checklist §3).

---

## Kurucu önceliği / müşteri umursamaz

Aşağıdakiler ürün kalitesi için önemli olabilir; **ilk müşteri satın alma ve günlük kullanım kararında** tipik olarak listeye girmez:

- **ADR-012 Security Codex CLOSED mi** — müşteri codex checkpoint görmez; panelde «güvenli his» yeterli veya yetersiz algılanır.
- **Köprü `consume_confirmation` wiring (RB-02)** — teknik tutarlılık; müşteri «sohbet neden çalışmıyor?» der, wiring adını bilmez.
- **Panel LockState env vekili vs runtime kilit (RB-03)** — aynı oturumda farklı kilit algısı müşteriye «tutarsız» olarak yansıyabilir ama kök nedeni aramaz.
- **P2 `SECURITY_NEVER_AUTO` engine kapsam genişliği (RB-04)** — iç politika; müşteri SECURITY_NEVER_AUTO terimini bilmez.
- **Python paketleme / `PYTHONPATH` (RB-06)** — self-host geliştirici derdi; Pro müşterisi barındırılan hizmet bekler.
- **Publish CI / PyPI workflow (RB-08)** — dağıtım operasyonu; müşteri «indir / kullan» ister.
- **Vault OD-001–005 implementation-pending** — müşteri «şifrelerim güvende» ister; vault katman mimarisini okumaz.
- **Trust Faz 4 merkezi trust motoru (RB-11)** — iç mimari; dışarıdan «güvenilir mi?» sorusu hukuki sayfa + davranışla cevaplanır.
- **Quantum Readiness Faz-2 / ADR taslak durumu** — müşteri menüde «Kuantum» görür; ADR-013 kapanışını takip etmez.
- **KKTC sanal POS başvuru paketi, PSP seçimi, e-fatura entegrasyonu** — müşteri için önemli olan sonuç: **ödeme çalışıyor mu**; banka evrak süreci görünmez.
- **`panel.astro` monolit boyutu (RB-23 / td-01)** — performans sorunu yoksa fark edilmez.
- **CONTRIBUTING.md eksikliği (RB-14)** — OSS katkıcısı içindir; Pro müşterisi değil.
- **Versiyon parçalanması lumos-core / ui / kando (RB-15)** — iç release disiplini.

---

## Eziklik kaynakları

«Eziklik» = müşterinin zihninde oluşan beklenti ile bugünkü gerçeklik arasındaki açık; karşılanmazsa hayal kırıklığı, utanç (kurucu/satış tarafında «abarttık» hissi) veya erken churn üretir. Yumuşatma **ürün metni / satış çerçevesi** ile; bu belgede kod önerisi yok.

| # | Beklenti (müşteri zihninde) | Neden oluşur | Risk ifadesi | Yumuşatma (copy / ürün yüzü) |
|---|----------------------------|--------------|--------------|------------------------------|
| E1 | «Resmi Lumos'u satın alıp hemen kullanırım» | README / welockai.com / packaging Pro tanımı; landing eksik | Ödeme yolu yokken satış vaadi | Her vitrinde **«Resmi hizmet henüz açık değil / erken erişim listesi»**; OSS vs Pro ayrımı tek cümle |
| E2 | «Sohbet eden akıllı asistanım olacak» | Genel AI pazarı, README «voice / assistant layer» dili | Prod panel **Sınırlı mod**; sohbet köprü olmadan kapalı | İlk ekranda **Sınırlı mod** ne demek, ne çalışır (görev yerel) — hero'da değil, onboarding'de |
| E3 | «Menüde posta/takvim var = bağlanır» | Panel modül iskeleti, ROADMAP «taşındı» dili | Modül açılınca içerik boş / beklemede | Modül girişinde **«Henüz aktif değil — erken erişim»** rozeti; menüyü gizleme veya gri etiket |
| E4 | «Kuantum = ileri güvenlik ürünüm var» | Modül adı, Quantum Readiness tarayıcı, güvenlik pazarlama | Gerçekte yerel hazırlık tarayıcısı; entropy/üretim iddiası yok ([`README.md`](../../README.md) Quantum notu) | Kuantum bölümünde **«Hazırlık taraması — iddia değil»**; mock/live ayrımı kullanıcı dilinde |
| E5 | «Güvenlik modülü = hesabım kilitli ve güvende» | Panel Güvenlik/Kimlik menüsü, «güvenli komuta paneli» ([`PRODUCT_SUMMARY.md`](../PRODUCT_SUMMARY.md)) | Vault prod değil stub; gizlilik sayfası yok | Güvenlik sayfasında **demo/erken erişim sınırı** + gizlilik taslağı linki (yayınlanınca) |
| E6 | «GitHub'daki ile ödediğim aynı şey» | Açık kaynak repo + aynı marka adı | «Neden para verdim?» / iade baskısı | Karşılaştırma tablosu: **Starter vs Pro** — barındırma, destek, entegrasyon, SLA |
| E7 | «14 gün deneyip sevmezsem kolay çıkarım» | Packaging §5.2 deneme önerisi (henüz operasyon yok) | Deneme/checkout olmadan vaat | Deneme metnini yalnızca **checkout canlı olunca** yayınla; öncesinde pilot sözleşmesi |
| E8 | «Cihazlarımı ve ev otomasyonumu yönetir» | README «devices, home automation, vehicles» vizyonu | v1 Faz A: görev/plan; cihaz otomasyonu yok | Vizyonu «yol haritası» footnote'a; **bugün ne yapar** listesi üstte |
| E9 | «Destek yazdım, 2 günde dönerler» | Packaging SLA placeholder (2 iş günü Pro) | Destek kanalı yokken SLA dili | Erken erişimde **«best effort — yanıt süresi garanti değil»** yazılı onboarding |
| E10 | «Banka kartı güvende, şirket ciddi» | Profesyonel site + ödeme beklentisi | Hukuki sayfalar, iletişim, fiyat eksik ([`bank-readiness-checklist.md`](./bank-readiness-checklist.md) B3–B5) | Ödeme açılmadan **«ön kayıt / pilot görüşmesi»**; sahte checkout yok |

---

## İlk 10 müşteri senaryosu (kısa anlatı)

**Keşif:** Küçük ajans sahibi LinkedIn veya `welockai.com` üzerinden Lumos'u görür. «Onaylı AI asistan», «güvenli panel» mesajı ilgisini çeker. Site tam vitrin olmadığı için doğrudan `/panel` dener veya GitHub README'ye düşer.

**Deneme:** Panel açılır; **Sınırlı mod** rozeti ve «yerel görevler kullanılabilir» metni görür. Bir görev ekler — `[Yerel]` ile kaydedilir; bu kısa süreli «bir şey işe yarıyor» hissi verir. Sohbet alanında mesaj göndermek ister; «köprü olmadan çalışmaz» uyarısı ile karşılaşır. Posta veya Entegrasyon menüsüne girer; içerik derinliği beklentiyi karşılamazsa «henüz bitmemiş» algısı oluşur.

**Ödeme:** «Pro'ya geç» veya fiyat arar — **checkout yok**. E-posta / iletişim formu net değilse WhatsApp/DM ile kurucuya yazar (ilk 10 müşteri tipik olarak bu yolu bulur). Kurucu «erken erişim pilotu» teklif ederse, müşteri **sözlü vaat vs panel gerçeği** arasında gerilim yaşar; yazılı sözleşme ve sınırlar kritik.

**Günlük kullanım:** Köprü kurulmamışsa ürün «yerel görev defteri + güzel kabuk» kalır. Köprü kurulursa sohbet açılır ama posta/takvim hâlâ yoksa «yarın yine aynı araçlara döndüm» durumu. Onay metinleri güven verir; fakat gerçek entegrasyon olmadan onay akışı **sınamaz**.

**Churn tetikleyicileri:** (1) «Sınırlı mod»un ne zaman biteceği belirsiz; (2) ödediği halde GitHub self-host ile aynı sınırlı deneyim; (3) destek yanıt gecikmesi; (4) menüde boş modül keşfi; (5) gizlilik/iade sayfası olmadan veri güveni zayıflaması; (6) «Kuantum/güvenlik» pazarlama dili ile içerik uyumsuzluğu; (7) entegrasyon vaadi (Pro packaging) vs gerçek — **«planlanan»ı «var» sandım»**.

---

## Ticari packaging ve banka checklist — müşteri güvenine etki

| Packaging / checklist boşluğu | Müşteri güvenine yansıması |
|--------------------------------|----------------------------|
| Checkout / fiyat / abonelik yok (Packaging §5; checklist B2, B4) | Satın alma mümkün değil; «ciddi ürün mü?» sorusu |
| Hukuki sayfalar yok (checklist §4; Packaging §9) | Veri paylaşma ve kart girme reddi |
| Landing + iletişim eksik (checklist B5; OD-048) | Keşif → deneme dönüşümü düşük |
| Destek e-postası TBD (Packaging §7) | İlk sorunda «yapayalnızım» hissi |
| OSS vs resmi hizmet ayrımı repoda net, vitrinde zayıf (Packaging §1.3) | Yanlış beklenti ve iade/chargeback riski (checklist §6.3 çerçevesi) |
| Erken erişim / beta etiketi önerisi (Packaging §3.3, §7.2) | **Henüz müşteri yüzünde sistematik uygulanmıyor** — eziklik E1, E7 ile örtüşür |

Release engellerinden **müşterinin görebileceği** etkiler (RB numarası yok): erken geliştirme etiketi ile README uyumu; demo-safe stub'ların prod iddiası taşımaması; çoğu modülün iskelet olması — «foundation build» olarak etiketlenmezse hayal kırıklığı ([`release-blockers.md`](./release-blockers.md) RB-09, RB-16, RB-17 yorumu).

---

## Özet tablo — durum dağılımı (Top 10)

| Durum | Öncelik numaraları |
|-------|-------------------|
| **Var / kabul edilebilir erken faz** | 8 (ilke düzeyinde; sınırlı günlük kanıt) |
| **Kısmi** | 1, 3, 5, 6, 7, 9 |
| **Yok** | 2, 4, 10 |

**En acil müşteri yüzü boşlukları (tek cümle):** ödeme ve fiyat yok; entegrasyon yok; hukuki/iletişim güven yüzeyi eksik.

---

## Feragat

- Bu belge **pazar araştırması, anket veya gelir projeksiyonu değildir**.
- **Sahte müşteri yorumu, kullanıcı sayısı veya gelir iddiası içermez**.
- Durum tespiti **2026-06-21** itibarıyla repo ve analiz belgelerine dayanır; canlı site davranışı için [`LUMOS_V1_READINESS.md`](../LUMOS_V1_READINESS.md) prod smoke referansı kullanılmıştır.
- Hukuki, vergi ve banka maddeleri için [`bank-readiness-checklist.md`](./bank-readiness-checklist.md) feragatı geçerlidir.
- Kod değişikliği, PR veya uygulama taahhüdü **yoktur**.

---

## Çapraz referanslar

| Belge | İlişki |
|-------|--------|
| [`commercial-product-packaging.md`](./commercial-product-packaging.md) | Pro persona, paket vaadi, destek/SLA çerçevesi |
| [`bank-readiness-checklist.md`](./bank-readiness-checklist.md) | Müşteri yüzü boşluk envanteri (checkout, hukuk, vitrin) |
| [`release-readiness-gap-analysis.md`](./release-readiness-gap-analysis.md) | Teknik release ekseni (ayrı perspektif) |
| [`PRODUCT_SUMMARY.md`](../PRODUCT_SUMMARY.md) | Faz A kapsamı, tek cümlelik vaat |
| [`LUMOS_V1_READINESS.md`](../LUMOS_V1_READINESS.md) | Canlı panel, Sınırlı mod, v1 sınırları |

---

*Son güncelleme: 2026-06-21 — yalnızca analiz metni; kod yok.*
