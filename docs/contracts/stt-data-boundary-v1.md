<!-- markdownlint-disable MD013 -->

# STT veri sınırı v1

Durum: **Accepted (2026-08-19)** — kurucu kararı; OpenAI resmî dokümantasyonuyla doğrulandı.
Kod izni: sentetik / hassas olmayan test sesi ile batch iskelet. Gerçek Meet sesi
açılış kapısı yazılı kapanmadan **yok**.

Normatif karar kaydı: [ADR-025](../decisions/ADR-025-stt-openai-data-boundary.md).
Güvenlik özeti: [SEC-033+](../security-architecture.md).

Bu sözleşme, Representative STT hattının **kod öncesi tek önkoşuludur**. Aşağıdaki
metin bağlayıcıdır; gevşetmek ayrı kurucu kararı ister.

```
STT VERİ SINIRI (gerçek Meet sesi için önkoşul)
  1. Katılımcı açık onayı olmadan gerçek toplantı sesi gönderilmez.
  2. Yalnız /v1/audio/transcriptions (batch). Realtime kapsam dışı.
  3. Ayrı API projesi; kendi ZDR/MAM ayarı proje düzeyinde.
  4. Bölge: eu.api.openai.com — depolama VE işleme Avrupa'da.
     Not: %10 bölgesel işleme ek ücreti kabul edilir.
  5. Ham ses log/artifact olarak kalıcı saklanmaz. (Endpoint zaten
     application state ve abuse log tutmuyor — dokümantasyonla doğrulandı.)
  6. Model: OPENAI_MODEL_STT (whisper-1 / gpt-4o-transcribe /
     gpt-4o-mini-transcribe). Sohbet/cyber modelinden ayrı.

  AÇILIŞ KAPISI: Avrupa veri yerleşimi + MAM/ZDR onayı organizasyonda
  YAZILI doğrulanana kadar yalnız sentetik/hassas olmayan test sesi.
  Onay gelene kadar 1. madde mutlak.
```

## Doğrulanmış zemin (2026-08-19)

- `/v1/audio/transcriptions` uygulama durumu saklamaz; abuse monitoring
  saklaması bu uç için "None"; uç ZDR-uygun. Sohbet uçlarındaki 30 günlük
  abuse log transcription'da yoktur.
- Mart 2023'ten beri API'ye gönderilen veri, açık izin yoksa model
  eğitiminde kullanılmaz.
- Avrupa (EEA + İsviçre) depolama ve işleme sunar; MAM veya ZDR gerektirir.
  ABD dışı bölge için abuse-monitoring onayı ve Modified Retention
  değişikliği imzası gerekir.
- `eu.api.openai.com` depolamayı Avrupa'ya alır; bölgesel **işleme** ayrı
  onaydır. Audio transcription işleme bölgeleri ABD ve Avrupa olarak
  listelenir — ikisi birden Avrupa'da mümkündür, MAM/ZDR onayına bağlı.
- 5 Mart 2026 sonrası uygun modellerde veri yerleşimi uçları %10 ek ücret
  alır. Bütçe kaydına girer; bölgesel işleme bedava değildir.
- Veri saklama kontrolleri **proje düzeyinde** yapılandırılır; STT ayrı
  OpenAI API projesinde çalışır (amaç-başına ayrı proje/model).

Madde 4'teki "işleme de Avrupa'da" ayrımı kasıtlıdır: bazı bölgeler yalnız
depolama sunar; ses o bölgede saklanıp ABD'de işlenir. Avrupa, ikisini birden
sunan iki bölgeden biridir; Meet sesi için doğru seçimdir.

## Kod kapısı

| Kaynak | Davranış |
| --- | --- |
| Sentetik / hassas olmayan test sesi | Batch `/v1/audio/transcriptions` iskeleti kurulabilir. Model yalnız `OPENAI_MODEL_STT`. |
| Gerçek toplantı / canlı mikrofon sesi | `LUMOS_STT_RESIDENCY_WRITTEN=1` **ve** `OPENAI_STT_BASE_URL=https://eu.api.openai.com/v1` olmadan API çağrısı **yok**. Env bayrağı yazılı org onayını **oluşturmaz**; onay kaydı geldikten sonra operatör tarafından set edilir. |
| Realtime STT | Bu sözleşmenin Meet-sesi kapsamı **dışı**. |

Realtime, sohbet ve cyber modelleri bu sözleşmeyi karşılamaz.
