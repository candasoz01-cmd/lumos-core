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

## "Done" değerlendirmesi (kurucu kriterleri)

- [ ] Medyan gecikme ≤ 3 sn (jsonl kayıtlarından hesaplanır)
- [ ] TR→EN doğal ve anlaşılır; EN→TR güvenilir (kurucu değerlendirmesi)
- [ ] E-sınıfı cümleler eksiksiz, YENİ taahhüt üretilmemiş (transcript'ten kontrol)
- [ ] Düşük güvenli cümle işaretlendi, sessizce uydurulmadı
- [ ] Echo testi: çeviri döngüsü oluşmadı
- [ ] İki dilli transcript (jsonl + markdown) üretildi

Sonuçlar bu belgeye tarih damgalı işlenir; done ise dilim kapanır ve sıra
"Recall hazır" tetiğine döner (MeetingIngress + bot kill-switch + gerçek prova).
