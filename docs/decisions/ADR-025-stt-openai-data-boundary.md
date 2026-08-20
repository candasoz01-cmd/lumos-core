# ADR-025 — STT OpenAI veri sınırı (Meet sesi)

> 2026-08-19 kurucu kararı: OpenAI resmî dokümantasyonuyla doğrulanmış STT
> veri sınırı, Representative görev sözleşmesine gömülür. Bu ADR o kararı
> kayda geçirir. Gerçek Meet sesi, açılış kapısındaki **yazılı** Avrupa
> yerleşimi + MAM/ZDR onayı olmadan gönderilmez.

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (2026-08-19)** — kurucu; dokümantasyon her maddeyi doğruladı |
| Uygulama durumu | Batch iskelet (sentetik ses) izinli; gerçek Meet sesi kapalı |
| Tarih | 2026-08-19 |
| Üst ilişki | [ADR-023](ADR-023-lumos-representative-avatar.md) Representative / Meet; amaç-bazlı model deseni `OPENAI_MODEL_CHAT` / `OPENAI_MODEL_CYBER` (PR #759) STT'ye `OPENAI_MODEL_STT` olarak genişler |
| Sözleşme | [`docs/contracts/stt-data-boundary-v1.md`](../contracts/stt-data-boundary-v1.md) |

## Karar

Bağlayıcı metin sözleşmededir. Özet:

1. Katılımcı açık onayı olmadan gerçek toplantı sesi yok.
2. Yalnız `POST /v1/audio/transcriptions` (batch). Realtime Meet-sesi kapsam dışı.
3. Ayrı OpenAI API projesi; ZDR/MAM proje düzeyinde (OpenAI'nin kendi önerdiği yapı).
4. `eu.api.openai.com`: depolama **ve** işleme Avrupa'da. Bölgesel işleme ayrı onaydır. %10 ek ücret kabul.
5. Ham ses log/artifact olarak kalıcı saklanmaz.
6. Model yalnız `OPENAI_MODEL_STT` (`whisper-1` / `gpt-4o-transcribe` / `gpt-4o-mini-transcribe`). Sohbet ve cyber env'lerine düşülmez.

**Açılış kapısı:** Avrupa veri yerleşimi + MAM/ZDR organizasyonda yazılı
doğrulanana kadar yalnız sentetik/hassas olmayan test sesi. Onay gelene
kadar madde 1 mutlak.

## Bilinçli sınırlar

- Bu ADR yeni AI sağlayıcısı seçmez (STOP LIST). Mevcut OpenAI yolu, amaç-bazlı model + ayrı proje.
- Recall medya saklama kararı ([Meet giriş yolu taslağı](../drafts/meet-faz0-giris-yolu-karar-tablosu.md)) durur; bu ADR OpenAI transcription tarafını kilitler.
- `LUMOS_STT_RESIDENCY_WRITTEN` operatör bayrağıdır; yazılı hukuki/org onayının kendisi değildir.
