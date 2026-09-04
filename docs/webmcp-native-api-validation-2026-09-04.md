# MCP/WebMCP — Native + API-backed final validation record

**Tarih:** 2026-09-04
**Kapsam:** Yalnızca MCP/WebMCP kapanışı. Yeni mimari, yeni özellik, yeni ADR yok.
**Kapatılan açık:** #818'de kayda geçen *"API-backed completion path was not exercised natively"*.

---

## 1. Neden bu koşum gerekliydi

`ui/e2e/webmcp-native-verify.mjs` native Chrome kanıtını üretiyor, ama paneli
`startStaticServer(DIST_DIR, port)` ile **statik dist** üzerinden servis ediyor
(`webmcp-native-verify.mjs:153`). Canlı `panel_tasks_server` yok; bu yolda panelin
yazmaları `shouldSkipGorevlerTasksApi()` / `shouldFallbackGorevlerTasksLocal()`
dallarından localStorage'a düşer. Yani native kanıt **vardı**, ama sunucu tarafı
policy + confirmation zincirinden geçen yol native olarak **denenmemişti**.

Bu koşum aynı native ortamı kurar, farkı tek noktada kapatır: panel canlı
`panel_tasks_server.py` REST yüzeyine bağlıdır.

---

## 2. Ortam

| | |
| --- | --- |
| Commit | `4b4a909a44307c9eb33d7c9615e615776839d51e` — *Merge pull request #821 from candasoz01-cmd/fix/webmcp-complete-consent-gate* |
| Ağaç | `origin/main`'den detached worktree — koşum başlangıcında temizdi (`git status` = 0 değişiklik); koşum sonrasında bu kayıt ve sürücü betiği olmak üzere iki kanıt dosyası oluştu |
| Tarayıcı | Google Chrome **152.0.7977.76** |
| Bayraklar | `--enable-features=WebMCP --enable-blink-features=DocumentModelcontext` |
| Profil | geçici `user-data-dir` (kullanıcı profiline dokunulmadı) |
| Sayfa enjeksiyonu | **YOK** — `addInitScript` kullanılmadı, shim/polyfill yok |
| Panel | `ui/dist` statik servis → `http://127.0.0.1:24063/panel/` |
| **Tasks API** | **`panel_tasks_server.py` → `http://127.0.0.1:8766` (canlı)** |
| Sunucu env | `LUMOS_MODE=online`, `LUMOS_PROFILE=guvenli_yurut`, `LUMOS_SESSION_UNLOCKED=true`, **`LUMOS_CONFIRMATION_ENABLED=true`** |
| `LUMOS_BASE_DIR` | geçici dizin — kullanıcının `.lumos`'una dokunulmadı |
| Onaylar | **İnsan** verdi (Chrome penceresinde elle tıklama). Otomatik onay yok. |
| Platform | macOS 26.6.2 / Darwin 25.6.0 arm64, Node v25.2.1, Python 3.14.2 |
| Sürücü | `ui/e2e/webmcp-native-api-drive.mjs` (interaktif; otomatik onay vermez) |
| Ham log | `webmcp-native-api-run.log` (233 satır) |

API tabanı sayfaya **enjekte edilmedi**: `panel.astro:35` build zamanı varsayılanı
(`http://127.0.0.1:8766`) kullanıldı ve tasks server tam o portta ayağa kaldırıldı.
Sayfada `window.LUMOS_PANEL_TASKS_API_BASE` tanımsızdı.

---

## 3. Native yüzey kanıtı

```json
{
  "chromeUserAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
  "brandString": "[object ModelContext]",
  "constructorName": "ModelContext",
  "prototypeMembers": ["constructor", "executeTool", "getTools", "ontoolchange", "registerTool"],
  "registerToolSource": "function registerTool() { [native code] }",
  "executeToolSource": "function executeTool() { [native code] }",
  "documentPrototypeGetter": "function get modelContext() { [native code] }",
  "ownPropertyOnDocument": false,
  "globalInterfaces": ["ModelContext", "WebMCPEvent"],
  "pageStatus.registered": ["lumos-list-tasks", "lumos-propose-task", "lumos-complete-task"]
}
```

`ownPropertyOnDocument: false` + `Document.prototype` üzerinde `[native code]`
getter → yüzeyi sayfa değil tarayıcı sağlıyor. Önceki kayıttan farklı olarak bu
koşum **headed** (UA'da `HeadlessChrome` yok), çünkü onayları insan verdi.

---

## 4. Adım adım kanıt

Tüm çağrılar native imzayla: `executeTool(RegisteredTool, argsJsonString)`.

### 4.1 Consent yokken sızıntı yok — ve üyelik oracle'ı kapalı

`lumos-complete-task`, izin yokken **üç farklı girdiyle** çağrıldı:

| Girdi | Sonuç |
| --- | --- |
| `{"ref":"boyle-bir-gorev-yok-12345"}` (var olmayan) | `read_consent_required` / `detail: complete_requires_read_consent` |
| `{}` (ref yok) | **birebir aynı payload** |
| `{"ref":"tsk_1788510726914_7851"}` (revoke sonrası, gerçek + tamamlanmış görev) | **birebir aynı payload** |

Üçünde de: onay penceresi **açılmadı**, **hiçbir API isteği gitmedi**, gövdede
`task` / `tasks` / `count` **yok**. Sunucuda arama yapılmadığı için ayrışacak bir
cevap üretilmedi — oracle native ortamda da kapalı.

### 4.2 Okuma izni — ret

```
← {"ok":false,"approved":false,"reason":"read_consent_required",
   "detail":"user_rejected","consent":{"granted":false,"scope":"session"}}
```

İki kez bağımsız olarak "Vazgeç" ile üretildi, ikisi de aynı. Gövdede `tasks`/`count`
yok — boş tahta değil, ret. `detail` ayrımı korunuyor: `user_rejected` (kullanıcı
reddetti) ≠ `complete_requires_read_consent` (izin hiç istenmedi).

Onay diyaloğu kullanıcıya şunları gösterdi: paylaşılan alanlar, **kapsam**
("yalnızca bu tarayıcı oturumu, sekme kapanınca sona erer"), **geri alma yolu**
("Görevler modülündeki 'İzni geri al' düğmesi") ve **kaynak**
("Ajan · WebMCP · lumos-list-tasks").

### 4.3 Okuma izni — onay

```
← {"ok":true,"approved":true,
   "consent":{"granted":true,"scope":"session","at":"2026-09-04T08:31:05.653Z"},
   "count":0,"tasks":[]}
```

Panel rozeti `data-granted="true"`, "İzni geri al" düğmesi göründü,
`sessionStorage["lumos_panel_webmcp_read_consent_v1"] = {"granted":true,"at":"…"}`.

### 4.4 `lumos-propose-task` → insan onayı → **API üzerinden yazma**

Onay diyaloğu yazılacak her alanı gerçek değeriyle gösterdi:
`Başlık: MCP closeout native API smoke` · `Öncelik: yüksek (yuksek)` ·
`Zaman: Yarın 14:00` · `Durum: bekliyor` · `Kaynak: Ajan · WebMCP · lumos-propose-task`.

```
← {"ok":true,"approved":true,"task":{"id":"tsk_1788510726914_7851",
    "title":"MCP closeout native API smoke","priority":"yuksek","status":"bekliyor","when":"Yarın 14:00"}}
   API istekleri: POST /lumos-confirm/request, POST /tasks, GET /tasks
```

Sunucu tarafı gerçek (`GET /tasks`):

```json
{"id":"tsk_1788510726914_7851","title":"MCP closeout native API smoke",
 "status":"active","createdAt":"2026-09-04T08:32:06Z","completedAt":null}
```

### 4.5 `lumos-complete-task` → insan onayı → **API üzerinden tamamlama** ← *kapatılan açık*

Diyalog durum değişikliğini ve **değişmeyenleri** açıkça yazdı:
`Durum değişikliği: bekliyor → tamamlandı` · `Öncelik: yüksek (değişmiyor)` ·
`Zaman: Yarın 14:00 (değişmiyor)` · `Eşleşen referans: tsk_1788510726914_7851`.

```
← {"ok":true,"approved":true,"task":{"id":"tsk_1788510726914_7851","status":"tamamlandi",…}}
   API istekleri: POST /lumos-confirm/request, POST /tasks/complete, GET /tasks
```

Sunucu tarafı gerçek:

```json
{"id":"tsk_1788510726914_7851","status":"done",
 "createdAt":"2026-09-04T08:32:06Z","completedAt":"2026-09-04T08:32:58Z"}
```

Olay güncesi:

```json
[{"type":"task_created","taskId":"tsk_1788510726914_7851","ts":"2026-09-04T08:32:06Z"},
 {"type":"task_completed","taskId":"tsk_1788510726914_7851","ts":"2026-09-04T08:32:58Z"}]
```

Her iki mutasyonda da sıra aynı: **`POST /lumos-confirm/request` (sunucu tarafı
confirmation kaydı) → mutasyon endpoint'i → doğrulama okuması.** `confirmation_enabled: true`
olduğu `GET /tasks` yanıtında da görünüyor. Bu, localStorage yolu değildir.

### 4.6 Revoke → erişim kesildi

```
revoke sonrası: {"granted":"false","revokeVisible":false,"sessionStorage":null}
```

Ardından `lumos-complete-task` hem gerçek (tamamlanmış) ref hem uydurma ref ile
çağrıldı → §4.1'deki **aynı** reddi aldı, dialog açılmadı, API'ye gidilmedi.
Yani revoke sonrası ne veri döndü ne de "bu görev var/tamamlanmış" bilgisi sızdı.

---

## 5. Bu kayıtla kapanan / kapanmayan

### Kapandı

* API-backed `propose` ve **`complete`** yolları native `document.modelContext`
  üzerinden, insan onayıyla, canlı `panel_tasks_server` REST yüzeyinde koşuldu.
* Sunucu tarafı confirmation zinciri (`POST /lumos-confirm/request` → mutasyon)
  native ortamda doğrulandı; `LUMOS_CONFIRMATION_ENABLED=true` ile.
* Consent yokluğunda sızıntı yok; üyelik oracle'ı native ortamda da kapalı.
* Revoke gerçekten kesiyor (bellek + `sessionStorage` + sonraki çağrılar).

### Bilinen sınırlar (bu dilimde kapatılmadı, kapatılması da önerilmiyor)

1. **`lumos-list-tasks` sunucudan okumaz.** İzin verildikten sonraki başarılı
   `list` çağrısında API'ye **hiçbir istek gitmedi**; tool panelin bellekteki
   `panelGorevlerTasks` projeksiyonunu döndürür. Bu koşumda tahta o anda boş
   olduğu için sunucu gerçeğiyle örtüştü, ama iki kaynağın ayrışabileceği
   durum test edilmedi. *(Yazma yolları etkilenmiyor — onlar API'ye gidiyor.)*
2. **`task_not_found` ayrımı**, izin **verildikten sonra** hâlâ mevcut — bu
   `docs/webmcp-challenge-2026.md:151`'de zaten "kalan sınır" olarak kayıtlı ve
   bilinçli: izin verilmişken tahta zaten okunabilir olduğu için oracle değil.
3. **ChatGPT in-app browser** yine denenmedi. Kanıt yalnızca Chrome 152 içindir.
4. **Client-side fallback yolu bu koşumda test edilmedi.** Sunucu erişilemezken
   panelin localStorage'a düşmesi ve sunucu policy katmanının atlanması ayrı bir
   güvenlik konusudur — bkz. §6.
5. Koşum **tek makinede, tek oturumda, tek kez** yapıldı; CI'da tekrarlanmıyor.
   `npm run e2e:webmcp` (harness) ve `e2e:webmcp:native` (statik native) CI'da;
   API-backed native koşum **elle**dir.

---

## 6. Bu kapanışın DIŞINDA bırakılan güvenlik bulguları

Aynı gün yapılan genel güvenlik döngüsü gap analizinde çıkan aşağıdaki maddeler
**MCP kapanışının parçası değildir** ve ayrı backlog kalemleri olarak izlenmelidir.
Bunları bu dilime bağlamak kapanışı dallandırır.

| Konu | Neden ayrı |
| --- | --- |
| Client-side policy fallback (`PanelRuntime.astro:3533/3556/10117/10130`) — sunucu erişilemezken sunucu policy katmanının tamamen atlanması | Panelin genel yazma mimarisi; WebMCP'ye özel değil, tüm panel mutasyonlarını kapsar |
| `panel_tasks_server.py:770` — auth yok, `Access-Control-Allow-Origin: *` | Sunucu yüzeyi güvenliği; tool katmanından bağımsız |
| `scanner.py` ↔ ADR-013 `verified` alanı tutarsızlığı | Quantum readiness tarayıcısı; MCP ile ilgisiz |
| Bulgu kaydının kalıcı kimliği/durumu/sahibi olmaması | Sürekli güvenlik döngüsü kök nedeni; ayrı iş |
| CI'da güvenlik taraması (SAST/SCA/secret) olmaması | CI hattı; ayrı iş |
| Shadow Watch vb. | Ayrı ADR/dal |

---

## 7. Tekrar üretim

```bash
# origin/main üzerinde temiz bir ağaçta
cd ui && NODE_ENV=development npm ci --include=dev && NODE_ENV=production npm run build

# interaktif sürücü (onayları İNSAN verir; otomatik onay yoktur)
NODE_ENV=development node e2e/webmcp-native-api-drive.mjs
# komutlar: proof | tools | consent | list | propose <başlık> | complete <ref> | revoke | api | net | quit
```

Sürücü şunları kendisi ayağa kaldırır: geçici `LUMOS_BASE_DIR` ile
`panel_tasks_server.py` (8766), `ui/dist` statik sunucu, WebMCP bayraklı Chrome
(geçici profil, CDP). Sayfaya hiçbir şey enjekte etmez.

> **Ham log hakkında not:** Bu kaydın dayandığı `webmcp-native-api-run.log`,
> API'ye istek gitmeyen çağrılar için `API istekleri: YOK (localStorage yolu!)`
> etiketini basar. Bu etiket yanıltıcıydı — ret yollarında ve `lumos-list-tasks`
> çağrısında API'ye istek gitmemesi **doğru davranıştır** (sırasıyla: sunucuda
> arama yapılmadan reddedilir / panel belleğinden okunur) ve localStorage'a
> yazıldığı anlamına gelmez. Etiket betikte
> `YOK (bu çağrıda Tasks API kullanılmadı)` olarak düzeltildi; arşivlenen log
> koşum anındaki haliyle bırakıldı, olduğu gibi okunmalıdır.

---

## 8. Bundan sonrası

MCP/WebMCP dilimi **kapanmıştır**. Yeni MCP özelliği eklenmez; çıkan fikirler
backlog'a (`docs/drafts/BACKLOG.md`, LUMOS-0013 / LUMOS-0014 hattı) yazılır.
