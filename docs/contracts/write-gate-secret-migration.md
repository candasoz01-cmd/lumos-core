<!-- markdownlint-disable MD013 -->

# Yazma kapısı sırrının ortama taşınması

| Alan | Değer |
| --- | --- |
| Durum | **TASLAK** — uygulanmadı, yetki üretmez |
| Tarih | 2026-11-13 kurucu `main` doğrulaması |
| Üst | [write-authorization-v1](write-authorization-v1.md), [ADR-029](../decisions/ADR-029-write-authority-split.md), TD-46 |
| Yasak | Ajan merge, `workflow_dispatch`, ortam onayı, anahtar basımı, depo sırrını silme, zorunlu kontrol listesini değiştirme |

Bu belge bir kesim prosedürü taslağıdır. Uygulanmış sayılmaz. Merge, imza,
ortam onayı veya sır silme yetkisi üretmez. TD-10 ve TD-46 bu metinle kapanmaz.
Hiçbir güvenlik kontrolü bu belgeyle kapanmaz veya kapatılmaz.

## 2026-11-13 doğrulama kaydı

Kurucu `main`'i 2026-11-13 tarihinde doğruladı. O günkü olgular:

1. `.github/workflows/write-sign-trusted.yml` imza işi kurucunun onayladığı
   `lumos-write-gate` ortamına bağlıdır. Zorunlu inceleyici ve yalnız `main`
   dal politikası yerinde kalır.
2. `.github/workflows/write-attestation-trusted.yml` işi
   `write-attestation-trusted` hâlâ `secrets.LUMOS_WRITE_GATE_SECRET` okur ve
   `environment:` anahtarı yoktur. Üretim HMAC sırrı, `pull_request_target`
   işine depo sırrı olarak açıktır.
3. `.github/workflows/claim-guard.yml` doğru olarak `on: pull_request` kullanır.
   Bunun `pull_request_target` olduğu yönündeki önceki rapor yanlıştır. Tetik
   değiştirilmez. Zorunlu CheckRun adları `claim-guard` ve `write-attestation`
   atlanmaz. Genel prova anahtarı o dosyada kalır. Üretim sırrı oraya eklenmez.
4. `.github/workflows/standing-class.yml` ADR-028 güven kökü olarak
   `on: pull_request_target` kullanır. Tetik değiştirilmez. Sır eklenmez.
   `standing-class` zorunlu durum kontrolü yapılmaz.
5. Bu belge `main`'de yoktu. Sır taşınmamıştı. Yeni anahtar kurulmamıştı.
   Bu kesim için PR yoktu. Kapatılmış bir güvenlik kontrolü yoktu.

`pull_request_target` doğrulayıcıda kalır. Checkout `base.sha` kalır.
Doğrulayıcı `lumos_board.claim_guard_trust` ile taban SHA'dan çıkarılır.
PR başlığı yalnız veri olarak fetch edilir. Üretim sırrı yalnız son doğrulama
adımındadır. Bu dosyayı tanıtan PR kendini üretim sırrıyla imzalayamaz.
`write-attestation-trusted` üzerinde `CLAIM_GUARD_UNAUTHORIZED` beklenen
bootstrap kilididir. Doğrulayıcı yeşile zorlanmaz. `.github/` standing
hariçtir; `standing-class` kırmızısı beklenir. Sınıflandırıcı eligible
yapılmaz.

## Tek güvenli sıra

Anahtar kurulumu, `origin/main` doğrulayıcı işinin `lumos-write-verify`
bağını içermesinden önce başlayamaz. Aynı yeni anahtar imzalayana yazılıp
doğrulayıcı hâlâ eski depo sırrını okursa imza ve doğrulama ayrışır.
Depo sırrı, aşağıdaki başarıdan önce silinirse doğrulama kırılır.

1. `lumos-write-gate` doğrulanır: zorunlu inceleyici `candasoz01-cmd`,
   dağıtım dalları yalnız `main`. `lumos-write-verify` oluşturulur: dağıtım
   dalları yalnız `main`, zorunlu inceleyici yok. İnceleyici, otomatik
   fail-closed kontrolü beklemeye alır. İmza onayı `lumos-write-gate`
   üzerinde kalır. Bu ortam merge onaylamaz.
2. Bu PR merge edilir. Ancak o zaman `main` üzerindeki `pull_request_target`
   `lumos-write-verify` seçer. O ana kadar `main` depo sırrını okumaya devam
   eder. Ajan merge etmez.
3. O merge'den sonra tek bir yeni anahtar üretilir (en az 32 bayt) ve aynı
   değer hem `lumos-write-gate` hem `lumos-write-verify` üzerine yazılır.
   Değer loga, sohbete veya git'e yazılmaz. Bu adım, `origin/main` iş değişikliğini
   gerçekten içermeden yapılmaz.
4. Doğrulama koşulur: üretim imzalı bir aralık `write-attestation-trusted`
   geçer. Genel `write-attestation` işi yalnız genel prova anahtarını
   kullanmaya devam eder.
5. Yalnız bu başarıdan sonra depo sırrı `LUMOS_WRITE_GATE_SECRET` silinir.

## Bu taslağın değiştirmediği kapılar

- `claim-guard` `pull_request` olarak kalır.
- `standing-class` `pull_request_target` olarak kalır.
- `write-attestation-trusted` zorunlu durum kontrolü yapılmaz.
- `standing-class` zorunlu durum kontrolü yapılmaz.
- Hiçbir kontrol bu belgeyle kapanmaz.
- Ajan merge etmez, `workflow_dispatch` çalıştırmaz, ortam onaylamaz.
