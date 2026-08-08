# ADR-020 — Meta communications tamamlama istisnası

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (2026-08-08)** |
| Uygulama durumu | **Yetkilendirildi; dilimler ayrı PR'larla uygulanacak** |
| Kapsam | WhatsApp, Instagram ve Facebook platform bağlantıları |
| Kapsam dışı | Meta/Llama model provider, kullanıcıya provider seçtirme, mesaj/yayın write yolu |
| Üst sınır | [`CONSTITUTION.md`](../CONSTITUTION.md), [`ROADMAP.md`](../ROADMAP.md), ADR-012, ADR-015, ADR-016, ADR-019 |

## Bağlam

`src/integrations/providers/communications_provider.py` WhatsApp, Instagram ve
Facebook için katalog, yapılandırma durumu ve salt-okunur kimlik doğrulama
iskeletini zaten içerir. Eksik olan katman yeni bir AI provider değil; mevcut
communications ailesinin gerçek hesap yetkilendirmesi, credential yaşam
döngüsü, webhook güvenliği ve kullanıcıya dürüst bağlantı durumudur.

Genel ROADMAP STOP LIST'i FAZ-1 bitene kadar yeni entegrasyonları durdurur. Bu
karar o kuralı kaldırmaz. Yalnız mevcut üç Meta communications kaydının güvenli
biçimde tamamlanmasına dar istisna verir.

## Karar

### 1. Provider sınırı değişmez

- WhatsApp, Instagram ve Facebook `IntegrationRegistry` altındaki dış platform
  entegrasyonlarıdır.
- Meta/Llama bir model provider adayıdır ve bu ADR'nin kapsamında değildir.
- ADR-019 ile ROADMAP'teki **OpenAI → Claude pilotu → DeepSeek** sırası aynen
  korunur; `ModelRegistry`, Router veya `model_client.py` değiştirilmez.

### 2. Uygulama sırası

Meta communications işi bağımlı, küçük PR'larla ilerler:

1. OAuth başlangıç/callback ve güvenli credential/vault bağlama.
2. Token yenileme, süre sonu ve revoke yaşam döngüsü.
3. Webhook doğrulama, imza kontrolü, replay/idempotency ve fail-closed davranış.
4. Instagram Login ile Facebook Login Graph host/kimlik ayrımı.
5. Salt-okunur bağlantı ve izinli senkron sözleşmesi.
6. Kullanıcı yüzünde dürüst bağlantı durumu.

Her dilim bir önceki PR `main`'e indikten sonra açılır. Her PR test + CI +
merge-sonrası `main` doğrulaması olmadan kapanmış sayılmaz.

### 3. İlk teslimde izin verilen davranış

- Hesap yetkilendirmesini başlatmak ve callback'i doğrulamak.
- Token değerini public repo, URL, log, hata mesajı veya client storage'a
  çıkarmadan sunucu tarafı credential katmanına bağlamak.
- Bağlantı kimliğini ve granted scope'ları salt-okunur doğrulamak.
- İmzalı webhook olaylarını doğrulamak; yalnız izinli metadata/mesaj zarfını
  normalize etmek.
- Tokenı yenilemek veya açık kullanıcı/operatör talebiyle revoke etmek.
- `disconnected`, `authorization_required`, `awaiting_credentials`,
  `connected_readonly`, `expired`, `revoked`, `external_approval_required` gibi
  kanıtlanabilir durumları göstermek.

### 4. İlk teslimde yasak davranış

- WhatsApp/Facebook/Instagram mesajı göndermek veya otomatik yanıtlamak.
- Gönderi, yorum, medya veya story yayımlamak/değiştirmek/silmek.
- Kullanıcı adına sessiz webhook aboneliği, scope genişletme veya yeniden
  yetkilendirme yapmak.
- Tokenı request payload, query/fragment, log, test fixture, UI veya git
  geçmişinde saklamak.
- App Review, Business Verification, credential veya canlı webhook yokken
  entegrasyonu `active` / `live` göstermek.

### 5. Credential ve veri sınırı

- Public kod yalnız opaque `vault_ref`/credential handle taşır; raw secret
  kalıcı uygulama durumuna yazılmaz.
- OAuth `state` tek kullanımlı, süreli ve redirect hedefi allowlist'li olmalıdır.
- Callback token exchange sunucu tarafında yapılır; browser'a yalnız sanitize
  edilmiş bağlantı sonucu döner.
- Webhook challenge ayrı; event `POST` doğrulaması ayrı sözleşmedir. İmza
  doğrulanmadan payload işlenmez.
- Provider hesabı, Lumos ID ve conversation/session kimlikleri birbirine
  dönüştürülmez; kaynak etiketleri ADR-016 sınırına uyar.

### 6. Canlılık ve dış bağımlılıklar

Kod ve testlerin tamamlanması canlı bağlantı kanıtı değildir. Canlı aktivasyon
için Meta App kimliği, doğru ürün yapılandırması, izinler, gerektiğinde App
Review/Business Verification, HTTPS callback/webhook ve operator-controlled
credential gerekir. Bunlardan biri yoksa dış bağımlılık açıkça raporlanır.

## Kabul kriterleri

- [ ] OAuth state/callback güvenlik testleri yeşil.
- [ ] Raw token hiçbir response, log, URL veya depoya sızmıyor.
- [ ] Credential handle ve revoke/expiry durumları testli.
- [ ] Webhook imza, replay ve idempotency testleri testli ve fail-closed.
- [ ] Instagram Graph host/kimlik modu açıkça ayrılmış.
- [ ] İlk dilimde bütün write eylemleri yok veya kapalı.
- [ ] UI katalog ile canlı bağlantıyı ayırıyor.
- [ ] Her PR CI ve merge-sonrası `main` üzerinde doğrulanmış.

## Sonuç

Bu ADR, genel STOP LIST'i kaldırmadan mevcut Meta communications ailesinin
güvenli tamamlanmasını yetkilendirir. Model provider yol haritası değişmez;
canlılık yalnız dış yetkilendirme ve gerçek bağlantı kanıtıyla ilan edilir.
