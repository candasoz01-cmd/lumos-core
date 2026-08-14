# Representative Faz 0 — Yerel TR↔EN Tercüme Dilimi

> Kapsam notu (2026-08-14): ADR-023 Faz 0'ın Recall'suz ilerleyebilen dilimi.
> Kurucu kararı (2026-08-14): gerçek blokaj Recall değil; Recall yalnız
> toplantıya girişi ve bot-düzeyi kill-switch testini kilitliyor. Bu dilim,
> tercüme zincirini YEREL düzenekte tek başına stabil hale getirir; Recall
> geldiğinde önüne yalnız MeetingIngress konur, arka yeniden yazılmaz.

| Alan | Değer |
|------|-------|
| Dal | `representative-phase0-local-translation-slice` |
| Üst karar | [ADR-023](../decisions/ADR-023-lumos-representative-avatar.md) + [Meet Faz 0 karar tablosu](meet-faz0-giris-yolu-karar-tablosu.md) |
| Durum | Aşama A merge (#724, 2026-08-14). Aşama B kodda: segmenter + half-duplex echo koruması + faster-whisper adaptörü + rig `--audio` modu; T7 mantığı birim testli, donanımlı doğrulama Aşama C provasında |

## Zincir (kurucu listesi, 2026-08-14)

mikrofon girişi → streaming STT → çeviri → confidence/uncertainty kontrolü →
düşük güvenli ifadeyi işaretleme → TTS çıkışı → gecikme ölçümü → feedback/echo
testi → 10–15 dakikalık kapalı prova.

## "Done" kriteri (kurucu, aynen)

Recall olmadan yerelde çalışan, ölçülmüş, düşük-güven davranışı ve feedback
testi geçen TR↔EN zinciri. Hedefler: **medyan ≤3 sn** (kanıtlanana kadar hedef,
iddia değil), anlam kaybı kabul edilebilir, düşük güvenli cümle sessizce
"uydurulmuyor", mikrofon geri beslemesi sistemi bozmuyor.

## Aşamalama (küçük adımlar)

- **Aşama A (bu PR):** Boru hattı çekirdeği + sözleşmeler: stage arayüzleri
  (STT/Translator/TTS), confidence gate, iki dilli append-only transcript,
  gecikme ölçümü, CI'da mock sağlayıcılarla birim testler. Metin-modu rig
  (stdin'den TR cümle → çeviri → gate → TTS) — STT olmadan zincirin geri
  kalanını gerçek çalıştırır.
- **Aşama B:** Mikrofon + streaming STT (aday: faster-whisper, opsiyonel
  bağımlılık grubu — core deps şişirilmez) + echo/feedback testi.
- **Aşama C:** 10–15 dk kapalı prova (iki dilli gerçek konuşma), ölçümler
  belgeye işlenir; done kriteri burada kapanır.

## Kod öncesi 5 soru (dilim düzeyi)

1. **Giriş noktası:** `python -m representative.local_rig` (yalnız geliştirici
   düzeneği; panel/çekirdeğe BAĞLANMAZ — tek arayüz kuralı gereği son
   kullanıcı yüzeyi değildir). Paket: `src/representative/`, izole; mevcut
   modüllere import bağımlılığı yok.
2. **Dev/test/prod:** dev = metin-modu + mock/gerçek sağlayıcı karışımı;
   test = CI'da tamamen mock (ağ yok, ses cihazı yok); prod bu dilimde YOK
   (yerel düzenek; prod yolu MeetingIngress diliminde).
3. **Local/cloud/CI:** STT/TTS yerel (faster-whisper / macOS `say`);
   çeviri sağlayıcısı arayüz arkasında — ilk gerçek adaptör mevcut
   `openai>=1.0` bağımlılığı üstünden (anahtar kurucudan, env ile; koda/repo'ya
   girmez). Repoda gerçek AI Router implementasyonu bulunmadığı doğrulandı
   (ADR-004 karar düzeyinde) — Router gelirse Translator adaptörü ona bağlanır,
   arayüz değişmez.
4. **Geçiş planı:** Aşama A→B→C bu dalda küçük PR'lar; Recall geldiğinde
   `MeetingIngress` STT'nin önüne ses kaynağı, TTS'in arkasına ses çıkışı
   olarak takılır — pipeline sözleşmesi sabit kalır.
5. **Kabul kriterleri:** Aşağıdaki test matrisi + kurucunun done kriteri.

## Test matrisi

| # | Vaka | Nasıl |
|---|------|-------|
| T1 | Düşük güven işaretlenir, sessiz geçilmez | Birim: confidence < eşik → kayıt `low_confidence=True` + uyarı kancası tetiklenir |
| T2 | Güven bilgisi YOKSA muhafazakâr davran (işaretle) | Birim: confidence=None → işaretli (fail-closed ruhu) |
| T3 | Pipeline çeviriye EK ÜRETMEZ | Birim: teslim edilen metin == çevirmen çıktısı, bire bir; pipeline hiçbir şey eklemez/çıkarmaz |
| T4 | **E-sınıfı cümle vakası (kurucu, 2026-08-14):** para/hukuk/taahhüt içeren cümle DOĞRU ve EKSİKSİZ çevrilir, ama YENİ taahhüt üretilmez | Birim: taahhüt cümlesi fikstürü uçtan uca korunur (T3 sözleşmesi) + Aşama C provasında insan değerlendirmeli anlam kontrolü — çeviri modunda bile anlam kayması ayrı vaka olarak ölçülür |
| T5 | İki dilli transcript append-only ve tam | Birim: her söz için ts + kaynak + çeviri + güven + gecikme kaydı |
| T6 | Gecikme ölçümü doğru | Birim: sahte saat ile söz-sonu → TTS-başlangıç; medyan hesabı |
| T7 | Feedback/echo sistemi bozmuyor | Tasarım: yarı-çift-yönlü (half-duplex) kapı — TTS konuşurken mikrofon karesi düşürülür, döngü hiç kurulamaz; yarım kalan söz tamponu da atılır. Birim testli (kapalı kapıda kare sızmaz, kapı açılınca temiz başlar). Donanımlı doğrulama (gerçek hoparlör→mikrofon) Aşama C provasının ilk maddesi |
| T8 | 10–15 dk kapalı prova ölçümleri | Aşama C: medyan ≤3 sn, sapma örnekleri, düşük-güven sayısı belgeye |

## Sağlayıcı seçimleri (teknik sorumlu; arayüz arkasında değiştirilebilir)

- **STT:** faster-whisper (yerel, anahtarsız) — Aşama B'de, `representative`
  opsiyonel bağımlılık grubu olarak.
- **Çeviri:** mevcut `openai` bağımlılığı üstünden ilk adaptör; model/anahtar
  env'den. Confidence: sağlayıcı skoru yoksa modelden kalibre edilmiş
  öz-değerlendirme istenir; o da yoksa None → T2 gereği işaretlenir.
- **TTS (yalnız yerel rig):** macOS `say` — anahtarsız, ölçüm için yeterli.
  Ürün sesi (nötr/profesyonel/sakin erkek, ADR-023) AYRI karar; bu rig sesi
  ürün iddiası değildir.
