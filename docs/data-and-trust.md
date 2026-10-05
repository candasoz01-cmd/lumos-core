# Veri ve güven — bu depodaki davranış

| Alan | Değer |
| --- | --- |
| Durum | Kod envanteri — 2026-10-05; kaynak 39effc6 |
| Kapsam | Canlı uygulama kaynağı olarak doğrulanan 39effc6 sürümünde okunan yollar. Ortam ayarları ve harici servis davranışları ayrıca doğrulanmadı. Başka bir kurulum ek servis bağlarsa bu sayfa onu kapsamaz. |
| Public özet | [`ui/src/pages/data-and-trust.astro`](../ui/src/pages/data-and-trust.astro) |

Bu belge, Lumos’un bugün yaptığı veri işlemlerini dosya ve işlev adıyla yazar. Kodda olmayan bir mekanizma burada “uygulanır” denmez.

Bu belge ve `/data-and-trust` sayfası teknik envanterdir; hukuki gizlilik bildirimi değildir. Veri sorumlusu, iletişim ve başvuru kanalı, silme talebi süreci, hukuki dayanak ve KVKK/GDPR hakları burada yayımlanmadı. Bunlar ayrı bir hukuk ve politika kararı bekler. Google/Meta kayıtlarında kullanılan `/privacy` adresi mevcut gizlilik bildirimi olarak korunur; teknik envanter onun yerine geçmez.

“Lumos güvencesi”, aşağıdaki **uygulanan** kontrollerin ortak adıdır. Eksik satırlar güvencenin parçası değildir.

## Uygulanan

| Kontrol | Nerede | Ne yapar |
| --- | --- | --- |
| Oturum zorunluluğu | `api/bridge/chat.js`, `api/_lib/hosted_lumos.js` | Barındırılan sohbet, `lumos_session` çerezi veya Bearer oturum yoksa 401 döner. İstekteki `lumos_id` oturumla uyuşmazsa 409. |
| Google erişim belirteci saklanmaz | `api/auth/google/callback.js` | Userinfo çağrısından sonra `access_token` çereze yazılmaz. |
| Mühürlü oturum | `api/_lib/lumos_session.js` | Çerez `lumos_session`, HttpOnly, Secure, SameSite=Lax, `Max-Age` 604800 saniye. İddialar: `sid`, `lumos_id`, `sub`, `email`, `name`, `picture`, `door`, `provider`, `package`, `iat`, `exp`. |
| Çıkış | `api/auth/logout.js` | Bu tarayıcıdaki oturum ve köprü vekil çerezlerini temizler. `session_version` artırımı veya kopyalanmış belirteçleri topluca geçersiz kılma bu sürümde yoktur. |
| İleti sınırı | `buildOpenAIRequest`, `buildGeminiRequest` | İleti en fazla 8000 karakter. Geçmiş son 12 tur, tur başına 4000 karakter. İsteğe bağlı görsel en fazla 380000 karakter. |
| Hafıza özeti sınırı | `cleanMemoryItems` | Yüklü hafızadan en fazla 12 özet, her biri 1000 karakter, model isteğine eklenir. |
| OpenAI `store: false` | `buildOpenAIRequest` | `OPENAI_API_KEY` varsa istek `https://api.openai.com/v1/responses` adresine gider ve gövdede `store: false` bulunur. Bu alan, sağlayıcının kopya tutmadığının doğrulaması değildir. |
| Sağlayıcı adı yanıtta yok | `api/bridge/chat.js` | Kullanıcıya dönen JSON, `provider` ve `model` alanlarını çıkarır. |
| Sohbet işleyicisinde kayıt yok | `api/bridge/chat.js` | Bu işleyici sohbet metnini kendi içinde bir veritabanına veya `.lumos/logs` dosyasına yazmaz. “Hatırla” özeti ayrı hafıza servisine gider (aşağıda). |
| Hafıza kapalıysa yazılmaz | `rememberExplicitMemory` | Hafıza adresi veya belirteç yoksa, ya da onay yoksa, “hatırla” cümlesi kaydedilmez. İşleyici “kaydetmedim” der. “Hatırla” iletisi model API’sine gitmez; yanıtı işleyici verir. |
| Hafıza silme | `api/mobile/memory.js` | `action: delete` ve `confirm: true` gerekir. Servis `ok` dönerse silinmiş sayılır. |
| Gözlem allowlist | `api/_lib/observability.js` | `SENTRY_DSN` veya `LUMOS_AXIOM_TOKEN` yoksa dış gözlem isteği atılmaz. İzinli alanlar: `route`, `status`, `errorCode`, `provider`, `door`, `lumosId`, `method`, `path`, `durationMs`, `upstreamStatus`, `attempt`. E-posta, ad ve `access_token` bu listede değildir. Sentry, hata iletisi ve yığın izinin ilk 2000 karakterini de gönderir. |
| Yerel dosya geçmişi | `ui/src/components/panel/PanelRuntime.astro` | Yükleme özeti `localStorage` içinde, en fazla 5 kayıt. |
| Görev motoru durdurma | `src/task_engine/engine.py`, `profiles.py` | `SECURITY_NEVER_AUTO` ile eşleşen adım durdurulur. Motor dalı `permanent_delete` üyesini bu kontrolün dışında tutar. |
| Onay kapısı | `src/policy/confirmation_policy.py` | Yalnız `LUMOS_CONFIRMATION_ENABLED` değeri `1`, `true` veya `yes` ise açıktır. Üretim ortamı adı tek başına katmanı açmaz; canlı ayar doğrulanmadı. Barındırılan sohbet yanıtı ayrı onay beklemez. |
| Toplantı botu saklama şartı | `src/representative/meeting_ingress.py` | `retention` açıkça verilmeden bot isteği oluşturulmaz. Bu kural yalnız o yoldadır. |
| Dönüş ayıklama | `api/_lib/chat_visible_markup.js` | Model metnindeki `TextReference` işaretleri ayıklanır. Bu bir güvenlik filtresi değildir. |

## Kodda var, ürün akışına bağlı değil

`cleanup_audit_logs`, `delete_audit_logs` ve `Memory.delete_all` yalnız testlerden çağrılır; runtime, UI veya API bağlantısı yoktur. Bu yardımcı işlevler uygulanmış otomatik saklama veya kullanıcıya sunulmuş silme denetimi sayılmaz.

| Yardımcı işlev | Açıkça çağrılırsa | Eksik bağlantı |
| --- | --- | --- |
| `cleanup_audit_logs` | `.lumos/logs` dosya adındaki tarihe göre `LUMOS_LOG_RETENTION_DAYS` (varsayılan 14) günden eski dosyaları siler. | Zamanlayıcı/runtime çağrısı yok; `append_audit_log` çağırmaz. Otomatik günlük saklama süresi uygulanmış değildir. |
| `delete_audit_logs` | `.lumos/logs` altındaki günlük dosyalarını siler. | UI/API veya runtime çağrısı yok. |
| `Memory.delete_all` | Kilit açıkken not listesini boşaltıp kaydetmeyi dener. | UI/API veya runtime çağrısı yok; üründe yerel not silme denetimi değildir. |

## Model isteğine giren veriler

`buildOpenAIRequest` ve `buildGeminiRequest`, `identityInstruction` ile her isteğe şunları ekler:

| Veri | Kaynak | Sınır |
| --- | --- | --- |
| Sabit sistem talimatı | kod | — |
| Kullanıcı adı | oturum çerezi `name` (yoksa “ad yüklenmedi”) | — |
| Hesap sağlayıcısı ve bağlı durumu | oturum çerezi `provider` (varsayılan `google_web`) | — |
| Hafıza durumu | `loadAllowedMemory` | `loaded`, `empty`, `not_granted`, `unavailable` |
| İzinli hafıza özetleri | hafıza servisi | en fazla 12, her biri 1000 karakter |
| İleti | istek gövdesi | 8000 karakter |
| Geçmiş (önceki Lumos yanıtları dahil) | istek gövdesi | son 12 tur, tur başına 4000 karakter |
| Görsel | istek gövdesi | 380000 karakter |

Oturumdaki e-posta adresi ve `lumos_id` model isteğine ayrıca konmaz. Kullanıcının iletiye yazdığı kişisel bilgiler bu sürümün sohbet yolunda otomatik ayıklanmaz.

## Lumos hafıza servisi

Hafıza, sohbet işleyicisinden ayrı bir saklama ve işleme katmanıdır (`callMemoryService`, `api/_lib/hosted_lumos.js`).

- Adres `LUMOS_MEMORY_LOOKUP_URL`; boşsa `BRIDGE_UPSTREAM_URL` + `/memory/hosted/lookup`. Belirteç `LUMOS_MEMORY_SERVICE_TOKEN`; boşsa `KANDO_BRIDGE_SECRET`. Adres veya belirteç yoksa çağrı yapılmaz.
- Her sohbet isteğinde `lookup` çağrılır (`lumos_id`, `purpose: hosted_chat`); model çağrısı olmasa da.
- İleti “hatırla”, “unutma” veya “remember” ile başlıyorsa ve izin varsa `remember` en fazla 1000 karakterlik özeti ve `source_provider` değerini gönderir.
- `consent` ve `delete` (`confirm: true`) eylemleri aynı servise gider.
- Servis bu depoda değildir. Saklama süresi ve konumu bu koddan doğrulanamaz.

## Gmail salt-okuma yolu

`src/integrations/mail/providers/gmail_oauth.py`, `gmail_api_client.py`, `src/integrations/providers/mail_provider.py`.

- Tanımlı izin `https://www.googleapis.com/auth/gmail.readonly`. Google tarafında bu izin posta kutusunu okumaya yetki verir.
- Kod yalnız `users.messages.list` (`q=is:unread`, en fazla 20) ve `format=metadata` ile `Subject`, `From`, `Date` başlıklarını ister; gövde istenmez. Konu 120, gönderen 80 karakterde kesilir.
- Belirteç kasa bağdaştırıcısından okunur; kasada yoksa `vault_credential_not_configured` ile durur.
- Canlı çağrı yalnız `LUMOS_GMAIL_SMOKE` değeri `1`, `true` veya `yes` iken yapılır; aksi halde örnek veri döner.
- Sonuç çağıran entegrasyon adımına döner. Bu yol onu diske yazmaz ve bir model API’sine göndermez.
- Gmail OAuth onay ve geri çağrı işleyicisi bu depoda yoktur (`oauth_contract.py` yalnız sözleşme sabitleridir). welockai.com Google girişi (`api/auth/google/start.js`) yalnız `openid email profile` ister.

## Meta bağlantıları (Facebook, Instagram, Pages, WhatsApp)

`api/auth/meta/*`, `api/integrations/meta/*`, `api/webhooks/meta.js`, `api/_lib/meta_*.js`.

| Sağlayıcı | İstenen izin | Okunan alanlar |
| --- | --- | --- |
| Facebook | `public_profile` | `id`, `name`; `me/accounts` için sayfa `id`, `name` |
| Instagram | `instagram_business_basic` (Instagram Login) | `id`, `username`, `account_type`, `media_count` |
| Pages | `pages_show_list` (Business app) | sayfa `id`, `name` |
| WhatsApp | `business_management`, `whatsapp_business_management` | işletme `id`, `name`; WABA `id`, `name`; telefon `id`, `display_phone_number`, `verified_name` |

- Geri çağrı (`api/auth/meta/callback.js`) kodu erişim belirtecine çevirir, uzun süreli belirtece uzatır, kimliği okur ve `writeMetaCredential` ile belirteç, süre, `auth_mode`, hesap kimliği ve `owner_lumos_id` değerini `LUMOS_CREDENTIAL_VAULT_WRITE_URL` servisine yazar (yalnız `https`). Belirteç çereze yazılmaz.
- Pages, Instagram ve WhatsApp bağlantı kayıtları (`upsertMetaConnection`: sayfa, işletme, WABA, telefon alanları) aynı servise yazılır.
- İmzası doğrulanan webhook olayları (`whatsapp_business_account`, `instagram`, `page`) yükün tamamıyla `LUMOS_META_WEBHOOK_SINK_URL` servisine iletilir. Yük ileti içeriği taşıyabilir.
- Kasa ve webhook servisi bu depoda değildir. Saklama süresi ve konumu doğrulanamaz.
- Bu yol Meta verisini bir model API’sine göndermez.

**Kaldırma.** `api/integrations/meta/token.js` `action: revoke`: önce Meta’da `DELETE /me/permissions`, sonra `deleteMetaCredential`. Meta isteği başarısızsa belirteç yine silinir, yanıt `502 revoked_local` olur. Bağlantı kayıtları ve webhook servisine iletilmiş olaylar silinmez; bu depoda `connection.delete` çağrısı yoktur. Meta veri silme geri çağrısı veya yetki kaldırma geri çağrısı için uç nokta yoktur.

## Eksik — güvencenin parçası değil

| Konu | Durum |
| --- | --- |
| Ülkeye göre hukuk motoru, saklama yeri veya yurt dışı aktarım kuralı | Bu sürümde yok. Sohbet yolunda ülke profili ve sağlayıcı politika kaydı kapısı da yoktur. |
| Tam maskeleme sistemi | Bu sürümün sohbet yolunda otomatik e-posta, telefon ve kimlik benzeri dizi değiştirme uygulanmamıştır. |
| Gemini çağrısında `store: false` karşılığı | `buildGeminiRequest` bu alanı koymaz. Anahtar varsa istek `generativelanguage.googleapis.com` adresine gider. |
| Sağlayıcının saklama, eğitim veya silme API’si | Bu kodla doğrulanmıyor; sağlayıcı kopyası silinmiş sayılmaz. |
| Hafıza servisinin saklama süresi ve konumu | Servis bu depoda yok; doğrulanmıyor. |
| Sunucuda çıkışa bağlı oturum iptali | Bu sürümde `session_version` mekanizması yoktur. |
| Meta kasası ve webhook servisinin saklama süresi ve konumu | Servisler bu depoda yok; doğrulanmıyor. |
| Meta veri silme / yetki kaldırma geri çağrısı | Bu depoda uç nokta yok. |
| Meta bağlantı kayıtlarının ve iletilmiş webhook olaylarının silinmesi | Bu depoda silme çağrısı yok. |
| Gmail verisi için Google API Hizmetleri Kullanıcı Verileri Politikası beyanı | Bu depoda bir politika beyanı yok; ayrı hukuk/politika kararı bekler. |
| Barındırılan sohbette kullanıcının hangi API’nin çağrıldığını görmesi | Yanıt bu adı taşımaz. |
| Onay katmanının her kurulumda açık olması | `LUMOS_CONFIRMATION_ENABLED` açık değilse no-op kalır; canlı ayar doğrulanmadı. |
| Sohbet yanıtından önce ayrı onay | Barındırılan sohbet, model yanıtını onay adımı beklemeden döndürür. |
| Çıkışın günlük, hafıza servisi veya sağlayıcı kopyasını silmesi | Yapmaz. Çıkış bu tarayıcının çerezlerini temizler. Yerel not ve `.lumos/logs` için yalnız testlerden çağrılan yardımcı işlevler vardır; ürün akışına bağlı silme denetimi yoktur. |
| Ürün analitiği etiketi | `ui/src` içinde yok. Bu, her dağıtımın gözlem kapalığı anlamına gelmez; Sentry ve Axiom ortam değişkenine bağlıdır. |
| Reklam veya veri satış entegrasyonu | Bu depoda yok. Bu cümle bir şirket taahhüdü değil, bu kod ağacının envanteridir. |

## Barındırılan sohbet akışı

```text
Kullanıcı iletisi
→ oturum var mı (yoksa 401)
→ lumos_id uyuşuyor mu (değilse 409)
→ "hatırla" ise ve hafıza servisi onaylıysa en fazla 1000 karakter yazılır; değilse yazılmaz
→ "hatırla" iletisi, "ben kimim" ve saat soruları model çağrısı olmadan yanıtlanır
→ hiç model anahtarı yoksa 503 (model çağrısı yok)
→ ileti 8000, geçmiş 12×4000, görsel 380000 karakterle kesilir; ad, sağlayıcı, hafıza durumu ve özetler eklenir
→ OPENAI_API_KEY varsa Responses API (store: false)
→ OpenAI hata dönerse, istisna fırlatırsa veya boş yanıt verirse ve Gemini anahtarı varsa generateContent (store alanı yok)
→ ikisi de yanıt üretmezse 502
→ provider ve model JSON'dan çıkarılır
→ kullanıcı
```

İkinci çağrı, birincisi hata verir, istisna fırlatır veya boş dönerse kullanılan yedektir. Bu sürümde çağrı öncesi ülke/sağlayıcı politika kapısı yoktur.

## Yerel sohbet günlüğü

`packages/kando_runtime/src/kando_runtime/lumos_audit.py` içindeki `append_chat_turn_telemetry`, `user_message` alanını 10000 karakterde keser ve `intent`, `reply`, isteğe bağlı `model` ile birlikte `.lumos/logs/YYYY-MM-DD.log` dosyasına ekler. Barındırılan sohbet işleyicisi bu fonksiyonu çağırmaz. Köprü süreci çağırırsa kayıt o makinededir.

## Şifreli notlar

`src/memory/secure_store.py`, kilit açıkken notları `src/.lumos/notes.enc.json` dosyasına AES-GCM ile yazar. `Memory.cleanup` yalnız `ttl_seconds` dolu notları süresinde düşürür. `LUMOS_MEMORY_TTL_SECONDS` doluysa yeni nota o süre yazılır; boşsa süresiz not kalır. `Memory.delete_all` yalnız testlerden çağrılan bir yardımcı işlevdir; runtime, UI veya API bağlantısı yoktur. Üründe kullanılabilir silme denetimi sayılmaz.


## Mevcut gizlilik bildirimi için açık politika işleri (2026-10-03)

`/privacy` sayfası ve TR/EN `umbrella.privacy` metinleri, kayıtlı URL korunması için `ca258cfc` sürümündeki haliyle tutulur. Bu koruma, bildirimin hukuki veya teknik yeterliliğinin doğrulandığı anlamına gelmez. Bildirimde son güncelleme 15 Temmuz 2026'dır; silme/destek kanalı hâlâ canlı OAuth öncesinde yayımlanacak olarak anlatılır. Somut başvuru kanalı ve veri sorumlusu iletişim ayrıntıları, kesin saklama süreleri ve veri türlerine göre silme süreci bu metinde yer almaz. Hukuki dayanak ve hakların kullanımı ayrıca politika incelemesi gerektirir. Veri satışı/eğitim kullanımı hakkındaki mevcut kurumsal beyanlar bu kod envanterinin doğrulayabildiği davranışlardan ayrıdır; burada yeni hukuki vaat veya uygulama kanıtı üretilmez.
