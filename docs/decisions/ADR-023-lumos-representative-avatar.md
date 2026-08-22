# ADR-023 — Lumos Representative: Yetkilendirilmiş Dijital Temsilci

> Kapsam notu (2026-08-11): Bu belge, kurucunun 2026-08-11 tarihli yönlendirmesini
> ("yan proje değil, Lumos'un gerçek ürün modülü") kayda geçirir. Aynı gün kurucu
> üç açık soruyu cevaplayıp çekirdek kabul ölçütünü sabitledi (bkz. §Kurucu
> kararları) ve ADR Accepted'a çekildi. Henüz hiçbir kod yazılmamıştır.

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (2026-08-11)** — kurucu onayı; üç açık sorunun cevabı ve çekirdek kabul ölçütüyle (bkz. §Kurucu kararları) |
| Uygulama durumu | **Faz 0 (Tercüman Modu) uygulanmış durumda** — `src/representative/` main'de (13 kaynak, 11 `test_representative_*` testi); uygulama dilimleri #735, #737, #740, #741, #743, #744. Temsil/beyan kararı ayrıca #779. Canlı insan testleri yapıldı (#746). **Faz 0 çıkış kapısı henüz geçilmedi**; kabul kriterleri tamamlanmadı. Faz 1 ve Faz 2 devreye alınmadı. Meet avatar görsel dilimi ertelendi; #780 kapatıldı, merge edilmedi. |
| Üst ilişki | [ADR-022](ADR-022-meta-write-authority-domains.md) AuthorityDomain modeli konuşma yetkisine genişletilir; [ADR-007](ADR-007-trust-engine-layer.md) Trust, [ADR-006](ADR-006-ai-firewall-guard-layer.md) Firewall sınırları geçerli; [ADR-008](ADR-008-agent-network-boundary.md) ile ilişki §Sınırlar'da |
| Kapsam | Lumos'un, kurucu adına toplantılara katılan, çeviren, brifing dahilinde konuşan ve her şeyi denetim kaydına yazan temsilci modülü |

## Kurucu yönlendirmesi (2026-08-11)

> "Avatar" sadece ekranda yüzle konuşan video karakteri olmayacak; Candaş'ın
> yetkilendirilmiş dijital temsilcisi olacak. Toplantıya katılacak, karşı tarafı
> anlayacak, Türkçe↔İngilizce çevirecek, Lumos bağlamını bilecek, senin adına
> konuşurken sınırlarını bilecek, toplantı sonunda transcript/karar/aksiyon
> çıkaracak. İlk hedef: bir sonraki yabancı toplantıda Candaş Türkçe konuşacak,
> karşı taraf doğal İngilizce iletişim kuracak.

Kurucu ayrıca dürüstlük sınırını kendisi koydu: her platformda "senmiş gibi
sınırsız işlem yapan" tam otonom sistem bugün teknik ve platform/kimlik kuralları
nedeniyle garanti edilemez; kimlik doğrulama, biyometri, sözleşme/onay, finansal
işlem insan onayı gerektirir. Bu ADR bu sınırı saklamaz, modele gömer.

## Kurucu kararları (2026-08-11 — taslağı Accepted'a çeken cevaplar)

1. **İsim**: Ana ad **Lumos Representative** (ürün/modül adı). **Avatar**,
   sistemin adı değil, ileriye dönük görsel/bedensel sunum katmanının adıdır:
   **Representative Avatar** (yüz/ses/karakter katmanı, ayrı karar). Böylece
   "avatar" sistemi yüz filtresine indirgemez. İsim kaydı Lumos repo
   `docs/canonical/decisions.md` marka bölümüne patch'lenecek (takip işi).
2. **İlk platform**: **Google Meet.** Gerekçe: gerçek acı bugün burada yaşandı,
   canlı kullanım senaryosu elde. Faz 0 tek platform hedefler; Zoom/Teams
   sonraki dilimler.
3. **v0 sesi**: Nötr, profesyonel, sakin, **erkek** ses. Ne robotik ne
   tiyatral; hızlı ama aceleci değil. İlk sürümde kurucunun sesi
   KLONLANMAZ — ifşa çizgisi böyle daha temiz; ses klonu ayrı karardır.
4. **Faz 0 başarı ölçütü sabitlendi**: Ölçüt "avatar güzel göründü" DEĞİL,
   "toplantıda dil bariyerini gerçekten ortadan kaldırdı mı?"dır. Çekirdek
   kabul kriterleri §Kod öncesi 5 soru / madde 5'te bu ölçüte göre yazılmıştır.

## Tez: Identity ≠ Authority'nin canlı ürünü

Temsilci, kurucunun **kimliğini temsil eder** ama kurucunun **yetkilerine
otomatik sahip olmaz**. Bu, Lumos'un Identity ≠ Authority tezinin ilk
kullanıcıya görünür ürünleşmesidir:

- **Kimlik temsili**: "Ben Lumos, Candaş Öz'ün yetkili temsilcisiyim" — açık
  beyan. Temsilci hiçbir zaman insan gibi davranmaz, kendini gizlemez
  (ifşa ilkesi, aşağıda).
- **Yetki**: ADR-022'deki AuthorityDomain deseni konuşma eylemlerine genişler.
  Alan bir kez tanımlanır, içinde otonom; alan dışı her şey eskalasyon.

### Konuşma yetki sınıfları (öneri — kurucu onayı gerekir)

| Sınıf | Tanım | Onay modeli |
|-------|-------|-------------|
| **T — Tercüme** | Kurucunun/karşı tarafın sözünü çevirmek; içerik üretmez, aktarır | Alan içinde tam otonom |
| **A — Anlatım** | Lumos'u/şirketi onaylı brifing kapsamında anlatmak, bilgi sorusu cevaplamak | Brifing = alan sınırı; içinde otonom |
| **E — Eskalasyon zorunlu** | Para, fiyat, hukuki taahhüt, ortaklık/şart kabulü, takvim taahhüdü, gizli bilgi paylaşımı | Asla otonom değil; "Bunu Candaş'a götürüyorum" der, kurucuya iletir |

- Kill-switch ADR-022 ile aynı ilkededir ve yetkinin ÜSTÜNDEDİR: tek komutla
  temsilci toplantıdan çıkar, tüm alanlar askıya alınır.
- E sınıfı, kurucunun koyduğu dürüstlük sınırının modeldeki karşılığıdır;
  hiçbir alan tanımı E sınıfını A'ya indiremez.

## Temsil yetki sınırı (Representative authority boundary)

**Karar tarihi:** 2026-08-20 · **Kaynak:** #779 kapı onayı, merge `884fe1e`

**Capability implementation does not imply authority grant.**
Bir yeteneğin kodda çalışıyor olması, o yetkinin verildiği anlamına gelmez.

"Representative" bu üründe **toplantıya katılım ve iletişim rolünü** ifade eder.
Şunları **vermez**:

| Vermediği yetki |
| --- |
| Karar verme |
| Fiyat / para taahhüdü |
| Hukuki temsil |
| Ortaklık veya şart kabulü |
| Takvim taahhüdü |
| Gizli bilgiyi açıklama |

Bu liste yukarıdaki **E — Eskalasyon zorunlu** sınıfıyla aynı kapsamdır:
E asla otonom değildir.

### Bugünkü durum

| Sınıf | Durum |
| --- | --- |
| **T — Tercüme** | **Uygulanmış sınır.** Bugün fiilen yürürlükte |
| **A — Anlatım** | Genişletme; ayrı insan kararı ister |
| **E — Eskalasyon** | Tanımlı; otonom yetki vermez |

**T/A/E tablosu "öneri — kurucu onayı gerekir" statüsünden otomatik çıkmış
sayılmaz.** Bu bölümün eklenmesi o tabloyu onaylamaz; yalnız bugün uygulanan
sınırı kalıcılaştırır.

### İfşa metninin rolü

#779'daki sesli beyan bu sınırı **ifade eder**; sınırı **genişletmez**. Metnin
"authorized AI representative" demesi, yukarıdaki yetkilerin verildiği anlamına
gelmez — cümle aynı nefeste rolü daraltır: *"I will interpret in this meeting."*

Disclosure metni değişirse yetki değişmez; yetki ancak **açık insan kararı ve
ilgili yönetişim kaydının güncellenmesiyle** değişir.

### Uygulanmış örnek

#780 (Meet avatarı) teknik olarak çalışır durumdaydı — testleri yeşil, güvenlik
incelemesi temiz. **Yine de kapatıldı**, çünkü görsel katman kapsam kararı
verilmemişti. Yetenek ≠ yetki ilkesinin ilk somut uygulaması budur.

## İfşa ilkesi (pazarlıksız)

1. Temsilci her toplantıya kendini tanıtarak girer: yapay zekâ olduğu, kimi
   temsil ettiği, kaydın/transcriptin tutulduğu açıkça söylenir.
2. Kayıt bildirimi platform kurallarının da gereğidir (Zoom/Meet/Teams bot ve
   kayıt bildirimleri); ürün bunun üstüne çıkar, altına inmez.
3. **Ses klonlama v0 kapsamı DIŞIdır** ve varsayılan kapalıdır; açılması ayrı
   kurucu kararı + karşı tarafa ifşa gerektirir. v0 nötr, kaliteli bir TTS
   sesi kullanır. Bu madde **değişmedi**.

   **Görsel katman — 2026-08-22 kurucu kararıyla AÇILDI (sınırlı).**

   | | Durum |
   |---|-------|
   | **Soyut görsel gösterge** (idle / speaking, kamera değil) | ✅ **Açık** |
   | **İnsan yüzü / gerçekçi avatar** | ❌ Kapalı — ayrı kurucu kararı gerektirir |
   | **Ses klonlama** | ❌ Kapalı — yukarıdaki madde aynen geçerli |

   Açılan şey bir **yüz** değil: sabit iki durumlu soyut ışık göstergesi. İnsan
   varlığını taklit etmez, bu yüzden "AI olduğunu gizleme" ilkesiyle çelişmez.
   Gerçekçi yüz veya kamera görüntüsü hâlâ kapsam dışıdır.

   Madde 3'ün **ifşa şartı korunmuştur ve karşılanmıştır**: beyan metni
   görüntünün üretilmiş bir gösterge olduğunu, kamera olmadığını söyler
   (bkz. §İfşa metni). İfşa olmadan görsel katman açılmaz.

## Faz planı

| Faz | Ad | Kurucu toplantıda mı? | Yetki | Çıkış kapısı |
|-----|----|----------------------|-------|--------------|
| **0** | Tercüman Modu | Evet, konuşan taraf | Yalnız T | Kabul kriterleri (aşağıda) gerçek toplantı öncesi iç testte geçer |
| **1** | Brifingli anlatıcı | Evet, izleyici/müdahale edebilir | T + A | Faz 0 sahada en az 2 gerçek toplantıda sorunsuz; brifing formatı tanımlı |
| **2** | Sınırlı otonom temsilci | Hayır (sonradan rapor alır) | T + A + E-eskalasyon | Faz 1'de eskalasyon mekanizması gerçek vakada test edilmiş; kurucu ayrı Accepted kararı |

**İlk hedef (kurucu, 2026-08-11): Faz 0.** Bir sonraki yabancı toplantıda
kurucu Türkçe konuşur, karşı taraf doğal İngilizce duyar; karşı tarafın
İngilizcesi kurucuya Türkçe aktarılır. Bu fazda yetki sorusu neredeyse yoktur
(temsilci içerik üretmez) — riskin en düşük, değerin en yüksek olduğu dilim.

## Mimari iskelet (Faz 0)

```
Toplantı platformu (Meet/Zoom/Teams)
        │  bot-katılımcı (toplantı linkiyle katılır)
        ▼
Meeting Ingress  ──►  STT (akış, TR+EN tanıma)
                          │
                          ▼
                  Çeviri katmanı (LLM, Lumos bağlam sözlüğüyle:
                  ürün adları, marka hiyerarşisi, teknik terimler;
                  düşük-güven cümleler işaretlenir, sessizce geçilmez)
                          │
                          ▼
                  TTS (akış, doğal EN/TR ses)  ──►  toplantıya ses çıkışı
                          │
                          ▼
              Append-only kayıt: iki dilli transcript
              → toplantı sonrası özet / karar / aksiyon çıkarımı
```

- **Ardıl çeviri (consecutive)** hedeflenir: konuşmacı durur, çeviri konuşulur.
  Eşzamanlı (simultane) çeviri Faz 0 hedefi DEĞİLDİR; gecikme ve üst üste
  konuşma problemleri kanıtlanmadan vadedilmez.
- **İlk platform Google Meet'tir** (kurucu kararı, 2026-08-11). Toplantıya
  giriş için Meet tarafında resmî API (Meet Media API — erişimi
  kısıtlı/önizleme olabilir, doğrulanmadan varsayılmaz) ile hazır
  bot-altyapı sağlayıcısı karşılaştırılır; seçim ayrı teknik dilimdir, bu
  ADR sağlayıcı kilitlemez. Zoom/Teams sonraki dilimlerdir.
- Barındırma: hosted varsayılan (2026-07-25 hosted-vs-local kararı, Seçenek C
  ile tutarlı); ses işleme hattı bulutta koşar.

## Kod öncesi 5 soru

1. **Giriş noktası**: Kullanıcı tarafı tek arayüz kuralına uyar — Lumos chat'e
   toplantı linki verilir ("bu toplantıya tercüman olarak katıl"); ileride
   takvim entegrasyonu. Teknik giriş: panel/çekirdekten AYRI bir
   meeting-service (kendi süreç/deploy'u); panel yalnız durum ve transcript
   gösterir.
2. **Dev/test/prod ayrımı**: dev = kendi iki hesabımız arasında test
   toplantısı; test = iç katılımcılarla prova toplantısı (kabul kriterleri
   burada ölçülür); prod = gerçek dış toplantı, yalnız kabul kriterleri
   geçtikten sonra.
3. **Local/cloud/CI akışı**: servis cloud-hosted; CI'da ses hattı uçtan uca
   koşmaz (gerçek toplantı gerektirir) — birim testler çeviri/transcript
   katmanını kayıtlı ses örnekleriyle test eder; uçtan uca doğrulama manuel
   prova toplantısıdır ve sonucu belgeye işlenir.
4. **Geçiş planı**: Faz kapıları yukarıdaki tabloda; her faz ayrı kurucu
   onayı. Faz 0 hiçbir mevcut modülü değiştirmez (yeni, izole servis) —
   geri dönüş = servisi kapatmak.
5. **Kabul kriterleri (Faz 0)** — başarı ölçütü kurucu tarafından sabitlendi:
   "avatar güzel göründü" değil, **"toplantıda dil bariyerini gerçekten ortadan
   kaldırdı mı?"**. Çekirdek kriterler (kurucu, 2026-08-11):
   - TR → EN ardıl konuşma doğal ve anlaşılır.
   - EN → TR geri çeviri güvenilir.
   - Kritik düşük-güvenli cümlede uyarı: çeviri katmanı bir cümleden emin
     değilse, kendinden emin yanlış çeviri yerine bunu açıkça işaretler
     (kurucuya işaret + transcript'te düşük-güven etiketi).
   - İki dilli transcript üretilir.
   - Kill-switch: tek komutla bot toplantıdan çıkar, kanıtla gösterilir.
   - Temsilci kimliği açık: girişte kendini tanıtır (§İfşa ilkesi).
   - Para/hukuk/taahhüt alanında otomatik konuşma yok (E sınıfı asla otonom
     değil — Faz 0'da temsilci zaten içerik üretmez, bu kriter bunu test eder).

   Ölçülebilir işletme eşikleri (çekirdek kriterlerin ölçüm aracı, amaç değil):
   30 dakikalık prova toplantısı kesintisiz; söz bitişi → çeviri sesi medyan
   ≤ 3 sn; Lumos terimleri (ürün/marka adları) sözlükten doğru — prova kaydı
   üzerinden kurucu spot-check onayı.

## Sınırlar ve ilişkiler

- **ADR-008 (Lumos Board)**: Temsilci, ajan ağına bağlı DEĞİLDİR; tek başına,
  yıldız topolojide kurucuya bağlı çalışır. Board entegrasyonu ancak ADR-008
  ön koşulları kapandığında ayrı karardır.
- **Tek arayüz kuralı**: Son kullanıcı/karşı taraf hiçbir dev aracı, port, log
  görmez; hata durumunda temsilci toplantıda düz dille durumu söyler
  ("bağlantı sorunu yaşıyorum, bir dakika") ve kurucuya bildirir.
- **Gözlemlenebilirlik**: Beta öncesi Sentry vb. bağlanmadan (mevcut açık
  konu) Faz 2'ye geçilmez; Faz 0-1 kurucu gözetiminde olduğu için bu koşulu
  beklemez.

## Açık sorular

Taslaktaki üç açık soru (isim, ilk platform, v0 sesi) 2026-08-11'de kurucu
tarafından cevaplandı — bkz. §Kurucu kararları. Kalan takip işleri:

1. **Marka kaydı patch'i**: "Lumos Representative / Representative Avatar"
   isim kararının Lumos repo `docs/canonical/decisions.md` marka bölümüne
   işlenmesi (henüz yapılmadı).
2. **Meet giriş yolu seçimi**: Resmî API vs bot-altyapı sağlayıcısı —
   Faz 0'ın ilk teknik dilimi; kanıt toplanmadan karar yazılmayacak.
3. **STT veri sınırı (2026-08-19, kilitlendi)**: gerçek Meet sesi için
   OpenAI batch transcription sözleşmesi
   [`stt-data-boundary-v1`](../contracts/stt-data-boundary-v1.md) /
   [ADR-025](ADR-025-stt-openai-data-boundary.md). Açılış kapısı yazılı
   MAM/ZDR + Avrupa işleme onayına bağlıdır; bu maddenin kendisi artık
   açık soru değildir.
