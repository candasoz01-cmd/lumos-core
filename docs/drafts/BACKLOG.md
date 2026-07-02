# WeLockAI · Lumos — karar günlüğü (taslak)

> **Çatı:** WeLockAI yayıncı ve kurumsal çatı; Lumos ürün ve referans içeriği bu çatı altında. Bu dosya proje tarihçesidir — sohbet değil, tarihli karar kaydı (bkz. `docs/lumos-book-outline.md` Belge §10).

## Sıralama kuralı

- Ters kronoloji: en yeni üstte
- Aynı gün: Lansman → Ürün → Mimari → Politika
- DONDURULDU / tag blokları günlük kararların üstünde ayrı tutulur

## Durum etiketleri

| Etiket | Anlam |
|--------|-------|
| 🟢 AKTİF | Geçerli, uygulanıyor |
| 🟡 TEST | Pilot / deneme |
| 🔴 İPTAL | Vazgeçildi |
| 🔒 DONDURULDU | Beklemede / değişmez çapa |
| 🚀 YAYINLANDI | Metne veya ürüne geçti |

## 🔒 DONDURULDU

**lumos-book-v0.1** (`0799c34`): `docs/lumos-book-outline.md` bu sürüme yeni fikir eklenmez. Yeni bölüm / vizyon / manifesto fikirleri yalnızca backlog'a veya yeni taslak dosyasına gider.

## Merged taslaklar

| Durum | Bölüm | Dosya | Not |
|-------|--------|-------|-----|
| Merged | §14 – Lumos Academy (Uzun Vadeli Vizyon) | [`section-14-lumos-academy-vision.md`](./section-14-lumos-academy-vision.md) (arşiv) | `lumos-book-outline.md` §14 — V1 dışı · taslak arşivde |

## İleride — karar kimliği (ADR-lite)

Karar sayısı arttıkça arama ve izlenebilirlik için kısa kimlik şeması (ADR-lite) pilot edilir.

**Önerilen alanlar:** ID (LUMOS-NNNN), Tarih, Durum, Karar, Gerekçe, Etkilenen dosyalar, Son güncelleme.

- Aynı karar evrildiğinde **aynı ID** korunur; geçmiş git diff'te kalır.
- Yalnızca **gerçekten yeni** kararlar yeni ID alır.

**Durum:** değerlendirme — pilot başladı, tam şema ileride.

Tam şema taslağı: [decision-engine-schema.md](./decision-engine-schema.md)

## Aktif kararlar

```
ID: LUMOS-0016
[2026-07-03] 🟢 AKTİF
🟢 Karar: Karar süreci ve denetim zinciri. Beş adım (sabit sıra): öneri → risk/gerekçe → uyarı → açık onay → kayıt. Lumos hiçbir zaman kullanıcı adına gizlice işlem yapmaz. Mahkeme ve denetim sorularına yanıt omurgası: kim karar verdi, kim onayladı, kim uyguladı; yetki; risk bildirimi; log. Omurga dokümanları (kazık eşşek — değiştirilmez çapa): ToS, gizlilik, açık onay, log, yetki matrisi, denetim kayıtları.
🎯 Gerekçe: LUMOS-0015 (sorumluluk dengesi ve açık onay), LUMOS-0008 (L0 karar zinciri, yetki matrisi) ve LUMOS-0014 (onay halkaları, dış veri) ile birlikte denetlenebilir karar akışını tamamlar; «gizli otomasyon» ve «kanıtsız onay» anti-pattern'lerini reddeder.
Legal review: Pending — genel ilkeler hukuki koruma yerine geçmez.
Evidence: Team governance articulation
🚫 Kapsam dışı: Runtime implementasyonu; mahkeme prosedürü veya bölgesel hukuk danışmanlığı bu kayıtla verilmez.
Decision level: L1 (governance)
İlişkili kararlar: LUMOS-0015, LUMOS-0008, LUMOS-0014
Etkilenen dosyalar: docs/drafts/BACKLOG.md
Son güncelleme: 2026-07-03
```

```
ID: LUMOS-0015
[2026-07-03] 🟢 AKTİF
🟢 Karar: Karar desteği ve sorumluluk dengesi. Çekirdek ilke: «Lumos önerir, açıklar ve riskleri bildirir; kullanıcının açık onayıyla gerçekleştirilen işlemlerin nihai sorumluluğu kullanıcıya aittir.» Tam ifade: Lumos karar desteği sağlar; nihai karar ve kullanıcı tarafından açık onayla gerçekleştirilen işlemlerin sorumluluğu kullanıcıya aittir. Denge yükümlülüğü: Lumos, riskli veya uygun olmadığını değerlendirdiği işlemlerde uyarı vermek, gerekçe sunmak ve güvenli alternatif önermekle yükümlüdür.
🎯 Gerekçe: Karar destek sistemi ile sorumluluk kaçışı veya «Lumos dedi» savunması arasında net denge; LUMOS-0005 (nihai karar kullanıcıda, hakem modeli), LUMOS-0008 (L0 — karar zinciri, «reddeder ama bırakmaz») ile uyumlu governance / legal-UX temeli; LUMOS-0013 ve LUMOS-0014 güvenlik ve onay halkalarıyla birlikte okunur.
Kapsam dışı anti-patterns (açıkça reddedilir):
- ❌ «Lumos sorumlu değildir» tek başına — kullanıcıdan kaçış algısı
- ❌ Kullanıcının «Lumos dedi diye yaptım» savunması
- ❌ Lumos'un «hiçbir şeyden sorumlu değilim» noktası
Evidence: Team principle articulation
🚫 Kapsam dışı: Sahte kurumsal onay veya endorsement; uydurma «Approved by» (LUMOS-0003 onay bütünlüğü).
Decision level: L1 (governance / legal-UX foundation)
İlişkili kararlar: LUMOS-0005 (hakem / belirsizlik), LUMOS-0008 (L0 yetki, karar zinciri), LUMOS-0013, LUMOS-0014
Etkilenen dosyalar: docs/drafts/BACKLOG.md
Son güncelleme: 2026-07-03
```

```
ID: LUMOS-0014
[2026-07-03] 🟢 AKTİF
🟢 Karar: Untrusted external data / dolaylı prompt injection — çekirdek ilke: Dışarıdan gelen her veri güvenilmez kabul edilir; aynı doğrulama kapısından geçer. Kaynak örnekleri (hepsi «dış veri»): PDF, mail, GitHub README, Slack, MCP tool output, OBD, robot sensör, kamera OCR. Mimari savunma: Karar zinciri mimariye dağılır; prompt injection savunması «daha iyi system prompt» değil — kimlik, yetki, risk, onay ayrı halkalar. Connector Layer kuralı: Tüm dış veri girişleri Connector Layer üzerinden; yetki matrisi ile birlikte.
🎯 Gerekçe: Dolaylı enjeksiyon ve rol karışıklığı perspektifi mevcut güvenlik mimarisini somutlaştırır; LUMOS-0013 (dış doğrulama) ile uyumlu; savunma LUMOS-0008 (L0 yetki matrisi), LUMOS-0009 (Trust Layer) ve LUMOS-0010 (Connector Layer) halkalarına dağılır.
Evidence: External reference — role confusion / prompt injection research + team design alignment
🚫 Kapsam dışı: Runtime implementasyonu; spesifik sanitizer algoritmaları. Sahte kurumsal onay veya endorsement (LUMOS-0003 onay bütünlüğü).
Decision level: L1 (güvenlik mimarisi)
İlişkili kararlar: LUMOS-0013, LUMOS-0010, LUMOS-0008, LUMOS-0009
Etkilenen dosyalar: docs/drafts/BACKLOG.md
Son güncelleme: 2026-07-03
```

```
ID: LUMOS-0013
[2026-07-02] 🟢 AKTİF
🟢 Karar: External validation — AI güvenlik mimarisi (security bulletin). Çekirdek ilke kaydedildi: «AI security comes from surrounding architecture, not the model alone» — model tek başına güvenlik sağlamaz; kimlik, yetki, connector ve anahtar katmanları birlikte güvenlik üretir. Dış güvenlik bülteni analizi Lumos karar duvarına işlendi; dört tema mevcut L0–L2 kararlarıyla eşlendi.
🎯 Gerekçe: Harici güvenlik perspektifi mevcut mimari kararları bağımsız doğrular; LUMOS-0008 (L0 yetki matrisi), LUMOS-0009 (Trust Layer / Lumos Key), LUMOS-0010 (Connector Layer) ve ürün çerçevesi (LUMOS-0011, LUMOS-0012) ile tutarlılık kanıtlanır.
Harita (dış tema → Lumos):
- Prompt injection / role confusion → Kimlik ve yetki prompt'tan ayrı; kullanıcı metni otoriteyi değiştiremez; rol değişimi yalnız güvenilir sistem katmanından (Trust Layer — LUMOS-0009; L0 yetki matrisi — LUMOS-0008).
- MCP güvenliği → Connector Layer + yetki matrisi (LUMOS-0010, LUMOS-0008); denetlenen tool çağrıları; araçlar eşit güvene sahip değildir.
- Multi-agent pentest → Çok modelli orkestrasyon güvenlik görevlerini destekler; hakem ve karar zinciri (LUMOS-0005, LUMOS-0008) ile uyumlu — otomatik saldırı veya yetki genişlemesi değil.
- Kriptografi / anahtar üretimi → Lumos Key; güvenlik yalnızca algoritmaya değil anahtar üretim ve kanıt cihazı modeline bağlı (LUMOS-0009).
Evidence: External reference — security bulletin analysis
🚫 Kapsam dışı: Bülten kaynağının resmî kurumsal onayı veya endorsement; sahte «Approved by» alanı; yeni runtime implementasyonu; model vendor onay adı uydurma (LUMOS-0003 onay bütünlüğü).
🔄 İleride değerlendirilecek: Bülten kaynağı URL/kanıt alanı doldurulması; tema bazlı ADR veya şema alanı eşlemesi (`decision-engine-schema.md`).
Decision level: L1 (dış doğrulama / güvenlik mimarisi)
İlişkili kararlar: LUMOS-0008 (L0 yetki matrisi), LUMOS-0009 (Trust Layer / Lumos Key), LUMOS-0010 (Connector Layer), LUMOS-0011 (MicroTools — onaylı yürütme), LUMOS-0012 (ürün aileleri — Trust)
Etkilenen dosyalar: docs/drafts/BACKLOG.md
Son güncelleme: 2026-07-02
```

```
ID: LUMOS-0012
[2026-07-02] 🟢 AKTİF
🟢 Karar: Lumos ürün aileleri haritası — tek sayfalık vizyon referansı (implementasyon değil). Aileler: Trust, Work, Mobility, Home, Health, Finance, Robotics, Accessibility, MicroTools. Harita yeni özellik ve backlog maddelerinin hangi aileye ait olduğunu gösterir; detay roadmap veya kod modülü taşımaz.
🎯 Gerekçe: Dağınık ürün kararları tek görünür çatı altında toplanmalı; Mobility (LUMOS-0007), Trust (LUMOS-0009) ve MicroTools (LUMOS-0011) aynı haritada konumlanır. Vizyon tutarlılığı için referans katmanı.
🚫 Kapsam dışı: Aile başına MVP önceliklendirme, sprint planı, kod paketleri veya modül implementasyonu. lumos-book-v0.1 outline'a doğrudan ekleme yok.
🔄 İleride değerlendirilecek: Aile başına MVP sıralaması; ADR eşlemesi; haritanın panel veya dokümantasyon yüzeyine taşınması (onay ile).
Decision level: L1 (ürün vizyonu / harita)
İlişkili kararlar: LUMOS-0007 (Mobility), LUMOS-0009 (Trust), LUMOS-0011 (MicroTools)
Etkilenen dosyalar: docs/drafts/BACKLOG.md
Son güncelleme: 2026-07-02
```

```
ID: LUMOS-0011
[2026-07-02] 🟢 AKTİF
🟢 Karar: MicroTools — Lumos tekrar eden işleri fark eder ve küçük, güvenli, kişisel araç önerir. İlke: «Kullanıcı araç aramaz; Lumos ihtiyacı fark eder.» Öneri yerel-önce ve onaylı yürütme ile hizalı; otomatik kurulum veya geniş yetki genişlemesi yok.
🎯 Gerekçe: Tekrarlayan kişisel iş yükünü azaltmak; kullanıcıyı marketplace veya araç arama yükünden kurtarmak. LUMOS-0006 yerel-önce ve LUMOS-0008 yetki matrisi (🟡 Öner / 🟠 Yürüt kurallı) ile uyumlu.
🚫 Kapsam dışı: Üçüncü parti plugin marketplace, otomatik kurulum, geniş sistem yetkisi isteyen araçlar, ticari app store modeli.
🔄 İleride değerlendirilecek: MicroTool şablon kataloğu; güven profili eşlemesi; tekrar tespiti için minimal pilot (onay kapılı).
Decision level: L1 (ürün davranışı)
İlişkili kararlar: LUMOS-0006 (yerel-önce), LUMOS-0008 (yetki matrisi)
Etkilenen dosyalar: docs/drafts/BACKLOG.md
Son güncelleme: 2026-07-02
```

```
ID: LUMOS-0010
[2026-07-02] 🟢 AKTİF
🟢 Karar: Connector Layer — dış sistem entegrasyonunda resmî API / resmî entegrasyon önceliklidir; resmî yol yoksa güvenli köprü (bridge) kullanılır. Ortak connector mantığı: araç, robot, banka, GitHub ve benzeri hedefler aynı güven ve onay modelini paylaşır; her hedef için ayrı güvenlik felsefesi üretilmez.
🎯 Gerekçe: Dağınık entegrasyon güven açığı ve bakım yükü yaratır; Trust Layer (LUMOS-0009) üzerinde tek connector sözleşmesi tutarlılık sağlar. [ADR-014](../decisions/ADR-014-personal-workspace-language.md) kişisel/organizasyonel ayrımı korunur — connector yalnızca onaylı, kanıtlanabilir veri akışı taşır.
🚫 Kapsam dışı: Spesifik üçüncü parti API implementasyonları, üretim bridge deploy, operasyonel backend altyapısı (public repo sınırı).
🔄 İleride değerlendirilecek: Connector sözleşmesi (ADR); güvenli köprü proxy deseni; hedef başına resmî vs köprü karar matrisi.
Decision level: L2 (mimari / entegrasyon)
İlişkili kararlar: LUMOS-0009 (Trust Layer), ADR-014 (PWL — katman ayrımı)
Etkilenen dosyalar: docs/drafts/BACKLOG.md
Son güncelleme: 2026-07-02
```

```
ID: LUMOS-0009
[2026-07-02] 🟢 AKTİF
🟢 Karar: Trust Layer — kimlik, yetki, onay ve audit omurgası. Lumos Key hazırlığı: kanıt cihazı (proof device) modeli; Lumos sır taşımaz, kanıt ve onay zincirini yönetir. Tüm yazma, dış etki ve kritik adımlar bu katmandan geçer.
🎯 Gerekçe: Connector (LUMOS-0010) ve MicroTools (LUMOS-0011) güvenli olmadan anlamlı değildir. LUMOS-0003 onay bütünlüğü ve LUMOS-0008 yetki matrisi (🔴 Kritik onay) bu katmanda somutlaşır. [ADR-014](../decisions/ADR-014-personal-workspace-language.md) organizasyonel kayıt ve audit ihtiyacı ile uyumlu.
🚫 Kapsam dışı: Üretim keystore, donanım sürücüsü, ticari Lumos Key ürün lansmanı, operasyonel kimlik servisi (public repo).
🔄 İleride değerlendirilecek: Audit kayıt formatı standardizasyonu; kanıt cihazı MVP tanımı; onay zinciri şema alanları (`decision-engine-schema.md`).
Decision level: L2 (mimari / güven)
İlişkili kararlar: LUMOS-0003 (onay bütünlüğü), LUMOS-0008 (L0 yetki matrisi), ADR-014
Etkilenen dosyalar: docs/drafts/BACKLOG.md, docs/drafts/decision-engine-schema.md
Son güncelleme: 2026-07-02
```

```
ID: LUMOS-0008
[2026-07-02] 🟢 AKTİF
🟢 Karar: Çekirdek ilkeler (L0 / anayasa). Lumos kullanıcıyı temsil eder; Lumos'un sınırı kullanıcının sınırıdır. Yetki matrisi: 🟢 Oku · 🟡 Öner · 🟠 Yürüt (kurallı) · 🔴 Kritik onay. Karar zinciri: Anla → Yorumla → Risk → Onay → Uygula. Risk / etik / yasal kapı vardır; reddeder ama bırakmaz — «Lumos engel koymaz, sınırları açıklar». Lumos yeni yetki istemez; mevcut kullanıcı onayı ve profil sınırları içinde kalır.
🎯 Gerekçe: L0 katmanı tüm alt kararların (L1–L4) değişmez çapasıdır; `decision-engine-schema.md` L0 tanımı ile hizalı. LUMOS-0005 hakem modeli — belirsizlik gizlenmez, nihai karar kullanıcıda — bu ilkeye bağlıdır. Risk kapısı LUMOS-0005 confidence/ikilem sunumunu tamamlar; reddetme açıklamalıdır.
🚫 Kapsam dışı: `docs/lumos-karar-sozlesmesi.md` metninin yeniden yazımı; runtime otomasyon; yeni yetki profili veya güvenlik gevşetmesi. L0 değişikliği onay + ADR zorunludur (mevcut sözleşme dokunulmaz).
🔄 İleride değerlendirilecek: Yetki matrisinin Decision Engine alan kataloğuna eklenmesi; karar zinciri adımlarının şema alanları; L0 uyum denetimi checklist'i.
Decision level: L0 (kurucu ilkeler / anayasa)
İlişkili kararlar: LUMOS-0005 (hakem — belirsizlik, nihai karar kullanıcıda), LUMOS-0003 (onay bütünlüğü)
Etkilenen dosyalar: docs/drafts/BACKLOG.md, docs/drafts/decision-engine-schema.md
Son güncelleme: 2026-07-02
```

```
ID: LUMOS-0007
[2026-07-02] 🟢 AKTİF
Karar: Lumos Mobility / Araç Sağlığı — Read-Only MVP. Lumos aracı kontrol etmez; veriyi okur, açıklar ve riski azaltmaya yardımcı olur. Kapsam yalnızca OBD-II salt okunur: ECU yazma, kritik sistem müdahalesi veya araç kontrolü yok. Akış: adaptör → okuyucu → normalize → yorum → rapor. Ürün katmanları: Auto (temel okuma ve açıklama), Auto Pro (derinleştirilmiş tanı ve geçmiş), Auto Expert (uzman yorumu ve karşılaştırma), Performance (ayrı / son / riskli — kontrol veya agresif müdahale iddiası taşımaz). Hakem modeliyle hizalı: teşhis ve açıklama; kontrol veya kesin garanti değil.
Gerekçe: Araç sağlığı alanında güven, salt okunur sınır ve dürüst belirsizlik sunumuyla başlar; kontrol iddiası güveni ve hukuki riski artırır. Hakem rolü (LUMOS-0005) teşhis sunar, aracı yönetmez.
Uygulama: Mobility MVP yalnızca OBD-II read pipeline; write/ECU kapısı kapalı; Performance katmanı ayrı risk profili ve onay hattı. Rapor çıktısı: normalize veri + yorum + güven düzeyi; nihai karar kullanıcıda.
İlişkili kararlar: LUMOS-0005 (hakem — teşhis, kontrol değil)
Decision level: L1 (ürün / mobility MVP)
Etkilenen dosyalar: docs/drafts/BACKLOG.md
Son güncelleme: 2026-07-02
```

```
ID: LUMOS-0006
[2026-06-30] 🟢 AKTİF
Karar: Panel UX — kullanıcıyı gereksiz bekletme. Hazır modüller (Sohbet, Görevler, Dosyalar) yerel iş mümkünken «tam bağlantı gerekli» ile bloklanmaz; yapılabilir kısım hemen yerelde çalıştırılır. Tam bağlantı yalnızca internet/dış kaynak gerçekten gerektiğinde istenir. Zihniyet: «Bağlantı olmadan yapabildiğimi yaparım; gerektiğinde izin isterim.» Yetenek kararını Lumos verir; kullanıcı her seferinde tahmin etmez. Panel genelinde tutarlı ton: «Yapabildiğim kısmı şimdi yapıyorum» — «yapamıyorum» değil. Bağlantılar: önizleme ve örnekler önceden gösterilir; kullanıcının hesabı varsa aktif, yoksa Lumos açma/kayıt yolunda yardımcı olur.
Gerekçe: Bekleme ve «önce bağlan» duvarı güveni düşürür; yerel iş varken tam bağlantı şartı kullanıcıyı gereksiz durdurur. Lumos yetenek sınırını netleştirir; kullanıcı modül modül tahmin etmez.
Uygulama: Panel sınırlı mod, modül durumları ve bağlantı yüzeyi — yerel-önce akış; tam bağlantı yalnızca gerekli adımda; bağlantı kartlarında önizleme/örnek ve hesap durumuna göre aktif veya yardımcı kayıt yolu.
Decision level: L1 (panel UX / ürün davranışı)
İlişkili kararlar: LUMOS-0002 (yerelleştirme omurgası)
Etkilenen dosyalar: ui/src/i18n/messages/panel/tr.ts, ui/src/i18n/messages/panel/en.ts, docs/drafts/BACKLOG.md
Son güncelleme: 2026-06-30
```

```
ID: LUMOS-0005
[2026-06-28] 🟢 AKTİF
Karar: Belirsizlik hata değildir; gizlenen belirsizlik hatadır. Hakem rolü susmak veya kesin konuşmak değil; ikilemi açık tutmaktır. Karar net değilse ikilem gizlenmez: seçenek A/B (artıları ve riskleri), Lumos değerlendirmesi, güven düzeyi (confidence) ve belirsizlik açıkça sunulur; nihai karar kullanıcıya aittir.
Gerekçe: Sahte kesinlik veya sessizlik güveni zedeler; dürüst karar hafızası belirsizliği görünür kılar, boş veya yanlış alan üretmez (bkz. LUMOS-0003).
Uygulama: Decision Engine ve hakem modeli — belirsiz kararlarda A/B şablonu; confidence ve uncertainty alanları doldurulur veya bilinçli boş bırakılır; son söz kullanıcıda.
İlişkili kararlar: LUMOS-0003
Decision level: L2 (hakem modeli, Decision Engine davranışı)
Etkilenen dosyalar: docs/drafts/decision-engine-schema.md, docs/drafts/BACKLOG.md
Son güncelleme: 2026-06-28
```

```
ID: LUMOS-0003
[2026-06-28] 🟢 AKTİF
Karar: Karar kayıtları zengin alan seti taşıyabilir (Proposed by, Reviewed by, Technical/Security/Accessibility/Privacy review, Risk level, Confidence, Evidence, Related decisions, Supersedes, Superseded by, Effective from, Last reviewed, Review due, Status, Decision level L0–L4); gün birinde çoğu alan boş kalabilir. Onay bütünlüğü: uydurma onaylayıcı yasak — «Approved by: OpenAI» veya «WeLockAI Board» gibi gerçek olmayan değerler yazılmaz. İzinli örnekler: Pending, Project Owner, Core Team (yalnızca gerçekten onaylandıysa). Çekirdek kural: **Boş alan olabilir, yanlış alan olmamalı.** İleride 30–40 anlamlı ve doğrulanabilir kaynaklı alan kabul edilir.
Gerekçe: Karar hafızası güvenilir olmalı; eksik bilgi boş bırakılır, sahte onay veya kurul adı üretilmez.
Uygulama: `docs/drafts/decision-engine-schema.md` alan kataloğu ve onay bütünlüğü bölümü; yeni kayıtlarda alanlar yalnızca kanıtlandığında doldurulur.
Etkilenen dosyalar: docs/drafts/decision-engine-schema.md, docs/drafts/BACKLOG.md
Son güncelleme: 2026-06-28
```

```
ID: LUMOS-0001
[2026-06-28] 🟢 AKTİF
Karar: Engelli modu lansmanda görünür; temel erişilebilirlik özellikleri ücretsiz açık belirtilir; küçük ve hedef odaklı değişiklik politikası korunur.
Gerekçe: Kullanıcının ilk gördüğü anda Lumos'un sosyal faydası anlaşılmalı.
Uygulama: Belge §12 lansman metinleri — v0.1 outline'a doğrudan ekleme yok; v0.2 veya ayrı commit.
Etkilenen dosyalar: docs/lumos-book-outline.md Belge §12 (v0.2+)
Son güncelleme: 2026-06-28
```

```
ID: LUMOS-0002
[2026-06-28] 🟢 AKTİF
Karar: Yerelleştirme (TR arayüz) erişilebilirlik omurgasının parçasıdır; sonradan eklenen süs değil. Panel / arayüz çok dilli sunum Belge §12 🌍 Dil engeli ile hizalı.
Gerekçe: Kullanıcı kendi dilinde rahat hissetmeli; anlaşılır ve erişilebilir olmak özellik kadar önemli.
Uygulama: Belge §12 dil engeli tablosu; lansman metinlerinde dil/erişilebilirlik birlikte düşünülür — v0.1 outline'a doğrudan ekleme yok.
Not: Kurucu kişisel tercih — «TR arayüz gelmeden aktif kullanmama» — ürün hedefi ile uyumlu; teknik zorunluluk değil.
Etkilenen dosyalar: docs/lumos-book-outline.md Belge §12 (v0.2+)
Son güncelleme: 2026-06-28
```

**Kural:** Backlog maddeleri web/lansman/yayımlandı indeksine Belge §11 onayı olmadan taşınmaz; v0.1 dondurulmuşken yeni fikirler outline'a yazılmaz.
