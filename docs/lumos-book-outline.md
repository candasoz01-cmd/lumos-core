# Lumos Referanslar 1 — Kurucu Kitap İskeleti

> **Yayın notu**
>
> - Bu belge taslak kurucu referanstır.
> - Henüz nihai kitap değildir.
> - **Tek kaynak:** GitHub'daki bu dosya yaşayan belgedir.
> - **Okuma ve kitap sürümleri** aynı kaynaktan üretilir; ayrı metin yönetilmez (bkz. Belge §10).
> - Web/kitap yayımlamadan önce **Belge §11 — Tamamlanmadan yayımlama** altı kontrolden geçer.

### Numaralandırma (iki sistem)

Bu belgede iki numara dizisi vardır; referans verirken karıştırılmamalıdır:

| Önek | Anlam | Kapsam |
|------|-------|--------|
| **Kitap §** | Kitabın bölüm iskeleti | Belge §3–§4 listesindeki 1–15 arası bölümler |
| **Belge §** | Bu referans dosyasının ana bölümleri | `## 1`–`## 14` arası başlıklar |

Örnek: **Kitap §7** = Panel dili; **Belge §7** = Kurucu hikâye notları. **Kitap §14** = Açık kaynak çekirdek; **Belge §14** = Lumos Academy vizyonu.

## 1. Kitabın adı

**Lumos — Dream it. Approve it. Done.**

Alt açıklama: **İzinli, şeffaf ve güvenilir yapay zekâ yardımı için bir ürün düşüncesi.**

*Nihai başlık kararıdır (2026-09-30, Belge §6 #10); önceki çalışma adı «Lumos: Kontrol Kullanıcıda» kapanmıştır. «Done», ürünün tamamen bitmiş olduğu iddiası değildir; Lumos'un iş akışı ilkesidir. Neyin bugün var olduğu, neyin planlı veya vizyon olduğu Belge §12–§14 durum etiketleriyle okunur.*

## 2. Ana fikir

Bu kitap, Lumos'u kontrolsüz otonom bir ajan olarak değil, kullanıcının kararını merkeze alan güvenilir bir yardımcı ve kontrol katmanı olarak anlatır.

Ana tez: Lumos kullanıcının niyetini anlamaya, dağınık işleri parçalamaya, riskleri görünür kılmaya ve uygulanabilir sonraki adımı önermeye çalışır; kalıcı, hassas, dış etkili veya geri dönüşü zor adımlarda son karar kullanıcıdadır.

Kitap; ürün felsefesi, karar sözleşmesi, panel dili, güvenlik/onay sınırları, entegrasyon yaklaşımı ve uzun vadeli araştırma alanlarını aynı hikâyede toplar. Amaç pazarlama metni değil; Lumos'un neden böyle davranması gerektiğini açıklayan kurucu bir taslak omurga oluşturmaktır.

### Önsöz için niyet beyanı

Bu kitap yalnızca ticari kazanç amacıyla değil, Lumos'un gelişimini ve toplumsal faydayı desteklemek amacıyla hazırlanmıştır. Lumos vizyonuyla uyumlu bir dernek veya vakıf yapısı oluştuğunda, aşağıdaki gelirlerin toplumsal fayda projelerine yönlendirilmesi hedeflenir:

- Kitap gelirleri.
- Eğitim gelirleri.
- Lisans gelirleri.
- Patent veya fikri mülkiyet gelirleri (oluşursa).
- Quantum güvenliği ve benzeri ileri araştırmalardan doğabilecek meşru ticari gelirler (oluşursa).

#### Değerin Geri Dönüş İlkesi

Lumos'tan doğan değerin yalnızca teknoloji üretmesi değil, insanlara geri dönmesi hedeflenir. Ticari sürdürülebilirlik sağlandıktan sonra oluşan fazla değerin önemli bir bölümünün eğitim, erişilebilirlik, bilimsel araştırma ve toplumsal fayda projelerini desteklemesi amaçlanır.

Bu ifade bugün hukuki bir taahhüt değil, niyet beyanıdır. Gelecekte kurulacak dernek, vakıf veya benzeri yapı tarafından resmîleştirilebilir. Kurucu ekip, Lumos'un sürdürülebilirliğini sağlayacak makul işletme giderlerini ayırabilir; kalan kaynakların büyük bölümünün toplumsal faydaya yönlendirilmesi hedeflenir.

### Kitabın üç katmanı

1. **Hikâye:** Lumos fikrinin nasıl doğduğu, hangi problemleri gördüğü ve neden klasik bir yapay zekâ kitabı olmayacağı.
2. **İlkeler:** Karar sözleşmesi, güvenlik, karakter, kullanıcı kontrolü, gizlilik ve onay mantığı.
3. **Mimari:** Çekirdek, dal ajanlar, güvenlik katmanları, entegrasyon sınırları ve sistemin neden bu şekilde tasarlandığı.

## 3. Bölüm listesi

*Biçim: kısa bir kurucu mektubu girişi açar; arkasından aşağıdaki bölümlü kitap gelir (Belge §6).*

### Katman 1 — Hikâye

1. Neden Lumos?
2. Lumos fikri hangi problemden doğdu?
3. Kullanıcı kararı neden merkezde?

### Katman 2 — İlkeler

4. Lumos'un karakteri
5. Tek yüz: kullanıcı Lumos ile konuşur
6. Niyeti parçalamak ve işi başlatmak
7. Panel dili ve güven veren arayüz
8. Onay, yetki ve karar sözleşmesi
9. Gizlilik, audit ve veri sınırları

### Katman 3 — Mimari

10. Çekirdek, dal ajanlar ve sözleşmeyle korunan kök
11. Entegrasyonlar: araçların verisine saygı
12. Yerel çalışma, cihazlar ve köprü mantığı
13. Quantum Readiness ve araştırma disiplini
14. Açık kaynak çekirdek ve ticari omurga
15. Yol haritası: kontrollü gelişen Lumos

## 4. Her bölüm için kısa açıklama

### 1. Neden Lumos?

Lumos'un çıkış problemini anlatır: yapay zekânın kullanıcı yerine karar veren görünmez bir otoriteye dönüşmesi yerine, kullanıcıya durum, risk ve seçenek gösteren bir yardımcı olması. Bu bölüm ürün vaadini sade bir dille kurar.

**Taslak açılış (Kitap metni — ana kaynak Belge §7):**

> Yalnızlık bana düşünmeyi öğretti. Şüphe ise korku değil, doğrulamayı öğretti. Lumos bu ikisinin arasındaki dengeyi arayan bir fikirdi.

### 2. Lumos fikri hangi problemden doğdu?

Lumos'un sadece teknik bir araç olarak değil, kullanıcının yorgunluğunu, dağınık iş akışını, güvenlik kaygısını ve kontrol ihtiyacını aynı anda ele alan bir fikir olarak nasıl doğduğunu anlatır. Bu bölüm kitabın hikâye katmanını kurar.

### 3. Kullanıcı kararı neden merkezde?

Kalıcı, hassas, maliyetli veya başkalarını etkileyen işlemlerde son karar merciinin kullanıcı olduğunu açıklar. "Yardım" ile "yerine karar verme" arasındaki fark kitabın temel ekseni olarak yerleşir.

### 4. Lumos'un karakteri

Lumos'un güven veren ama manipüle etmeyen, emin olmadığında kesin konuşmayan, önce gözlemleyen sonra önerede bulunan karakterini tanımlar. Bu bölüm karakterin uzun promptlarla değil; sözleşme, kod ve ürün diliyle korunduğunu anlatır. Uzun vadeli ürün ifadesi (Companion) için bkz. Belge §7 «Companion: karakter ve ürün», Belge §13.

### 5. Tek yüz: kullanıcı Lumos ile konuşur

Son kullanıcı deneyiminde görünen dış yüzün Lumos olduğunu anlatır. Arka plandaki teknik veya operasyonel katmanlar kullanıcıya marka karmaşası olarak taşınmaz; sonuç, soru ve onay Lumos diliyle gelir.

### 6. Niyeti parçalamak ve işi başlatmak

Uzun, dağınık veya komut gibi yazılmamış isteklerin nasıl uygulanabilir parçalara ayrılacağını açıklar. Net ve düşük riskli istekte Lumos'un pasif kalmamasını; riskli veya belirsiz durumda ise durup net soru sormasını işler.

### 7. Panel dili ve güven veren arayüz

Panelin bir reklam veya tüketim yüzeyi değil, güvenli çalışma ve kontrol alanı olduğunu anlatır. Dil ilkesi: kısa özet, ne anladım, ne yapacağız, gerekirse tek kritik soru.

### 8. Onay, yetki ve karar sözleşmesi

Karar katmanlarını merkez bölüm olarak açıklar: sadece cevap ver, analiz et, öner ama bekle, açık onayla uygula, asla dokunma. Kalıcı silme, dış yazma, kritik sistem ayarı ve geri dönüşsüz işlemlerin neden otomatik yapılamayacağını anlatır.

### 9. Gizlilik, audit ve veri sınırları

Kullanıcı verisinin ürün malzemesi olmadığını ve satılmadığını (veri satmama bir ilkedir) ve gereksiz arşiv mantığından uzak durulması gerektiğini açıklar. Reklamsızlık ise mutlak bir ilke değil, mevcut tercih/stratejidir; ileride ekip tarafından etik sınırlar içinde yeniden değerlendirilebilir, karar değişmese bile bilinçli biçimde yeniden teyit edilir. Audit'in amacı kullanıcıyı izlemek değil, sistemin söz verdiği sınırlarda durduğunu kanıtlamaktır.

### 10. Çekirdek, dal ajanlar ve sözleşmeyle korunan kök

Lumos'un yalnızca konuşan bir arayüz değil, sözleşmeyle korunan bir çekirdek etrafında büyüyen sistem olarak neden tasarlandığını anlatır. Dal ajanların kök olmadığını; kökün karakter, karar sözleşmesi, güvenlik ve audit ilkeleriyle korunduğunu açıklar.

Sık tekrarlanan ve bağlama göre uzmanlık isteyen işlerde **tek odaklı dal ajan** modeli kullanılır. Örneğin marka bağlam ajanı; yüzeyin anlamına göre logo biçimi, renk, boyut ve boşluk önerisi üretir. Bu ajan:

- Yalnızca kullanıcıdan veya Lumos Orkestratör'den görev alır; başka bir ajandan emir kabul etmez.
- Ana marka geometrisini veya karar sözleşmesini değiştiremez; yalnızca onaylı kurallardan varyant önerir.
- Dosya yayını, dış paylaşım veya kalıcı değişiklik yapmaz; sonucu tek merkez kontrol noktasına iletir.
- Karar, risk, uygulama durumu ve gerekçeyi ana merkezdeki bildirim duvarına standart olay olarak bırakır.
- Bildirim duvarı icra makamı değildir; kullanıcıya ve Orkestratör'e görünürlük sağlar.

Akış: **Kullanıcı / Lumos Orkestratör -> tek odaklı ajan -> merkez kontrol noktası -> bildirim duvarı -> onaylı uygulama**. Bu desen, `Karşılıklı denetim, sıfır kontrol` ilkesini korur; ajanlar birbirini yönetmez.

### 11. Entegrasyonlar: araçların verisine saygı

GitHub, Slack, Google, Gmail ve Calendar'daki verinin kaynak sistemde kaldığını ve Lumos'un bu veriyi sahiplenmediğini anlatır. Kaynak sistem ve veri hakları korunur. Lumos yalnızca kullanıcı izni ve politika kapsamında gerekli özeti, metadata'yi veya eylemi işler; tam kopya, sessiz senkron veya onaysız dış yazma varsayılan değildir.

### 12. Yerel çalışma, cihazlar ve köprü mantığı

Lumos'un yerel çalışma, panel, CLI, cihaz ve köprü bağlamlarını nasıl düşündüğünü anlatır. Offline modda dış ağ yoktur; online modda kimlik, kilit, consent ve onay zinciri devrededir.

### 13. Quantum Readiness ve araştırma disiplini

Kuantum alanını abartılı "quantum powered" iddialarından ayırır. Lumos Quantum Readiness'in yerel, salt okunur, kanıtlı bir hazırlık tarayıcısı olarak konumlanmasını; araştırma ile ürün iddiası arasındaki sınırı anlatır. «Lumos Quantum» (Labs) bu bölümün konusu değildir; gelecek araştırma/vizyon alanı olarak ayrı durur (Belge §13, ⚪).

### 14. Açık kaynak çekirdek ve ticari omurga

Public Lumos çekirdeği ile ticari güven/politika katmanının ayrımını anlatır. Açık kaynak repo demo-safe foundation taşır; production credential, faturalama, kurumsal orkestrasyon ve operasyonel backend ayrıdır.

### 15. Yol haritası: kontrollü gelişen Lumos

Lumos'un tek hamlede her şeyi yapan bir sistem değil, kontrollü gelişen bir panel ve yardımcı olduğunu anlatır. Faz A görev/plan omurgasından başlayarak entegrasyon, cihaz, mobil onay, quantum readiness ve daha ileri araştırma alanlarına nasıl genişleyebileceğini toparlar.

## 5. Toplanacak kaynak notları

- `README.md`: Lumos'un genel vaadi, prensipleri, mevcut durum ve modül listesi.
- `docs/PRODUCT_SUMMARY.md`: erken faz, ne yapar/ne yapmaz, kontrollü gelişen panel fikri.
- `docs/lumos-urun-vizyon-ve-arastirma-cercevesi.md`: ürün karakteri, sessiz araştırma sınırı, yüzeye çıkarma kriterleri.
- `docs/lumos-kullanici-akisi.md`: tek yüz ilkesi, normal sohbet, panodaki metni iletme ve görev detayından iletme akışları.
- `docs/lumos-persona-layers.md`: kullanıcıya görünmeyen iç katmanlar ve tek dış geçit prensibi.
- `docs/lumos-karar-sozlesmesi.md`: karar katmanları, dokunulmaz çekirdek alanlar, açık onay ve asla otomatik yapılmayan işler.
- `docs/lumos-karar-motoru.md`: basit/orta/ürünsel iş sınıflandırması, risk ve hazır çözüm akışı.
- `docs/lumos-uzun-istek-isleme.md`: uzun isteği ayrıştırma, parçalama, kritik soru stratejisi.
- `docs/lumos-konusmadan-gorev-cikarma.md`: açık komut yokken iş sinyali yakalama ve güvenli başlatma.
- `docs/lumos-panel-dili-rehberi.md`: panel dili, cevap sırası, sade Türkçe ve güven veren ton.
- `docs/security-architecture.md`: onay, trash, offline, secret ve public repo güvenlik sınırları.
- `docs/analysis/lumos-privacy-manifesto-draft.md`: veri satışı yok (ilke), reklam yok (kaynak taslak; kitapta mevcut tercih/strateji olarak ele alınır, Kitap §9), audit/gizlilik dengesi.
- `docs/integrations-overview.md`: entegrasyon yüzeyleri, read/write/delete izin modeli, OSS/private ayrımı.
- `docs/analysis/welockai-charter-draft.md`: Lumos ile ticari omurga arasındaki rol ayrımı.
- `docs/analysis/welockai-trust-model-draft.md`: rol, yetki, onay zinciri ve trust boundary notları.
- `docs/analysis/lumos-approved-naming-registry.md`: onaylı isimler, roller, yüzeyler ve demo-safe adlandırma.
- `docs/ARCHITECTURE.md` ve `docs/ARCHITECTURE_MAP.md`: teknik omurga, karar/pipeline, workspace ve panel kontratları.
- `docs/decisions/ADR-013-lumos-quantum-security-readiness.md`: Quantum Readiness tanımı, kapsam dışı iddialar ve rapor alanları.
- `docs/analysis/lumos-quantum-first-companion.md`: Qiskit/Aer'in araştırma önceliği ve otomatik bağlantı olmadığı sınırı.

Kaynak notları toplanırken dikkat: kitabın kullanıcıya dönük ana metninde Lumos dış yüz olarak kalmalı; iç teknik katman adları gerekiyorsa kaynak notu veya mimari dipnot seviyesinde tutulmalı.

## 6. Karara bağlanan sorular

> **Kapanış notu (2026-09-30):** Bu bölümdeki sorular kurucu kararlarıyla kapatıldı; karar her sorunun yanında yazılıdır. Nihai başlık sonradan karara bağlandı (#10, güncel karar); bilerek açık kalan nokta yayın tarihidir (TBD, koşullu). Dondurma sahibi onayı: kararlar `lumos-book-v0.1` iskeletine yalnız açık bırakılmış karar noktalarının kapatılması olarak işlendi; yeni fikir, yeni kapsam veya tarih eklenmedi.

- Kitap bir public manifesto mu, iç ürün kitabı mi, yoksa geliştirici rehberiyle karışık bir kurucu metin mi olacak? → **Karar (kurucu, 2026-09-30):** Karışık kurucu metin. Manifesto ruhunu taşır ama yalnız manifesto değildir; ürünün nedenini, ilkelerini ve nasıl çalıştığını anlatır.
- Birincil hedef kitle kim: son kullanıcı, geliştirici, yatırımcı/partner, kurumsal müşteri, yoksa ekip içi karar okuyucusu mu? → **Karar:** Tek birincil kitle seçilmez. Kitap erken kullanıcı, geliştirici/teknik okuyucu ve kurumsal/partner okuyucu tarafından anlaşılabilir olur; yatırımcıya özel bir kitaba dönüşmez. Öncelik sırası metne yazılmaz.
- Dil yalnızca Türkçe mi olacak, yoksa Türkçe ana metin + İngilizce özet/terim sözlüğü mu hazırlanacak? → **Karar:** Türkçe tek kaynak metindir; diğer diller sabit bir Türkçe sürümden türetilir. İlk uluslararası türev İngilizce olabilir. Mimari: LUMOS-0020 (çok dilli yayın mimarisi), candasoz01-cmd/lumos-core#895 ile `main`'e alındı (merge commit `ca258cfc`, 2026-10-01).
- WeLockAI ticari omurgası kitapta ne kadar görünür olacak; hangi bölümlerde yalnızca arka plan sınırı olarak kalacak? → **Referans yayınında çözüldü (Belge §10):** WeLockAI yayıncı/ön planda; kitap içinde Lumos ürün sesi ağırlıkta, WeLockAI ticari omurga **Kitap §14** ve dipnotlarda. **Kurucu (2026-09-30): kapalı; yeniden açılmaz, Belge §10 kararı geçerlidir.**
- Teknik detay derinliği ne olacak: kod/pipeline anlatımı mi, yoksa ürün ilkeleri ve örnek senaryolar mi ağırlıkta olacak? → **Karar:** İlke ağırlıklı ana metin; gerektiğinde teknik dipnot veya ayrı teknik ek. Gövde pipeline ve kodla yüklenmez; teknik iddialar dayanaksız bırakılmaz.
- Quantum Readiness bölümü araştırma disiplini olarak mi kalacak, yoksa ayrı bir gelecek vizyonu bölümü mu olacak? → **Karar:** İkisi ayrı kalır. Kitap §13 araştırma disiplini/readiness olarak kalır; Belge §13'teki «Lumos Quantum» (Labs) açıkça gelecek araştırma/vizyon alanı olarak ayrı durur. Mevcut olmayan yetenek iddiası (ör. «quantum powered») yapılmaz.
- Gizlilik ve audit iddiaları için hukuki/uyum kontrolü gerekecek mi? → **Karar:** İddia içeren bölümler için gerekli. Kurucu kararlar bu kontrolle yeniden açılmaz. Hukuk tarafı, gizlilik, audit, veri işleme ve uyum kararlarının uygulama biçimini ve kamusal ifade ile uyum gerekliliklerini inceler. Kitabın tamamı için hukuki redaksiyon gerekmez (bkz. Belge §11, madde 5).
- Bölümlerde gerçek kullanıcı senaryoları, panel ekranları veya vaka çalışmaları kullanılacak mi? → **Karar:** Karışık. Vizyon senaryoları açıkça «vizyon» diye etiketlenir; gerçek ürün ekranı veya gerçek davranış gösteriliyorsa kanıtlanabilir mevcut sürümden gelir. Vizyon ile çalışan ürün karıştırılmaz (bkz. Belge §11, madde 6).
- Kitap kısa bir "founder letter + ilkeler" metni mi, yoksa uzun soluklu bölümlü kitap mi olacak? → **Karar:** İkisi de. Kısa bir kurucu mektubu giriş olur; arkasından bölümlü kitap gelir.
- Son başlık "Lumos: Kontrol Kullanıcıda" olarak mi kalacak, yoksa daha sıcak/insani bir çalışma adına mi evrilecek? → **Karar (güncel, 2026-09-30):** Nihai başlık «Lumos — Dream it. Approve it. Done.» olur; çalışma adı kapanmıştır. «Done» ürünün tamamlandığı iddiası değil, iş akışı ilkesidir (bkz. Belge §1). Önceki karar (çalışma adı kalır, başlık yayın öncesi dondurulur) bu kararla yürürlükten kalkar.
- **Lansman / yayın tarihi:** Belge §10 «Lansman türleri». Referans web/PDF için tarih **TBD** kalır; Life ve ticari lansmanların kendi tarihleri de yoktur. Dış kamu AI haberleri Lumos takvimi değildir. → **Karar:** Tarih konmaz. §6 kararları, nihai başlık, §11 sadeleştirmesi ve çok dilli mimari (#895, `main`'e indi) kapanmıştır. Tarih için hâlâ açık olanlar: Belge §11 kontrollerinin yayın sürümünde geçmesi, hukuki gözden geçirme ve yayın sürümünün hazır olması. Takvim için içerik sıkıştırılmaz.

## 7. Kurucu hikâye notları

- Lumos fikrinin ilk çıkış nedeni
- Yalnızlık, kontrol, güven ve yardım ihtiyacı
- Kullanıcı kararının neden merkezde olduğu
- Neden “asistan” değil “yoldaş/koruyucu katman” gibi düşünüldüğü
- İlkelere bağlılık meselesi
- Çok ajanlı yapıya geçişin nasıl fark edilmeden olgunlaştığı
- Kitap gelirlerinin dernek/vakıf niyetiyle ilişkilendirilmesi
- Bu kitabın teknik reklam değil kurucu metin olması

### Köken cümlesi (taslak paragraf)

Kitapta — özellikle önsöz veya «Neden Lumos?» bölümünde — aşağıdaki cümle omurga olarak kullanılabilir:

> Yalnızlık bana düşünmeyi öğretti. Şüphe ise korku değil, doğrulamayı öğretti. Lumos bu ikisinin arasındaki dengeyi arayan bir fikirdi.

Bu cümle, kitabın hikaye katmanı ile ilke katmanını tek paragrafta birleştirir: kişisel deneyimden ürün felsefesine geçiş.

### Kişisel deneyimden ürün ilkesine (not)

Kurucu hikâyede psikolojik teşhis dili kullanılmaz. Bunun yerine, deneyimin Lumos ilkelerine nasıl dönüştüğü anlatılır:

| Deneyim | Lumos'ta karşılığı |
|---------|-------------------|
| Yalnızlık → düşünmeye zorlanma | Derinlemesine analiz, acele etmeme, «önce anla» |
| Şüphecilik → güvenlik katmanları | Karar sözleşmesi, onay zinciri, `SECURITY_NEVER_AUTO` |
| Kontrol ihtiyacı | «Son karar kullanıcıda» ilkesi |
| Güven arayışı | Karar katmanları, profil matrisi, audit |
| Dağınık işleri toplama isteği | Panel, görev mantığı, niyeti parçalama |

**Etiket notu:** Bu tablo «paranoya» diye okunmamalı. Daha doğru çerçeve: **yüksek risk farkındalığı** ve **kanıt önceliği**. Gerçek paranoyada kanıt olmadan kesin yargı sık görülür; Lumos ve bu projenin çalışma disiplini ise tersine gider: «Emin değilsek yazmayalım», «Kanıtlayalım», «Önce analiz», «Sessizce kontrol et.» Bu, güvenlik ve mühendislik tarafında doğal bir prensiptir — korku değil, doğrulama.

**Önerilen bölüm eşlemesi:** **Kitap §1** Neden Lumos?, **Kitap §3** Kullanıcı kararı neden merkezde?, **Belge §7** Kurucu hikâye notları (bu bölüm).

### Companion: karakter ve ürün (konumlandırma)

**Kitap §4** (Lumos'un karakteri) ve **Belge §7** (kurucu hikâye) karakter pusulasını taşır: güven veren, manipüle etmeyen, emin olmadığında kesin konuşmayan. **Belge §13** Companion sütunu aynı karakterin uzun vadeli **ürün** ifadesidir — dijital yol arkadaşlığı, bağlam ve öğrenme stilini zamanla anlama. Çelişki değil; katman farkı: karakter ilke olarak sabit kalır, Companion vizyon ürün yolculuğunda ⚪ uzun vadeli hedef olarak durur.

### Uzun yol yaklaşımı

- Hızlı başarı yerine uzun ömürlü yapı.
- Güvenin özelliklerden önce gelmesi.
- İnsan merkezli teknoloji.
- Kontrolün kullanıcıda kalması.
- Toplumsal fayda hedefi.

## 8. Kurucu Manifestosu

- Neden başladık?
- Neden vazgeçmedik?
- Ne inşa etmek istiyoruz?
- Başarıyı nasıl tanımlıyoruz?
- Bu miras kim için?

### Pusula (değişmez ilke — ana kaynak)

> **İnsanların önündeki engelleri teknolojiyle azaltmak.**

Bu cümle **değişmez**; yalnızca uygulama alanları zamanla genişler. Vaat değil; kurucu pusuladır (Belge §11). Kitabın geri kalanı — erişilebilirlik, eğitim, laboratuvar, yönetim — aynı gövdenin farklı dallarıdır (Belge §13).

**Apple analojisi:** Apple'ın pusulası karmaşıklığı azaltmaktı; Lumos'un pusulası **insanların önündeki engelleri teknolojiyle azaltmak**tır.

**Ürün karar filtresi:** «Bu özellik Lumos'a yakışıyor mu?» — pusula ile uyumluysa değerlendirilir; değilse ne kadar ilginç olursa olsun dışarıda kalır. Yıllar içinde proje yayılımını önler.

#### Aynı pusula, farklı alanlar (harita)

Manifesto cümleleri, eğitim ilkeleri, gömülü öğretim kuralları ve UX pusulaları **burada tekrarlanmaz** — ilgili ana kaynak bölümde tanımlıdır.

| Alan | Engel türü | Ana kaynak |
|------|------------|------------|
| 🌍 **Erişilebilirlik** | Fiziksel ve iletişim engelleri | Belge §12 |
| 🎓 **Eğitim** (gömülü, çapraz) | Bilgi engeli (📚) | Belge §13–Belge §14 |
| 🧪 **Lumos Labs** | Deney yapamama engeli | Belge §13 |
| 🗣️ **Çok dilli** | Dil engeli (🌍) | Belge §12 — [engel tablosu](#engel-kavramı--lumos-yaklaşımı-pusula-tablosu) |
| 📍 **Kamera rehberliği** | Mekânsal engel (📍) | Belge §12 — [engel tablosu](#engel-kavramı--lumos-yaklaşımı-pusula-tablosu) |
| 🏢 **Şirket yönetimi** | Karmaşıklık engeli (🧠) | Belge §13 — uzun vade |

#### Dört sütun (Belge §13 — özet)

| Sütun | Kapsam | Ana kaynak |
|-------|--------|------------|
| 🌍 **Lumos Life** | Günlük yaşam, erişilebilirlik, iletişim | Belge §12 — 🟢 / 🟡 şimdiki omurga |
| 🎓 **Lumos Academy** | Kişiye uyarlanmış eğitim; simülasyonlar | Belge §14 — ⚪ uzun vadeli |
| 🧪 **Lumos Labs** | Bilim, tıp, mühendislik — sanal deney | Belge §13 — ⚪ uzun vadeli |
| 🤝 **Lumos Companion** | Uzun süreli dijital yol arkadaşlığı | Belge §13 — ⚪; karakter: Kitap §4 / Belge §7 |

Engel türlerinin ayrıntılı sınıflandırması: Belge §12 [engel kavramı tablosu](#engel-kavramı--lumos-yaklaşımı-pusula-tablosu).

## 9. Kapsam ve Değişim Notu

Bu kitap, Lumos'un belirli bir tarihteki anlayışını ve mimarisini belgeleyen yaşayan bir kurucu metindir.

Yeni araştırmalar, teknik gelişmeler ve edinilen deneyimler doğrultusunda güncellenebilir.

Kitapta yer almayan bir konu, Lumos'un o alanı reddettiği anlamına gelmez; yalnızca o tarihte yeterince olgunlaşmadığını veya doğrulanmadığını gösterir.

Bu kitap kesin doğrular kitabı değil, ilkeler, deneyimler ve kanıtlanmış yaklaşımlar üzerine inşa edilen yaşayan bir referanstır.

## 10. Yayın ve dağıtım modeli

> **Belge §10**, Lumos'un ne söylediğini değil; aynı içeriğin farklı kanallarda nasıl ve hangi kurallarla yayımlandığını tanımlar.

### 1. Amacı (neden var?)

- **Tek kaynak, çok yüz:** GitHub’daki yaşayan belge kanıt kalır; okuyucu insancıl web/kitap yüzeyinde okur — iki ayrı metin senkron tutulmaz.
- **Şeffaflık:** Diff, geçmiş ve kaynak linki erişilebilir kalır (Belge §8 pusulası: kanıt önceliği).
- **Marka hiyerarşisi:** WeLockAI yayıncı; Lumos Referanslar içerik; GitHub teknik altyapı — okuyucu depoya değil kütüphaneye girer.
- **Lansman karışıklığını önlemek:** «Lansman» türlerini ayırır; dış haberler ve ürün lansmanı bu bölümde karışmaz ([Lansman türleri](#lansman-türleri-karıştırma-notu)).

**İlke:** Tek belge, üç yüz.

### 2. Kapsamı (neleri içerir?)

| Konu | Özet |
|------|------|
| **Üç katman** | GitHub (kaynak) → web okuma sürümü → PDF/ePub |
| **Marka / yüzey** | WeLockAI · Lumos Referanslar · GitHub kaynak linki |
| **Referans Kütüphanesi** | Ana indeks; Referans 1–5 planı (aşağıda tablo) |
| **Sayfa hedefi** | `welockai.com/referanslar`, menü: Web / PDF / GitHub kaynağı |
| **Lansman türleri** | Referans yayını, Life, ticari, iç mühendislik kapısı — ayrı satırlar, TBD |
| **Vizyon uyumu** | Kontrol kullanıcıda; kaynak açık, okuma deneyimi insancıl |

Ayrıntılar aşağıda alt başlıklarda; burada tekrarlanmaz.

### 3. Sınırları (neleri içermez?)

- **Ürün özellik vaadi** — erişilebilirlik, eğitim, Labs içeriği → Belge §12–§14.
- **Yayımlama kalite kapısı** (altı kontrol, «tamamlanmadan yayımlama») → **Belge §11**; bu bölüm yalnızca referans verir.
- **Kurucu pusula ve vizyon dalları** → Belge §8, §13.
- **Ticari aşama planı** (Alpha / Beta / Commercial giriş kriterleri) → `docs/analysis/pre-commercial-release-plan.md`.
- **Otomasyon / CI / build pipeline** — henüz kurulmadı; bu belge hedef mimariyi tanımlar, uygulama taahhüdü değildir.
- **Takvim taahhüdü** — TBD; ayrı yazılı karar + onay olmadan eklenmez (Belge §11).

### 4. V1 / yakın gelecek / uzun vadeli

| Dönem | Ne | Durum |
|-------|-----|--------|
| **Şimdi (V1 / erken faz)** | GitHub kaynak (`docs/lumos-book-outline.md`); taslak; diff açık | ✅ Yaşayan belge |
| **Yakın gelecek** | Referans 1 web okuma sürümü; §11 altı kontrol; basit GitHub Pages veya welockai.com/referanslar/1 | 🟢 planlı — otomasyon TBD |
| **Yakın gelecek** | PDF/ePub aynı kaynaktan türetim (tek omurga) | 🟢 planlı |
| **Yakın gelecek** | Referans 2–5 ayrı iskeletler; kütüphane indeksi | planlı |
| **Uzun vadeli** | Tam referans kütüphanesi; çoklu dil (mimari kararı: LUMOS-0020, #895 ile `main`'de); otomatik üç yüz pipeline | ⚪ |

**Not:** Panel v1 kapanışı (**2026-06-12**) iç mühendislik kapısıdır; referans web yayını değildir.

### 5. Diğer bölümlerle bağlantısı

| Bölüm | Bağlantı |
|-------|----------|
| **Belge §11** | Web/PDF/indeks «yayımlandı» sayılmadan önce altı kontrol |
| **Belge §8** | Pusula; şeffaflık ve kanıt önceliği |
| **Belge §12** | Life **ürün** lansmanı; tarih TBD — §10 yalnızca tür haritası |
| **Belge §13–§14** | Vizyon; referans yayını kapsam dışı |
| **Belge §6** | WeLockAI görünürlüğü sorusu → §10 marka tablosu |
| **Kitap §14** | Ticari omurga kitap içeriği; §10 yayıncı yüzeyi |
| **Üst yayın notu** | GitHub tek kaynak; §11 öncesi okuma sürümü sunulmaz |

---

### Üç katman (sıra)

| Katman | Rol | Hedef kitle |
|--------|-----|-------------|
| **1. GitHub** | Gerçek kaynak — yaşayan belge, diff, geçmiş | Geliştirici, katkıcı, kanıt arayan |
| **2. GitHub Pages veya resmî web** | Okuma sürümü — temiz tipografi, mobil uyum | Sadece okumak isteyen |
| **3. PDF / ePub** | Kitap sürümü — indirilebilir, çevrimdışı | Derin okuma, arşiv, paylaşım |

GitHub'daki belge güncellendiğinde web (ve isteğe bağlı PDF/ePub) **aynı kaynaktan** üretilir. İki ayrı metin senkron tutulmaz; tek omurga korunur.

### Marka ve yüzey hiyerarşisi

**WeLockAI ön planda** — yayıncı ve kurumsal çatı; okuyucu önce bir markaya, sonra bir depoya girer.

| Katman | Yüzey | Rol |
|--------|--------|-----|
| **WeLockAI** | `welockai.com`, site üst bilgisi, telif, yayıncı satırı | Ön plan — «kim sunuyor» |
| **Lumos Referanslar** | İçerik kütüphanesi adı, bölüm başlıkları | «Ne okuyorsun» — ürün felsefesi ve teknik referans |
| **GitHub** | Kaynak linki, diff, katkı | Arka plan — «kanıt nerede» |

Ürün sohbetinde kullanıcı yalnızca **Lumos** görür; referans kütüphanesi sayfasında ise **WeLockAI · Lumos Referanslar** birlikte görünür — tıpkı bir yayınevinin kitap serisi gibi. GitHub logosu ve «kaynak» linki ikincil kalır.

**Örnek üst bilgi:** `WeLockAI` · Lumos Referanslar · Referans 1

### Sayfa örneği (hedef)

**Ana indeks:** `welockai.com/referanslar` (veya `lumos.ai/referanslar` — WeLockAI markası üst bilgide ön planda)

**Bu belge:** `…/referanslar/1` — Kurucu Kitap İskeleti

Sağ üst veya sabit menü:

- 📖 Web'de Oku (mevcut sayfa)
- 📄 PDF İndir
- 💻 GitHub Kaynağı (`docs/lumos-book-outline.md`)

### Lumos Referans Kütüphanesi (ana indeks)

Ana sayfa başlığı yalnızca: **Referanslar**

Altında zamanla oluşan belgeler — kullanıcı «GitHub deposu»na değil, **WeLockAI · Lumos Referans Kütüphanesi**ne girer; GitHub teknik altyapı kalır.

| # | Başlık | Durum | Repo kaynağı (hedef) |
|---|--------|-------|----------------------|
| 📘 1 | Kurucu Kitap İskeleti | **taslak (bu belge)** | `docs/lumos-book-outline.md` |
| 📗 2 | Karar Sözleşmesi | planlı | `docs/lumos-karar-sozlesmesi.md` |
| 📙 3 | Mimari | planlı | `docs/ARCHITECTURE.md`, `docs/ARCHITECTURE_MAP.md` |
| 📕 4 | Güvenlik | planlı | `docs/security-architecture.md`, ADR-012 zinciri |
| 📓 5 | Quantum Readiness | planlı | `docs/decisions/ADR-013-lumos-quantum-security-readiness.md` |

**Not:** 2–5 numaralı referanslar henüz ayrı «Referanslar N» iskeleti olarak yazılmadı; mevcut repo belgeleri kaynak adayıdır. Her biri olgunlaştıkça aynı üç yüz modeli uygulanır.

### Vizyon uyumu

Bu model Lumos'un «kontrol kullanıcıda», şeffaflık ve kanıt önceliği ilkesiyle uyumludur: kaynak açık, okuma deneyimi insancıl, sürüm geçmişi izlenebilir.

Web ve kitap sürümüne çıkmadan önce Belge §11 altı kontrolden geçilir; GitHub'daki taslak kaynak yaşayan belge olabilir ancak «okuma sürümü» olarak sunulmaz.

### Lansman türleri (karıştırma notu) {#lansman-türleri-karıştırma-notu}

Bu belgede **«lansman»** tek anlama gelmez. Dış haberler (ör. başka ülkelerin kamu AI projeleri) Lumos lansmanı **değildir**.

| Tür | Ne | Tarih (repo) | Ana kaynak |
|-----|-----|--------------|------------|
| **Referans yayını** | Kurucu kitap / Referanslar web veya PDF | **TBD** — tarih yok; açık koşullar Belge §6 yayın tarihi kararında | Belge §10 |
| **Life lansmanı** | Erişilebilirlik omurgası; 🟢🟡 özellik tanıtımı | **TBD** — taahhüt tarihi yok | Belge §12 |
| **Ticari lansman** | Open Beta → Commercial Launch | **TBD** — Pre-Alpha; `docs/analysis/pre-commercial-release-plan.md` | Repo plan belgeleri |
| **İç mühendislik kapısı** | Panel v1 kapanışı | **2026-06-12** (`LUMOS_V1_READINESS.md`) | Halka lansman değil |

**Kural:** Belge §11 — yarım düşünceyi tamamlanmış gibi sunma; **takvim taahhüdü** yalnızca ayrı yazılı karar + onay ile eklenir.

## 11. Yayımlama ilkesi: Tamamlanmadan yayımlama

**İlke:** Tamamlanmadan yayımlama.

Her yeni belge, referans veya mimari karar — web okuma sürümü, PDF/ePub veya «Referanslar» kütüphanesinde okuyucuya açılan sürüm — yayımlanmadan önce şu **altı kontrolden** geçer:

### 1. Doğruluk

- Kanıtlanamayan iddialar açıkça belirtilir.
- «Emin değilsek yazmayalım» disiplini: tahmin, varsayım ve henüz doğrulanmamış noktalar gizlenmez.

### 2. Tutarlılık

- Mevcut karar sözleşmeleri ve referanslarla çelişmez.
- Çelişki varsa bilinçli güncelleme veya açık «defer / taslak» işareti konur; sessiz çelişki bırakılmaz.

### 3. Tamamlanma

- Bölüm kendi amacı için yeterince olgundur.
- Bilerek bırakılan eksikler açıkça işaretlenmiştir («planlı», «belirsiz», «henüz doğrulanmadı»).

### 4. Gözden geçirme

- En az bir kez baştan sona okunur.
- Bağlantılar, başlıklar, dil ve kaynaklar kontrol edilir.

### 5. Hukuki ve uyum kontrolü

- Gizlilik, audit, veri işleme ve uyum iddiası taşıyan yerlerde uygulama biçimi ile kamusal ifade ve uyum gereklilikleri yayımlanmadan önce kontrol edilir. Kurucu kararlar bu kontrolle yeniden açılmaz.
- Bu kontrol kitabın tamamını bir hukuk onayına bağlamak için değildir; iddia taşıyan yerlerin uygulanması ve kamusal ifadesi içindir.

### 6. Vizyon ve gerçek ayrımı

- Gerçek ekran veya davranış, kanıtlı sürümden gelir.
- Vizyon açıkça vizyon diye etiketlenir.

**Amaç:** Kusursuzluk değil; **yarım kalmış düşünceleri tamamlanmış gibi sunmamaktır.**

| Sürüm | Bu ilkeye tabi mi? |
|-------|-------------------|
| GitHub kaynak (taslak, diff açık) | Hayır — yaşayan belge olabilir; durum etiketi gerekir |
| Web okuma sürümü | Evet |
| PDF / ePub | Evet |
| Referans Kütüphanesi indeksinde «yayımlandı» | Evet |

**Referans:** `docs/lumos-karar-sozlesmesi.md` (cevap disiplini, emin değil); Belge §6 karara bağlanan sorular (yayın tarihi TBD).

## 12. Lumos Life — Erişilebilirlik Platformu ve Toplumsal Katkı

*Ana kaynak:* gerçek dünya erişilebilirliği, [engel tablosu](#engel-kavramı--lumos-yaklaşımı-pusula-tablosu), lansman taahhüdü. Eğitim, Labs, şirket yönetimi → Belge §13 / Belge §14. Vizyon ağacı sütunu: 🌍 **Lumos Life** (Belge §13). Pusula (değişmez): Belge §8.*

Lumos, erişilebilirliği temel tasarım ilkelerinden biri olarak görür. Bu alan «engelli modu» gibi dar bir çerçeveye sıkıştırılmaz; herkesin ihtiyacı zamanla değişebilir. Bir gün geçici bir sakatlık, bir gün ameliyat, yaş alma, yoğunluk, yorgunluk veya çevresel koşullar erişilebilirliği herkes için gerekli hale getirebilir.

Lumos'un amacı, insanları teknolojiye uyarlamak değil; teknolojiyi insanların farklı ihtiyaçlarına uyarlamaktır.

### Geniş vizyon — engel kavramına göre

Lumos erişilebilirliği **kişi etiketlerine** («görme engelli», «işitme engelli») göre değil, **insanın önündeki engel kavramına** göre düşünür. Amaç: «Lumos engelli uygulaması» değil; **insanların önüne çıkan engelleri azaltmayı hedefleyen** bir yapay zekâ katmanı.

Engeller yalnızca fiziksel değildir. **Dil**, **mesafe**, **bilgiye erişememe**, **yön bulma**, **iletişim** ve **teknoloji karmaşıklığı** de aynı pusulanın parçasıdır — geçici veya kalıcı; engelli birey, yaşlı, yabancı dil kullanıcısı, teknolojiye uzak veya yalnız yaşayan biri için aynı mantıkla ele alınabilir. Kurucu pusula (değişmez): Belge §8.

> Engeller sadece fiziksel değildir. Dil de bir engeldir. Mesafe de bir engeldir. Bilgiye erişememek de bir engeldir. Lumos, teknolojiyle bu engelleri **azaltmayı hedefler** — bugün tamamlanmış bir ürün listesi vaat etmez.

> **Manifesto cümlesi (taslak):** Biz insanlar arasındaki farklara değil, insanların önündeki engellere odaklanıyoruz.

#### Engel kavramı → Lumos yaklaşımı (pusula tablosu)

Birincil sınıflandırma budur. **Lumos yaklaşımı** hedef yöndür; **durum** güncel geliştirme aşamasını gösterir (vaat değil).

| Engel kavramı | Lumos yaklaşımı (hedef) | Durum (taslak) |
|---------------|-------------------------|----------------|
| 👁️ **Görme engeli** | Çevre analizi; yön tarifi; nesne/kaldırım betimleme | 🟢 Planlandı / 🟡 Geliştiriliyor |
| 👂 **İşitme engeli** | Canlı altyazı; konuşmayı yazıya; işaret dili desteği (uygun teknolojiyle) | 🟡 Geliştiriliyor |
| 🌍 **Dil engeli** | Anlık çok dilli arayüz; konuşma ve metin çevirisi (kademeli) | 🟢 Planlandı (arayüz dili) / ⚪ Araştırma (canlı konuşma çevirisi) |
| 📍 **Mesafe engeli** | Kamera ile uzaktan rehberlik; mesafe ve yön ipuçları | 🟡 Geliştiriliyor |
| 📚 **Bilgi engeli** | Bilgiyi sadeleştirerek anlatma; adım adım yönlendirme | 🟢 Planlandı |
| 💬 **İletişim engeli** | Kişiye uygun ifade biçimi; hazır kartlar; işaret dili avatarı (araştırma/geliştirme) | 🟡 Geliştiriliyor |
| 🧠 **Teknoloji engeli** | Karmaşık işlemleri parçalama; tek net komutla yönlendirme; sesle kontrol | 🟢 Planlandı |

**Okuma notu:** Aynı özellik birden fazla engel kavramına hizmet edebilir (ör. altyazı hem işitme hem gürültülü ortam). Lansman ve web metinlerinde **engel kavramı** sütunu, «hangi engeli azaltmayı hedefliyoruz» sorusunu yanıtlar.

**📚 Bilgi engeli — katman notu:** 🟢 planlı satırlar (sadeleştirme, adım adım yönlendirme) Life omurgasındadır; kişiselleştirilmiş öğretim ve simülasyon Academy vizyonudur ([Belge §14](#14-lumos-academy-uzun-vadeli-vizyon), ⚪). Life'taki 🟢 planlı özellikler Academy vaadi sayılmaz.

Bu hedef, aşağıdaki **lansman özellik tablosu** ile sınırlıdır; tabloda yer almayan hiçbir özellik tanıtımda sunulmuş sayılmaz (Belge §11, Belge §12 taahhüdü).

Görme, işitme, konuşma, motor beceri ve bilişsel farklılıkları olan kullanıcılar için erişilebilir özellikler geliştirmek ürünün uzun vadeli hedefleri arasındadır. Bu alandaki temel erişilebilirlik özelliklerinin mümkün olduğunca ücretsiz sunulması hedeflenir.

İleri düzey kurumsal veya ticari özellikler ücretli olabilir; ancak temel erişilebilirlik desteği ticari bir ayrıcalık değil, toplumsal sorumluluğun parçası olarak değerlendirilir. Bu bölüm bugünden tek tek ücretsiz özellik garantisi vermez; Lumos'un uzun vadeli tasarım pusulasını tanımlar.

### Erişilebilirlik Taahhüdü (beklenti yönetimi)

Lumos, erişilebilirliği **temel bir ilke** olarak benimser.

**Kapsam sınırı:** Bu taahhüt yalnızca aşağıda **durum etiketiyle açıkça listelenen** ve gerçekten geliştirmeyi planladığımız alanlar için geçerlidir. Taahhüt metni, hiç düşünülmemiş özellikleri vaat etmez; baştan sınırları dürüstçe çizer.

**Avantajları:**

- «Başta böyle demiştiniz» tartışmalarını azaltır.
- Her ülkeye aynı anda hizmet verme zorunluluğu doğurmaz.
- Yeni sponsor veya kamu desteği geldikçe kapsam genişletilebilir.
- Bir özellik geçici olarak kaldırılsa bile verilen sözle çelişmez.

#### Durum etiketleri (lansman / web)

«Hedefleniyor» gibi pasif ifadeler yerine kullanıcı **bugün neyin kullanılabilir**, **neyin hangi aşamada** olduğunu net görür:

| Etiket | Anlam |
|--------|--------|
| 🟢 **Planlandı** | Yol haritasında; tasarım ve kapsam netleşmiş |
| 🟡 **Geliştiriliyor** | Aktif geliştirme; henüz genel kullanıma açık değil |
| 🔵 **Pilot** | Sınırlı bölge / kullanıcı grubunda deneme |
| ⚪ **Araştırma** | Teknik veya etik fizibilite; ürün vaadi değil |

Durumlar lansman görseli, web ve referans metinlerinde **her özellik satırının yanında** gösterilir; güncellendikçe etiket değiştirilir (Belge §11 yayımlama ilkesi).

**Örnek lansman listesi (taslak — durumlar olgunlaştıkça güncellenir):**

Ayrıntılı tablo: [Lansman özellik tablosu](#lansman-özellik-tablosu-taslak) (aşağıda).

#### Lansman ve web metinleri (Belge §12 çıktıları)

**1. Kısa vizyon (kart / hero altı):** Engeller yalnızca fiziksel değildir — dil, mesafe, bilgi, yön ve iletişim de erişilebilirlik alanıdır. Lumos bu engelleri azaltmayı hedefler; kapsam aşağıdaki tablo ile sınırlıdır.

**2. Lansman sloganı (tek satır):**

> **Engeller çeşitlidir. Lumos erişilebilirliği geniş tutar.**

**Alternatif (manifesto kısa):**

> **Farklara değil, engellere odaklanıyoruz.**

**3. Web / görsel alt şerit:**

> Not: Ücretsiz erişilebilirlik hizmetleri ülke, mevzuat, teknik altyapı, cihaz uyumluluğu ve sponsor desteklerine bağlı olarak değişebilir. Görselde yer almayan özellikler sunulmuş sayılmaz.

#### Taahhüt metni (lansman / web / kart altı)

⸻

**Erişilebilirlik Taahhüdü**

Lumos, erişilebilirliği temel bir ilke olarak benimser.

Ücretsiz erişilebilirlik hizmetleri; ülke, yerel mevzuat, teknik altyapı, cihaz uyumluluğu ve sponsor desteklerine bağlı olarak değişebilir. Bazı özellikler belirli bölgelerde henüz sunulmamış veya pilot aşamada olabilir.

Lumos, erişilebilirlik özelliklerini mümkün olduğunca genişletmeyi hedefler; ancak **hiçbir görsel veya tanıtım materyali**, burada açıkça belirtilmeyen bir özelliğin kullanıma sunulduğu anlamına gelmez.

⸻

**Kısa not (tek satır, alt şerit):**

> Not: Ücretsiz erişilebilirlik hizmetleri ülke, mevzuat, teknik altyapı, cihaz uyumluluğu ve sponsor desteklerine bağlı olarak değişebilir.

Son cümle («görsel… anlamına gelmez») beklenti yönetimi ve tanıtım sınırı için zorunlu parçadır; «Resimde vardı, o zaman kesin vardı» yorumunun önüne geçer.

#### Lansman özellik tablosu (taslak) {#lansman-özellik-tablosu-taslak}

Yalnızca planlanan vizyon alanları. Durumlar Belge §11 ile uyumlu; olgunlaştıkça güncellenir.

| Durum | Özellik / alan | Engel kavramı |
|-------|----------------|---------------|
| 🟢 Planlandı | Görme desteği (genel) | 👁️ Görme |
| 🟢 Planlandı | Kamera ile çevre tarifi | 👁️ Görme · 📍 Mesafe |
| 🟢 Planlandı | Metin sadeleştirme | 📚 Bilgi |
| 🟢 Planlandı | Sesle okuma (TTS) | 📚 Bilgi · 💬 İletişim |
| 🟢 Planlandı | Sesle tam kontrol, büyük arayüz | 🧠 Teknoloji · motor erişilebilirlik |
| 🟢 Planlandı | Niyeti parçalama, adım adım yönlendirme | 🧠 Teknoloji · 📚 Bilgi |
| 🟢 Planlandı | Panel / arayüz çok dilli sunum | 🌍 Dil |
| 🟡 Geliştiriliyor | Gerçek zamanlı altyazı / konuşmayı yazıya | 👂 İşitme · 💬 İletişim |
| 🟡 Geliştiriliyor | İşaret dili avatarı (temel iletişim) | 👂 İşitme · 💬 İletişim · 🌍 Dil |
| 🟡 Geliştiriliyor | Akıllı yön ve mesafe rehberliği | 📍 Mesafe · 👁️ Görme |
| 🟡 Geliştiriliyor | Acil durum kısa yolları | 💬 İletişim · güvenlik |
| ⚪ Araştırma | Anlık çok dilli konuşma çevirisi | 🌍 Dil |
| ⚪ Araştırma | Gelişmiş erişilebilirlik (göz takibi vb.) | 🧠 Teknoloji · motor |
| ⚪ Araştırma | İç mekân yönlendirme (teknik imkâna bağlı) | 📍 Mesafe · 👁️ Görme |

**Durum açıklaması:** 🟢 planlandı · 🟡 geliştiriliyor · 🔵 pilot · ⚪ araştırma — hiçbiri «bugün herkes için kullanılabilir» anlamına gelmez.

Özellik alanlarının kısa özeti yukarıdaki lansman tablosunda verilir; ayrı «vizyon başlıkları» listesi tekrarlanmaz.

Lumos'un başarısı yalnızca teknolojisiyle değil, ulaşabildiği insan sayısıyla ölçülür. Erişilebilirlik, sonradan eklenen bir özellik değil; tasarımın temel parçalarından biridir.

**Lansman görseli:** Her özellik satırında 🟢🟡🔵⚪ durum etiketi; altında **Erişilebilirlik Taahhüdü** bloğu (görsel sınır cümlesi dahil). Belge §11: listede olmayan özellik görselde vaat edilmez.

## 13. Lumos vizyon ağacı — dört sütun (uzun vadeli)

*Harita bölümü — ayrıntılar ana kaynaklarda. Gövde: Belge §8. Life: Belge §12. Eğitim: Belge §14. Vaat değil; vizyon pusulasıdır (Belge §11).*

### Öncelik ve dört sütun

| Sıra | Sütun | Odak | Durum |
|------|-------|------|--------|
| **1** | 🌍 **Lumos Life** (Belge §12) | Günlük yaşam, erişilebilirlik, iletişim, gerçek dünya | 🟢 / 🟡 — **şimdiki omurga** |
| **2** | 🎓 **Lumos Academy** ([Belge §14](#14-lumos-academy-uzun-vadeli-vizyon)) | Kişiye uyarlanmış eğitim; simülasyon; video platformu değil | ⚪ — V1 dışı |
| **3** | 🧪 **Lumos Labs** | Bilim, tıp, mühendislik; güvenli sanal deney evrenleri | ⚪ — V1 dışı |
| **4** | 🤝 **Lumos Companion** | Uzun süreli dijital yol arkadaşlığı; kişiyi tanıma | ⚪ — V1 dışı |

Çoğu yapay zekâ **cevap verir**. Lumos’un en büyük **uzun vadeli etkisi eğitim tarafında olabilir** — deneyim yaşatmayı hedefler; Life omurgasının yerine geçmez.

**İki yüz, aynı gövde:** Önce gerçek dünya (Belge §12). Sonra — olgunlaştıkça — deneyimleten öğrenme (Belge §14).

Eğitim manifestoları, gömülü öğretim kuralları, dört faz ve UX pusulası **Belge §14**'te tanımlıdır; burada tekrarlanmaz.

**Deneyim sloganı (pusula, vaat değil):** «Hayal etmen yeterli.»

Hepsi Belge §8 gövdesinin ve Belge §12 [engel tablosunun](#engel-kavramı--lumos-yaklaşımı-pusula-tablosu) farklı dallarıdır.

### 🎓 Lumos Academy (⚪ — özet)

Eğitim çoğu zaman herkese aynı biçimde anlatır; Lumos kişiye uyarlanmış öğrenmeyi hedefler. Örnek diyaloglar, kişiselleştirme mimarisi, çok kanallı öğretim ve Labs entegrasyonu → **[Belge §14](#14-lumos-academy-uzun-vadeli-vizyon)** (ana kaynak).

### 🧪 Lumos Labs — deneyim evrenleri (⚪)

Bilim, tıp, mühendislik ve keşif için **güvenli sanal deney** ortamları. Academy ile örtüşür; Labs **disiplin evrenleri** ağırlıklıdır. Eski ad «Lumos Worlds» burada toplanır.

### Gömülü eğitim (çapraz yetenek — özet)

Eğitim ayrı bir uygulama değil; tüm sütunlarda çapraz yetenektir. **Ana kaynak:** Belge §14 («Yapabiliyorsa, öğretebilmeli», dört faz, örnek tablolar, UX pusulası, öğretmen sınırı).

### 🤝 Lumos Companion (⚪ — ürün vizyonu)

**Konumlandırma:** Karakter ilkesi **Kitap §4** / **Belge §7**; bu alt bölüm uzun vadeli **ürün** ifadesidir (bkz. Belge §7 «Companion: karakter ve ürün»).

Uzun süreli **dijital yol arkadaşlığı** — tercihler, öğrenme stili, sınırlar, bağlam (`docs/analysis/welockai-charter-draft.md` «ilk yol arkadaşı»). Life ve Academy’yi destekler; yerine geçmez. «Kişiyi tanıma» pusulası: nasıl öğrendiğini zamanla anlamayı hedefler (⚪).

### Labs — alt evrenler (taslak — tümü ⚪)

Hiçbiri V1 veya erken faz omurgasında değildir. Tanıtımda yalnızca **vizyon** ve **durum etiketi** ile geçer.

| Dünya | Olası deneyim | Not |
|-------|---------------|-----|
| 🧪 **Lumos Lab** | Sanal kimya laboratuvarı; patlama riski olmadan deney; molekül birleştirme; hataları Lumos anlatır | Eğitim simülasyonu |
| 🧬 **Lumos Bio** | Hücre içi; DNA kopyalanması (3B); kan dolaşımı; bağışıklık simülasyonu | Eğitim simülasyonu |
| 🫀 **Lumos Med** | Sanal ameliyat simülasyonu; organ modelleri; hastalık ilerlemesi gözlemi | **Yalnızca eğitim** — gerçek tıbbi tavsiye yerine geçmez |
| 🚀 **Lumos Space** | Mars; kara deliğe yaklaşma; ışık hızı etkileri (simülasyon) | Bilimsel model + sadeleştirme |
| ⚛️ **Lumos Quantum** | Qubit deneyleri; devre sürükle-bırak; sonuç görselleştirme | ADR-013 / Quantum Readiness ile hizalı araştırma sınırı; Kitap §13 (Quantum Readiness) ile karıştırılmaz, mevcut yetenek iddiası değildir |
| 🏛️ **Lumos History** | Roma, Göbeklitepe, Ayasofya dönemleri — karşılaştırmalı gezinti | Tarihsel model + belirsizlik işaretleme |
| 🌊 **Lumos Ocean** | Okyanus dibi (~11 km); basınç ve canlılar simülasyonu | Eğitim / keşif |

**Ortak kurallar (Academy · Labs · Companion · gömülü eğitim):**

- Simülasyon **gerçeğin yerine geçmez**; «emin değilsek yazmayalım» tarih ve bilimde de geçerli.
- Med ve Bio içerikleri **tıbbi teşhis veya tedavi vaadi** taşımaz.
- Gömülü eğitim **öğretmeni veya uzmanı ikame etmez**; güçlendirme pusulası tüm modüllerde geçerlidir.
- Engel kavramı (Belge §12) Labs/Academy’de de geçerli: bilgi engeli, mesafe engeli (sanal erişim) — **hedef**, garanti değil.
- Ücretsiz / erişilebilir eğitim hedefi Belge §12 taahhüdü ile uyumlu düşünülür; kapsam ülke, altyapı ve sponsor ile sınırlı kalabilir.
- Öğretir ve Birlikte uygular evreleri **⚪ uzun vadeli**; lansmanda mevcut özellik olarak sunulmaz (Belge §11).

### Lansman / kitapta nasıl geçer

- **Ana lansman:** Belge §12 Lumos Life (🟢🟡).
- **Vizyon kartı / kitap:** Dört sütun + gövde; Academy, Labs, Companion **⚪**; «Hayal etmen yeterli» altında «henüz ürün değil».
- Belge §11: Vizyon görselleri tek başına «mevcut özellik» algısı yaratmaz.

**Referans:** `docs/PRODUCT_SUMMARY.md`; `docs/decisions/ADR-013-lumos-quantum-security-readiness.md`; `docs/analysis/welockai-charter-draft.md`.

## 14. Lumos Academy (Uzun Vadeli Vizyon)

*Ana kaynak:* eğitim manifestoları, gömülü öğretim, dört faz, UX pusulası, öğretmen sınırı, örnek tablolar. Gövde: Belge §8 — 📚 **bilgi engeli** dalının eğitim tasarımı. Belge §13 harita; bu bölüm ayrıntı. Vaat değil; uzun vadeli vizyon pusulasıdır (Belge §11).*

**Durum:** ⚪ Araştırma / uzun vadeli — **V1 ve erken faz omurgasının dışındadır.** Ana omurga: Belge §12 Lumos Life (🟢 / 🟡).

### Academy nedir?

**Lumos Academy**, Lumos'un uzun vadeli eğitim dalıdır. Bugün bir görevi tamamlayan Lumos, yarın aynı bağlamda «neden böyle» sorusunu taşıyan bir öğrenme yolculuğu sunmayı **hedefler** — hedef yön; mevcut ürün listesi veya lansman taahhüdü değildir.

Academy yalnızca «okul modu» değildir; **gömülü eğitim** pusulası günlük görevlerden Academy'ye uzanır (Belge §13 özet).

> **Eğitim manifestosu:** Lumos öğretmenin veya profesyonelin yerine geçmez; öğrenmeyi kişiye göre uyarlamayı hedefler.

> **Deneyim manifestosu:** Öğrenmeyi yalnızca anlatan değil, **deneyimleten dijital dünyalar** oluşturmak — uzun vadeli hedeflerden biri.

> **Gömülü eğitim ilkesi:** Lumos sadece işini yapan bir yapay zekâ değildir. Gerekirse yaptığı işi sana da öğretebilir.

### Temel ilke ve dört faz

**Çapraz pusula (Belge §8 — vaat değil):**

> **Yapabiliyorsa, öğretebilmeli.**

| Faz | Ne anlama gelir | Academy'de durum (taslak) |
|-----|-----------------|---------------------------|
| **Yapar** | İşi tamamlar | Life omurgasında kısmen gerçekçi (Belge §12) |
| **Anlatır** | «Neden böyle» sorusuna kısa yanıt | 🟢 planlı — Belge §12 📚 bilgi engeli ile örtüşür |
| **Öğretir** | Adım adım, kişiye uyarlanmış öğretim | ⚪ — Academy çekirdeği |
| **Birlikte uygular** | Kullanıcıyla ortak pratik | ⚪ uzun vadeli |

Erken fazda yalnızca «Yapar» ve sınırlı «Anlatır» katmanları gerçekçidir; «Öğretir» ve «Birlikte uygular» Academy'nin asıl vizyon alanıdır — bugün ürün iddiası taşımaz.

### Gömülü eğitim — örnekler ve vakalar

Lumos bir modülde bir işi yapabiliyorsa, aynı bağlamda o işin mantığını anlatmayı ve öğretmeyi de hedefler:

| Yapabildiği | Öğretebilmeyi hedeflediği |
|-------------|---------------------------|
| Muhasebe işlemi | Muhasebe mantığı |
| Kod yazma / düzenleme | Kodlama ve karar gerekçesi |
| Şirket / süreç yönetimi | Yöneticilik ve önceliklendirme |
| Hukuki süreç hazırlığı | Sürecin mantığı (hukuki tavsiye yerine geçmez) |
| Siber güvenlik kurulumu | «Neden böyle» — tehdit ve önlem mantığı |
| Tıbbi simülasyon | Anatomi ve süreç (teşhis/tedavi yerine geçmez) |

**Vaka örnekleri (hedef yön — vaat değil, Belge §11):** Kurumsal ISO uyumu adım adım öğretim; PLC programlama birlikte uygulama; Lumos Space ile fizik keşfi; Lumos Med eğitim simülasyonu (tıbbi tavsiye yerine geçmez).

**Kişiselleştirme hedefleri (⚪):** görsel → 3B simülasyon; işitsel → diyalog; tekrarlayan hata → öğretim biçimini değiştirme; hızlı ilerleme → zorluk artırma; zorlanma → farklı örneklerle yeniden açma.

**Örnek diyaloglar (vizyon dili — bugün ürün iddiası değil):**

| İstek | Hedeflenen deneyim |
|-------|-------------------|
| «Elektrik öğrenmek istiyorum.» | Sanal ev; arızayı birlikte bulma |
| «Kalbin nasıl çalıştığını öğrenmek istiyorum.» | «Kanın içinde yolculuk» — 3B simülasyon |
| «Beni insan vücudunun içine götür.» | «Hazır. Kalbin içindeyiz.» — deneyimsel öğrenme |

### Kişiye uyarlanmış öğrenme (⚪)

Academy'nin mimari hedefi: kullanıcının öğrenme biçimini zamanla anlamak ve öğretimi buna göre kişiselleştirmek — hangi açıklama düzeyi işe yarıyor, metin mi ses mi görsel mi daha etkili, tekrar ihtiyacı nerede artıyor, hangi konularda «birlikte uygula» tercih ediliyor.

**Öğretmen / profesyonel sınırı:** Lumos öğretmenin, doktorun, avukatın veya başka bir profesyonelin yerine geçmez. Öğrenmeyi kişiye göre uyarlamayı ve bilgi engelini azaltmayı hedefler; sınıfın veya kliniğin yerine geçen «yapay öğretmen» değil, öğrenmeyi güçlendiren yardım katmanıdır. Bu analiz **kullanıcıyı etiketlemek** için değil; **engeli azaltmak** için düşünülür (Belge §12 **📚 Bilgi engeli**).

### Çok kanallı öğretim (hedef mimari)

Öğretimi tek sohbet metnine sıkıştırmama hedefi:

| Kanal | Olası rol | Durum |
|-------|-----------|--------|
| **Metin** | Adım adım açıklama, özet, sadeleştirme | Life ile örtüşür — kademeli (Belge §12) |
| **Ses** | Dinleyerek öğrenme, telaffuz, ritim | 🟢 / 🟡 planlı (erişilebilirlik ile) |
| **Görsel** | Şema, diyagram, karşılaştırmalı görüntü | ⚪ uzun vadeli |
| **3B simülasyon** | Mekânsal ve yapısal kavramları deneyimletme | ⚪ — Labs ile hizalı (Belge §13) |
| **Uygulamalı öğrenme** | Birlikte yaparak öğrenme, güvenli deneme alanı | ⚪ uzun vadeli |

Hiçbir kanal «yarın hepsi hazır» anlamına gelmez; her satır **hedef mimari yöndür** (Belge §11).

### Labs / Worlds entegrasyonu (⚪)

Academy, Belge §13'teki **Lumos Labs** deneyim evrenleriyle uzun vadede birleşmeyi hedefler — bugünün ürünü değil, araştırma ve tasarım yönüdür.

**Doğru sıra:**

1. **Gerçek dünya** (Belge §12): Bulunduğun yeri anlatır, engelleri azaltır, bilgiyi sadeleştirir.
2. **Academy + Labs** (Belge §13, bu bölüm): Öğrenmek istediğin konunun **içinde dolaşarak** öğrenmeyi hedefler.

Örnek hedef dil (ürün iddiası değil): «Kalp nasıl çalışıyor, anlamak istiyorum.» → kısa metin/ses özeti; olgunlaştıkça Lumos Bio veya Lumos Med eğitim simülasyonuna taşıma. Labs alt dünyaları Academy'nin **uygulamalı öğretim sahnesi**; simülasyon gerçeğin yerine geçmez, tıbbi teşhis/tedavi veya resmi sınav garantisi taşımaz (Belge §13 ortak kurallar).

### Pusula uyumu

Academy, Belge §8 pusulasının **📚 bilgi engeli** dalının uzun vadeli derinleşmiş karşılığıdır. Belge §12 [engel tablosunda](#engel-kavramı--lumos-yaklaşımı-pusula-tablosu) «bilgiyi sadeleştirerek anlatma; adım adım yönlendirme» 🟢 planlıdır; Life'taki 🟢 planlı özellikler Academy vaadi sayılmaz.

| Engel | Academy yaklaşımı (hedef) | Durum |
|-------|-------------------------|--------|
| 📚 **Bilgi engeli** | Karmaşık konuyu kişiye uygun düzeyde anlatma; öğretme; deneyimletme | ⚪ (Life'ta kademeli 🟢) |
| 📍 **Mesafe engeli** | Fiziksel erişilemeyen yere sanal erişim (Labs) | ⚪ uzun vadeli |
| 🧠 **Teknoloji engeli** | Karmaşık işi öğrenerek yapabilme | 🟢 / ⚪ kademeli |

**Gizli slogan (pusula, vaat değil):** «Bilgiyi saklayan değil, paylaşan yapay zekâ.»

### UX deseni (vizyon — ⚪)

> «Bunu senin yerine yapmamı mı istersin, yoksa birlikte öğrenerek yapalım mı?»

🟢 **Benim yerime yap** | 🎓 **Bana öğret** — bugün her ekranda mevcut olduğu anlamına gelmez. Lumos kullanıcının gelişiminde ortak olmayı hedefler; bağımlılık üretmeyi değil (Belge §11).

### Neden ayrı bölüm?

| Bölüm | Rol | Zaman |
|-------|-----|-------|
| Belge §12 Life | Erişilebilirlik omurgası, gerçek dünya | Bugün — 🟢 / 🟡 |
| Belge §13 Pusula | Tek ilke, çok dal, Labs/Worlds haritası | Vizyon çerçevesi |
| **Belge §14 Academy** | Eğitim dalının ayrıntılı uzun vadeli tasarımı | ⚪ — V1 dışı |

- **Belge §12 ile karışmaması için:** Life'ın dürüst lansman sınırları bulanıklaşır; 📚 bilgi engelinin «şimdi» ve «sonra» katmanları ayrışmaz.
- **Belge §13 ile karışmaması için:** Pusula haritası ile detaylı eğitim tasarımı üst üste biner; Belge §13 referans verir, Belge §14 açıklar.

```
Belge §8 Pusula (değişmez ilke)
 └── Belge §12 Life — bugün, erişilebilirlik, 📚 bilgi (kademeli)
 └── Belge §13 Pusula dalları — harita, Labs, dört sütun
      └── Belge §14 Academy — eğitim dalı ayrıntı (bu bölüm)
```

### Belge §11 uyumu — bu bölüm ne iddia etmez

- «Bugün Academy modu var»
- «Kişiselleştirilmiş öğretim çalışıyor»
- «Worlds eğitim senaryoları kullanıma açık»
- «3B simülasyonla öğretim mevcut»

Academy görselleri veya örnek diyalogları tek başına «mevcut özellik» algısı yaratmaz; tüm maddeler **⚪** ile geçer; ana lansman Belge §12 omurgasındadır. Web okuma sürümü veya kitap yayımlanmadan önce Belge §11 altı kontrolden geçer.

⸻

> ### ⚪ V1 KAPSAMI DIŞI — UZUN VADELİ VİZYON
>
> **Lumos Academy** bu belgede tanımlandığı haliyle **V1 ve erken faz ürün kapsamının dışındadır.**
>
> | Ne değildir | Ne hedef yöndür |
> |-------------|-----------------|
> | Bugün kullanılabilir özellik | Kişiye uyarlanmış öğretim mimarisi |
> | Lansman taahhüdü | «Yapabiliyorsa öğretebilmeli» pusulası |
> | Öğretmen / uzman ikamesi | Bilgi engelini azaltan yardım katmanı |
> | Labs/Worlds'in yerine geçen ürün | Academy + Labs gelecek entegrasyonu |
>
> **Durum etiketi:** ⚪ Araştırma / uzun vadeli · **Ana omurga:** Belge §12 · **Yayımlama:** Belge §11 altı kontrol
>
> Bu kutudaki hiçbir ifade ürün vaadi, tarih taahhüdü veya «yakında geliyor» iddiası değildir.

⸻

## Paylaşım notu

- GitHub linki üzerinden kaynak metin okunabilir ve incelenebilir.
- Okuma sürümü (web) ve kitap sürümü (PDF/ePub) aynı kaynaktan türetilir — henüz otomasyon kurulmadı.
- Resmî yayın değildir.
- Değişiklik geçmişi repo üzerinden izlenebilir.
