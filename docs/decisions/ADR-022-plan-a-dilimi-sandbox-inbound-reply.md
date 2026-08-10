# ADR-022 Eki — A Dilimi Uygulama Planı: Sandbox WhatsApp Gelen-Mesaja Yanıt

| Alan | Değer |
|------|-------|
| Durum | **Onaylı plan (2026-08-10)** — kurucu onayı, iki teknik düzeltmeyle; kod bu plandaki dilim sırasına göre gelir |
| Üst karar | [ADR-022](ADR-022-meta-write-authority-domains.md) (Accepted) — A sınıfı ilk uygulama dilimi |
| Kapsam | YALNIZ sandbox (Test WABA `1533094525525137`, test numarası `1274066459120730`); gerçek numara/ücretli işlem yok |

## Beş soru (kurucu ayrımıyla)

### 1. Inbound event kaynağı

Webhook `welockai.com/api/webhooks/meta` (challenge + imza kanıtlı; 1046 secret'ı
S4a'dan beri kabul ediliyor). Açık doğrulama işi (D1): 1046'nın webhook
aboneliğinde WhatsApp **`messages` alanı** abone mi — konsoldan kanıtlanacak,
varsayılmayacak.

**Kurucu düzeltmesi (2026-08-10): inbound METİN kalıcı saklanmaz.** İlk dilimde
kontrol düzlemi kanıtlanır; yanıt sabit/deterministik sandbox metnidir. Gateway'de
tutulan zarf yalnız: `message_id, from_wa_id, phone_number_id, waba_id,
timestamp, message_type` + gerekirse **içerik hash'i**. Mesaj gövdesinin
TTL/şifreleme/retention modeli, akıllı içerik üretimine geçilirken AYRI kararla
gelir.

### 2. connection_id + AuthorityDomain eşleşmesi

Gateway `connection.lookup(phone_number_id, waba_id)` — **tam eşleşme,
fail-closed**: eşleşme yoksa gönderim yok, olay "eşleşmeyen inbound" olarak
denetim kaydına düşer. Dönen kayıttan `connection_id` + owner bulunur;
AuthorityDomain eşleşmesi `connection_ids[]` üzerinden yapılır.

### 3. Customer-service window kanıtı

Her inbound'da `(connection_id, from_wa_id) → last_inbound_at` güncellenir;
gönderim öncesi sunucu `now − last_inbound_at < 24h` ön-kontrolünü KENDİ
kaydından yapar. **Açık kayıt: bu yerel ön-kontroldür; pencerenin son otoritesi
Meta'dır** — Meta reddederse sonuç `failed` olarak finalize edilir, yerel kontrol
Meta kararının yerine geçmez.

### 4. Send audit + idempotency — iki aşamalı (kurucu düzeltmesi, 2026-08-10)

Tek aşamalı "gönder→audit" fail-closed ÇELİŞKİLİDİR; model iki aşamalı:

1. **Rezervasyon:** gönderimden ÖNCE `SEND_INTENT` kaydı + idempotency marker
   (`SEND__<inbound_message_id>`) atomik yazılır. **Bu yazım başarısızsa gönderim
   YAPILMAZ** — gerçek fail-closed budur. Marker zaten varsa (webhook
   yeniden-teslimatı) ikinci gönderim fiziken engellenir.
2. **Finalize:** Meta çağrısından sonra AYNI kayıt `sent/failed` +
   `provider_message_id` ile güncellenir. Append-only denetim izi: rezervasyon +
   finalize satırları birlikte tam hikâyeyi verir; finalize edilmemiş intent =
   görünür anomali.

### 5. Kill-switch ve scope guard sırası

Gönderim öncesi zincir, kısa devreli ve bu sırayla:

```
(0) global kill-switch  ← SIFIRINCI kontrol; tüm yazma alanlarının üstünde
(1) AuthorityDomain active?
(2) sınıf = A ve eylem eşleşiyor?
(3) pencere ön-kontrolü (yerel; son otorite Meta)
(4) SEND_INTENT + idempotency rezervasyonu (yazılamazsa DUR)
(5) oran limitleri
→ GÖNDER → finalize (sent/failed + provider_message_id)
```

`doesNotMatch(/messaging/)` scope guard'ı **en son, kendi başına ayrı bir PR'da**
bilinçli güncellenir; messaging scope'u isteyen kod, koruma altyapısı main'de
olmadan asla merge edilmez.

## App Review — varsayım yok, kanıt deneyi (D1)

Bilinen tek kesinlik: mevcut OAuth token'ı (`business_management +
whatsapp_business_management`) mesaj GÖNDEREMEZ (scope'ta yok). Gerisi deneyle:

- **Deney 1:** Konsolun sandbox "Generate access tokens" yolu dev-mode'da App
  Review'suz gönderim yetkisi veriyor mu? (Alıcı ekleme adımına KADAR koşulur.)
- **Deney 2:** `whatsapp_business_messaging` içeren AYRI bir Login Configuration
  ("Lumos WhatsApp Reply"; ReadOnly config'e dokunulmaz) admin/tester
  hesabına dev-mode'da bu izni grant ediyor mu?
- Sonuç tablosu bu dosyaya işlenir: sandbox için kanıtlanan yol vs. yalnız live
  mode için gereken (App Review). Live mode bu dilimin kapsamı dışıdır.

## Dilimler

| Dilim | İçerik | Kod? |
|-------|--------|------|
| D1 | Konsol: webhook `messages` aboneliği doğrulaması + izin deneyleri (1 ve 2). **Alıcı ekleme adımında DUR** — dış sistemde gerçek hesap etkisi, kurucu onay kapısı | YOK |
| D2 | Gateway ops: `inbound.store` (zarf, metin yok) · `connection.lookup` · `SEND_INTENT/finalize` · `AUDIT` | Var |
| D3 | Kontrol zinciri + gönderim yolu; scope guard PR'ı AYRI ve en son | Var |
| D4 | Canlı sandbox kanıtı (kurucu telefonu alıcı olarak eklendikten sonra) | Kanıt |

D1 sonucu raporlanıp kanıtlanmadan D2'ye geçilmez.
