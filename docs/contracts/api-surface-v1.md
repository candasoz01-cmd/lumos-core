# Lumos public API yüzey sözleşmesi — v1 (TD-09)

| Alan | Değer |
| --- | --- |
| Durum | KOD — bu PR ile (koddan doğrulanmış envanter) |
| Borç kaydı | [TECHNICAL_DEBT.md](../TECHNICAL_DEBT.md) TD-09 |
| Kapsam | `api/*` Vercel serverless fonksiyonları (repo kökü, bağımlılıksız) |
| Kaynak gerçeği | Sözleşme ile kod ayrışırsa **kod esastır**; ayrışma borç sayılır |

Bu belge `api/` altındaki public uçların **gözlemlenen** davranışını sabitler.
Amaç: iOS ve 3. taraf entegrasyonları körlemesine değil, tek referansla
bağlanabilsin. Uç ekleyen/değiştiren PR bu belgeyi de günceller.

## Ortak kurallar

- **Kimlik:** mühürlü Lumos oturumu HTTP-only cookie ile taşınır; **token
  gövdeye/URL'e yazılmaz**. Yetki gerektiren uçlar oturum yoksa `401` döner.
  **Mobil istisna:** cookie kullanamayan istemciler oturumu
  `Authorization: Bearer <sealed>` başlığıyla da sunabilir (yalnız köprü
  uçları; cookie önceliklidir).
- **Yöntem uyumsuzluğu:** `405` (`method_not_allowed`).
- **Önbellek:** kimlik/oturum uçları `Cache-Control: no-store`.
- **Hata gövdesi:** JSON uçlarda `{ error: "<kod>" }`; bazı uçlarda ek
  `errorKind` (`unauthorized` | `identity_mismatch` | `model_error`).
- **Yapılandırılmamış bağımlılık:** LLM/köprü anahtarı yoksa uç `503` +
  `unconfigured` döner (hata değil, açık durum sinyali).

## Uçlar

### Kimlik (`api/auth/*`)

| Uç | Yöntem | Başarılı | Hata durumları |
|----|--------|----------|----------------|
| `/api/auth/google/start` | GET | `302` → Google consent (state cookie set). **Mobil:** `?mobile=1&app_state=<20-128 [A-Za-z0-9_-]>` → ayrıca kısa ömürlü (600 sn) mühürlü `lumos_mobile_oauth` cookie set edilir | `400 {ok:false,error:"invalid_app_state"}`; `302 /auth?error=missing_client_id\|auth_not_configured` |
| `/api/auth/google/callback` | GET | Web: `302 /panel?...` (session cookie set). **Mobil akış:** `302 lumos://auth#session=<sealed>&state=<app_state>` | `302 /auth?error=<kod>` (invalid_state, token_http_error, userinfo_http_error, no_access_token, identity_subject_missing, auth_not_configured, missing_credentials_or_code, provider_error) — **mobil akışta** `302 lumos://auth#error=<kod>&state=<app_state>` |
| `/api/auth/session` | GET | `200 {ok:true, authenticated:true, session:{session_id, lumos_id, email, name, picture, door, provider, package, exp}}` | `401 {ok:false, authenticated:false[, error:"identity_missing"]}` |
| `/api/auth/logout` | GET \| POST | GET → `302`; POST → `200 {ok:true, logged_out:true}` (session + bridge cookie temizlenir) | `405` |
| `/api/auth/readiness` | GET | `200 {ok:true, live_login, client_id_prefix, redirect_uri, has_client_secret, has_dedicated_state_secret, stable_identity, has_dedicated_identity_secret, consent_memory_lookup, door}` | `405` |

**Not:** `readiness` yalnız yapılandırma sağlık sinyali döndürür — gizli değer
değil, yalnız `client_id_prefix` (ilk 8) ve boolean bayraklar.

### Köprü (`api/bridge/*`)

| Uç | Yöntem | Başarılı | Hata durumları |
|----|--------|----------|----------------|
| `/api/bridge/health` | GET \| HEAD | `200 {status:"ok", gate:true, llm:true, mode:"hosted_secure", model}` | `401 unauthorized`; `503 {status:"unconfigured", llm:false}`; `405` |
| `/api/bridge/status` | GET | `200 {health:"ok", chat:"ready", visionConfigured, model, provider, runtime:"hosted"}` | `401 unauthorized`; `503 {health:"unconfigured", chat:"unconfigured"}`; `405` |
| `/api/bridge/chat` | POST | `200 {reply, mode, identity}` (mode: hosted_chat \| hosted_local \| hosted_identity_status) | `400 invalid_json\|message_required`; `401/403 {error, errorKind}`; `503 model_unconfigured`; `502 model_unavailable`; `405`; `204` (OPTIONS) |
| `/api/bridge/[...path]` | İstek yöntemi upstream'e olduğu gibi geçirilir (GET/HEAD dışı yöntemlerde gövde forward edilir) | Upstream yanıtı ve durum kodu proxy'lenir (`Cache-Control: no-store`) | `404 bridge_proxy_forbidden` (allowlist dışı yol); `401 bridge_proxy_unauthorized`; `503 bridge_proxy_unconfigured\|_auth_unconfigured\|_secret_unconfigured`; `502 bridge_upstream_unreachable` |

### Mobil (`api/mobile/*`)

| Uç | Yöntem | Not |
|----|--------|-----|
| `/api/mobile/chat` | POST | `bridge/chat` ile **aynı** handler (re-export). Ayrı yol adı, mobil istemcinin sabit uç kullanabilmesi için; davranış/sözleşme `bridge/chat` ile birebir aynıdır. |

**Proxy allowlist (`ALLOWED_BRIDGE_PATHS`):** `task`, `chat`, `health`,
`status`, `last-result`, `controlled`, `transcribe`, `panel/upload`. Bu küme
dışındaki yol `404` (güvenlik olayı olarak audit'e düşer). Köprü secret'ı
**yalnız** caller-auth + allowlist geçtikten sonra enjekte edilir; gerçek
upstream URL yanıta yazılmaz.

## Güvenlik sınırları (kodla doğrulanmış)

- `bridge/[...path]`: allowlist-dışı yol, yetkisiz proxy ve `invalid_state`
  gibi olaylar güvenlik olayı olarak kaydedilir (observability).
- `chat`: client/session `lumos_id` uyuşmazlığı `identity_mismatch` ile
  reddedilir.
- Gönderilmeyen alanlar (observability allowlist'i): email, name, picture,
  sub, access_token, code, state, cookie, client_secret.

## Mobil akış — bilinen riskler (açık kayıt)

- **Deep-link token taşıma:** mühürlü oturum `lumos://auth#session=…`
  fragment'ında dönüyor. Fragment sunucuya gitmez, ancak cihazda aynı özel
  şemayı kaydeden başka bir uygulama varsa token kaçırılabilir (custom-scheme
  hijack). `app_state` bağlaması kısmi koruma sağlar; kalıcı çözüm
  **universal link + ASWebAuthenticationSession** olarak açık kalmıştır.
- **Bearer kabulü** oturumu cookie korumalarının (SameSite, HttpOnly) dışına
  taşır; sızan mühürlü oturum doğrudan kullanılabilir. Oturum ömrü (7 gün)
  bu nedenle mobil için ayrıca değerlendirilmelidir.

## v1 sınırları (dürüst)

- Sürümleme yok: uçlar `/api/*` altında sürümsüz. Kırıcı değişiklik bu
  sözleşmede `supersedes` ile işaretlenmeli.
- Şema doğrulaması gövde düzeyinde asgari (`chat` yalnız `message` zorunlu).
  Tipli istek/yanıt şeması (JSON Schema) v2 adayı.
- Rate limit / kota bu katmanda tanımlı değil (Vercel/altyapı seviyesinde).
