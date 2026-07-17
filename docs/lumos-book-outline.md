# Lumos Referanslar 1 — Kurucu Kitap İskeleti

> **Yayın notu**
>
> - Bu belge taslak kurucu referanstır.
> - Henüz nihai kitap değildir.
> - **Tek kaynak:** GitHub'daki bu dosya yaşayan belgedir.
> - **Okuma ve kitap sürümleri** aynı kaynaktan üretilir; ayrı metin yönetilmez (bkz. Belge §10).
> - Web/kitap yayımlamadan önce **Belge §11 — Tamamlanmadan yayımlama** dört kontrolden geçer.

### Numaralandırma (iki sistem)

Bu belgede iki numara dizisi vardır; referans verirken karıştırılmamalıdır:

| Önek | Anlam | Kapsam |
|------|-------|--------|
| **Kitap §** | Kitabın bölüm iskeleti | Belge §3–§4 listesindeki 1–15 arası bölümler |
| **Belge §** | Bu referans dosyasının ana bölümleri | `## 1`–`## 14` arası başlıklar |

Örnek: **Kitap §7** = Panel dili; **Belge §7** = Kurucu hikâye notları. **Kitap §14** = Açık kaynak çekirdek; **Belge §14** = Lumos Academy vizyonu.

## 1. Kitabin calisma adi

**Lumos: Kontrol Kullanicida**

Alt calisma cumlesi: **Izinli, seffaf ve guvenilir yapay zeka yardimi icin bir urun dusuncesi.**

## 2. Ana fikir

Bu kitap, Lumos'u kontrolsuz otonom bir ajan olarak degil, kullanicinin kararini merkeze alan guvenilir bir yardimci ve kontrol katmani olarak anlatir.

Ana tez: Lumos kullanicinin niyetini anlamaya, daginik isleri parcalamaya, riskleri gorunur kilmaya ve uygulanabilir sonraki adimi onermeye calisir; kalici, hassas, dis etkili veya geri donusu zor adimlarda son karar kullanicidadir.

Kitap; urun felsefesi, karar sozlesmesi, panel dili, guvenlik/onay sinirlari, entegrasyon yaklasimi ve uzun vadeli arastirma alanlarini ayni hikayede toplar. Amac pazarlama metni degil; Lumos'un neden boyle davranmasi gerektigini aciklayan kurucu bir taslak omurga olusturmaktir.

### Onsoz icin niyet beyani

Bu kitap yalnızca ticari kazanç amacıyla değil, Lumos'un gelişimini ve toplumsal faydayı desteklemek amacıyla hazırlanmıştır. Lumos vizyonuyla uyumlu bir dernek veya vakıf yapısı oluştuğunda, aşağıdaki gelirlerin toplumsal fayda projelerine yönlendirilmesi hedeflenir:

- Kitap gelirleri.
- Eğitim gelirleri.
- Lisans gelirleri.
- Patent veya fikri mülkiyet gelirleri (oluşursa).
- Quantum güvenliği ve benzeri ileri araştırmalardan doğabilecek meşru ticari gelirler (oluşursa).

#### Değerin Geri Dönüş İlkesi

Lumos'tan doğan değerin yalnızca teknoloji üretmesi değil, insanlara geri dönmesi hedeflenir. Ticari sürdürülebilirlik sağlandıktan sonra oluşan fazla değerin önemli bir bölümünün eğitim, erişilebilirlik, bilimsel araştırma ve toplumsal fayda projelerini desteklemesi amaçlanır.

Bu ifade bugün hukuki bir taahhüt değil, niyet beyanıdır. Gelecekte kurulacak dernek, vakıf veya benzeri yapı tarafından resmîleştirilebilir. Kurucu ekip, Lumos'un sürdürülebilirliğini sağlayacak makul işletme giderlerini ayırabilir; kalan kaynakların büyük bölümünün toplumsal faydaya yönlendirilmesi hedeflenir.

### Kitabin uc katmani

1. **Hikaye:** Lumos fikrinin nasil dogdugu, hangi problemleri gordugu ve neden klasik bir yapay zeka kitabi olmayacagi.
2. **Ilkeler:** Karar sozlesmesi, guvenlik, karakter, kullanici kontrolu, gizlilik ve onay mantigi.
3. **Mimari:** Cekirdek, dal ajanlar, guvenlik katmanlari, entegrasyon sinirlari ve sistemin neden bu sekilde tasarlandigi.

## 3. Bolum listesi

### Katman 1 — Hikaye

1. Neden Lumos?
2. Lumos fikri hangi problemden dogdu?
3. Kullanici karari neden merkezde?

### Katman 2 — Ilkeler

4. Lumos'un karakteri
5. Tek yuz: kullanici Lumos ile konusur
6. Niyeti parcalamak ve isi baslatmak
7. Panel dili ve guven veren arayuz
8. Onay, yetki ve karar sozlesmesi
9. Gizlilik, audit ve veri sinirlari

### Katman 3 — Mimari

10. Cekirdek, dal ajanlar ve sozlesmeyle korunan kok
11. Entegrasyonlar: araclarin verisine saygi
12. Yerel calisma, cihazlar ve kopru mantigi
13. Quantum Readiness ve arastirma disiplini
14. Acik kaynak cekirdek ve ticari omurga
15. Yol haritasi: kontrollu gelisen Lumos

## 4. Her bolum icin kisa aciklama

### 1. Neden Lumos?

Lumos'un cikis problemini anlatir: yapay zekanin kullanici yerine karar veren gorunmez bir otoriteye donusmesi yerine, kullaniciya durum, risk ve secenek gosteren bir yardimci olmasi. Bu bolum urun vaadini sade bir dille kurar.

**Taslak acilis (Kitap metni — ana kaynak Belge §7):**

> Yalnizlik bana dusunmeyi ogretti. Suphe ise korku degil, dogrulamayi ogretti. Lumos bu ikisinin arasindaki dengeyi arayan bir fikirdi.

### 2. Lumos fikri hangi problemden dogdu?

Lumos'un sadece teknik bir arac olarak degil, kullanicinin yorgunlugunu, daginik is akisini, guvenlik kaygisini ve kontrol ihtiyacini ayni anda ele alan bir fikir olarak nasil dogdugunu anlatir. Bu bolum kitabin hikaye katmanini kurar.

### 3. Kullanici karari neden merkezde?

Kalici, hassas, maliyetli veya baskalarini etkileyen islemlerde son karar merciinin kullanici oldugunu aciklar. "Yardim" ile "yerine karar verme" arasindaki fark kitabin temel ekseni olarak yerlesir.

### 4. Lumos'un karakteri

Lumos'un guven veren ama manipule etmeyen, emin olmadiginda kesin konusmayan, once gozlemleyen sonra oneride bulunan karakterini tanimlar. Bu bolum karakterin uzun promptlarla degil; sozlesme, kod ve urun diliyle korundugunu anlatir. Uzun vadeli urun ifadesi (Companion) icin bkz. Belge §7 «Companion: karakter ve urun», Belge §13.

### 5. Tek yuz: kullanici Lumos ile konusur

Son kullanici deneyiminde gorunen dis yuzun Lumos oldugunu anlatir. Arka plandaki teknik veya operasyonel katmanlar kullaniciya marka karmasasi olarak tasinmaz; sonuc, soru ve onay Lumos diliyle gelir.

### 6. Niyeti parcalamak ve isi baslatmak

Uzun, daginik veya komut gibi yazilmamis isteklerin nasil uygulanabilir parcalara ayrilacagini aciklar. Net ve dusuk riskli istekte Lumos'un pasif kalmamasini; riskli veya belirsiz durumda ise durup net soru sormasini isler.

### 7. Panel dili ve guven veren arayuz

Panelin bir reklam veya tuketim yuzeyi degil, guvenli calisma ve kontrol alani oldugunu anlatir. Dil ilkesi: kisa ozet, ne anladim, ne yapacagiz, gerekirse tek kritik soru.

### 8. Onay, yetki ve karar sozlesmesi

Karar katmanlarini merkez bolum olarak aciklar: sadece cevap ver, analiz et, oner ama bekle, acik onayla uygula, asla dokunma. Kalici silme, dis yazma, kritik sistem ayari ve geri donussuz islemlerin neden otomatik yapilamayacagini anlatir.

### 9. Gizlilik, audit ve veri sinirlari

Kullanici verisinin urun malzemesi olmadigini; reklam, veri satisi ve gereksiz ariv mantigindan uzak durulmasi gerektigini aciklar. Audit'in amaci kullaniciyi izlemek degil, sistemin soz verdigi sinirlarda durdugunu kanitlamaktir.

### 10. Cekirdek, dal ajanlar ve sozlesmeyle korunan kok

Lumos'un yalnizca konusan bir arayuz degil, sozlesmeyle korunan bir cekirdek etrafinda buyuyen sistem olarak neden tasarlandigini anlatir. Dal ajanlarin kok olmadigini; kokun karakter, karar sozlesmesi, guvenlik ve audit ilkeleriyle korundugunu aciklar.

Sik tekrarlanan ve baglama gore uzmanlik isteyen islerde **tek odakli dal ajan** modeli kullanilir. Ornegin marka baglam ajani; yuzeyin anlamina gore logo bicimi, renk, boyut ve bosluk onerisi uretir. Bu ajan:

- Yalnizca kullanicidan veya Lumos Orkestrator'den gorev alir; baska bir ajandan emir kabul etmez.
- Ana marka geometrisini veya karar sozlesmesini degistiremez; yalnizca onayli kurallardan varyant onerir.
- Dosya yayini, dis paylasim veya kalici degisiklik yapmaz; sonucu tek merkez kontrol noktasina iletir.
- Karar, risk, uygulama durumu ve gerekceyi ana merkezdeki bildirim duvarina standart olay olarak birakir.
- Bildirim duvari icra makami degildir; kullaniciya ve Orkestrator'e gorunurluk saglar.

Akis: **Kullanici / Lumos Orkestrator -> tek odakli ajan -> merkez kontrol noktasi -> bildirim duvari -> onayli uygulama**. Bu desen, `Karşılıklı denetim, sıfır kontrol` ilkesini korur; ajanlar birbirini yonetmez.

### 11. Entegrasyonlar: araclarin verisine saygi

GitHub, Slack, Google, Gmail, Calendar gibi araclarin kendi verisinin sahibi oldugunu anlatir. Lumos yalnizca kullanici izni ve politika kapsaminda gerekli ozeti, metadata'yi veya eylemi isler; tam kopya, sessiz senkron veya onaysiz dis yazma varsayilan degildir.

### 12. Yerel calisma, cihazlar ve kopru mantigi

Lumos'un yerel calisma, panel, CLI, cihaz ve kopru baglamlarini nasil dusundugunu anlatir. Offline modda dis ag yoktur; online modda kimlik, kilit, consent ve onay zinciri devrededir.

### 13. Quantum Readiness ve arastirma disiplini

Kuantum alanini abartili "quantum powered" iddialarindan ayirir. Lumos Quantum Readiness'in yerel, salt okunur, kanitli bir hazirlik tarayicisi olarak konumlanmasini; arastirma ile urun iddiasi arasindaki siniri anlatir.

### 14. Acik kaynak cekirdek ve ticari omurga

Public Lumos cekirdegi ile ticari guven/politika katmaninin ayrimini anlatir. Acik kaynak repo demo-safe foundation tasir; production credential, faturalama, kurumsal orkestrasyon ve operasyonel backend ayridir.

### 15. Yol haritasi: kontrollu gelisen Lumos

Lumos'un tek hamlede her seyi yapan bir sistem degil, kontrollu gelisen bir panel ve yardimci oldugunu anlatir. Faz A gorev/plan omurgasindan baslayarak entegrasyon, cihaz, mobil onay, quantum readiness ve daha ileri arastirma alanlarina nasil genisleyebilecegini toparlar.

## 5. Toplanacak kaynak notlari

- `README.md`: Lumos'un genel vaadi, prensipleri, mevcut durum ve modul listesi.
- `docs/PRODUCT_SUMMARY.md`: erken faz, ne yapar/ne yapmaz, kontrollu gelisen panel fikri.
- `docs/lumos-urun-vizyon-ve-arastirma-cercevesi.md`: urun karakteri, sessiz arastirma siniri, yuzeye cikarma kriterleri.
- `docs/lumos-kullanici-akisi.md`: tek yuz ilkesi, normal sohbet, panodaki metni iletme ve gorev detayindan iletme akislari.
- `docs/lumos-persona-layers.md`: kullaniciya gorunmeyen ic katmanlar ve tek dis gecit prensibi.
- `docs/lumos-karar-sozlesmesi.md`: karar katmanlari, dokunulmaz cekirdek alanlar, acik onay ve asla otomatik yapilmayan isler.
- `docs/lumos-karar-motoru.md`: basit/orta/urunsel is siniflandirmasi, risk ve hazir cozum akisi.
- `docs/lumos-uzun-istek-isleme.md`: uzun istegi ayrisitirma, parcalama, kritik soru stratejisi.
- `docs/lumos-konusmadan-gorev-cikarma.md`: acik komut yokken is sinyali yakalama ve guvenli baslatma.
- `docs/lumos-panel-dili-rehberi.md`: panel dili, cevap sirasi, sade Turkce ve guven veren ton.
- `docs/security-architecture.md`: onay, trash, offline, secret ve public repo guvenlik sinirlari.
- `docs/analysis/lumos-privacy-manifesto-draft.md`: veri satisi yok, reklam yok, audit/gizlilik dengesi.
- `docs/integrations-overview.md`: entegrasyon yuzeyleri, read/write/delete izin modeli, OSS/private ayrimi.
- `docs/analysis/welockai-charter-draft.md`: Lumos ile ticari omurga arasindaki rol ayrimi.
- `docs/analysis/welockai-trust-model-draft.md`: rol, yetki, onay zinciri ve trust boundary notlari.
- `docs/analysis/lumos-approved-naming-registry.md`: onayli isimler, roller, yuzeyler ve demo-safe adlandirma.
- `docs/ARCHITECTURE.md` ve `docs/ARCHITECTURE_MAP.md`: teknik omurga, karar/pipeline, workspace ve panel kontratlari.
- `docs/decisions/ADR-013-lumos-quantum-security-readiness.md`: Quantum Readiness tanimi, kapsam disi iddialar ve rapor alanlari.
- `docs/analysis/lumos-quantum-first-companion.md`: Qiskit/Aer'in arastirma onceligi ve otomatik baglanti olmadigi siniri.

Kaynak notlari toplanirken dikkat: kitabin kullaniciya donuk ana metninde Lumos dis yuz olarak kalmali; ic teknik katman adlari gerekiyorsa kaynak notu veya mimari dipnot seviyesinde tutulmali.

## 6. Henuz belirsiz kalan sorular

- Kitap bir public manifesto mu, ic urun kitabi mi, yoksa gelistirici rehberiyle karisik bir kurucu metin mi olacak?
- Birincil hedef kitle kim: son kullanici, gelistirici, yatirimci/partner, kurumsal musteri, yoksa ekip ici karar okuyucusu mu?
- Dil yalnizca Turkce mi olacak, yoksa Turkce ana metin + Ingilizce ozet/terim sozlugu mu hazirlanacak?
- WeLockAI ticari omurgasi kitapta ne kadar gorunur olacak; hangi bolumlerde yalnizca arka plan siniri olarak kalacak? → **Referans yayininda cozuldu (Belge §10):** WeLockAI yayınci/on planda; kitap icinde Lumos urun sesi agirlikta, WeLockAI ticari omurga **Kitap §14** ve dipnotlarda.
- Teknik detay derinligi ne olacak: kod/pipeline anlatimi mi, yoksa urun ilkeleri ve ornek senaryolar mi agirlikta olacak?
- Quantum Readiness bolumu arastirma disiplini olarak mi kalacak, yoksa ayri bir gelecek vizyonu bolumu mu olacak?
- Gizlilik ve audit iddialari icin hukuki/uyum kontrolu gerekecek mi?
- Bolumlerde gercek kullanici senaryolari, panel ekranlari veya vaka calismalari kullanilacak mi?
- Kitap kisa bir "founder letter + ilkeler" metni mi, yoksa uzun soluklu bolumlu kitap mi olacak?
- Son baslik "Lumos: Kontrol Kullanicida" olarak mi kalacak, yoksa daha sicak/insani bir calisma adina mi evrilecek?
- **Lansman / yayın tarihi:** Belge §10 «Lansman türleri» — Life ve ticari için **TBD**; referans web/PDF Belge §11 sonrası; dış kamu AI haberleri Lumos takvimi değildir.

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
- **Yayımlama kalite kapısı** (dört kontrol, «tamamlanmadan yayımlama») → **Belge §11**; bu bölüm yalnızca referans verir.
- **Kurucu pusula ve vizyon dalları** → Belge §8, §13.
- **Ticari aşama planı** (Alpha / Beta / Commercial giriş kriterleri) → `docs/analysis/pre-commercial-release-plan.md`.
- **Otomasyon / CI / build pipeline** — henüz kurulmadı; bu belge hedef mimariyi tanımlar, uygulama taahhüdü değildir.
- **Takvim taahhüdü** — TBD; ayrı yazılı karar + onay olmadan eklenmez (Belge §11).

### 4. V1 / yakın gelecek / uzun vadeli

| Dönem | Ne | Durum |
|-------|-----|--------|
| **Şimdi (V1 / erken faz)** | GitHub kaynak (`docs/lumos-book-outline.md`); taslak; diff açık | ✅ Yaşayan belge |
| **Yakın gelecek** | Referans 1 web okuma sürümü; §11 dört kontrol; basit GitHub Pages veya welockai.com/referanslar/1 | 🟢 planlı — otomasyon TBD |
| **Yakın gelecek** | PDF/ePub aynı kaynaktan türetim (tek omurga) | 🟢 planlı |
| **Yakın gelecek** | Referans 2–5 ayrı iskeletler; kütüphane indeksi | planlı |
| **Uzun vadeli** | Tam referans kütüphanesi; çoklu dil; otomatik üç yüz pipeline | ⚪ |

**Not:** Panel v1 kapanışı (**2026-06-12**) iç mühendislik kapısıdır; referans web yayını değildir.

### 5. Diğer bölümlerle bağlantısı

| Bölüm | Bağlantı |
|-------|----------|
| **Belge §11** | Web/PDF/indeks «yayımlandı» sayılmadan önce dört kontrol |
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

Web ve kitap sürümüne çıkmadan önce Belge §11 dört kontrolden geçilir; GitHub'daki taslak kaynak yaşayan belge olabilir ancak «okuma sürümü» olarak sunulmaz.

### Lansman türleri (karıştırma notu) {#lansman-türleri-karıştırma-notu}

Bu belgede **«lansman»** tek anlama gelmez. Dış haberler (ör. başka ülkelerin kamu AI projeleri) Lumos lansmanı **değildir**.

| Tür | Ne | Tarih (repo) | Ana kaynak |
|-----|-----|--------------|------------|
| **Referans yayını** | Kurucu kitap / Referanslar web veya PDF | **TBD** — Belge §11 onayı sonrası | Belge §10 |
| **Life lansmanı** | Erişilebilirlik omurgası; 🟢🟡 özellik tanıtımı | **TBD** — taahhüt tarihi yok | Belge §12 |
| **Ticari lansman** | Open Beta → Commercial Launch | **TBD** — Pre-Alpha; `docs/analysis/pre-commercial-release-plan.md` | Repo plan belgeleri |
| **İç mühendislik kapısı** | Panel v1 kapanışı | **2026-06-12** (`LUMOS_V1_READINESS.md`) | Halka lansman değil |

**Kural:** Belge §11 — yarım düşünceyi tamamlanmış gibi sunma; **takvim taahhüdü** yalnızca ayrı yazılı karar + onay ile eklenir.

## 11. Yayımlama ilkesi: Tamamlanmadan yayımlama

**İlke:** Tamamlanmadan yayımlama.

Her yeni belge, referans veya mimari karar — web okuma sürümü, PDF/ePub veya «Referanslar» kütüphanesinde okuyucuya açılan sürüm — yayımlanmadan önce şu **dört kontrolden** geçer:

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

**Amaç:** Kusursuzluk değil; **yarım kalmış düşünceleri tamamlanmış gibi sunmamaktır.**

| Sürüm | Bu ilkeye tabi mi? |
|-------|-------------------|
| GitHub kaynak (taslak, diff açık) | Hayır — yaşayan belge olabilir; durum etiketi gerekir |
| Web okuma sürümü | Evet |
| PDF / ePub | Evet |
| Referans Kütüphanesi indeksinde «yayımlandı» | Evet |

**Referans:** `docs/lumos-karar-sozlesmesi.md` (cevap disiplini, emin değil); Belge §6 belirsiz sorular (açık işaretleme).

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
| ⚛️ **Lumos Quantum** | Qubit deneyleri; devre sürükle-bırak; sonuç görselleştirme | ADR-013 / Quantum Readiness ile hizalı araştırma sınırı |
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

Academy görselleri veya örnek diyalogları tek başına «mevcut özellik» algısı yaratmaz; tüm maddeler **⚪** ile geçer; ana lansman Belge §12 omurgasındadır. Web okuma sürümü veya kitap yayımlanmadan önce Belge §11 dört kontrolden geçer.

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
> **Durum etiketi:** ⚪ Araştırma / uzun vadeli · **Ana omurga:** Belge §12 · **Yayımlama:** Belge §11 dört kontrol
>
> Bu kutudaki hiçbir ifade ürün vaadi, tarih taahhüdü veya «yakında geliyor» iddiası değildir.

⸻

## Paylaşım notu

- GitHub linki üzerinden kaynak metin okunabilir ve incelenebilir.
- Okuma sürümü (web) ve kitap sürümü (PDF/ePub) aynı kaynaktan türetilir — henüz otomasyon kurulmadı.
- Resmî yayın değildir.
- Değişiklik geçmişi repo üzerinden izlenebilir.
