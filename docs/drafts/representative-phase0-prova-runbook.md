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

## Prova akışı (kurucu + ben)

1. **TR→EN (5-7 dk):**
   `PYTHONPATH=src .venv/bin/python -m representative.local_rig --audio --translator openai --jsonl-out prova_tr_en.jsonl`
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
