# WebMCP dilimi — Lumos paneli (WebMCP Challenge 2026)

**Kapsam sınırı (yarışma kuralı):** Bu belgede tanımlanan her şey **25 Ağustos
2026'dan sonra** yazılmıştır. Lumos'un kendisi (panel, Görevler modülü, onay
kapısı, `panel_tasks_server`) bu tarihten önce vardı ve yarışma kapsamı
**değildir**. Bu dilim, var olan ürünün üzerine yalnızca bir **WebMCP ajan
yüzeyi** ekler; ürün yeniden tasarlanmamış, yeni bir bağımsız ürün
oluşturulmamıştır.

Ayrım tek cümleyle: **Lumos önceden vardı; `document.modelContext` üzerinden
ajanlara açılması yeni.**

---

## 1. Ne eklendi

Üç WebMCP tool'u, panelin `/panel` sayfasında
`document.modelContext.registerTool()` ile kaydedilir.

| Tool | Tür | Onay | Ne yapar |
| --- | --- | --- | --- |
| `lumos-list-tasks` | okuma | **zorunlu (paylaşım izni)** | Panelin Görevler tahtasındaki satırları döndürür (`title`, `priority`, `status`, `when`, `id`) — **yalnızca** kullanıcı tahtayı ajanla paylaşmayı açıkça onayladıysa. |
| `lumos-propose-task` | yazma | **zorunlu** | Yeni görev **önerir**. Kullanıcı panelin kendi onay diyaloğunda "Onayla" demeden görev **oluşmaz**. |
| `lumos-complete-task` | yazma | **zorunlu** | Var olan görevi tamamlandı olarak işaretlemeyi **önerir**. Onay olmadan durum değişmez. |

Tool sonuçları MCP sözleşmesine uygun döner:
`{ content: [{ type: "text", text: "<JSON>" }] }`.

Yazma tool'larının JSON gövdesi ajana kararı açıkça söyler:

```json
{ "ok": false, "approved": false, "reason": "user_rejected" }
{ "ok": true,  "approved": true,  "task": { "title": "…", "status": "bekliyor" } }
```

`reason` değerleri: `user_rejected`, `confirmation_busy`, `title_required`,
`ref_required`, `task_not_found`, `create_failed`, `complete_failed`,
`panel_bridge_unavailable`, `read_consent_required`.

## 1b. Okuma da izne bağlı — mahremiyet kapısı

**Kapatılan açık:** ilk sürümde `lumos-list-tasks` tüm görev tahtasını hiçbir
onay olmadan ajana veriyordu. Görev başlıkları ve zaman planları kişisel ve iş
açısından hassas veridir; ajan tarafı bunu kullanıcı haberi olmadan dışarı
taşıyabilir. "Yan etkisiz" olması "paylaşılabilir" demek değildir.

Kural: **kullanıcı açıkça izin vermeden görev içeriği ajana dönmez.**

* İzin yokken tool, sessiz boş liste değil, **açık bir ret** döner — ajan neden
  reddedildiğini bilir ve tahtayı "boş" diye raporlayamaz:

  ```json
  {
    "ok": false,
    "approved": false,
    "reason": "read_consent_required",
    "consent": { "granted": false, "scope": "session" },
    "hint": "The user has not shared their Lumos task board with agents. Task content is withheld — this is not an empty board. Ask the user to approve the sharing prompt in the Lumos panel, then retry."
  }
  ```

  Bu gövde **hiçbir görev verisi taşımaz**: ne `tasks`, ne `count`, ne başlık.
* İzin, kullanıcının **gördüğü** onay diyaloğunda tek seferlik verilir. Diyalog
  ne paylaşıldığını, kapsamı ve nasıl geri alınacağını yazar:

  ```
  Ne     : Görev listesini ajanla paylaş
  Hedef  : Görev tahtası · 3 görev
  Etki   : Görev tahtanızın içeriğini bu oturum boyunca ajanın okumasına açar.
  ── Yazılacak alanlar ──
  Paylaşılan alanlar : Görev başlığı, öncelik, durum ve zaman notu
  Kapsam             : Yalnızca bu tarayıcı oturumu (sekme kapanınca sona erer)
  Geri alma          : Görevler modülündeki “İzni geri al” düğmesi
  Kaynak             : Ajan · WebMCP · lumos-list-tasks
  ```

* **Kapsam:** oturum düzeyi (`sessionStorage`). Sekme kapanınca izin biter; yeni
  oturum izni devralmaz. `sessionStorage` erişilemiyorsa **fail-closed** —
  izin verilmemiş sayılır.
* **Görünürlük:** Görevler modülünde kalıcı bir durum satırı
  (`#gorevler-webmcp-consent`) izin açık mı kapalı mı yazar.
* **Geri alınabilirlik:** aynı satırdaki **"İzni geri al"** düğmesi izni anında
  siler; sonraki okuma yine `read_consent_required` ile reddedilir.
* Okuma izni **yereldir**: mutasyon değildir, `POST /lumos-confirm/request`
  sunucu akışını kullanmaz, hiçbir şey yazmaz.
* Yan kanal kapatıldı: `lumos-complete-task`, zaten tamamlanmış bir görevde
  onay ekranı açmadan döner (`already_completed`). Bu yol artık görev içeriğini
  **yalnızca okuma izni varsa** taşır — aksi halde izin kapısını atlayan bir
  okuma olurdu.

**Kalan sınır (bilinen):** `lumos-complete-task`, tahtada olmayan bir referans
için `task_not_found` döndürür. Bu, tam başlığı **zaten bilen** bir ajana o
başlığın var olup olmadığını söyleyen dar bir varlık sinyalidir. İçerik
sızdırmaz (başlık, öncelik, zaman dönmez) ve tamamlamayı büsbütün okuma iznine
bağlamak, kullanıcının "şu görevi kapat" demesini de engellerdi; bu yüzden
bilinçli olarak açık bırakıldı.

## 1c. Onay ekranı — yazılacak HER alan görünür

**Kapatılan açık:** onay diyaloğu yalnızca *Ne / Hedef / Etki* gösteriyordu;
`priority` ve `when` kullanıcıya gösterilmeden yazılıyordu. Kullanıcı görmediği
bir şeyi onaylıyordu — kapı kâğıt üstünde vardı, pratikte eksikti.

Artık diyalogda ikinci bir bölüm var: **"Yazılacak alanlar"**. İçindeki her
değer, tool çağrısındaki **gerçek** değerden türetilir (sabit metin değil), ve
boş/varsayılan alanlar **gizlenmez, açıkça yazılır**.

`lumos-propose-task` — `{ title: "Cuma 10:00 yatırımcı özeti", priority: "yuksek" }`:

```
Ne     : Görev oluştur
Hedef  : Cuma 10:00 yatırımcı özeti
Etki   : Yerel listeye görev ekler.
── Yazılacak alanlar ──
Başlık  : Cuma 10:00 yatırımcı özeti
Öncelik : yüksek (yuksek)
Zaman   : belirtilmedi (zaman planlanmıyor)      ← boş alan da yazılı
Durum   : bekliyor (bekliyor)
Kaynak  : Ajan · WebMCP · lumos-propose-task
```

`priority` hiç verilmezse: `Öncelik : belirtilmedi (varsayılan: orta)`.

`lumos-complete-task` — durum değişikliği neyi neye çevirdiğini yazar:

```
Ne     : Görevi tamamla
Hedef  : Cuma 10:00 yatırımcı özeti
Etki   : Görevi tamamlandı olarak işaretler.
── Yazılacak alanlar ──
Görev              : Cuma 10:00 yatırımcı özeti
Durum değişikliği  : bekliyor → tamamlandı (bekliyor → tamamlandi)
Öncelik            : yüksek (değişmiyor)
Zaman              : Yarın 14:00 (değişmiyor)
Eşleşen referans   : t-0007
Kaynak             : Ajan · WebMCP · lumos-complete-task
```

Uygulama notları:

* Alanlar `showPanelConfirmationModal(preview)` içindeki
  `renderPanelConfirmationFields(preview.fields)` ile basılır; değerler
  `textContent` ile yazılır — ajandan gelen metin **hiçbir zaman HTML olarak
  yorumlanmaz**.
* Sunucu onay akışı yalnızca *ne/hedef/etki* döndürür. `priority`/`when` gibi
  alanlar yalnızca köprüde bilinir, bu yüzden
  `panelEnsureMutationConfirmation(path, body, previewFields)` ile önizlemeye
  taşınır — **iki onay yolu da aynı alanları gösterir**, ayrışamazlar.
* Ekranda gösterilen durum ile yazılan durum aynı değişkendir (`proposeStatus`);
  biri değişip diğeri sabit kalamaz.
* `fields` verilmeyen eski onay çağrıları bölümü **gizli** bırakır — mevcut
  panel akışlarının davranışı değişmez.

## 2. Hangi kullanıcı akışı

İnsan-onaylı görev akışı zaten Lumos'un çekirdeğiydi. WebMCP dilimi bu akışın
**girişini** ajana açar, **kararını** kullanıcıda bırakır:

1. Kullanıcı ajanına (ChatGPT in-app browser / WebMCP açık Chrome) konuşarak
   iş verir: "Şu panelde cuma sabahı için yatırımcı özeti görevi aç."
2. Ajan `lumos-list-tasks` ile tahtayı okumak ister. İlk seferde **panel**
   paylaşım izni sorar; kullanıcı vermezse ajan içerik yerine
   `read_consent_required` alır ve tahtayı hiç görmez.
3. Ajan `lumos-propose-task` çağırır.
4. **Panel** — ajan değil — Görevler modülünü öne alır ve kendi onay
   diyaloğunu açar: *Ne / Hedef / Etki* + **yazılacak alanların tamamı**
   (başlık, öncelik, zaman, durum, kaynak) + **Vazgeç / Onayla**.
5. Kullanıcı onaylarsa görev panelin normal yolundan yazılır
   (`POST /tasks` → `.lumos/tasks.json`, sunucu yoksa yerel liste).
   Vazgeçerse **hiçbir şey yazılmaz** ve ajana `approved:false` döner.
6. `lumos-complete-task` aynı kapıdan geçer.

## 3. Güvenlik sözleşmesi — onay kapısı atlanamaz

* Yazma tool'ları hiçbir zaman doğrudan REST/localStorage'a dokunmaz; yalnızca
  `window.__lumosPanelWebMcp` köprüsünü çağırır (bkz. `PanelRuntime.astro`).
* Köprüdeki `panelWebMcpHumanGate()` iki durumu da kapsar:
  * Sunucu onayı açıksa (`LUMOS_CONFIRMATION_ENABLED`) →
    `panelEnsureMutationConfirmation()` → `POST /lumos-confirm/request` +
    panel modali; alınan `confirmation_id` mutasyona taşınır (çift diyalog yok).
  * Kapalıysa → yerel `showPanelConfirmationModal()`.
* Onay alınmadan dönülen her yolda mutasyon çağrısı **hiç yapılmaz**.
* Onay diyaloğu Görevler modülünün içinde yaşadığı için, ajan başka sekmedeyken
  çağırdığında köprü önce o modülü öne alır — aksi halde `showModal()` görünmez
  kalır ve kullanıcı göremediği bir kapıyla karşılaşırdı.
* Aynı anda ikinci bir onay isteği gelirse ajana `confirmation_busy` döner;
  "kullanıcı reddetti" gibi yanıltıcı bir cevap verilmez.

### Bu dilimde ortaya çıkan gerçek hata düzeltmesi

`<dialog>.close()` `close` olayını **kuyruğa** alır. Ardışık iki onay açıldığında
birinci onayın gecikmiş `close` olayı ikinci diyaloğa düşüyor ve onu kendi
kendine "vazgeçildi" yapıyordu. `showPanelConfirmationModal()` içindeki
`onClose` artık `if (dlg.open) return;` ile bu bayat olayı yok sayar. Hata
WebMCP tool'ları sayesinde görünür oldu; kullanıcı hızlı iki onay açtığında da
oluşuyordu.

## 4. Dosyalar

Yeni:

| Dosya | İçerik |
| --- | --- |
| `ui/src/components/panel/WebMcpTools.astro` | `document.modelContext.registerTool()` çağrıları, tool şemaları, destek yoklaması. |
| `ui/e2e/webmcp-panel-tools.mjs` | Playwright senaryosu — ajan tarafı **taklit** (harness): okuma izni, onay alanları, reddetme, onaylama, tamamlama. |
| `ui/e2e/webmcp-native-verify.mjs` | **Native** doğrulama: gerçek Chrome, WebMCP bayrağı, sayfaya sıfır enjeksiyon. |
| `tests/test_panel_webmcp_tools.py` | Kaynak sözleşmesi testleri (kapı atlanamaz, izin kapısı, onay alanları). |
| `docs/webmcp-challenge-2026.md` | Bu belge. |

Değişen (yalnızca ek / dar düzeltme):

| Dosya | Değişiklik |
| --- | --- |
| `ui/src/pages/panel.astro` | `WebMcpTools` import + mount; onay diyaloğuna **"Yazılacak alanlar"** bölümü; Görevler modülüne **görünür izin durumu + "İzni geri al"** satırı; ikisinin stilleri. |
| `ui/src/components/panel/PanelRuntime.astro` | WebMCP köprüsü (`window.__lumosPanelWebMcp`) + **okuma izni kapısı**; `renderPanelConfirmationFields()`; `panelEnsureMutationConfirmation` artık `previewFields` alıyor; `persistPanelGorevCreateViaApi` `confirmationId` taşıyabiliyor; `showPanelConfirmationModal` bayat `close` olayını yok sayıyor. |
| `ui/src/i18n/messages/panel/{tr,en}.ts` | `confirmation.labelFields`, `share_task_board` eylemi, `agent_read_task_board` etkisi ve `shell.infra.webmcp.*` etiketleri. |
| `ui/package.json`, `package.json` | `e2e:webmcp` ve `e2e:webmcp:native` betikleri. |

`document.modelContext` yoksa hiçbir şey kaydedilmez, panel eskisi gibi çalışır:
`document.documentElement.dataset.lumosWebmcp` `"unsupported"` olur.
**Shim/polyfill yazılmadı** — tarayıcı desteği taklit edilmez.

## 5. Test

### Birim / sözleşme

```bash
cd /Users/candasoz/work_2026/lumos-core
.venv/bin/python -m pytest tests/test_panel_webmcp_tools.py -q
# regresyon:
.venv/bin/python -m pytest tests/ -q -k "panel or confirmation or gorev or task"
```

### Uçtan uca — harness (ajan tarafı taklit)

```bash
cd ui && npm run build && npm run e2e:webmcp
# beklenen: WEBMCP_PANEL_E2E_RESULT: PASS
```

**Dürüstlük notu:** bu senaryoda `document.modelContext`'i **test enjekte eder**
(`page.addInitScript`). Sayfanın kendi `registerTool` + `execute` kodu gerçek
çalışır ama tarayıcı desteği taklittir. Bu bir **native doğrulama değildir** —
onun için aşağıdaki bölüm kullanılır.

Doğrulananlar: üç tool kaydı ve şemalar; **izin yokken okumanın içerik
döndürmemesi** (`read_consent_required`, ret gövdesinde `tasks`/`count` yok);
izin verilince içeriğin gelmesi; görünür durumun açılması; **"İzni geri al"**
sonrası okumanın yine reddedilmesi; yeni oturumun izni devralmaması; onay
diyaloğunun **`priority` ve `when`'i gerçek değerlerle** göstermesi; verilmeyen
alanların "belirtilmedi (varsayılan: …)" olarak yazılması; "Vazgeç"ten sonra
**hiçbir görev yazılmaması**; "Onayla"dan sonra görevin hem tool sonucunda hem
panelin kalıcı listesinde görünmesi; tamamlamanın aynı kapıdan geçmesi ve durum
değişikliğini göstermesi; bilinmeyen referansta modalin hiç açılmaması.

### Uçtan uca — NATIVE WebMCP (gerçek tarayıcı desteği)

```bash
cd ui && npm run build && npm run e2e:webmcp:native
# beklenen: WEBMCP_NATIVE_RESULT: PASS
# görmek için: WEBMCP_HEADED=1 npm run e2e:webmcp:native
```

Bu betik sistemdeki gerçek Chrome'u **ayrı bir `user-data-dir`** ile başlatır
(kullanıcı profiline dokunulmaz) ve sayfaya **hiçbir şey enjekte etmez** —
`addInitScript` kullanılmaz, tek satır shim yoktur. `document.modelContext`
tamamen tarayıcıdan gelir.

### Canlı panelde elle doğrulama

```bash
cd ui && npm run build && npx serve -l 4319 dist
# tarayıcıda: http://127.0.0.1:4319/panel/
```

**A) WebMCP açık Chrome (elle)** — bayrakları vererek ayrı profille başlatın:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir=/tmp/lumos-webmcp-profile \
  --enable-features=WebMCP \
  --enable-blink-features=DocumentModelcontext \
  http://127.0.0.1:4319/panel/
```

DevTools konsolunda:

```js
Object.prototype.toString.call(document.modelContext)   // "[object ModelContext]"
String(document.modelContext.registerTool)              // "…{ [native code] }"
document.documentElement.dataset.lumosWebmcp            // "registered"
const tools = await document.modelContext.getTools();   // 3 tool
// Native imza: executeTool(RegisteredTool, argsJsonString) → JSON *string*
await document.modelContext.executeTool(
  tools.find((t) => t.name === "lumos-list-tasks"), "{}");
```

**B) ChatGPT in-app browser** — paneli uygulama içi tarayıcıda açın; sayfa
yüklenince tool'lar ajana görünür. "Panelde cuma için yatırımcı özeti görevi aç"
deyin; izin ve onay diyalogları **panelde** çıkar, kararı siz verirsiniz.
(Bu ortam bu dilimde **denenmedi** — kanıt Chrome üzerinden üretildi.)

## 6. Native WebMCP doğrulama kaydı

Bu kayıt **harness ile değil**, tarayıcının kendi WebMCP uygulamasıyla üretildi.

**Ortam**

| | |
| --- | --- |
| Tarayıcı | Google Chrome **152.0.7977.64** (macOS 15 / Darwin 25.5.0, arm64) |
| İkili | `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` |
| Bayraklar | `--enable-features=WebMCP --enable-blink-features=DocumentModelcontext` |
| Profil | geçici `user-data-dir` (kullanıcı profiline dokunulmadı) |
| Sayfa enjeksiyonu | **YOK** — `addInitScript` kullanılmadı, shim/polyfill yok |
| Betik | `ui/e2e/webmcp-native-verify.mjs` (`npm run e2e:webmcp:native`) |

Bayrak adları Chrome ikilisindeki sembollerden doğrulandı: `kWebMCP`
(base::Feature) ve `kDocumentModelcontext` (Blink runtime-enabled feature);
ayrıca `blink::ModelContext`, `blink::ModelContextTool`, `"Enables the WebMCP
API."` ve `document.modelContext cannot be used when document.domain is
enabled.` dizgeleri mevcut.

**`modelContext`'in native olduğunun kanıtı** (betiğin çıktısı):

```json
{
  "chromeUserAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/152.0.0.0 Safari/537.36",
  "brandString": "[object ModelContext]",
  "constructorName": "ModelContext",
  "prototypeMembers": ["constructor", "executeTool", "getTools", "ontoolchange", "registerTool"],
  "registerToolSource": "function registerTool() { [native code] }",
  "executeToolSource": "function executeTool() { [native code] }",
  "documentPrototypeGetter": "function get modelContext() { [native code] }",
  "ownPropertyOnDocument": false,
  "globalInterfaces": ["ModelContext", "WebMCPEvent"],
  "pageRegistered": ["lumos-list-tasks", "lumos-propose-task", "lumos-complete-task"]
}
```

Neden bu native'dir, sayfa/harness değil:

* `modelContext`, `Document.prototype` üzerinde **`[native code]` gövdeli bir
  getter**. Harness `Object.defineProperty(document, …)` ile **instance own
  property** yaratır — burada `ownPropertyOnDocument: false`.
* Marka dizgesi `[object ModelContext]` ve global `ModelContext` /
  `WebMCPEvent` **arayüzleri** var; düz nesne taklidinde ikisi de olmaz.
* `registerTool` / `executeTool` / `getTools` gövdeleri `[native code]`.
* **Negatif kontrol:** *aynı* Chrome 152, *aynı* betik, bayraklar kaldırılınca →
  `"modelContext" in document === false`,
  `Object.getOwnPropertyDescriptor(Document.prototype, "modelContext") === null`,
  global `ModelContext` yok. Yani yüzeyi sağlayan bayraklı tarayıcıdır, sayfa değil.
* Native imza da spec'e uyuyor ve harness'tan farklı:
  `executeTool(RegisteredTool, argsJsonString)` → JSON **string** döner.
  Betik bu gerçek imzayı kullanır.

**Native ortamda uçtan uca akış sonucu**

```
read without consent : refused (read_consent_required), no task data
read with consent    : 0 task(s)
propose declined     : nothing written
propose approved     : Native WebMCP 1788201905653
complete approved    : tamamlandi
```

Adım adım, hepsi native `document.modelContext` üzerinden:

* Üç tool `getTools()` ile tarayıcıdan görülebiliyor.
* `lumos-list-tasks` → panel paylaşım izni sordu → **Vazgeç** →
  `read_consent_required`, gövdede `tasks`/`count` **yok**.
* Aynı çağrı → **Onayla** → liste geldi, Görevler modülündeki görünür durum
  `data-granted="true"` oldu.
* `lumos-propose-task` (`priority: "yuksek"`, `when: "Yarın 14:00"`) → onay
  diyaloğunda **Öncelik** ve **Zaman** alanları gerçek değerleriyle göründü →
  **Vazgeç** → görev sayısı değişmedi (hiçbir şey yazılmadı).
* Aynı çağrı → **Onayla** → görev oluştu.
* `lumos-complete-task` → diyalogda durum değişikliği (`bekliyor → tamamlandı`)
  göründü → **Onayla** → `status: "tamamlandi"`.

**Kurulamayan ortam:** ChatGPT in-app browser bu dilimde denenmedi; oradaki
sonuç raporlanmıyor.

## 7. Kapsam dışı

Demo videosu, Devpost formu ve Submit/Publish adımları bu dilime dahil değildir.
