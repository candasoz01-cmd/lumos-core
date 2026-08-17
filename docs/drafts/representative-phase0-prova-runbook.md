# Representative Faz 0 — Kapalı Prova Runbook (Aşama C)

> Kapsam notu (2026-08-14): Yerel TR↔EN tercüme diliminin "done" kriterini
> kapatacak 10-15 dakikalık kapalı prova prosedürü. Kurucu katılımı gerekir
> (mikrofona konuşacak kişi). Gerçek dış muhatap YOK; toplantı platformu YOK.

## Ön koşullar

1. `pip install -e '.[representative]'` (bu makinede kurulu — 2026-08-14).
2. `OPENAI_API_KEY` ortam değişkeni (kurucu terminalde export eder;
   repoya/chat'e girmez). Anahtar yoksa prova `--translator mock` ile yalnız
   STT+gecikme ölçer, çeviri kalitesi ölçülmez — bunu "done" sayma.
3. Sessiz oda; dahili hoparlör + dahili mikrofon (echo testi kasıtlı olarak
   harici kulaklıksız yapılır).
4. İlk çalıştırmada macOS mikrofon izni sorar — terminal uygulamasına izin ver.

## Ölçülmüş ön veriler (2026-08-14, sentetik seslerle — insan sesi değil)

| Model | Isınmış STT süresi | Doğruluk (3 cümle) |
|-------|--------------------|---------------------|
| tiny | 0.31–0.45 sn | RED — "imzalayacağız" bozuldu, marka adı bozuldu |
| base | 0.58–0.78 sn | RED — **özne kayması**: "imzalayacağız" → "imza alayacağınız" (E-sınıfı ihlal riski) |
| small | 1.80–2.23 sn | Kabul — S1 birebir; terim istemi olmadan marka adı bozuk |
| **small + LUMOS_TERMS_PROMPT** | 1.88–2.28 sn | **SEÇİLDİ** — taahhüt cümlesi anlamca doğru ("50 bin dolara imzalayacağız… bir ekimde"), "Lumos temsilcisi" doğru; kalan tek hata "katılıp→katılık" |

Karar (teknik sorumlu, veriyle): rig varsayılanı **small + terim istemi**.
tiny/base, E-sınıfı anlam kayması kanıtı nedeniyle reddedildi. Gecikme riski:
STT ~2 sn + LLM çeviri → ≤3 sn medyan sınırda; prova ölçecek, gerekirse
iyileştirme sırası: kısa söz segmentleri (segmenter ayarı) → beam_size →
akışlı transkripsiyon. Hedef hâlâ hedef, iddia değil.

## Stres testi 1 bulguları (2026-08-14 — veri yakalanamadı, düzenek dersleri)

İlk kapalı prova denemesi kaos/stres testine dönüştü: rig, ajan oturumunun
arka plan süreci olarak koşarken oturum geçişinde öldü ve HİÇBİR söz
yakalanmadı. Üç zafiyet bulundu ve kapatıldı:

1. **Yaşam döngüsü**: Rig ajan oturumuna bağlı süreç olarak KOŞULMAZ —
   `nohup ... &` ile bağımsız başlatılır (aşağıdaki komutlar güncellendi).
2. **Veri kaybı**: JSONL yalnız temiz çıkışta yazılıyordu → artık her söz
   anında append edilir (`BilingualTranscript.append_jsonl`); çökme o ana
   kadarki veriyi kaybettirmez.
3. **Ölçüm hatası**: `speech_end_ts` STT'den sonra damgalanıyordu → kayıtlı
   gecikme STT süresini (~2 sn) ve endpointing beklemesini (0.7 sn)
   DIŞLIYORDU. Düzeltildi: damga, segmenter söz-sonu anına çekildi; bundan
   önceki tüm gecikme sayıları eksik sayımdır, kıyaslanamaz.

## Sabit prova metni (test 2 — kaynak metin sabit, karşılaştırma birebir)

Kurucu sırayla okur (doğal tempo, cümle arasında ~1 sn dur):

1. Merhaba, ben Candaş. Bugün Lumos projesini konuşmak istiyorum.
2. ChatLumos, kullanıcının tüm yapay zekâ araçlarını tek yerden yönetmesini sağlar.
3. Sözleşmeyi elli bin dolara imzalayacağız ve teslimat bir Ekim'de olacak. *(E-sınıfı)*
4. Ödemenin yüzde kırkı peşin, kalanı teslimatta ödenecek. *(E-sınıfı)*
5. Hukuki sorumluluğu We Lock AI olarak biz üstleniyoruz. *(E-sınıfı + marka)*
6. Toplantı notlarını yarın sabah size göndereceğim.
7. *(bilerek mırıldan / yarım bırak — düşük güven işareti düşmeli)*
8. Teklifi kabul ederseniz gelecek hafta başlayabiliriz.

Değerlendirme: satır satır "söylenen → duyulan (STT) → çeviri (EN) → işaret"
tablosu; E-sınıfı satırlarda rakam/tarih/özne birebir kontrol.

## Prova akışı (kurucu + ben)

1. **TR→EN (5-7 dk)** — bağımsız süreç olarak (stres testi 1 dersi):
   `nohup env PYTHONUNBUFFERED=1 PYTHONPATH=src .venv/bin/python -m representative.local_rig --audio --translator openai --jsonl-out prova_tr_en.jsonl > prova_tr_en.log 2>&1 & echo $! > prova.pid`
   Bitirme: `kill -INT $(cat prova.pid)` (temiz kapanış: transcript + jsonl).
   Kurucu doğal tempoda Türkçe konuşur; aralarda şu zorunlu vakalar:
   - E-sınıfı cümle: para + tarih + taahhüt içeren en az 3 cümle
     (ör. "Sözleşmeyi elli bin dolara imzalayacağız, teslimat bir Ekim'de.")
   - Marka terimleri: Lumos, ChatLumos, We Lock AI geçen cümleler
   - Bilerek mırıldanan/yarım bir cümle → düşük güven işareti düşmeli
2. **EN→TR (3-5 dk):**
   `... --audio --source-lang en --target-lang tr --voice Yelda --translator openai --jsonl-out prova_en_tr.jsonl`
3. **Echo/feedback testi (T7, donanımlı):** TR→EN modunda TTS konuşurken
   kurucu SUSAR — hoparlör sesi mikrofona döner. Beklenen: hiçbir "duyulan"
   satırı TTS çıktısından türememeli (half-duplex kapı). Sonra TTS
   konuşurken kurucu KONUŞUR — beklenen: o söz düşer (bilinen half-duplex
   ödünü; kayda geçir, kabul edilebilirliğini kurucu değerlendirir).
4. **Kill-switch (rig düzeyi):** Ctrl+C → rig transcript'i basıp temiz çıkar.
   (Bot düzeyi kill-switch Recall diliminde.)

## Test 3 sonuçları (2026-08-14 — sabit metin, ilk GERÇEK veri)

Düzenek bu kez çalıştı: 16 kayıt, echo döngüsü YOK (TTS çıktısının yeniden
duyulduğu satır yok), halüsinasyon spam'i YOK, çökme-güvenli kayıt tam.
Kalibrasyon ilk denemede gürültü zirvesiyle eşiği 14765'e itti (rig
sağırlaştı, 0 algı) → medyan+tavan düzeltmesiyle ikinci denemede 500.

**Ölçümler:** medyan 3.49 sn | p90 5.79 sn | max 7.19 sn → **≤3 sn hedefi
GEÇİLEMEDİ** (gerçek, düzeltilmiş ölçümle).

**Satır değerlendirmesi (özet):**
| Senaryo satırı | Sonuç |
|---|---|
| 1 Merhaba, ben Candaş… | ✓ STT birebir, çeviri doğru |
| 2 ChatLumos… | ~ küçük STT bozulmaları, anlam korundu |
| 3 elli bin dolar + 1 Ekim | **✗ E-sınıfı:** 50.000 ✓ ama cümle ortadan bölündü; "Ekim" ayı "ekime kadar / planting" oldu — tarih KAYBOLDU |
| 4 yüzde kırk peşin | **✗ E-sınıfı:** %40 → %45 duyuldu (rakam hatası), "peşin" kayboldu |
| 5 We Lock AI | **✗ marka:** "viluk" duyuldu; hukuki özne bozuldu |
| 6, 8 | kayıtlarda yok (okunmadı/algılanmadı) |
| 7 mırıltı | ✗ işaretlenmedi — "Zatçı Hürriyav" akıcı ama uydurma çevrildi ("I am free to sell"); açılıştaki ilk mırıltı ise doğru işaretlendi |
| Çevirmen meta-cevabı | ✗ bir kayıtta model "I'm sorry, but the provided text…" özrünü çeviri diye döndürdü — TTS bunu sesli okudu; istem sertleştirildi (asla yorum/özür yok, bozuk girdiye düşük güven zorunlu) |

**Done checklist durumu:** echo ✓, transcript ✓; medyan gecikme ✗ (3.49),
E-sınıfı doğruluk ✗ (rakam/tarih/marka), düşük-güven yakalama kısmi.
**Dilim henüz DONE DEĞİL.** EN→TR ayağı ve donanımlı echo vakaları da
koşulmadı.

**Sonraki iyileştirme adayları (öncelik sırası):** (1) cümle bölünmesi —
end_silence 700ms→~1000ms; (2) E-sınıfı rakam/tarih doğruluğu — daha güçlü
STT modeli (medium/large-v3 kıyası) veya bulut STT adayı; (3) mırıltıda
güven — çevirmen istemi sertleştirildi, ölçülecek; (4) gecikme — çeviri
modeli/akış optimizasyonu. Ölçmeden hiçbiri "çözüldü" sayılmaz.

## STT yol kararı (2026-08-14 — kalite turu, kurucunun 4 sütunlu tablosu)

Sentetik E-sınıfı set (S2 elli bin/1 Ekim, S4 yüzde kırk, S5 We Lock AI,
S3 Lumos temsilcisi); "istemli" = LUMOS_TERMS_PROMPT ile:

| Model | İstemli E-sınıfı doğruluk | Marka doğruluğu | Gerçek süre |
|-------|---------------------------|-----------------|-------------|
| small (yerel) | Kısmi — 50.000 ✓, "bir rekim" (tarih ✗); canlıda %40→45 ✗ | "Lumos temsilcisi" ✓ (istemle), We Lock AI ✗ | 1.8–2.3 sn |
| medium (yerel) | ✗ — %45 hatası AYNEN, "bir ekimde" bozuk | ✗ ("logikağı", "Tlumos") | **5.1–6.7 sn — ELENDİ** (3× yavaş, kazanım yok) |
| large-v3 (yerel) | ÖLÇÜLMEDİ — medium 3× yavaşlayıp kazanım vermedi; ~2× büyük modelin CPU'da bütçeyi imkânsız kılacağı öngörüsüyle gerekçeli eleme | — | (öngörü ~8-12 sn) |
| whisper-1 (bulut) | Anlamca ✓ ama normalize (50 bin / 1 Ekim); ikinci sıra | ✗ ("WeLogica'a" → TermCorrector düzeltir) | 1.4–1.9 sn |
| **gpt-4o-mini-transcribe (bulut) — SEÇİLDİ** | **✓ BİREBİR: "elli bin dolara… bir Ekim'de", "yüzde kırkı peşin"** | ✗ ("ve lojikayı") → **TermCorrector düzeltir (0.78) → birlikte ✓** | **0.9–1.8 sn** |

**Karar:** Faz 0 rig STT = `gpt-4o-mini-transcribe` (bulut, istemli) +
TermCorrector; yerel small `--stt-backend local` ile çevrimdışı yedek.
Gizlilik: ses OpenAI'ye gider — çeviri katmanıyla aynı işlemci; kapalı prova
için kabul, gerçek dış toplantı öncesi DPA blokajı zaten geçerli.
Uyarı: sentetik ses canlı konuşmayı tam temsil etmez (canlıdaki %40→45 hatası
sentetikte small'da bile yok) — nihai söz test 4'ün canlı ölçümünde.
**Öngörülen bütçe:** bekleme 0.9 + STT ~1.3 + çeviri ~1.2 ≈ 3.4 sn — ≤3 sn
hâlâ kanıtlanmadı; sıradaki kaldıraç çeviri ayağı (akış/model).

## Test 4 sonuçları (2026-08-14 — bulut zinciri, kaos koşusu)

Planlanan temiz okuma yerine fiilen kaos testi oldu (müzik, türkü, kedi,
serbest konuşma) — 26 kayıt, echo yok, kayıt tam. **Gerçek medyan 3.08 sn**
(test 3: 3.49; bulut zinciri hızlandırdı). ≤3 sn hedefi HÂLÂ BAŞARISIZ
(3.08 > 3), kurucu kararıyla kanıtlanana kadar böyle anılır.

Üç geçiş kriteri:
1. **E-sınıfı — kısmi/başarısız:** "Sözleşmeyi elli bin dolara imzalayacağız"
   güven 1.0 ile birebir ✓; ama cümle yine bölündü ve ikinci yarı "teslimat
   bir Ekim'de" → "Mesesimatı birlekinli" → **"The meeting will be in
   December"** (0.8 güvenle UYDURULMUŞ TARİH — en tehlikeli hata sınıfı).
   %40 satırı kaosta hiç yakalanmadı.
2. **Marka — düzeltici GERİ TEPTİ:** "Lumos projesini" (0.62) "Lumos
   temsilcisi"ne çevrildi — gerçek konuşmada anlam bozan yanlış pozitif.
3. **Mırıltı — çoğunlukla ✓:** kaos girdilerinin çoğu 0.2-0.7 güvenle
   işaretlendi; ama "birlekinli" vakası 0.8 ile geçti (bkz. 1).

Bulunan ve KAPATILAN iki yeni bug:
- **İstem yankısı**: bulut STT gürültüde terim istemini transkripsiyon diye
  döndürdü (26 kaydın 9'u!) ve düzeltici bunları iyice bozdu →
  `is_prompt_echo` filtresi: istem metnine ≥0.60 benzeyen STT çıktısı
  çeviriye girmeden düşürülür.
- **Düzeltici yanlış pozitifi**: korumalı bant 0.55→0.70 (gerçek düzeltmeler
  0.78-0.97'de kalıyor; "WeLogica'a" 0.59 bilinçli kapsam dışına çıktı —
  altın kural: emin değilsen dokunma).

Açık kalan: uydurulmuş-tarih vakası ("birlekinli"→December) çevirmen güven
skorunun bozuk girdiyi 0.8'le geçirmesi — bir sonraki sertleştirme adayı
(bozuk Türkçe girdi tespiti). Test 5 = TEMİZ okuma (müzik/kedi yok) ile üç
kriterin gerçek ölçümü.

## Test 5 sonuçları (2026-08-16 — temiz okuma, tam sertleştirilmiş zincir)

34 kayıt. **MEDYAN 2.89 sn — ≤3 sn HEDEFİ İLK KEZ GEÇİLDİ** (gerçek,
düzeltilmiş ölçümle; max 6.4 sn uzun cümle kuyruğu, p90 ~3.5 sn).

Üç geçiş kriteri:
1. **E-sınıfı — İLK KEZ BÜYÜK ÖLÇÜDE ✓:** "Sözleşmeyi elli bin dolara
   imzalayacağız ve teslimat bir Ekim'de olacak" güven 1.0 ile BİREBİR
   ("delivery will be on October first") — tarih ilk kez tam geçti, iki kez
   doğrulandı ("Teslimat 1 Ekim'de" → "October 1st" ✓ 1.0). "%40" ilk kez
   doğru korundu. İlk denemedeki bölünme doğru şekilde ⚠ işaretlendi (0.7).
   Kalan leke: "Ödemenin" → "Ödemeyenin" STT hatası özneyi kaydırdı
   ("non-payers", 0.9 güvenle) — tek gerçek E-sınıfı sapma.
2. **Marka — hâlâ ✗ ama artık DÜRÜST:** "We Lock AI" canlı konuşmada STT'de
   hiç doğru duyulmadı (üç deneme: "Bir sonluğu" 0.7⚠, "bilip al" 0.9,
   "We..." 0.5⚠); düzeltici tasarım gereği dokunmadı (emin değilsen dokunma —
   yanlış pozitif üretmedi ✓, "Lumos projesini" bu kez dokunulmadan geçti ✓).
   İstem yankısı filtresi 11 yankının 11'ini kesti ✓. Sonraki aday: tam
   gpt-4o-transcribe denemesi ve/veya prompt yazım varyantları.
3. **Mırıltı — ✓✓:** tüm bozuk girdiler işaretlendi (0.1-0.7), hiçbiri akıcı
   uydurmaya dönüşmedi; test 4'ün "December" vakası TEKRARLAMADI.

Done checklist güncel durumu: medyan ✓ (İLK KEZ) · düşük güven ✓ · echo ✓ ·
transcript ✓ · TR→EN anlaşılırlık büyük ölçüde ✓ · E-sınıfı kısmi (tarih ve
rakam ✓, marka ✗, bir özne sapması) · **EN→TR ayağı ve donanımlı echo
vakaları hâlâ koşulmadı → dilim hâlâ DONE DEĞİL ama ilk kez mesafe kısa.**

## Test 6 sonuçları (2026-08-16 — EN→TR ayağı, iki koşu)

Koşu 1 (900 ms): "uzun olunca eksik çeviriyor" — kurucu canlı yakaladı;
cümle içi duraklar (ikinci dil temposu) 900 ms'te bölünüyor + YENİ BUG:
karışık dilde çevirmen yön çeviriyordu ("Aranızda var mı?" → "Are you
there?"). Koşu 2 = `--end-silence-ms 1400` + istem yön kilidi.

Koşu 2 (14 kayıt):
- **E-sınıfı çekirdek ✓:** "We will sign the contract for \$50,000 and
  delivery is on October 1st" → "\$50,000'lık sözleşmeyi imzalayacağız ve
  teslimat 1 Ekim'de yapılacak" — güven 1.0, BİREBİR, bölünmeden. %40
  yapısı korundu. Bölünme sorunu 1400 ms ile çözüldü.
- **Mırıltı/parça ✓:** "If you..." 0.3 ⚠ doğru işaretlendi.
- **Medyan 4.03 sn — bu yönde hedef ÜSTÜ** (bilinçli ödün: 1400 ms bekleme;
  bütünlük > hız tercihi bu tur doğrulandı, optimizasyon sonraki tur).
- **Marka yine ✗:** "We Lock AI will take on…" — STT markayı cümle başında
  tamamen DÜŞÜRDÜ ("will take on the legal responsibility"), çeviri birinci
  tekile kaydı ("üstleneceğim") — EN yönünde de marka çözülmedi, #1 açık.
- **Yön kilidi kısmen delik:** istem düzeltmesi çoğunlukla tuttu (TR girdiler
  TR kaldı) ama iki kayıtta TR girdi İngilizce çıktı / içerik kaybıyla
  kısaldı — istem tek başına yetmiyor; aday: çıktı dili deterministik
  tespit + uymarsa yeniden çeviri (post-check).

Done checklist: EN→TR ayağı KOŞULDU — çekirdek doğruluk ✓ ama "güvenilir"
için marka + yön kilidi + bu yönün medyanı kalmalı. Dilim hâlâ DONE değil;
kalan üç kalem net: (1) We Lock AI (her iki yönde #1), (2) yön kilidi
post-check, (3) EN yönü gecikme optimizasyonu. Donanımlı echo vakaları da
hâlâ ayrıca koşulmadı.

## Marka kararı (2026-08-16 — kalem 1 kapanışı: "düzelt" değil "işaretle")

Matris ölçümü (2 model × 3 istem × 4 söyleyiş): EN söyleyişte marka
çoğunlukla ✓; TR konuşma içinde HİÇBİR model/istem kombinasyonu güvenilir
değil ("Biolojik", "ve lojistiği", "lojikal"). Çevirmen katmanında bağlamlı
onarım denendi (statik toplantı brifingi + son 4 söz yuvarlanır bağlam):
model onarım YAPMADI ama bozuk-marka cümlelerini 0.5-0.7 güvene düşürdü =
işaretleniyor; kontroller (gerçek biyoloji/lojistik cümleleri) temiz.

**Karar (teknik sorumlu):** TR içi bozuk marka OTOMATİK ONARILMAZ —
işaretlenir; kurucu toplantıda bayrağı görür. Gerekçe: tüm onarım yolları
(alias/fuzzy/LLM) gerçek kelime çakışması riski taşıyor ("ve lojistik
olarak" gerçek cümlede de geçer); Faz 0'da yanlış-ama-özgüvenli çıktı,
işaretli-eksik çıktıdan KÖTÜdür. Tutarlılık için düzelticiye gerçek-kelime
stoplist'i eklendi (lojistik/biyolojik vb. hiçbir fuzzy eşleşmede yutulmaz).
Kazanım olarak kalan: çevirmene konuşma bağlamı (brifing + son 4 söz) —
genel çeviri kalitesi ve gönderme çözümü için kalıcı iyileştirme.

## Çıktı dili post-check (2026-08-16 — kalem 2 kapanışı, kurucu kuralıyla)

Kural aynen uygulandı: deterministik TR/EN tespiti (`langcheck.detect_lang`
— Türkçe karakter + işlev-kelime skorlaması; kısa/sinyalsiz çıktı "unknown"
sayılır ve BLOKLANMAZ) → yanlış dilde çıktı → EN FAZLA 1 yeniden çeviri →
ikinci çıktı da yanlışsa TTS'E VERİLMEZ: `delivered=false`,
`flag=wrong_output_language` (fail-closed). Retry döngüsü yok (testle sabit:
çevirmen tam 2 kez çağrılabilir, fazlası imkânsız).

Gecikme muhasebesi (kalem 3 için): post-check'in eklediği süre kayıtta AYRI
alanda — `postcheck_ms` (retry çevirisi dahil; retry yoksa 0) + `retried`
bayrağı. Test 6 verisine göre retry oranı düşük beklenir (istem kilidi çoğu
vakayı tutuyor); gerçek oran ve maliyet bir sonraki canlı provada ölçülür.

## Gecikme optimizasyonu (2026-08-17 — kalem 3: akışlı STT)

Yapısal analiz: EN→TR 4.03 sn medyanın tabanı 1.4 sn istemci bekleme + ~1.1
sn toplu STT idi — parça oynatarak ≤3'e inmiyor. Çözüm: **GA Realtime API ile
akışlı transkripsiyon** (`--stt-backend realtime`): transkript konuşma
SIRASINDA akar; endpointing sunucu VAD'de (600 ms), yerel segmenter/
kalibrasyon bu backend'de devre dışı; half-duplex kural yakalama anında
(kapı kapalıyken kare websocket'e gitmez → echo transkripti oluşamaz).

Sentetik ölçümler (2026-08-17):
- Ses sonu → transkript: **1.88 sn** (0.6 sn VAD dahil); metin E-sınıfı
  dahil kusursuz ("$50,000, and delivery is on October 1st").
- Çeviri ayağı ısınmış medyan **0.95 sn** (soğuk ilk çağrı 2.16 → rig
  açılışına ısıtma çağrısı eklendi).
- **Öngörülen sıcak bütçe: 0.6 VAD + ~1.3 STT kuyruğu + 0.95 çeviri ≈ 2.85 sn
  — hedef altı; KANITLANMIŞ SAYILMAZ, test 7 canlı ölçecek.** (Sentetik
  uçtan uca koşuda görülen 4.7-5.9 sn, test düzeneğinin soğuk bağlantı +
  hantal sessizlik beslemesindendi; ayrıştırma yukarıda.)

Test 7 komutu (EN→TR, akışlı):
`nohup env PYTHONUNBUFFERED=1 PYTHONPATH=src .venv/bin/python -m representative.local_rig --audio --stt-backend realtime --translator openai --source-lang en --target-lang tr --voice Yelda --jsonl-out prova_rt.jsonl > prova_rt.log 2>&1 & echo $! > prova.pid`

## Test 7 sonuçları (2026-08-17 — akışlı zincir CANLI, EN→TR)

32 kayıt (KILL'e rağmen tam — artımlı jsonl işledi). Kurucunun beş kriteri:

1. **CANLI MEDYAN 1.92 sn — ≤3.00 hedefi canlıda GEÇİLDİ** (p90 2.28,
   max 3.94). Akışlı STT + ısıtılmış çevirmen yapısal kazancı kanıtladı;
   4.03 → 1.92.
2. **E-sınıfı doğruluk — bu koşuda değerlendirilemedi:** koşu serbest
   konuşmaya döndü (talimat okumaları + Türkçe sohbet karıştı); 3. satır
   parçalara bölündü ("Ekim 1." parçası doğru çevrildi). VAD 600 ms
   ikinci-dil İngilizce temposunu fazla bölüyor → varsayılan 800 ms yapıldı
   (--vad-silence-ms). Temiz okuma teyidi test 8'e.
3. **Post-check: 2/32 retry, toplam ~2.1 sn maliyet** (retry başına ~1 sn) —
   oran düşük, maliyet ölçüldü; fail-closed hiç tetiklenmedi (retry'lar
   kurtardı).
4. **Echo: SIFIR** — hiçbir TTS çıktısı yeniden duyulmadı (32 kayıtta
   birebir eşleşme 0; half-duplex + yakalama-anı düşürme çalışıyor).
5. **B2 bilinçli kayıp vakası** düzenli koşulamadı (serbest akış) — test 8'de.

Bulunan ve KAPATILAN yeni bug: model 5 kayıtta boş çeviri + yalnız güven
satırı döndürdü ve rig **"confidence: 0.3" metnini seslendirdi** →
parse_reply sağlamlaştırıldı ('confidence: X' deseni metinden her yerde
sökülür) + pipeline boş çeviriyi ASLA seslendirmez (empty_translation,
fail-closed, testli).

**Test 8 (final teyit, kısa):** temiz 8 satır + B1/B2 echo vakaları,
akışlı zincir + 800 ms VAD + parser düzeltmesiyle. Geçerse done checklist
kurucu final değerlendirmesine gider.

## Test 8 sonuçları (2026-08-17 — FİNAL TEYİT, akışlı zincir + tüm düzeltmeler)

21 kayıt. **Medyan 2.28 sn | p90 2.63 | max 3.04** — ≤3 hedefi ikinci canlı
koşuda da teyit. Echo: 0. Retry: 1/21 (672 ms). Fail-closed: 2 kez tetiklendi
ve ÇALIŞTI — boş çeviri "[TESLİM EDİLMEDİ]" olarak düştü, seslendirilmedi
(test 7 bug'ının düzeltmesi sahada doğrulandı).

Satır sonuçları: 1 ✓ · 2 ~ (STT "AI tools"→"altcoins" duydu — anlam hatası,
işaretlenmedi; bilinen STT sınırı) · 3 ilk denemede "sign"→"seek" (anlam
kayması), kurucu tekrarında ✓ birebir ("$50,000 için sözleşmeyi
imzalayacağız"); "1 Ekim" ✓ · 4 ✓✓ BİREBİR ("yüzde kırkı peşin… teslimat") —
üç E-sınıfı değer (para/tarih/yüzde) İLK KEZ AYNI CANLI KOŞUDA doğru ·
5 marka düşük ("işaretle" kararı kapsamında bilinen sınır) · 6 ✓ · 7 mırıltı/
sohbet 9 kez işaretlendi ✓ · 8 ✓ iki kez birebir.

## Done checklist — FİNAL DURUM (2026-08-17, teknik değerlendirme)

- [x] Medyan gecikme ≤ 3 sn — CANLI: 1.92 (test 7) ve 2.28 (test 8)
- [x] TR→EN doğal ve anlaşılır (test 5) / EN→TR güvenilir (test 8)
- [x] E-sınıfı eksiksizlik — $50,000 ✓ / 1 Ekim ✓ / %40+peşin ✓ (test 8'de
      üçü birden); bilinen sınırlar belgeli: tekil STT yanlış duymaları
      (seek/altcoins) işaret/tekrar ile telafi edildi, marka = işaretle kararı
- [x] Düşük güven işaretleme + boş çeviri fail-closed (2 canlı tetiklenme)
- [x] Echo — 0 (test 7: 32 kayıt, test 8: 21 kayıt; yapısal half-duplex)
- [x] İki dilli transcript + çökme-güvenli jsonl (KILL'e rağmen tam kayıt)
- [ ] **KURUCU FİNAL DEĞERLENDİRMESİ** — teknik öneri: yerel dilim DONE;
      karar kurucunun. Not: B2 (TTS sırasında konuşmanın bilinçli kaybı)
      yapısal olarak garanti (kare websocket'e gitmiyor) ama ayrı vaka
      olarak sahnelenmedi; kurucu isterse 2 dakikalık ek koşu yapılır.

Done ilan edilirse: yerel TR↔EN dilimi kapanır; sıradaki kapı "Recall hazır"
(MeetingIngress + bot kill-switch + gerçek toplantı provası + bot-düzeyi
disclosure). Realtime backend'in varsayılan yapılması da done kararıyla
birlikte önerilir (iki canlı koşu kanıtı var).

## Recall / MeetingIngress dilimi (2026-08-17 — "Recall hazır" tetiği alındı)

Kurucu zinciri onayladı: Recall hazır → MeetingIngress → mevcut ölçülmüş
tercüme çekirdeği. Durum:

1. **Secret**: `RECALL_API_KEY` henüz env'de YOK. Yerleştirme (değer chat'e/
   repoya girmez): `echo 'export RECALL_API_KEY=ANAHTAR' >> ~/.zshenv`
   Bölge taban URL'si de env ile: `RECALL_REGION_URL` (ör.
   `https://us-west-2.recall.ai` — hesabın açıldığı bölgeye göre).
2. **İskelet main'de**: `meeting_ingress.py` — sağlayıcı-bağımsız
   `MeetingIngress` arayüzü + `RecallMeetingIngress`. Kurucu şartları kod
   düzeyinde testli: retention imza-düzeyi zorunlu (fail-closed; "forever"
   diye bir seçenek YOK), prova=timed/24h + erken `delete_media`, gerçek
   toplantı=zero, yalnız Meet URL, Recall transkripsiyonu asla, metadata
   yalnız opak referans, ifşa cümleleri (TR+EN) hazır, `kill()` ayrı uç.
3. **Bot kapalı provası (anahtar gelince)**: kurucu boş bir Meet açar →
   bot katılır → ifşa cümlesini söyler → 8 adımlık senaryo (katılım →
   disclosure → TR→EN → EN→TR → düşük güven → transcript → kill-switch →
   çıkış) → `delete_media` ile erken silme kanıtlanır. HTTP uç şekilleri
   ilk canlı çağrıda doğrulanır; sapma çıkarsa iskelet küçük PR ile düzelir.
4. **Hatırlatma**: gerçek DIŞ katılımcılı toplantı öncesi DPA + veri
   bölgesi hâlâ BLOKAJ (karar tablosu şartı 4).

## "Done" değerlendirmesi (kurucu kriterleri)

- [ ] Medyan gecikme ≤ 3 sn (jsonl kayıtlarından hesaplanır)
- [ ] TR→EN doğal ve anlaşılır; EN→TR güvenilir (kurucu değerlendirmesi)
- [ ] E-sınıfı cümleler eksiksiz, YENİ taahhüt üretilmemiş (transcript'ten kontrol)
- [ ] Düşük güvenli cümle işaretlendi, sessizce uydurulmadı
- [ ] Echo testi: çeviri döngüsü oluşmadı
- [ ] İki dilli transcript (jsonl + markdown) üretildi

Sonuçlar bu belgeye tarih damgalı işlenir; done ise dilim kapanır ve sıra
"Recall hazır" tetiğine döner (MeetingIngress + bot kill-switch + gerçek prova).

## BOT PROVA 2 — FİNAL PASS (2026-08-17)

Tam zincir toplantı İÇİNDE canlı doğrulandı: kurucu Meet'te Türkçe konuştu,
bot İngilizce SESLE cevap verdi. 24 kayıt | **toplantı-içi medyan 2.05 sn** |
p90 4.97 (bot konuşurken half-duplex bekleme sivrilmeleri — bilinen ödün).

- E-sınıfı final: "50.000 dolara… 1 Ekim'de" → "fifty thousand dollars …
  October first" ✓ (2.02s); "yüzde kırkını peşin" → "forty percent in
  advance" ✓ (1.93s). Kurucu kulak teyidi alındı.
- Fail-closed toplantı içinde 1 kez çalıştı (boş çıktı seslendirilmedi);
  5 düşük-güven işareti.
- Kill-switch 200 + erken delete_media 200 (ilk deneme çıkış anında 400 —
  medya işleniyordu; kısa bekleme sonrası geçti; runbook notu).
- Canlı doğrulanan yeni şekiller: realtime ws push (audio_mixed_raw.data,
  data.data.buffer), create için audio_mixed_raw artefact şartı, boş b64
  reddi. "Regresyon vakası" düzeltmesi: prova sırasında görülen bozuk
  İngilizce ("Ayten only See my One speakers…") bizim çıktı DEĞİL — Meet'in
  kendi altyazı motorunun botun gerçek sesini yanlış yazması; bu aynı
  zamanda output_audio'nun dolaylı kanıtı (kurucu teyitli).

**Recall canlı entegrasyonu: 7 uç canlı doğrulandı; uçtan uca toplantı-içi
tercüme PASS. Faz 0 zinciri (Recall hazır → MeetingIngress → çekirdek)
TAMAMLANDI.** Kalan (Faz 0 sonrası): DPA/veri bölgesi (gerçek dış katılımcı
blokajı), gecikme sivrilmeleri, Meet-altyazı etkileşimi notu.

## Canlı insan testi FAIL ×2 — kök neden ve düzeltme (2026-08-17)

İki insan oturumunda çeviri yoktu. Kök neden zinciri (log + Recall bot
nesnesi + tünel öz-testiyle kanıtlı, tahminsiz):
1. Oturum 1: bot_rig o Meet için HİÇ başlatılmamıştı (adım 0; Recall'da bot
   yok). Ürün dersi: oturum başlatma otomasyonu yok — ayrı dilim.
2. Oturum 2: bot girdi, Recall'da realtime endpoint kayıtlıydı ama ws
   BAĞLANMADI: ngrok ücretsiz katman ara sayfası (**ERR_NGROK_6030**)
   tarayıcı-olmayan istemcileri 400'lüyor. Rig bunu fark etmeden botu
   toplantıya soktu — sessiz altyapı arızası.

Düzeltmeler (main):
- Taşıyıcı: **cloudflared quick tunnel birincil** (ws ara sayfasız), ngrok
  yedek; yarışan ajan temizliği başlangıçta.
- **Zorunlu tünel öz-testi (fail-closed)**: bot yaratılmadan önce genel wss
  adresine dışarıdan probe → yerel sunucuya ulaşmazsa bot HİÇ yaratılmaz.
  macOS çözücü yanlış-negatifi için 1.1.1.1 + SNI doğrudan bağlantı yolu.
- Doğrulama: botsuz öz-test 10 sn'de GEÇTİ (dış dünya → cloudflared →
  yerel ws). Bir sonraki insan testi bu kapının arkasından başlar.

## Oturum otomasyonu — dilim 1 (2026-08-17)

Kurucu hedef davranışı: "linki ver → gerisini Lumos yapar; kullanıcı bot_rig
bilmez." Bu dilim CLI düzeyinde tam yaşam döngüsünü otomatikleştirir:

Tek komut: `python -m representative.bot_rig --meeting-url <link>` →
tünel + zorunlu öz-test → bot + ifşa → tercüme → **toplantı bitince
KENDİLİĞİNDEN kapanış** (Recall durumu call_ended/done/fatal algılanır) →
leave + STT/tünel kapanışı + **otomatik erken delete_media** (varsayılan;
teşhis için --keep-media) + transcript/özet. Bekleme odasında 5 dk kabul
edilmezse gürültülü vazgeçer (fail-loud) — asılı sağır bot kalmaz.

Kalan (dilim 2 — ürün yüzeyi): girişin ChatLumos'tan verilmesi ("toplantıya
katıl <link>") — tek-arayüz kuralının gerçek karşılığı; panel/chat
entegrasyonu ürün yüzeyi kararı olarak kurucuyla şekillenecek. Bir sonraki
insan testi bu otomasyonla yapılacak (üçüncü davet öncesi hazır olan bu).

## Canlı insan testi FAIL ×3 — oturum hiç başlamadı (2026-08-17)

> Kapsam notu: kayıt kurucunun toplantı-içi canlı gözlemine dayanır
> (katılımcı listesi + ses akışı); bu FAIL için log/Recall doğrulaması bu
> oturumdan yapılmadı.

Üçüncü insan testi (katılımcı: Tolga) **FAIL**. Toplantıda yalnız kurucu ve
Tolga vardı; Lumos Temsilcisi botu katılımcı olarak HİÇ görünmedi. Kurucunun
Türkçe sesi Tolga'ya doğrudan gitti — ortada aktif çeviri zinciri yoktu.
Test, Tolga bekletilmeden FAIL yazılıp sonlandırıldı.

Kök neden — çeviri kalitesi DEĞİL, oturum başlatma: ChatLumos → execute →
Mac/Recall backend bağlantısı gerçek oturumu başlatmadı. Lumos PR #342
("Dilim 2 — ChatService join kablosu (canlı Meet yok)") bilinçli olarak
canlı Meet'siz; `CallableMeetingBackend(join_fn)` boşluğu açıkken zincir
"hazır" ilan edildi. Süreç dersi: FAIL ×1'deki ders ("oturum başlatma
otomasyonu yok — ayrı dilim") CLI düzeyinde kapatılmıştı ama ChatLumos
yüzeyinden uca kadar doğrulanmadan insan testine çıkıldı.

Bir sonraki insan testinin ön koşulu (kurucu kararı): `join_fn` canlıya
gerçekten bağlanacak; **bot toplantıda üçüncü katılımcı olarak görünür +
ifşa (disclosure) sesli duyulur** — ancak ondan sonra Türkçe konuşulur.
Bu iki işaret görülmeden test başlamaz (fail-closed, botsuz test yok).

## Canlı insan testi 4 — zincir canlı, gecikme kuyruk-ucu FAIL (2026-08-17)

> Kapsam notu: metrikler oturumun jsonl kaydından hesaplandı (n=60 söz, 59
> teslim); rapor yazılırken oturum hâlâ açıktı, sayılar o andaki anlık
> görüntüdür. Zincir kanıtları köprü çıktısı + oturum günlüğünden.

FAIL ×3'ün ön koşulu bu testte kapatıldı ve zincir İLK KEZ ChatLumos komut
sözleşmesi üzerinden uçtan uca canlı koştu: Lumos PR #342
`evaluate_meeting_join_command(execute=True)` → `run_execute` → gerçek
`CallableMeetingBackend(join_fn)` → bot_rig (cloudflared tünel → zorunlu
öz-test GEÇTİ → ifşa → Recall bot `0d4633b1`). Bot üçüncü katılımcı olarak
görünüp ifşa duyulduktan sonra konuşuldu; tercüme iki insan (kurucu +
karşı taraf) arasında ~55 dk aktı.

**Gecikme — hedef p50 ≤2.5 sn / p90 ≤4 sn:** p50 **2.13 sn** (hedef İÇİNDE),
p90 **7.49 sn**, max **15.07 sn** → **p90 FAIL**. Teşhis: "sistem genel
yavaş" değil, kuyruk ucu bozuk — TTS tam klip çalarken half-duplex kapı
kapalı; ardışık kısa sözler kuyrukta birikip 8-15 sn'ye şişiyor. Çözüm
adayı (cümle-chunk TTS + yeni konuşmada kuyruk kesme) bu yazım anında
**repo gerçeği DEĞİL** — başka oturumun çalışma alanında; ayrı teknik PR
olarak gelecek, test/CI görmeden "yapıldı" sayılmaz.

**Üç ürün bulgusu (kurucu + günlük, kaybolmayacak):**
1. **EN→TR yön yok + papağan:** oturum tek yön tr→en; karşı tarafın
   İngilizcesi STT'ye düşüp aynen geri seslendirildi ("How are you?" →
   "How are you?"). Kaynak-dil filtresi / yön yönlendirme gerekiyor.
2. **Strict translation-only modu yok:** papağan davranışı toplantıda
   "bot kendi kafasına cevap veriyor" olarak algılandı; tercüman kipi
   konuşma üretmemeli, yalnız çevirmeli, gerektiğinde susmalı.
3. **Meta-sızıntı + below_threshold'a rağmen teslim (EN CİDDİSİ):** iç
   güven etiketi 3 kez botun sesinden toplantıya okundu ("LOW",
   "Translation not clear; LOW confidence."); 23/60 söz düşük güven
   işaretine rağmen seslendirildi (yalnız 1 empty_translation düşürüldü).
   İç etiket kullanıcıya ses olarak asla çıkmamalı; ConfidenceGate teslim
   politikası ürün kararı olarak yeniden ele alınacak.

**Karar (kurucu, 2026-08-17):** Yeni insan testi için acele YOK. Sıra:
(1) bu kayıt + bulgular main'e, (2) chunk TTS ayrı teknik PR, (3) yön
yönlendirme + strict tercüman kipi + meta-sızıntı kapanışı, (4) ancak
ondan sonra p50/p90 yeniden canlı ölçülür.

---

## Botsuz kapanışlar — insan testi 5 öncesi (2026-08-17)

Kurucu kuralı: **insan testi boşa harcanmaz.** Tek kişiyle/botsuz
doğrulanabilen her şey önce kapatılır; testçiye "gel bakalım yine çalışıyor
mu" değil, "her şey hazır, son gerçek dünya kontrolü" denir.

| # | Bulgu (test 4) | Durum | Kanıt |
|---|----------------|-------|-------|
| 1 | EN→TR yön yok + papağan | **Kapandı** | `routing.DirectionRouter` — yön her söz için duyulan dile göre; kaynak≠hedef yapısal garanti. auto yönde STT'ye dil verilmez. 14 test |
| 2 | Strict tercüman kipi yok | **Kapandı** | İstemde `STRICT INTERPRETER MODE` + `<utterance>` sarmalama; çıktıda `is_non_translation` fail-closed kapısı. 21 test |
| 3a | Meta-sızıntı (iç etiket seslendirildi) | **Kapandı** | `is_meta_output` (#749) + regresyon takımı: etiketin her biçimi, yüksek güvenle de, parse_reply yolları dahil. 34 test |
| 3b | 23/60 söz eşik altı olmasına rağmen teslim | **Kapandı — kurucu kararı (c)** | Seslendirilir AMA işaretlenir: transkript artık "✓ duyuldu / ✕ seslendirilmedi" + okunur işaret etiketi taşır. (b) sessizlik yaratır, (a) şüpheli çeviriyi normalmiş gibi sunar |
| 4 | p90 sivrilmesi teşhis edilemiyor | **Ölçüm altyapısı hazır** | Aşama kırılımı (`translate_ms`/`tts_ms`), p50/p90 özet, `python -m representative.latency` PASS/FAIL + çıkış kodu |
| 5 | Cümle-chunk TTS (p90'ın kök nedeni) | **Repoda** | Lumos PR #343 handoff yaması `git am --3way` ile alındı, 6 çakışma elle çözüldü; ilk klip = first-audio, kalan arka planda, yeni sözde barge-in. **Canlı ölçüm hâlâ yapılmadı** |

### Ölçüm kaydını çözümleme

```bash
python -m representative.latency prova_bot.jsonl
```

Hedefler `p50 ≤ 2.5 sn`, `p90 ≤ 4 sn` (üstte); tutmazsa çıkış kodu **1**.
Rapor yön kırılımı, aşama p90'ları, işaret dağılımı ve en yavaş 5 sözü verir —
"genel yavaş" ile "kuyruk ucu bozuk" ayrımı artık kayıttan okunur.

### Çift yönlü kuru prova (botsuz, tek kişi)

```bash
python -m representative.local_rig --translator openai --jsonl-out prova_iki_yon.jsonl
```

TR ve EN cümleleri sırayla yaz; her satırda `yön: detected` görünmeli ve yön
cümleye göre değişmeli. Papağan (kaynak=hedef) çıkarsa dur — bu bir regresyondur.

### İnsan testi 5'in ön koşulu

Chunk TTS bu repoya girmeden ve yukarıdaki 3b kararı verilmeden yeni canlı
test **planlanmaz**. Test yapıldığında ölçüm dosyası doğrudan
`representative.latency` ile çözümlenir; PASS/FAIL beyanla değil çıkış koduyla
kayda geçer.

## Gecikme zinciri — first-audio (2026-08-17)

Ürün hedefi (doğal sohbet): **p50 ≤ 2.5 sn, p90 ≤ 4 sn** — damga
`speech-end → STT-final → translation-ready → TTS-start → first-audio-in-Meet`.
Eski `latency_ms` yalnız çeviri-hazır'ı ölçüyordu; TTS+kapı uykusu içeride
değildi. 2026-08-14 prova (medyan 3.49 / p90 5.79) bu hedefi **geçmez**;
PASS deme.

Kod kök nedeni (Meet, `RecallSpeaker`): tam paragraf `gpt-4o-mini-tts` MP3
sonra `time.sleep(0.075 * len(text) + 1.0)` ile kapı kilitli — inbound kare
düşer, half-duplex kuyruğu uzun TTS yüzünden konuşmayı bloklar.

Düzeltme (bu dilim, canlı Meet ölçümü yok):
- Aşama damgaları jsonl'de (`stt_ms`, `translate_ms`, `tts_to_first_audio_ms`,
  `e2e_first_audio_ms`) + p50/p90 + `largest_wait`.
- Cümle-chunk TTS: ilk klip first-audio; kalan arka plan; yeni söz barge-in
  (kuyruk düşer, mevcut klip echo için biter).
- Kapı hold = tek klip + 0.25s echo kuyruğu (tam paragraf + 1.0s değil).
- Recall PCM stream yok; chunk'lı MP3 mümkün olan kaldıraç.

Canlı doğrulama yalnız Mac (`RECALL_API_KEY` Cloud'da yok). jsonl özetinde
`first_audio_budget_pass` false ise **FAIL — PASS deme**.
