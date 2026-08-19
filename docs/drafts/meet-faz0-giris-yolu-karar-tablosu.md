# Google Meet Faz 0 Giriş Yolu — Karar Tablosu

> Kapsam notu (2026-08-12): ADR-023 Faz 0 (Tercüman Modu) için Google Meet'e
> gerçek zamanlı, çift yönlü ses erişimi seçeneklerinin araştırması. Araştırma
> 2026-08-11/12'de yapıldı; dört yük taşıyan iddia birincil kaynaklardan (Google
> ve sağlayıcı dokümanları) ayrıca doğrulandı. Doğrulama durumu her satırda
> işaretli. Bu belge karar ÖNERİSİ içerir; sağlayıcı seçimi kurucu onayı bekler
> (dış muhatapların sesi üçüncü taraf işlemciden geçeceği için ürün/gizlilik
> boyutu var).

## Belirleyici bulgu (birincil kaynaktan doğrulandı ✓)

**Google'ın resmî yolu Faz 0 için kapalı.** Meet Media API:

1. **Yalnız alıcı (receive-only)** — ses/video akışı tüketilir, toplantıya ses
   BASILAMAZ. Çeviri sesini toplantıya verecek bir mekanizması yok.
2. **Developer Preview** — GA değil (doküman güncellemesi 2026-07-22 itibarıyla).
3. **Toplantıdaki HERKESİN** (Cloud projesi + OAuth prensipali + tüm
   katılımcılar) Developer Preview Programı'na kayıtlı olması şart — dış
   muhatapla gerçek toplantıda fiilen imkânsız.
4. Ek sınır: aynı anda yalnız "en alakalı 3 katılımcının" ses akışı alınır.

Kaynak: developers.google.com/workspace/meet/media-api/guides/overview (✓ doğrudan fetch ile teyit).
Meet REST API canlı medyaya hiç dokunmaz (toplantı oluşturma + toplantı sonrası
transcript/kayıt artefaktları); Add-ons SDK yalnız UI iframe'i. İkisi de
tercüman için giriş yolu değil, tamamlayıcıdır.

**Sonuç:** Bugün Meet'e çeviri sesi basmanın kanıtlanmış tek yolu, toplantıya
katılımcı olarak giren (headless tarayıcı) bot altyapısıdır.

## Karar tablosu

| Eksen | Meet Media API (resmî) | Recall.ai | Attendee (açık kaynak) | Meeting BaaS |
|-------|------------------------|-----------|------------------------|--------------|
| Ses GİRİŞ (dinleme) | ✓ WebRTC, ama max 3 katılımcı akışı — ✓doğrulandı | ✓ Websocket PCM 16-bit/16kHz; katılımcı-başına ayrık ses (feature flag, 4-core bot) | ✓ Websocket PCM, mixed veya katılımcı-başına; 8/16/24 kHz — ✓doğrulandı | ✓ (Pipecat tabanlı) |
| Ses ÇIKIŞ (konuşma) | **✗ YOK — eleyen kriter** ✓doğrulandı | ✓ Meet'te teyitli: Output Audio (base64 MP3 klip, `automatic_audio_output`) veya Output Media (görünür video karosu ZORUNLU) — ✓doğrulandı | ✓ Websocket'ten base64 PCM geri basma, Meet örnekli — ✓doğrulandı | ✓ "Speaking Bots" ürünü |
| Erişim/onay koşulu | Tüm katılımcılar Preview üyesi + admin kapatabilir | API anahtarı, hemen | Self-host (Docker) veya hosted | API, token modeli |
| Gecikme | Yayınlanmış rakam yok (WebRTC) | Resmî rakam yok; topluluk ~200ms frame teslimi (ikincil kaynak) | Yayınlanmış rakam yok | Yayınlanmış rakam yok |
| Maliyet | Ücretsiz (ama kullanılamaz) | $0.50/sa + transkripsiyon $0.15/sa; startup $0.25/sa ilk 10k sa — ✓doğrulandı; 4-core $0.60/sa, GPU $1.50/sa (docs, pricing sayfasında yok) | Açık kaynak: altyapı maliyeti; hosted fiyatı belirsiz | ~$0.63–0.68/sa (üçüncü taraf döküm) + $99–299/ay abonelik |
| Platform kuralı / ifşa | Konsent diyaloğu host'a gösterilir | Bot "katılma isteği"nden geçer, insan kabul eder; bot görünür katılımcıdır (ifşa ilkemizle uyumlu) | Aynı (headless Chrome katılımcı) | Aynı |
| Vendor lock-in | Tam Google kilidi + hiçbir yere taşınmaz | Orta; ama aynı API Zoom/Teams/Webex'i kapsar → Faz sonrası platform genişlemesi bedava | En düşük (açık kaynak, websocket sözleşmesi basit) | Orta-yüksek (Pipecat'e görüşlü sarmalayıcı) |
| Olgunluk/risk | Google ciddiyeti ama ürün için kullanılamaz | En olgun; YC-launch'lı Output Media, geniş müşteri tabanı | Websocket hata geri bildirimi YOK (dokümanda itiraf); işletme yükü bizde | Örnekleri belirli STT/TTS'e gömülü; esneklik düşük |

## Ortak platform riski (yalnız İKİNCİL kaynak — birincil kanıt bulunamadı)

Google 2026'da riskli katılım isteklerini ayrı ekrana alan bir "safeguarded
admit" akışı ve admin'lere üçüncü taraf not-alıcı botları engelleme araçları
getirdi (vendor blogları; Google sayfasından teyit edilemedi). Tüm bot
sağlayıcıları için geçerli tek büyük risk budur: bot toplantıya "katılma
isteği" ile girer, karşı taraf admin'i engellemişse giremez. Faz 0'da
hafifletme: kurucu toplantıda zaten var; bot girişi reddedilirse temsilci
devre dışı kalır, toplantı insan-insana devam eder (zarif düşüş).

## Öneri (teknik sorumlu)

**Faz 0 pilotu: Recall.ai — Output Audio yoluyla.** Gerekçe:

1. Ardıl tercüme klip doğasındadır: cümle biter → çeviri üretilir → MP3 klip
   basılır. Recall'un Output Audio modeli buna birebir oturur; sürekli akış
   (Output Media'nın zorunlu video karosu) Faz 0'da gerekmez.
2. Hosted-varsayılan kararıyla (2026-07-25, Seçenek C) tutarlı: işletme yükü
   yok, bugün API anahtarıyla başlanır; prova toplantısına en kısa yol.
3. Maliyet önemsiz: 1 saatlik toplantı ≈ $0.65 (bot+transkripsiyon);
   startup tarifesiyle yarısı.
4. Zoom/Teams genişlemesi aynı API'de — ADR-023 yol haritasıyla uyumlu.

**Lock-in sigortası (şart):** Kod, sağlayıcıya değil ince bir
`MeetingIngress` arayüzüne yazılır (join/leave/audio-in/audio-out/kill).
Attendee aynı arayüzün ikinci gerçeklemesi olarak yedek yol kalır (açık
kaynak, çift yönlü PCM doğrulandı) — Recall fiyat/politika değiştirirse veya
self-host gerekirse geçiş maliyeti sınırlı olur.

**Gizlilik notu (kurucu kararı gerektiren kısım):** Recall.ai yolunda toplantı
sesi (dış muhataplar dahil) Recall altyapısından geçer; saklama davranışı
tamamen `recording_config.retention` alanına bağlıdır ve güncel hesaplarda
varsayılan SÜRESİZ saklamadır — bu yüzden alan her istekte açıkça set edilir
(fail-closed; ayrıntı ve nihai tanım aşağıda: "medya-sıfır-saklama + 7 gün
log + kalıcı meeting URL/custom metadata"). Gerçek dış toplantı öncesi
saklama/işleme koşulları (DPA, veri bölgesi) ayrıca incelenmeli. OpenAI STT
tarafı 2026-08-19'da kilitlendi: Avrupa depolama **ve** işleme
(`eu.api.openai.com`) + MAM/ZDR yazılı org onayı; gerçek Meet sesi bu kapı
kapanmadan gönderilmez — [stt-data-boundary-v1](../contracts/stt-data-boundary-v1.md).
Bu, sağlayıcı onayıyla birlikte verilecek karardır.

## Kurucu kararı (2026-08-12) — Recall.ai pilotu ONAYLANDI, şartlı

1. Recall.ai = ilk `MeetingIngress` implementasyonu; mimari MUTLAKA
   sağlayıcıdan bağımsız `MeetingIngress` arayüzünün arkasında kalır.
2. Attendee = ikinci/yedek implementasyon adayı.
3. **7 günlük varsayılan saklama olduğu gibi KABUL EDİLMEDİ**: Recall
   tarafında mümkün olan en kısa retention / mümkünse zero-retention veya
   işlem sonrası otomatik silme araştırılıp kullanılacak (pilot öncesi
   doğrulama şartı).
4. Dış katılımcıya AI tercümanın toplantıda olduğu VE sesin üçüncü taraf
   altyapısından işlendiği açıkça bildirilecek (ifşa ilkesine ek madde).
5. Faz 0'da ses klonu, avatar, otonom temsil YOK (teyit).
6. İlk test gerçek dış muhatapla DEĞİL, kapalı prova toplantısında.
7. Test senaryosu: bot katılımı → disclosure → TR→EN → EN→TR → düşük güven
   davranışı → iki dilli transcript → kill-switch → bot çıkışı.
8. ≤3 sn: kanıtlanana kadar HEDEF, özellik iddiası değil.

## Retention/gizlilik doğrulaması (2026-08-12, birincil kaynak: docs.recall.ai)

Kurucunun 3. şartının cevabı — **zero-retention MÜMKÜN ve bize uyuyor**:

- `recording_config.retention: null` (Create Bot isteğinde) = **sıfır saklama**:
  hiçbir kayıt medyası Recall sunucusunda tutulmaz; veriye erişimin tek yolu
  toplantı sırasında gerçek zamanlı akıştır. ✓ doğrulandı
  (docs.recall.ai/docs/storage-and-playback)
- Gerçek zamanlı ses akışı zero-retention'da ÇALIŞIR — Faz 0 hattımız zaten
  gerçek zamanlı; iki dilli transcript'i Recall değil BİZ üretip kendi
  tarafımızda saklarız. Mimariyle birebir uyumlu.
- Alternatif: `{"type": "timed", "hours": N}` ile saatlik hassasiyette kısa
  saklama. Ayrıca Delete Bot Media / Delete Recording uçları anlık, geri
  dönüşsüz silme sağlar.
- **Dikkat 1**: Varsayılan artık 7 gün DEĞİL — 2025-06-12 sonrası açılan
  hesaplarda varsayılan SÜRESİZ saklama. Retention alanını boş bırakmak kabul
  edilemez; her bot isteğinde açıkça set edilecek (kod tarafında zorunlu alan
  yapılacak, unutulamaz).
- **Dikkat 2**: Bot LOG dosyaları (medya değil, işletim logu) medya silmeden
  bağımsızdır ve 7 günde otomatik silinir; API ile medya silmek logları silmez.
- **Boşluk**: Veri bölgesi (ABD/AB) fetch edilen dokümanlarda belirtilmiyor —
  gerçek dış toplantı öncesi DPA/veri bölgesi sorusu Recall'a doğrudan
  sorulacak (ADR-023 gereği zaten Faz 0 kapalı provası için engel değil).

**Uygulama kararı (teknik sorumlu)**: Kapalı prova botları `timed / 24 saat`
(hata ayıklama penceresi — zero-retention'da hiçbir teşhis verisi kalmaz);
gerçek dış toplantı botları `null` (sıfır saklama). Kurucunun "mümkün olan en
kısa" şartının pratiğe dökülmüş hali.

### Kurucu güvenlik şartları (2026-08-12, pilot mimarisi onayıyla birlikte)

1. **Prova sonrası erken silme**: `timed/24h` kabul; ama test sorunsuz biter
   ve teşhis verisine ihtiyaç kalmazsa 24 saati beklemeden explicit delete
   (Delete Bot Media / Delete Recording) çalıştırılır.
2. **Fail-closed retention**: Gerçek dış toplantıda `retention: null`
   ZORUNLU. Kod tasarımı fail-closed: retention alanı açıkça verilmemişse
   bot OLUŞTURULMAZ (istek gönderilmez, hata üretilir). Varsayılana düşme
   yolu yok.
3. **"Zero-retention" ifadesi kapsam netleşene kadar KULLANILMAZ**: Yalnız
   recording media doğrulamak yetmez. Transcript, chat mesajları, bot
   logları, participant metadata, debug/event kayıtları — her artefact'ın
   saklama davranışı AYRI AYRI doğrulanacak (bkz. §Artefact saklama
   doğrulaması).
4. **Veri bölgesi/DPA**: Gerçek dış katılımcılı görüşme öncesi BLOKAJ olmaya
   devam eder. OpenAI transcription için blokaj 2026-08-19'da netleşti:
   yazılı Avrupa yerleşimi + MAM/ZDR (ADR-025) olmadan gerçek Meet sesi yok.
5. **API secret asla repo/chat'e girmez**: Anahtar yalnız secret store /
   ortam değişkeni; kurucu yerleştirir, kod ortamdan okur.

## Artefact saklama doğrulaması (2026-08-12, birincil kaynak: docs.recall.ai/docs/data-retention + bot-overview)

Kurucu şartı 3 gereği artefact-bazlı döküm. Sonuç: **"zero-retention" ifadesi
NİTELEMESİZ KULLANILMAZ** — doğru ifade: "medya-sıfır-saklama + 7 gün log +
kalıcı meeting URL/custom metadata".

| Artefact | `retention: null` kapsıyor mu? | Kaynak/nitelik |
|----------|-------------------------------|----------------|
| Kayıt (ses/video) | ✓ Evet — "Media" tanımında | ✓ doğrulandı |
| Transcript | ✓ Evet — "Media" tanımında; ayrıca Faz 0'da Recall transkripsiyonu HİÇ AÇILMAYACAK (STT bizde) → bu artefact hiç oluşmaz | ✓ doğrulandı |
| Speaker timeline | ✓ Evet — "Media" tanımında | ✓ doğrulandı |
| Participant metadata (katılım/ayrılma, zaman damgaları) | ✓ Evet — "Media" tanımında | ✓ doğrulandı |
| Meeting metadata (başlık) | ✓ Evet — "Media" tanımında | ✓ doğrulandı |
| Debug verisi | ✓ Evet — "Media" tanımında | ✓ doğrulandı |
| Chat mesajları | ~ Muğlak — bot-overview "participant events" içinde sayıyor ama data-retention sayfasının Media listesinde açıkça geçmiyor | Hafifletme: bot chat özelliği kullanılmaz; Recall'a netleştirme sorusu sorulacak |
| **Bot logları** | **✗ HAYIR** — ayrı yaşam döngüsü: 7 günde otomatik silinir, medya silme logları SİLMEZ | ✓ doğrulandı; kaçınılmaz kalıntı |
| **Custom metadata + meeting URL** | **✗ HAYIR** — "Custom metadata and the meeting URL are not deleted upon media expiration/deletion" | ✓ doğrulandı |

Kod tarafına yansıması (fail-closed tasarımla birlikte):
1. Custom metadata alanına ASLA anlamlı/hassas veri yazılmaz — yalnız opak
   iç ID (Recall tarafında kalıcı olduğu için).
2. Meeting URL Recall'da kalıcı iz bırakır — kabul edilen kalıntı; kayda
   geçirildi (URL tek başına içerik taşımaz ama toplantının varlığını gösterir).
3. Recall transkripsiyon add-on'u hiç etkinleştirilmez; iki dilli transcript
   tamamen bizim tarafta üretilir/saklanır.
4. Zero-retention modunda Recall'ın kendi transkripsiyonu gerekseydi
   `prioritize_low_latency` modu şart olurdu — kullanmadığımız için konu dışı,
   bilgi olarak not edildi.

## Sonraki dilim (onay sonrası)

1. ~~Retention/gizlilik doğrulaması~~ — TAMAMLANDI (yukarıda).
2. Recall.ai hesabı — **kurucu aksiyonu** (hesap açma/kimlik işlemi; API
   anahtarı ortam değişkeni/secret olarak teslim edilir, koda yazılmaz).
3. `MeetingIngress` arayüz iskeleti (Faz 0 servisi, izole; Recall = ilk
   gerçekleme, Attendee arayüz adayı olarak göz önünde).
4. Kapalı uçtan uca prova, kurucunun test senaryosuyla: bot katılımı →
   disclosure → TR→EN → EN→TR → düşük güven davranışı → iki dilli transcript
   → kill-switch → bot çıkışı. ≤3 sn medyan ölçülür (hedef; iddia değil).
5. STT/MT/TTS hattı seçimi ayrı küçük dilim (aday karşılaştırması + ölçüm).
