# Barındırılan yapay zekâ kapıları — kesintisiz üretime geçiş planı (#968 → #970)

Durum: **TASLAK.** Bu belge hiçbir adımı başlatmaz. Secret, deploy, Vercel/Cloudflare
ayarı, imza ve merge yalnız kurucunun ayrı onayıyla yapılır. `standing-class`
insan onayı ve `write-attestation-trusted` imza kapısı korunur.

## Doğrulanmış platform kuralları

| Kural | Kaynak | Bu plana etkisi |
|---|---|---|
| Vercel ortam değişkeni değişiklikleri yalnız **yeni** dağıtımlara uygulanır; çalışan dağıtım eski değerleri kullanır. | vercel.com/docs/environment-variables | Değişken girmek tek başına çalışan sohbeti etkilemez; etki yeniden dağıtımla gelir. Değişkeni önce girmek güvenlidir. |
| Preview değişkenleri belirli bir dala özel tanımlanabilir. | aynı sayfa | Üretime dokunmadan PR dalında canlı deneme yapılabilir. |
| Instant Rollback, önceki dağıtımı **kendi ortam değişkenleriyle** geri getirir; Hobby planında yalnız bir önceki dağıtıma dönülebilir. | vercel.com/docs/instant-rollback | Geri dönüş değişken silmeyi gerektirmez. Vercel planı doğrulanmadı; Hobby ise her adımdan sonra canlı doğrulama zorunludur (iki adım geriye dönülemez). |
| Workers Free: günde 100.000 Worker isteği, DO 100.000 istek / 100.000 satır yazma. | Cloudflare paneli (hesap Free) ve belgeler | Bkz. `ops/usage-guard/README.md`. |

## Süreç içi kanıt

`tests/test_hosted_ai_rollout_matrix.test.mjs` her adımı gerçek kodla canlandırır
(gerçek Worker kodu, gerçek HMAC imzası, SQLite Durable Object taklidi):

| Adım | Beklenen | Test |
|---|---|---|
| #968, izin listesi önceden girilmiş | Kurucu 200, diğerleri 403 | geçti |
| #968, izin listesi yok | Herkes 403 (**sohbet kesilir**) | geçti |
| #970, Worker + sayaç değişkenleri hazır | Kurucu 200 | geçti |
| #970, sınır dolu | 429, sağlayıcıya gitmez | geçti |
| #970, sayaç değişkeni yok / Worker yok / anahtar uyuşmuyor | 503 (**sohbet kesilir**), sağlayıcıya gitmez | geçti |
| #970'ten #968 dağıtımına geri dönüş | Kurucu 200 | geçti |

Bu kanıt kod mantığını doğrular; **canlı ortamı doğrulamaz.** Canlı kanıt aşağıdaki kapılarla toplanır.

## Sıra (her kapı geçilmeden sonraki adıma geçilmez)

**Adım 0 — başlangıç kaydı (salt okuma).** Üretimdeki dağıtım kimliği ve commit not edilir; giriş yapmış kurucuyla tek sohbet testi 200 (`hosted_chat`).

**Adım 1 — #968 için değişken (kurucu).** Vercel → `LUMOS_HOSTED_AI_ALLOWED_IDS` = kurucu Lumos ID'si. Önce yalnız **Preview** kapsamında, `claude/hosted-ai-access-gate` dalına özel.
- Kapı 1a: #968'in preview dağıtımı yeniden oluşturulur; preview adresinde kurucu 200, başka hesap 403.
  Not: Google girişinin preview adresinde çalışıp çalışmadığı doğrulanmadı (callback adresi izin listesine bağlı). Çalışmazsa bu kapı üretim adımında canlı testle kapatılır.
- Kapı 1b: Aynı değişken **Production** kapsamına da girilir. Çalışan üretim değişmez (yeni dağıtım yok). Adım 0 testi tekrarlanır: hâlâ 200.

**Adım 2 — #968 merge (kurucu, imza + SHA onayı).** Merge yeni üretim dağıtımını başlatır; değişken bu dağıtıma gömülür.
- Kapı 2: Dağıtım tamamlanınca kurucu sohbeti 200; başka bir test hesabı 403; Vercel loglarında `hosted_ai_access_denied` yalnız o hesap için.
- Geri dönüş: Instant Rollback → Adım 0 dağıtımı.

**Adım 3 — Worker (kurucu).** `ops/usage-guard`: ortak anahtar `wrangler secret put`, sonra `wrangler deploy`. Henüz Vercel ona bağlı değildir; üretim etkilenmez.
- Kapı 3: Worker'a imzasız istek 401; doğru imzalı tek istek 200. Cloudflare panelinde günlük istek sayısı beklenen aralıkta.

**Adım 4 — #970 için değişkenler (kurucu).** `LUMOS_USAGE_GUARD_URL`, `LUMOS_USAGE_GUARD_SECRET`: önce Preview (#970 dalı), sonra Production. Çalışan üretim değişmez.
- Kapı 4: #970 preview dağıtımında kurucu 200; sayaç kaydı Cloudflare'de görünür.

**Adım 5 — #970 hedefi `main` yapılır, testler yeniden çalışır, merge (kurucu, imza + SHA onayı).**
- Kapı 5: Kurucu 200; kısa sürede 11 istekte 11.'si 429; Worker 503/401 oranı sıfır.
- Geri dönüş: Instant Rollback → Adım 2 dağıtımı (#968). Worker ve değişkenler yerinde kalabilir.

## Doğrudan Worker erişimi — koruma tasarımı (uygulanmadı)

Sorun: `*.workers.dev` adresi herkese açıktır. İmzasız istek Durable Object'e ulaşmaz (401) ama 1 Worker isteği sayılır; günlük 100.000 sınır doldurulursa ücret çıkmaz, sohbet kapanır (erişilebilirlik riski).

| Seçenek | Ne yapar | Maliyet | Değişiklik türü | Açık soru |
|---|---|---|---|---|
| A. `workers_dev: false` + kendi alan adı (ör. `usage.welockai.com`) | Herkese açık workers.dev adresi kapanır | 0 | Cloudflare alan/DNS ayarı (üretim) | welockai.com DNS'inin Cloudflare'de olduğu doğrulanmalı (panelde alan adı görünüyor) |
| B. A + WAF özel kuralı: `POST /consume` dışını ve `x-lumos-sig` başlığı olmayanı engelle | Engellenen istek Worker'ı çalıştırmaz | 0 (Free planda özel kural var) | WAF ayarı | Engellenen isteğin Worker kotasından düşmediği belgeyle doğrulanmalı |
| C. A + hız sınırı kuralı | Free: 1 kural, yalnız IP, 10 sn pencere | 0 | WAF ayarı | Vercel çıkış IP'leri değişken; kural geniş tutulmalı |
| D. Hiçbir şey | — | 0 | — | Risk: kotayı dolduran saldırı sohbeti gün sonuna (00:00 UTC) kadar kapatır |

Öneri: A + B. Ücret yok, kod değişikliği yalnız `wrangler.jsonc` (`workers_dev: false` + `routes`). Uygulanması kurucu kararıdır.
