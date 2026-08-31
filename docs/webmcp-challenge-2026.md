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
| `lumos-list-tasks` | okuma | gerekmez | Panelin Görevler tahtasındaki satırları döndürür (`title`, `priority`, `status`, `when`, `id`). |
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
`panel_bridge_unavailable`.

## 2. Hangi kullanıcı akışı

İnsan-onaylı görev akışı zaten Lumos'un çekirdeğiydi. WebMCP dilimi bu akışın
**girişini** ajana açar, **kararını** kullanıcıda bırakır:

1. Kullanıcı ajanına (ChatGPT in-app browser / WebMCP açık Chrome) konuşarak
   iş verir: "Şu panelde cuma sabahı için yatırımcı özeti görevi aç."
2. Ajan `lumos-list-tasks` ile tahtayı okur (onaysız, yan etkisiz).
3. Ajan `lumos-propose-task` çağırır.
4. **Panel** — ajan değil — Görevler modülünü öne alır ve kendi onay
   diyaloğunu açar: *Ne / Hedef / Etki* önizlemesi + **Vazgeç / Onayla**.
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
| `ui/e2e/webmcp-panel-tools.mjs` | Playwright uçtan uca senaryo (kayıt + reddetme + onaylama + tamamlama). |
| `tests/test_panel_webmcp_tools.py` | Kaynak sözleşmesi testleri (kapı atlanamaz). |
| `docs/webmcp-challenge-2026.md` | Bu belge. |

Değişen (yalnızca ek / dar düzeltme):

| Dosya | Değişiklik |
| --- | --- |
| `ui/src/pages/panel.astro` | `WebMcpTools` bileşeni import + mount. |
| `ui/src/components/panel/PanelRuntime.astro` | Dosya sonuna WebMCP köprüsü (`window.__lumosPanelWebMcp`); `persistPanelGorevCreateViaApi` artık `confirmationId` taşıyabiliyor; `showPanelConfirmationModal` bayat `close` olayını yok sayıyor. |
| `ui/package.json`, `package.json` | `e2e:webmcp` betiği. |

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

### Uçtan uca (Playwright)

```bash
cd ui && npm run build && npm run e2e:webmcp
# beklenen: WEBMCP_PANEL_E2E_RESULT: PASS
```

Senaryo, tarayıcının WebMCP uygulamasını (ajan tarafını) taklit eder; sayfanın
kendi `registerTool` + `execute` kodu gerçek çalışır. Doğrulananlar: üç tool
kaydı, şemalar, "Vazgeç"ten sonra **hiçbir görev yazılmaması**, "Onayla"dan
sonra görevin hem tool sonucunda hem panelin kalıcı listesinde görünmesi,
tamamlamanın aynı kapıdan geçmesi, bilinmeyen referansta modalin hiç açılmaması.

### Canlı panelde elle doğrulama

```bash
cd ui && npm run build && npx serve -l 4319 dist
# tarayıcıda: http://127.0.0.1:4319/panel/
```

**A) WebMCP açık Chrome** — Chrome sürümünüzde WebMCP bayrağı varsa
(`chrome://flags` içinde "WebMCP" / "Model Context" arayın) açın ve paneli
yükleyin. DevTools konsolunda:

```js
document.documentElement.dataset.lumosWebmcp   // "registered" olmalı
await document.modelContext.getTools()          // 3 tool
```

**B) ChatGPT in-app browser** — paneli uygulama içi tarayıcıda açın; sayfa
yüklenince tool'lar ajana görünür. "Panelde cuma için yatırımcı özeti görevi aç"
deyin; onay diyaloğu **panelde** çıkar, kararı siz verirsiniz.

**C) Bayrağı olmayan tarayıcıda ajan tarafını elle canlandırma** (kayıt ve onay
kapısını gerçek tarayıcıda görmek için; sayfa kodu gerçek çalışır). Sayfayı
yükledikten sonraki ilk saniyelerde konsola yapıştırın:

```js
const reg = new Map();
Object.defineProperty(document, "modelContext", { configurable: true, value: {
  registerTool: (t) => (reg.set(t.name, t), Promise.resolve()),
  getTools: () => Promise.resolve([...reg.values()].map((t) => ({ name: t.name, description: t.description, inputSchema: t.inputSchema }))),
  executeTool: (n, a) => Promise.resolve(reg.get(n).execute(a || {})),
}});
location.reload === undefined; // sayfa 8 sn boyunca modelContext'i yoklar
```

Sonra:

```js
await document.modelContext.executeTool("lumos-propose-task",
  { title: "Cuma 10:00 yatırımcı özeti hazırla", priority: "yuksek", when: "Yarın 10:00" });
```

Onay diyaloğu açılır. "Vazgeç" → görev oluşmaz. "Onayla" → görev listede belirir.

## 6. Canlı doğrulama kaydı

`ui/dist` yerel olarak `http://127.0.0.1:4319/panel/` adresinde sunuldu ve
gerçek Chrome 152'de gerçek fare tıklamalarıyla sürüldü:

* Kayıt: `dataset.lumosWebmcp = "registered"`, `getTools()` üç tool döndürdü.
* `lumos-propose-task` → panel Görevler modülüne geçti, onay diyaloğu açıldı
  (*Ne: Görev oluştur · Hedef: Cuma 10:00 yatırımcı özeti hazırla · Etki: Yerel
  listeye görev ekler.*).
* **Vazgeç** → `{"ok":false,"approved":false,"reason":"user_rejected"}`,
  `lumos-list-tasks` → `count: 0` (hiçbir şey yazılmadı).
* **Onayla** → `{"ok":true,"approved":true,…}`, görev panelde göründü.
* `lumos-complete-task` → yine onay diyaloğu → **Onayla** →
  `status: "tamamlandi"`.
* Bilinmeyen referans → `task_not_found`, diyalog hiç açılmadı.

## 7. Kapsam dışı

Demo videosu, Devpost formu ve Submit/Publish adımları bu dilime dahil değildir.
