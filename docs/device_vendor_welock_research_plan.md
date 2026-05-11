# Device vendor adapter plan: WELOCK / smart locks

## Amaç

Lumos içinde akıllı kilit ve benzeri cihaz entegrasyonları için güvenli bir adapter yaklaşımı tanımlamak.
Bu doküman doğrudan cihaz kontrolü eklemez. Sadece WELOCK ve benzeri kilit sistemleri için araştırma ve entegrasyon sınırlarını belirler.

## Güvenlik kuralı

Kilit sistemleri yüksek riskli cihaz sınıfıdır.

- `lock` ve `unlock` işlemleri her zaman `risk_level = high` kabul edilir.
- `lock` ve `unlock` için kullanıcı onayı zorunludur.
- Kullanıcı onayı olmadan kilit açma/kapama isteği çalıştırılmaz.
- Cihaz kimliği olmadan cihaz durumu veya işlem isteği çalıştırılmaz.
- Vendor adapter yoksa işlem `device_provider_not_configured` döner.
- Resmî API, belgeli local protokol veya açık kullanıcı izni yoksa gerçek cihaz kontrolü eklenmez.

## Kabul edilen entegrasyon yolları

1. Resmî vendor API
   - WELOCK veya ilgili vendor tarafından sunulan resmî developer API.
   - OAuth, access token, refresh token veya vendor secret akışı varsa güvenli secret yönetimi gerekir.
2. Belgeli local protokol
   - Bluetooth, Wi-Fi veya yerel ağ üzerinden belgelenmiş protokol.
   - Minimum yetki, cihaz eşleştirme ve kullanıcı onayı gerekir.
3. Kullanıcı yönlendirmesi
   - Resmî API yoksa Lumos sadece kullanıcıyı vendor uygulamasına veya destek dokümanına yönlendirebilir.
   - Lumos kendi başına kilit açma/kapama yapmaz.

## Kabul edilmeyen yollar

- Yetkisiz reverse-engineering ile kapalı protokolü kontrol etmeye çalışma.
- Kullanıcı izni olmadan cihaz işlemi.
- Token veya cihaz secret bilgisini loglama.
- Kilit açma/kapama işlemini düşük riskli işlem gibi değerlendirme.
- Scraping veya kırılgan üçüncü taraf otomasyonlarla güvenlik cihazı kontrolü.

## Önerilen adapter şekli

```text
provider: device
vendor: welock
actions:
  - list_devices
  - lock_status
  - lock
  - unlock
```

## Araştırma notları (WELOCK)

- Resmî geliştirici / OpenAPI dokümantasyonu: vendor sitesi ve belge hostu üzerinden doğrulanmalı; sürüm ve kimlik doğrulama akışı netleştirilmeli.
- Ağ geçidi (gateway) gereksinimi: uzaktan işlemler için ek donanım veya mobil köprü var mı, dokümanda ayrıntı.
- Token ömrü ve yenileme: offline / token süresi doldu senaryoları.
- Test ortamı: üretim anahtarı olmadan mock veya sandbox var mı.

## Sonraki teknik adımlar (kod tarafı)

1. `_vendor_adapter_ready` içinde yalnızca onaylı vendor + yapılandırılmış secret iken `True`.
2. WELOCK için ince bir `WelockClient` (HTTP istemcisi, timeout, hata sınıflandırması).
3. `lock` / `unlock` için Lumos onay kaydı (mevcut gate / pending approval) ile bağlantı — bu dokümanın dışında tasarım.
4. Birim testleri: ağ çağrıları mock; CI’da secret yok.
