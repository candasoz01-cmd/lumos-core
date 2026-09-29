# Veri ve güven — bu depodaki davranış

| Alan | Değer |
| --- | --- |
| Durum | Kod envanteri — 2026-09-29 |
| Kapsam | Bu depoda okunan yollar. Başka bir kurulum ek servis bağlarsa bu sayfa onu kapsamaz. |
| Public özet | [`ui/src/pages/privacy.astro`](../ui/src/pages/privacy.astro) |

Bu belge, Lumos’un bugün yaptığı veri işlemlerini dosya ve işlev adıyla yazar. Kodda olmayan bir mekanizma burada “uygulanır” denmez.

Bu belge ve `/privacy` sayfası teknik envanterdir; hukuki gizlilik bildirimi değildir. Veri sorumlusu, iletişim ve başvuru kanalı, silme talebi süreci, hukuki dayanak ve KVKK/GDPR hakları burada yayımlanmadı. Bunlar ayrı bir hukuk ve politika kararı bekler.

“Lumos güvencesi”, aşağıdaki **uygulanan** kontrollerin ortak adıdır. Eksik satırlar güvencenin parçası değildir.

## Uygulanan

| Kontrol | Nerede | Ne yapar |
| --- | --- | --- |
| Oturum zorunluluğu | `api/bridge/chat.js`, `api/_lib/hosted_lumos.js` | Barındırılan sohbet, `lumos_session` çerezi veya Bearer oturum yoksa 401 döner. İstekteki `lumos_id` oturumla uyuşmazsa 409. |
| Google erişim belirteci saklanmaz | `api/auth/google/callback.js` | Userinfo çağrısından sonra `access_token` çereze yazılmaz. |
| Mühürlü oturum | `api/_lib/lumos_session.js` | Çerez `lumos_session`, HttpOnly, Secure, SameSite=Lax, `Max-Age` 604800 saniye. İddialar: `sid`, `lumos_id`, `sub`, `email`, `name`, `picture`, `door`, `provider`, `package`, `iat`, `exp`. |
| Çıkış | `api/auth/logout.js` | Tarayıcıdaki oturum çerezini ve köprü vekil çerezini siler. Sunucu tarafında iptal listesi yoktur; `openSession` yalnız `exp` alanına bakar, bu yüzden çerezin kopyası süresi dolana kadar (en fazla 604800 saniye) geçerlidir. |
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
| Toplantı botu saklama şartı | `src/representative/meeting_ingress.py` | `retention` açıkça verilmeden bot isteği oluşturulmaz. Bu kural yalnız o yoldadır. |
| Dönüş ayıklama | `api/_lib/chat_visible_markup.js` | Model metnindeki `TextReference` işaretleri ayıklanır. Bu bir güvenlik filtresi değildir. |

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

E-posta adresi ve `lumos_id` model isteğine konmaz.

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

## Eksik — güvencenin parçası değil

| Konu | Durum |
| --- | --- |
| Ülkeye göre saklama, süre, veri konumu veya yurt dışı aktarım kuralı | Bu depoda yok. |
| Model isteğinden önce maskeleme | Bu depoda yok. |
| Gemini çağrısında `store: false` karşılığı | `buildGeminiRequest` bu alanı koymaz. Anahtar varsa istek `generativelanguage.googleapis.com` adresine gider. |
| Sağlayıcının saklama veya eğitim davranışı | Doğrulanmıyor. |
| Hafıza servisinin saklama süresi ve konumu | Servis bu depoda yok; doğrulanmıyor. |
| Sunucu tarafında oturum iptali | Yok. Çıkış yalnız tarayıcı çerezini siler. |
| Gmail verisi için Google API Hizmetleri Kullanıcı Verileri Politikası beyanı | Bu depoda bir politika beyanı yok; ayrı hukuk/politika kararı bekler. |
| Barındırılan sohbette kullanıcının hangi API’nin çağrıldığını görmesi | Yanıt bu adı taşımaz. |
| Onay katmanının her kurulumda açık olması | `is_confirmation_enabled` yalnız `LUMOS_CONFIRMATION_ENABLED` değeri `1`, `true` veya `yes` ise açıktır. Aksi halde no-op. |
| Sohbet yanıtından önce ayrı onay | Barındırılan sohbet, model yanıtını onay adımı beklemeden döndürür. |
| Çıkışın günlük, hafıza veya sağlayıcı kopyasını silmesi | Yapmaz. |
| `.lumos/logs` için süre veya kullanıcı silme | `append_audit_log` ekler; bu fonksiyonda silme süresi yoktur. |
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

Bir görev birden fazla servisten geçecek genel bir yeniden kontrol döngüsü bu sohbet yolunda yoktur. İkinci çağrı, birincisi hata verir, istisna fırlatır veya boş dönerse kullanılan yedektir.

## Yerel sohbet günlüğü

`packages/kando_runtime/src/kando_runtime/lumos_audit.py` içindeki `append_chat_turn_telemetry`, `user_message` alanını 10000 karakterde keser ve `intent`, `reply`, isteğe bağlı `model` ile birlikte `.lumos/logs/YYYY-MM-DD.log` dosyasına ekler. Barındırılan sohbet işleyicisi bu fonksiyonu çağırmaz. Köprü süreci çağırırsa kayıt o makinededir.

## Şifreli notlar

`src/memory/secure_store.py`, kilit açıkken notları `src/.lumos/notes.enc.json` dosyasına AES-GCM ile yazar. `Memory.cleanup` yalnız `ttl_seconds` dolu notları süresinde düşürür. Süresiz not kalır. Bu modülde kullanıcıya açık bir silme işlevi yoktur.
