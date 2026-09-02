/**
 * WebMCP panel tool E2E — 2026-08-25 sonrası eklendi (WebMCP Challenge dilimi).
 *
 * Doğrulanan sözleşme:
 *  1. Panel yüklendiğinde 3 tool `document.modelContext.registerTool()` ile kaydedilir.
 *  2. OKUMA İZNİ: `lumos-list-tasks` kullanıcı görev tahtasını paylaşmayı açıkça
 *     onaylamadan HİÇBİR görev içeriği döndürmez; ajana `read_consent_required`
 *     reddi verilir. İzin verilince içerik gelir, panelde görünür duruma geçer,
 *     "İzni geri al" ile kapatılınca okuma yine reddedilir.
 *  3. ONAY EKRANI: `lumos-propose-task` onay diyaloğu, yazılacak HER alanı
 *     çağrıdaki gerçek değeriyle gösterir (başlık, öncelik, zaman, durum,
 *     kaynak). Verilmeyen alan "belirtilmedi (varsayılan: …)" olarak yazılır.
 *  4. "Vazgeç" seçilirse HİÇBİR görev yazılmaz (onay kapısı atlanamaz).
 *  5. Aynı tool "Onayla" ile gerçekten görev oluşturur ve panelde görünür.
 *  6. `lumos-complete-task` yine onay kapısından geçer ve durum değişikliğini
 *     (neyi neye çevirdiğini) ekranda yazar.
 *  6b. ÜYELİK ORACLE'I KAPALI: okuma izni yokken `lumos-complete-task`, ref'e
 *     göre AYRIŞMAZ — var olmayan / bekleyen / zaten tamamlanmış görev ve hiç
 *     ref verilmemesi BİREBİR aynı `read_consent_required` payload'ını alır ve
 *     hiçbirinde onay penceresi açılmaz. İzin verilince dördü yine ayrışır.
 *  7. Eşzamanlı iki mutasyon: ikincisi `confirmation_busy`; ilk diyalog açık kalır.
 *  8. Sunucu onay yolu: gecikmeli eşzamanlı çağrı, HTTP 500, bozuk JSON ve
 *     ağ istisnası `user_rejected` değil `confirmation_failed` /
 *     `confirmation_unavailable` olarak raporlanır; yazma yapılmaz.
 *
 * Not: Headless Chromium'da tarayıcının WebMCP uygulaması yok. Test yalnızca
 * TARAYICI TARAFINI (agent harness) taklit eder — sayfanın kendi kayıt ve
 * execute kodu gerçek olarak çalışır. Native WebMCP doğrulaması ayrı yapılır;
 * bkz. docs/webmcp-challenge-2026.md.
 */
import { chromium } from "playwright";
import http from "node:http";
import { waitForPanelDom, PANEL_READY_MS } from "./lib/panel-helpers.mjs";
import {
  closeServer,
  DIST_DIR,
  getDefaultServerTargets,
  startStaticServer,
  assertPanelDistBuilt,
  waitForServer,
} from "./lib/static-server.mjs";

const EXPECTED_TOOLS = ["lumos-list-tasks", "lumos-propose-task", "lumos-complete-task"];

function fail(reason) {
  console.error("WEBMCP_PANEL_E2E_RESULT: FAIL");
  console.error(reason);
  process.exit(1);
}

/** Onay beklerken askıda kalan tool çağrısı: reddi yutup sonuca çevirir. */
function pending(promise) {
  return promise.catch((e) => ({ __err: String((e && e.message) || e) }));
}

function assertNoToolError(label, result) {
  if (result && result.__err) fail(label + " tool çağrısı hata verdi: " + result.__err);
}

/** Tarayıcı tarafı taklidi: document.modelContext (registerTool/getTools/executeTool). */
const AGENT_HARNESS = function () {
  const registry = new Map();
  const modelContext = {
    registerTool(tool) {
      if (!tool || typeof tool.name !== "string" || typeof tool.execute !== "function") {
        return Promise.reject(new TypeError("invalid tool"));
      }
      registry.set(tool.name, tool);
      return Promise.resolve();
    },
    getTools() {
      return Promise.resolve(
        Array.from(registry.values()).map(function (t) {
          return {
            name: t.name,
            description: t.description,
            inputSchema: t.inputSchema,
            origin: location.origin,
          };
        }),
      );
    },
    executeTool(tool, args) {
      const name = typeof tool === "string" ? tool : tool && tool.name;
      const entry = registry.get(name);
      if (!entry) return Promise.reject(new Error("unknown tool: " + name));
      return Promise.resolve(entry.execute(args || {}));
    },
  };
  Object.defineProperty(document, "modelContext", {
    value: modelContext,
    configurable: true,
  });
  // Panel yerel modda kalsın: tasks REST yok, mutasyon yerel listeye yazılır.
  window.LUMOS_PANEL_TASKS_API_BASE = false;
};

/**
 * Sunucu onay yolu için mock tasks API.
 * `modeForHit(n)` → { delayMs?, status?, body?, rawBody?, drop? }
 */
function startConfirmMockServer(port, modeForHit) {
  let confirmHits = 0;
  const server = http.createServer((req, res) => {
    const url = String(req.url || "").split("?")[0];
    const cors = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type,Accept",
    };
    if (req.method === "OPTIONS") {
      res.writeHead(204, cors);
      res.end();
      return;
    }
    if (req.method === "GET" && url === "/tasks") {
      res.writeHead(200, { ...cors, "Content-Type": "application/json" });
      res.end(JSON.stringify({ ok: true, tasks: [], confirmation_enabled: true }));
      return;
    }
    if (req.method === "POST" && url === "/lumos-confirm/request") {
      confirmHits += 1;
      const hit = confirmHits;
      let body = "";
      req.on("data", (chunk) => {
        body += chunk;
      });
      req.on("end", () => {
        const mode =
          typeof modeForHit === "function"
            ? modeForHit(hit, body)
            : modeForHit || {};
        const respond = () => {
          if (mode.drop) {
            try {
              req.socket.destroy();
            } catch (_) {
              /* ignore */
            }
            return;
          }
          const status = mode.status != null ? mode.status : 200;
          res.writeHead(status, { ...cors, "Content-Type": "application/json" });
          if (mode.rawBody != null) {
            res.end(mode.rawBody);
            return;
          }
          if (mode.body != null) {
            res.end(JSON.stringify(mode.body));
            return;
          }
          res.end(
            JSON.stringify({
              ok: true,
              confirmation_id: "conf_mock_" + hit,
              preview: {
                what: "create_task",
                where: "mock",
                effect: "local_task_create",
              },
            }),
          );
        };
        if (mode.delayMs > 0) setTimeout(respond, mode.delayMs);
        else respond();
      });
      return;
    }
    res.writeHead(404, { ...cors, "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: false, error: "not_found" }));
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", () => {
      resolve({
        server,
        base: "http://127.0.0.1:" + port,
        confirmHits: () => confirmHits,
        close: () =>
          new Promise((resClose) => {
            server.close(() => resClose());
          }),
      });
    });
  });
}

/** Init script body: Playwright arg olarak apiBase geçirir (closure serileşmez). */
function agentHarnessWithTasksApi(apiBase) {
  const base = String(apiBase || "");
  const registry = new Map();
  const modelContext = {
    registerTool(tool) {
      if (!tool || typeof tool.name !== "string" || typeof tool.execute !== "function") {
        return Promise.reject(new TypeError("invalid tool"));
      }
      registry.set(tool.name, tool);
      return Promise.resolve();
    },
    getTools() {
      return Promise.resolve(
        Array.from(registry.values()).map(function (t) {
          return {
            name: t.name,
            description: t.description,
            inputSchema: t.inputSchema,
            origin: location.origin,
          };
        }),
      );
    },
    executeTool(tool, args) {
      const name = typeof tool === "string" ? tool : tool && tool.name;
      const entry = registry.get(name);
      if (!entry) return Promise.reject(new Error("unknown tool: " + name));
      return Promise.resolve(entry.execute(args || {}));
    },
  };
  Object.defineProperty(document, "modelContext", {
    value: modelContext,
    configurable: true,
  });
  window.LUMOS_PANEL_TASKS_API_BASE = base;
  /* E2E: sunucu onay yolunu panel sync'ini beklemeden aç. */
  window.LUMOS_PANEL_CONFIRMATION_ENABLED = true;
}

/** Ajan tool çağrısı: sonucu JSON payload'a çevirir. */
const CALL_TOOL = function (payload) {
  return document.modelContext
    .executeTool(payload.name, payload.args)
    .then(function (res) {
      const text = res && res.content && res.content[0] ? res.content[0].text : "";
      return JSON.parse(text);
    });
};

/** Onay diyaloğunun "Yazılacak alanlar" bölümünü ekrandan aynen okur. */
const READ_CONFIRM_FIELDS = function () {
  const wrap = document.getElementById("lumos-confirm-preview-fields-wrap");
  const dl = document.getElementById("lumos-confirm-preview-fields");
  if (!wrap || !dl) return { present: false, hidden: true, byKey: {}, order: [] };
  const byKey = {};
  const order = [];
  const nodes = Array.prototype.slice.call(dl.children);
  for (let i = 0; i + 1 < nodes.length; i += 2) {
    if (nodes[i].tagName !== "DT" || nodes[i + 1].tagName !== "DD") continue;
    const dd = nodes[i + 1];
    const key = dd.getAttribute("data-field") || "";
    const entry = {
      key,
      label: (nodes[i].textContent || "").trim(),
      value: (dd.textContent || "").trim(),
      unset: dd.getAttribute("data-unset") === "true",
    };
    order.push(entry);
    if (key) byKey[key] = entry;
  }
  return { present: true, hidden: wrap.hidden === true, byKey, order };
};

/** İzin durumunu panelin görünür yüzeyinden okur (iç değişkenden değil). */
const READ_CONSENT_CHIP = function () {
  const box = document.getElementById("gorevler-webmcp-consent");
  const text = document.getElementById("gorevler-webmcp-consent-text");
  const btn = document.getElementById("gorevler-webmcp-consent-revoke");
  return {
    present: !!box,
    granted: box ? box.getAttribute("data-granted") : null,
    text: text ? (text.textContent || "").trim() : "",
    revokeVisible: !!btn && btn.hidden === false,
    stored: (function () {
      try {
        return window.sessionStorage.getItem("lumos_panel_webmcp_read_consent_v1");
      } catch (_) {
        return null;
      }
    })(),
  };
};

function requireField(label, snapshot, key) {
  const f = snapshot.byKey[key];
  if (!f) {
    fail(
      label + ": onay ekranında '" + key + "' alanı YOK. Görünen alanlar="
      + JSON.stringify(snapshot.order.map((e) => e.key)),
    );
  }
  return f;
}

function requireContains(label, actual, needle) {
  if (String(actual).indexOf(needle) === -1) {
    fail(label + ": beklenen metin yok. beklenen=" + needle + " görünen=" + JSON.stringify(actual));
  }
}

assertPanelDistBuilt();

const { port, PANEL_URL } = getDefaultServerTargets();
let server;
let browser;

try {
  server = await startStaticServer(DIST_DIR, port);
  await waitForServer(PANEL_URL, PANEL_READY_MS);

  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.addInitScript(AGENT_HARNESS);
  await page.goto(PANEL_URL, { waitUntil: "domcontentloaded", timeout: PANEL_READY_MS });
  await waitForPanelDom(page, PANEL_READY_MS);

  // 1) Kayıt
  await page.waitForFunction(
    () => document.documentElement.dataset.lumosWebmcp === "registered",
    null,
    { timeout: PANEL_READY_MS },
  );
  const discovered = await page.evaluate(() => document.modelContext.getTools());
  const names = discovered.map((t) => t.name).sort();
  if (names.join(",") !== [...EXPECTED_TOOLS].sort().join(",")) {
    fail("Beklenen tool'lar kayıtlı değil; bulunan=" + JSON.stringify(names));
  }
  for (const t of discovered) {
    if (!t.description || String(t.description).length < 20) {
      fail("Tool açıklaması eksik: " + t.name);
    }
    if (!t.inputSchema || t.inputSchema.type !== "object") {
      fail("Tool inputSchema eksik/hatalı: " + t.name);
    }
  }
  // Okuma tool'u ajana iznin gerekli olduğunu söylemeli (sessiz boş liste değil).
  const listDesc = discovered.find((t) => t.name === "lumos-list-tasks").description;
  requireContains("lumos-list-tasks açıklaması", listDesc, "read_consent_required");

  // ── 2) MAHREMİYET: okuma izni olmadan görev içeriği DÖNMEZ ─────────────────
  const chip0 = await page.evaluate(READ_CONSENT_CHIP);
  if (!chip0.present) fail("Panelde görünür izin durumu satırı yok (#gorevler-webmcp-consent)");
  if (chip0.granted !== "false") {
    fail("Açılışta izin kapalı olmalı; görünen=" + JSON.stringify(chip0));
  }
  if (chip0.revokeVisible) fail("İzin yokken 'İzni geri al' düğmesi görünmemeli");

  const refusePromise = pending(
    page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  // İzin ekranı: kullanıcı ne paylaştığını, kapsamı ve geri almayı görür.
  const consentFields = await page.evaluate(READ_CONFIRM_FIELDS);
  if (consentFields.hidden) fail("İzin ekranı alan listesi gizli kalmış");
  requireField("izin ekranı", consentFields, "shared_fields");
  requireContains(
    "izin ekranı kapsam",
    requireField("izin ekranı", consentFields, "scope").value,
    "oturum",
  );
  requireField("izin ekranı", consentFields, "revoke");
  requireContains(
    "izin ekranı kaynak",
    requireField("izin ekranı", consentFields, "source").value,
    "lumos-list-tasks",
  );
  await page.click("#lumos-confirm-cancel");

  const refused = await refusePromise;
  assertNoToolError("lumos-list-tasks (izin reddi)", refused);
  if (refused.ok !== false || refused.approved !== false) {
    fail("İzin reddinde ok/approved false olmalı: " + JSON.stringify(refused));
  }
  if (refused.reason !== "read_consent_required") {
    fail("İzin reddinde net sebep dönmedi: " + JSON.stringify(refused));
  }
  // En kritik iddia: ret cevabı hiçbir görev verisi taşımaz.
  if ("tasks" in refused || "count" in refused) {
    fail("İzinsiz okumada görev içeriği sızmış: " + JSON.stringify(refused));
  }
  const refusedBlob = JSON.stringify(refused);
  if (refusedBlob.indexOf("title") !== -1) {
    fail("İzinsiz ret cevabında görev başlığı alanı görünüyor: " + refusedBlob);
  }
  const chipAfterRefuse = await page.evaluate(READ_CONSENT_CHIP);
  if (chipAfterRefuse.granted !== "false") fail("Ret sonrası izin açık görünüyor");

  // İzin verilince içerik gelir ve panel bunu görünür durum olarak gösterir.
  const allowPromise = pending(
    page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-approve");
  const before = await allowPromise;
  assertNoToolError("lumos-list-tasks (izin verildi)", before);
  if (!before.ok || !Array.isArray(before.tasks)) {
    fail("İzin verildikten sonra liste dönmedi: " + JSON.stringify(before));
  }
  if (!before.consent || before.consent.granted !== true || before.consent.scope !== "session") {
    fail("Liste cevabı izin durumunu taşımıyor: " + JSON.stringify(before.consent));
  }
  const chipOn = await page.evaluate(READ_CONSENT_CHIP);
  if (chipOn.granted !== "true") fail("İzin sonrası görünür durum açık değil: " + JSON.stringify(chipOn));
  if (!chipOn.revokeVisible) fail("İzin açıkken 'İzni geri al' düğmesi görünmüyor");
  if (!chipOn.stored) fail("İzin oturum düzeyinde kalıcı değil (sessionStorage boş)");
  const baselineCount = before.count;

  // İkinci okuma tekrar sormaz (tek seferlik oturum izni).
  const secondRead = await page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} });
  if (!secondRead.ok) fail("İzin verildikten sonra ikinci okuma reddedildi");
  if (await page.isVisible("#lumos-confirm-dialog[open]")) {
    fail("İzin verilmişken okuma yine onay sordu (tek seferlik değil)");
  }

  // Geri alınabilirlik: kullanıcı düğmeye basınca okuma yine reddedilir.
  await page.click("#gorevler-webmcp-consent-revoke");
  const chipOff = await page.evaluate(READ_CONSENT_CHIP);
  if (chipOff.granted !== "false") fail("Geri alma sonrası izin hâlâ açık: " + JSON.stringify(chipOff));
  if (chipOff.stored) fail("Geri alma sonrası oturum izni silinmemiş");
  const afterRevokePromise = pending(
    page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-cancel");
  const afterRevoke = await afterRevokePromise;
  if (afterRevoke.reason !== "read_consent_required" || "tasks" in afterRevoke) {
    fail("Geri alma sonrası okuma engellenmedi: " + JSON.stringify(afterRevoke));
  }

  // Testin kalanı için izni yeniden ver.
  const regrantPromise = pending(
    page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-approve");
  const regranted = await regrantPromise;
  if (!regranted.ok) fail("İzin yeniden verilemedi: " + JSON.stringify(regranted));

  const TITLE_REJECT = "WebMCP reddedilen " + Date.now();
  const TITLE_APPROVE = "WebMCP onaylanan " + Date.now();
  const TITLE_DEFAULTS = "WebMCP varsayilan " + Date.now();

  // ── 3) ONAY EKRANI: yazılacak her alan gerçek değeriyle görünür ────────────
  // Sohbet sekmesindeyken çağrılır: onay modali kullanıcıya görünür hale gelmeli.
  await page.click('.panel-body button[data-module="sohbet"]');
  const rejectPromise = pending(
    page.evaluate(CALL_TOOL, {
      name: "lumos-propose-task",
      args: { title: TITLE_REJECT, priority: "yuksek" },
    }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  const gorevlerActive = await page.getAttribute(
    '[data-module-panel="gorevler"]',
    "data-active",
  );
  if (gorevlerActive !== "true") {
    fail("Onay modali açılırken Görevler modülü öne alınmadı (modal görünmez kalır)");
  }
  const previewWhere = await page.textContent("#lumos-confirm-preview-where");
  if (String(previewWhere || "").trim() !== TITLE_REJECT) {
    fail("Onay önizlemesi görev başlığını göstermiyor: " + JSON.stringify(previewWhere));
  }

  const rejectFields = await page.evaluate(READ_CONFIRM_FIELDS);
  if (!rejectFields.present) fail("Onay ekranında 'Yazılacak alanlar' bölümü yok");
  if (rejectFields.hidden) fail("Onay ekranında alan listesi gizli kalmış");
  if (requireField("öneri (ret)", rejectFields, "title").value !== TITLE_REJECT) {
    fail("Onay ekranı başlığı gerçek değeri göstermiyor");
  }
  // priority ajanın verdiği GERÇEK değerden türemeli — sabit metin değil.
  const rejPriority = requireField("öneri (ret)", rejectFields, "priority");
  requireContains("öncelik alanı", rejPriority.value, "yuksek");
  if (rejPriority.unset) fail("Açıkça verilen öncelik 'belirtilmedi' işaretlenmiş");
  // when verilmedi: boş olduğu AÇIKÇA yazılmalı, gizlenmemeli.
  const rejWhen = requireField("öneri (ret)", rejectFields, "when");
  if (!rejWhen.unset) fail("Verilmeyen 'when' alanı belirtilmedi olarak işaretlenmemiş");
  requireContains("zaman alanı", rejWhen.value, "belirtilmedi");
  requireContains(
    "durum alanı",
    requireField("öneri (ret)", rejectFields, "status").value,
    "bekliyor",
  );
  requireContains(
    "kaynak alanı",
    requireField("öneri (ret)", rejectFields, "source").value,
    "lumos-propose-task",
  );

  await page.click("#lumos-confirm-cancel");
  const rejected = await rejectPromise;
  assertNoToolError("lumos-propose-task (reddet)", rejected);
  if (rejected.approved !== false || rejected.ok !== false || rejected.reason !== "user_rejected") {
    fail("Reddetme sonucu hatalı: " + JSON.stringify(rejected));
  }
  const afterReject = await page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} });
  if (afterReject.count !== baselineCount) {
    fail("Vazgeç sonrası görev yazılmış — onay kapısı atlanmış!");
  }
  if (afterReject.tasks.some((t) => t.title === TITLE_REJECT)) {
    fail("Reddedilen görev listeye sızmış: " + TITLE_REJECT);
  }

  // 3b) Hiç alan verilmeyen çağrı: varsayılanlar da ekranda YAZILI olmalı.
  const defaultsPromise = pending(
    page.evaluate(CALL_TOOL, {
      name: "lumos-propose-task",
      args: { title: TITLE_DEFAULTS },
    }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  const defaultFields = await page.evaluate(READ_CONFIRM_FIELDS);
  const defPriority = requireField("öneri (varsayılan)", defaultFields, "priority");
  if (!defPriority.unset) fail("Verilmeyen öncelik 'belirtilmedi' işaretlenmemiş");
  requireContains("varsayılan öncelik", defPriority.value, "belirtilmedi");
  requireContains("varsayılan öncelik", defPriority.value, "varsayılan");
  requireContains("varsayılan öncelik", defPriority.value, "orta");
  await page.click("#lumos-confirm-cancel");
  const defaultsRejected = await defaultsPromise;
  if (defaultsRejected.ok !== false) fail("Varsayılan senaryosunda vazgeç yazmış olmalı değil");

  // ── 4) Onaylama yolu — gerçek görev oluşur, when gerçek değeriyle görünür ──
  const approvePromise = pending(
    page.evaluate(CALL_TOOL, {
      name: "lumos-propose-task",
      args: { title: TITLE_APPROVE, priority: "yuksek", when: "Yarın 14:00" },
    }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  const approveFields = await page.evaluate(READ_CONFIRM_FIELDS);
  const appWhen = requireField("öneri (onay)", approveFields, "when");
  if (appWhen.value !== "Yarın 14:00") {
    fail("Zaman alanı gerçek değeri göstermiyor: " + JSON.stringify(appWhen.value));
  }
  if (appWhen.unset) fail("Verilen 'when' alanı belirtilmedi işaretlenmiş");
  requireContains(
    "öncelik alanı (onay)",
    requireField("öneri (onay)", approveFields, "priority").value,
    "yuksek",
  );
  await page.click("#lumos-confirm-approve");
  const approved = await approvePromise;
  assertNoToolError("lumos-propose-task (onayla)", approved);
  if (!approved.ok || approved.approved !== true || !approved.task) {
    fail("Onaylı oluşturma başarısız: " + JSON.stringify(approved));
  }
  if (approved.task.title !== TITLE_APPROVE || approved.task.priority !== "yuksek") {
    fail("Oluşan görev alanları hatalı: " + JSON.stringify(approved.task));
  }
  // Ekranda gösterilen ile yazılan aynı olmalı.
  if (approved.task.when !== "Yarın 14:00") {
    fail("Onaylanan zaman yazılana eşit değil: " + JSON.stringify(approved.task));
  }
  const afterApprove = await page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} });
  if (afterApprove.count !== baselineCount + 1) {
    fail("Onay sonrası görev sayısı artmadı: " + afterApprove.count);
  }
  const panelHasRow = await page.evaluate((title) => {
    const raw = localStorage.getItem("lumos_panel_gorevler_list_v1");
    if (!raw) return false;
    try {
      return JSON.parse(raw).some((t) => t && t.title === title);
    } catch {
      return false;
    }
  }, TITLE_APPROVE);
  if (!panelHasRow) fail("Görev panelin kendi kalıcı listesine yazılmadı");

  // ── 5) Tamamlama — aynı kapı + durum değişikliği ekranda yazılı ────────────
  const completeRejectPromise = pending(
    page.evaluate(CALL_TOOL, { name: "lumos-complete-task", args: { ref: TITLE_APPROVE } }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  const completeFields = await page.evaluate(READ_CONFIRM_FIELDS);
  const change = requireField("tamamlama", completeFields, "status_change");
  requireContains("durum değişikliği", change.value, "bekliyor");
  requireContains("durum değişikliği", change.value, "tamamlandi");
  requireContains("durum değişikliği", change.value, "→");
  if (requireField("tamamlama", completeFields, "task").value !== TITLE_APPROVE) {
    fail("Tamamlama ekranı görev başlığını göstermiyor");
  }
  requireContains(
    "tamamlama zaman alanı",
    requireField("tamamlama", completeFields, "when").value,
    "Yarın 14:00",
  );
  requireContains(
    "tamamlama kaynak alanı",
    requireField("tamamlama", completeFields, "source").value,
    "lumos-complete-task",
  );
  await page.click("#lumos-confirm-cancel");
  const completeRejected = await completeRejectPromise;
  assertNoToolError("lumos-complete-task (reddet)", completeRejected);
  if (completeRejected.approved !== false || completeRejected.reason !== "user_rejected") {
    fail("Tamamlama reddi hatalı: " + JSON.stringify(completeRejected));
  }
  const stillOpen = await page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} });
  const stillOpenRow = stillOpen.tasks.find((t) => t.title === TITLE_APPROVE);
  if (!stillOpenRow || stillOpenRow.status === "tamamlandi") {
    fail("Vazgeç sonrası görev tamamlanmış — onay kapısı atlanmış!");
  }

  const completePromise = pending(
    page.evaluate(CALL_TOOL, { name: "lumos-complete-task", args: { ref: TITLE_APPROVE } }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-approve");
  const completed = await completePromise;
  assertNoToolError("lumos-complete-task (onayla)", completed);
  if (!completed.ok || completed.approved !== true) {
    fail("Onaylı tamamlama başarısız: " + JSON.stringify(completed));
  }
  if (!completed.task || completed.task.status !== "tamamlandi") {
    fail("Görev durumu tamamlandı değil: " + JSON.stringify(completed.task));
  }

  // 6) Bilinmeyen referans — onay modali hiç açılmamalı
  const notFound = await page.evaluate(CALL_TOOL, {
    name: "lumos-complete-task",
    args: { ref: "olmayan-gorev-" + Date.now() },
  });
  if (notFound.reason !== "task_not_found") {
    fail("Bilinmeyen görev referansı beklenen hatayı vermedi: " + JSON.stringify(notFound));
  }

  // ── 6b) ÜYELİK/DURUM ORACLE'I KAPALI ──────────────────────────────────────
  // İzin YOKKEN lumos-complete-task, verilen ref'e göre AYRIŞAN cevap
  // vermemeli. Dört durumun da BİREBİR aynı payload'ı dönmesi ve hiçbirinde
  // onay penceresi açılmaması gerekir; aksi halde tam başlığı tahmin eden bir
  // ajan görevin varlığını ve tamamlanmışlığını çıkarabilirdi.
  //
  // Önce izin AÇIKKEN bir bekleyen görev üretilir (üçüncü durumun gerçekten
  // var olduğunu kanıtlamak için), sonra izin geri alınır.
  const TITLE_PENDING = "WebMCP bekleyen " + Date.now();
  const pendingCreatePromise = pending(
    page.evaluate(CALL_TOOL, {
      name: "lumos-propose-task",
      args: { title: TITLE_PENDING, priority: "dusuk", when: "Cuma 09:00" },
    }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-approve");
  const pendingCreated = await pendingCreatePromise;
  assertNoToolError("lumos-propose-task (bekleyen görev)", pendingCreated);
  if (!pendingCreated.ok || !pendingCreated.task || pendingCreated.task.status === "tamamlandi") {
    fail("Oracle testi için bekleyen görev üretilemedi: " + JSON.stringify(pendingCreated));
  }

  await page.click("#gorevler-webmcp-consent-revoke");
  const chipRevoked = await page.evaluate(READ_CONSENT_CHIP);
  if (chipRevoked.granted !== "false") {
    fail("Oracle testi öncesi izin geri alınamadı: " + JSON.stringify(chipRevoked));
  }

  const dialogIsOpen = () =>
    page.evaluate(() => {
      const d = document.getElementById("lumos-confirm-dialog");
      return !!(d && d.open === true);
    });

  const ORACLE_PROBES = [
    ["yok (izinliyken task_not_found)", { ref: "olmayan-gorev-oracle-" + Date.now() }],
    ["var + bekliyor (izinliyken onay penceresi)", { ref: TITLE_PENDING }],
    ["var + tamamlanmış (izinliyken already_completed)", { ref: TITLE_APPROVE }],
    ["ref verilmedi (izinliyken ref_required)", {}],
  ];
  const oracleProbeResults = [];
  for (const [label, args] of ORACLE_PROBES) {
    /**
     * Çağrı ASKIDA kalmamalı: onay penceresi açılan bir regresyonda
     * `evaluate` kullanıcı kararını sonsuza dek beklerdi. Yarıştırıp
     * askıda kalmayı da açık bir başarısızlık olarak raporluyoruz.
     */
    const probe = pending(page.evaluate(CALL_TOOL, { name: "lumos-complete-task", args }));
    const settled = await Promise.race([
      probe.then((r) => ({ done: true, r })),
      new Promise((r) => setTimeout(() => r({ done: false }), 4000)),
    ]);
    if (!settled.done) {
      const stuckOpen = await dialogIsOpen();
      await page.click("#lumos-confirm-cancel").catch(() => {});
      await probe.catch(() => {});
      fail(
        "İzin yokken tamamlama çağrısı askıda kaldı — " + label
        + (stuckOpen ? " (onay penceresi AÇILDI)" : " (pencere yok, çağrı dönmedi)"),
      );
    }
    const res = settled.r;
    assertNoToolError("lumos-complete-task (izinsiz · " + label + ")", res);
    if (await dialogIsOpen()) {
      fail("İzin yokken onay penceresi açıldı — " + label);
    }
    if (res.ok !== false || res.approved !== false || res.reason !== "read_consent_required") {
      fail("İzin yokken tamamlama ayrışan cevap verdi (" + label + "): " + JSON.stringify(res));
    }
    for (const leak of ["task", "tasks", "count", "title", "priority", "when", "id", "status"]) {
      if (leak in res) {
        fail("İzinsiz tamamlama zarfında '" + leak + "' var (" + label + "): " + JSON.stringify(res));
      }
    }
    const blob = JSON.stringify(res);
    if (blob.indexOf(TITLE_PENDING) !== -1 || blob.indexOf(TITLE_APPROVE) !== -1) {
      fail("İzinsiz tamamlama cevabında görev başlığı sızdı (" + label + "): " + blob);
    }
    oracleProbeResults.push({ label, blob });
  }
  const oracleDistinct = Array.from(new Set(oracleProbeResults.map((p) => p.blob)));
  if (oracleDistinct.length !== 1) {
    fail(
      "İzin yokken tamamlama cevapları ayrışıyor — üyelik oracle'ı açık:\n"
      + oracleProbeResults.map((p) => p.label + " → " + p.blob).join("\n"),
    );
  }

  // İzinsiz cevap, lumos-list-tasks'ın izinsiz reddiyle aynı biçimde olmalı.
  const listRefusePromise = pending(
    page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-cancel");
  const listRefusedAgain = await listRefusePromise;
  assertNoToolError("lumos-list-tasks (oracle karşılaştırması)", listRefusedAgain);
  const oracleShape = Object.keys(JSON.parse(oracleDistinct[0])).sort().join(",");
  const listShape = Object.keys(listRefusedAgain).sort().join(",");
  if (oracleShape !== listShape) {
    fail(
      "complete izinsiz cevabı list-tasks reddiyle aynı biçimde değil: complete="
      + oracleShape + " list=" + listShape,
    );
  }
  const oracleDoc = JSON.parse(oracleDistinct[0]);
  if (
    !oracleDoc.consent
    || oracleDoc.consent.granted !== false
    || oracleDoc.consent.scope !== "session"
    || typeof oracleDoc.hint !== "string"
    || !oracleDoc.hint
  ) {
    fail("İzinsiz tamamlama cevabında consent/hint eksik: " + oracleDistinct[0]);
  }

  // 6b-ii) lumos-propose-task DEĞİŞMEDİ: izin yokken de yazar, içerik taşımaz.
  const TITLE_NO_CONSENT = "WebMCP izinsiz oneri " + Date.now();
  const noConsentProposePromise = pending(
    page.evaluate(CALL_TOOL, {
      name: "lumos-propose-task",
      args: { title: TITLE_NO_CONSENT, priority: "yuksek", when: "Pazartesi 08:00" },
    }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-approve");
  const noConsentPropose = await noConsentProposePromise;
  assertNoToolError("lumos-propose-task (izinsiz)", noConsentPropose);
  if (JSON.stringify(noConsentPropose) !== '{"ok":true,"approved":true}') {
    fail(
      "İzinsiz propose başarı yanıtı tam olarak {\"ok\":true,\"approved\":true} değil: "
      + JSON.stringify(noConsentPropose),
    );
  }
  const wroteWithoutConsent = await page.evaluate((t) => {
    try {
      const raw = localStorage.getItem("lumos_panel_gorevler_list_v1");
      return raw ? JSON.parse(raw).some((r) => r && r.title === t) : false;
    } catch {
      return false;
    }
  }, TITLE_NO_CONSENT);
  if (!wroteWithoutConsent) {
    fail("İzinsiz onaylanan öneri panelin kendi listesine yazılmamış — ok:true yanıltıcı");
  }

  // ── 6b-iii) REGRESYON: izin verilince üç durum yine AYRIŞIR ───────────────
  const regrant2 = pending(page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} }));
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-approve");
  const regranted2 = await regrant2;
  if (!regranted2.ok) fail("Regresyon bölümü için izin yeniden verilemedi");

  const withConsentNotFound = await page.evaluate(CALL_TOOL, {
    name: "lumos-complete-task",
    args: { ref: "olmayan-gorev-regresyon-" + Date.now() },
  });
  if (withConsentNotFound.reason !== "task_not_found") {
    fail("İzinliyken task_not_found dönmedi: " + JSON.stringify(withConsentNotFound));
  }
  const withConsentRefRequired = await page.evaluate(CALL_TOOL, {
    name: "lumos-complete-task",
    args: {},
  });
  if (withConsentRefRequired.reason !== "ref_required") {
    fail("İzinliyken ref_required dönmedi: " + JSON.stringify(withConsentRefRequired));
  }
  const alreadyWithConsent = await page.evaluate(CALL_TOOL, {
    name: "lumos-complete-task",
    args: { ref: TITLE_APPROVE },
  });
  if (alreadyWithConsent.reason !== "already_completed") {
    fail("İzinliyken already_completed dönmedi: " + JSON.stringify(alreadyWithConsent));
  }
  if (!alreadyWithConsent.task || alreadyWithConsent.task.title !== TITLE_APPROVE) {
    fail("İzin varken already_completed içerik döndürmedi: " + JSON.stringify(alreadyWithConsent));
  }
  // Bekleyen görev: izinliyken onay penceresi yine açılır ve durum geçer.
  const pendingCompletePromise = pending(
    page.evaluate(CALL_TOOL, { name: "lumos-complete-task", args: { ref: TITLE_PENDING } }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-approve");
  const pendingCompleted = await pendingCompletePromise;
  assertNoToolError("lumos-complete-task (bekleyen, izinli)", pendingCompleted);
  if (
    !pendingCompleted.ok
    || !pendingCompleted.task
    || pendingCompleted.task.status !== "tamamlandi"
  ) {
    fail("İzinliyken bekleyen görev tamamlanmadı: " + JSON.stringify(pendingCompleted));
  }
  // Dört durumun izinliyken dördü de farklı: oracle yalnızca izinsiz kapalı.
  const withConsentReasons = [
    withConsentNotFound.reason,
    withConsentRefRequired.reason,
    alreadyWithConsent.reason,
    pendingCompleted.reason == null ? "completed" : pendingCompleted.reason,
  ];
  if (new Set(withConsentReasons).size !== 4) {
    fail("İzinliyken durumlar ayrışmıyor (regresyon): " + JSON.stringify(withConsentReasons));
  }

  // ── 6c) Eşzamanlı onaylar (yerel yol): ikinci çağrı busy, ilk diyalog açık ──
  const TITLE_CONCURRENT_A = "WebMCP concurrent A " + Date.now();
  const TITLE_CONCURRENT_B = "WebMCP concurrent B " + Date.now();
  const concurrentInfo = await page.evaluate(async ({ titleA, titleB }) => {
    function parse(res) {
      const text = res && res.content && res.content[0] ? res.content[0].text : "";
      return JSON.parse(text);
    }
    const p1 = document.modelContext
      .executeTool("lumos-propose-task", { title: titleA, priority: "orta" })
      .then(parse);
    await Promise.resolve();
    const p2 = document.modelContext
      .executeTool("lumos-propose-task", { title: titleB, priority: "dusuk" })
      .then(parse);
    const first = await Promise.race([
      p1.then((r) => ({ slot: "a", r })),
      p2.then((r) => ({ slot: "b", r })),
    ]);
    window.__webmcpConcurrent = { p1, p2 };
    const dlg = document.getElementById("lumos-confirm-dialog");
    return {
      firstReason: first.r && first.r.reason,
      firstOk: first.r && first.r.ok,
      firstApproved: first.r && first.r.approved,
      dlgOpen: !!(dlg && dlg.open === true),
    };
  }, { titleA: TITLE_CONCURRENT_A, titleB: TITLE_CONCURRENT_B });
  if (concurrentInfo.firstReason !== "confirmation_busy") {
    fail("Eşzamanlı ikinci çağrı confirmation_busy değil: " + JSON.stringify(concurrentInfo));
  }
  if (concurrentInfo.firstApproved !== false || concurrentInfo.firstOk !== false) {
    fail("Eşzamanlı busy yanıtı onaylı görünüyor: " + JSON.stringify(concurrentInfo));
  }
  if (!concurrentInfo.dlgOpen) {
    fail("Eşzamanlı çağrı ilk onay diyalogunu kapatmış");
  }
  await page.click("#lumos-confirm-cancel");
  const concurrentBoth = await page.evaluate(async () => {
    const pair = window.__webmcpConcurrent;
    const [a, b] = await Promise.all([pair.p1, pair.p2]);
    delete window.__webmcpConcurrent;
    return { a, b };
  });
  const concurrentReasons = [concurrentBoth.a.reason, concurrentBoth.b.reason].sort();
  if (concurrentReasons.join(",") !== "confirmation_busy,user_rejected") {
    fail("Eşzamanlı sonuçlar beklenen değil: " + JSON.stringify(concurrentBoth));
  }
  const afterConcurrent = await page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} });
  if (
    afterConcurrent.tasks.some(
      (t) => t.title === TITLE_CONCURRENT_A || t.title === TITLE_CONCURRENT_B,
    )
  ) {
    fail("Eşzamanlı reddedilen görevler yazılmış");
  }

  // 7) İzin oturuma bağlı: yeni oturum (yeni context) izni devralmaz.
  const freshContext = await browser.newContext();
  await freshContext.addInitScript(AGENT_HARNESS);
  const freshPage = await freshContext.newPage();
  await freshPage.goto(PANEL_URL, { waitUntil: "domcontentloaded", timeout: PANEL_READY_MS });
  await waitForPanelDom(freshPage, PANEL_READY_MS);
  await freshPage.waitForFunction(
    () => document.documentElement.dataset.lumosWebmcp === "registered",
    null,
    { timeout: PANEL_READY_MS },
  );
  const freshChip = await freshPage.evaluate(READ_CONSENT_CHIP);
  if (freshChip.granted !== "false") {
    fail("Yeni oturum izni devralmış: " + JSON.stringify(freshChip));
  }
  await freshContext.close();

  // ── 8) Sunucu onay yolu: gecikmeli eşzamanlı + HTTP/JSON/ağ hataları ───────
  const mockPort = Number(port) + 17;
  const delayedMock = await startConfirmMockServer(mockPort, (hit) => ({
    delayMs: hit === 1 ? 400 : 0,
  }));
  let apiPage = null;
  let apiContext = null;
  try {
    apiContext = await browser.newContext();
    await apiContext.addInitScript(agentHarnessWithTasksApi, delayedMock.base);
    apiPage = await apiContext.newPage();
    await apiPage.goto(PANEL_URL, { waitUntil: "domcontentloaded", timeout: PANEL_READY_MS });
    await waitForPanelDom(apiPage, PANEL_READY_MS);
    await apiPage.waitForFunction(
      () => document.documentElement.dataset.lumosWebmcp === "registered",
      null,
      { timeout: PANEL_READY_MS },
    );
    // confirmation_enabled senkronu: panel GET /tasks çeker.
    await apiPage.waitForFunction(
      async (base) => {
        try {
          const r = await fetch(base + "/tasks");
          const doc = await r.json();
          return doc && doc.confirmation_enabled === true;
        } catch {
          return false;
        }
      },
      delayedMock.base,
      { timeout: PANEL_READY_MS },
    );
    // Panelin kendi sync'i de aynı bayrağı alsın.
    await apiPage.evaluate(async (base) => {
      const r = await fetch(base + "/tasks", { headers: { Accept: "application/json" } });
      const doc = await r.json();
      // refreshPanelGorevlerFromTasksApi kapalı kalmasın diye bir kez tetikle:
      // panel zaten açılışta çağırır; yine de confirmation bayrağını zorla çek.
      window.dispatchEvent(new Event("focus"));
      return doc.confirmation_enabled === true;
    }, delayedMock.base);
    // Açılış sync'i kaçırdıysa Görevler sekmesine tıklayarak yenile.
    await apiPage.click('.panel-body button[data-module="gorevler"]');
    await new Promise((r) => setTimeout(r, 500));

    const TITLE_DELAY_A = "WebMCP delay A " + Date.now();
    const TITLE_DELAY_B = "WebMCP delay B " + Date.now();
    const delayedRace = await apiPage.evaluate(async ({ titleA, titleB }) => {
      function parse(res) {
        const text = res && res.content && res.content[0] ? res.content[0].text : "";
        return JSON.parse(text);
      }
      const p1 = document.modelContext
        .executeTool("lumos-propose-task", { title: titleA })
        .then(parse);
      await new Promise((r) => setTimeout(r, 30));
      const p2 = document.modelContext
        .executeTool("lumos-propose-task", { title: titleB })
        .then(parse);
      const first = await Promise.race([
        p1.then((r) => ({ slot: "a", r })),
        p2.then((r) => ({ slot: "b", r })),
      ]);
      window.__webmcpDelayedConcurrent = { p1, p2 };
      return { firstReason: first.r && first.r.reason, first: first.r };
    }, { titleA: TITLE_DELAY_A, titleB: TITLE_DELAY_B });
    if (delayedRace.firstReason !== "confirmation_busy") {
      fail(
        "Geciktirilmiş eşzamanlı çağrı confirmation_busy değil: " +
          JSON.stringify(delayedRace),
      );
    }
    if (delayedMock.confirmHits() < 1) {
      fail("Geciktirilmiş eşzamanlı test sunucu onay yolunu kullanmadı (confirmHits=0)");
    }
    await apiPage.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
    const delayedDlgStillOpen = await apiPage.evaluate(() => {
      const dlg = document.getElementById("lumos-confirm-dialog");
      return !!(dlg && dlg.open === true);
    });
    if (!delayedDlgStillOpen) {
      fail("Geciktirilmiş eşzamanlı çağrı ilk diyaloğu kapatmış");
    }
    await apiPage.click("#lumos-confirm-cancel");
    const delayedBoth = await apiPage.evaluate(async () => {
      const pair = window.__webmcpDelayedConcurrent;
      const [a, b] = await Promise.all([pair.p1, pair.p2]);
      delete window.__webmcpDelayedConcurrent;
      return { a, b };
    });
    const delayedReasons = [delayedBoth.a.reason, delayedBoth.b.reason].sort();
    if (delayedReasons.join(",") !== "confirmation_busy,user_rejected") {
      fail("Geciktirilmiş eşzamanlı sonuçlar hatalı: " + JSON.stringify(delayedBoth));
    }
  } finally {
    if (apiContext) await apiContext.close().catch(() => {});
    await delayedMock.close();
  }

  // 8b) HTTP 500 → confirmation_failed (user_rejected değil)
  const err500Mock = await startConfirmMockServer(mockPort + 1, () => ({
    status: 500,
    body: { ok: false, error: "boom" },
  }));
  try {
    apiContext = await browser.newContext();
    await apiContext.addInitScript(agentHarnessWithTasksApi, err500Mock.base);
    apiPage = await apiContext.newPage();
    await apiPage.goto(PANEL_URL, { waitUntil: "domcontentloaded", timeout: PANEL_READY_MS });
    await waitForPanelDom(apiPage, PANEL_READY_MS);
    await apiPage.waitForFunction(
      () => document.documentElement.dataset.lumosWebmcp === "registered",
      null,
      { timeout: PANEL_READY_MS },
    );
    await apiPage.click('.panel-body button[data-module="gorevler"]');
    await new Promise((r) => setTimeout(r, 600));
    const http500 = await apiPage.evaluate(CALL_TOOL, {
      name: "lumos-propose-task",
      args: { title: "WebMCP HTTP 500 " + Date.now() },
    });
    if (http500.reason !== "confirmation_failed") {
      fail("HTTP 500 confirmation_failed olmalı: " + JSON.stringify(http500));
    }
    if (http500.approved !== false || http500.ok !== false) {
      fail("HTTP 500 yazma yapmış görünüyor: " + JSON.stringify(http500));
    }
    const dlgAfter500 = await apiPage.evaluate(() => {
      const dlg = document.getElementById("lumos-confirm-dialog");
      return !!(dlg && dlg.open === true);
    });
    if (dlgAfter500) fail("HTTP 500 sonrası onay diyaloğu açılmış olmamalı");
  } finally {
    if (apiContext) await apiContext.close().catch(() => {});
    apiContext = null;
    await err500Mock.close();
  }

  // 8c) Bozuk JSON → confirmation_failed
  const badJsonMock = await startConfirmMockServer(mockPort + 2, () => ({
    status: 200,
    rawBody: "{not-json",
  }));
  try {
    apiContext = await browser.newContext();
    await apiContext.addInitScript(agentHarnessWithTasksApi, badJsonMock.base);
    apiPage = await apiContext.newPage();
    await apiPage.goto(PANEL_URL, { waitUntil: "domcontentloaded", timeout: PANEL_READY_MS });
    await waitForPanelDom(apiPage, PANEL_READY_MS);
    await apiPage.waitForFunction(
      () => document.documentElement.dataset.lumosWebmcp === "registered",
      null,
      { timeout: PANEL_READY_MS },
    );
    await apiPage.click('.panel-body button[data-module="gorevler"]');
    await new Promise((r) => setTimeout(r, 600));
    const badJson = await apiPage.evaluate(CALL_TOOL, {
      name: "lumos-propose-task",
      args: { title: "WebMCP bozuk JSON " + Date.now() },
    });
    if (badJson.reason !== "confirmation_failed") {
      fail("Bozuk JSON confirmation_failed olmalı: " + JSON.stringify(badJson));
    }
  } finally {
    if (apiContext) await apiContext.close().catch(() => {});
    apiContext = null;
    await badJsonMock.close();
  }

  // 8d) Ağ istisnası (kapalı port) → confirmation_failed
  const deadBase = "http://127.0.0.1:" + (mockPort + 3);
  // Önce confirmation_enabled'i canlı mock'tan al, sonra tabanı ölü porta çevir.
  const seedMock = await startConfirmMockServer(mockPort + 4, () => ({
    status: 200,
    body: {
      ok: true,
      confirmation_id: "should_not_be_used",
      preview: { what: "create_task", where: "x", effect: "local_task_create" },
    },
  }));
  try {
    apiContext = await browser.newContext();
    await apiContext.addInitScript(agentHarnessWithTasksApi, seedMock.base);
    apiPage = await apiContext.newPage();
    await apiPage.goto(PANEL_URL, { waitUntil: "domcontentloaded", timeout: PANEL_READY_MS });
    await waitForPanelDom(apiPage, PANEL_READY_MS);
    await apiPage.waitForFunction(
      () => document.documentElement.dataset.lumosWebmcp === "registered",
      null,
      { timeout: PANEL_READY_MS },
    );
    await apiPage.click('.panel-body button[data-module="gorevler"]');
    await new Promise((r) => setTimeout(r, 600));
    // confirmation bayrağı seed mock'tan geldi; network hatası için tabanı değiştir.
    await apiPage.evaluate((base) => {
      window.LUMOS_PANEL_TASKS_API_BASE = base;
    }, deadBase);
    const networkFail = await apiPage.evaluate(CALL_TOOL, {
      name: "lumos-propose-task",
      args: { title: "WebMCP network fail " + Date.now() },
    });
    if (networkFail.reason !== "confirmation_failed") {
      fail("Ağ istisnası confirmation_failed olmalı: " + JSON.stringify(networkFail));
    }
    if (networkFail.reason === "user_rejected") {
      fail("Ağ istisnası user_rejected sayılmış");
    }

    // 8e) API tabanı yokken (confirmation hâlâ açık) → confirmation_unavailable
    await apiPage.evaluate(() => {
      window.LUMOS_PANEL_TASKS_API_BASE = false;
    });
    const unavailable = await apiPage.evaluate(CALL_TOOL, {
      name: "lumos-propose-task",
      args: { title: "WebMCP unavailable " + Date.now() },
    });
    if (unavailable.reason !== "confirmation_unavailable") {
      fail(
        "API tabanı yokken confirmation_unavailable olmalı: " + JSON.stringify(unavailable),
      );
    }
  } finally {
    if (apiContext) await apiContext.close().catch(() => {});
    await seedMock.close();
  }

  await browser.close();
  browser = null;
  console.log("WEBMCP_PANEL_E2E_RESULT: PASS");
  console.log("surface: ui/dist static + document.modelContext");
  console.log("tools:", EXPECTED_TOOLS.join(", "));
  console.log("read consent: refused without approval, granted on approval, revocable");
  console.log("--- üyelik oracle'ı (izin YOK, lumos-complete-task) ---");
  for (const p of oracleProbeResults) console.log("  " + p.label + " → " + p.blob);
  console.log("  onay penceresi: hiçbirinde açılmadı");
  console.log("--- izin VERİLDİKTEN sonra (regresyon) ---");
  console.log("  yok            → " + JSON.stringify(withConsentNotFound));
  console.log("  ref verilmedi  → " + JSON.stringify(withConsentRefRequired));
  console.log("  tamamlanmış    → " + JSON.stringify(alreadyWithConsent));
  console.log("  bekliyor       → " + JSON.stringify(pendingCompleted));
  console.log("propose (izinsiz): " + JSON.stringify(noConsentPropose) + " · panele yazıldı");
  console.log("confirm dialog: title, priority, when, status, source rendered from real args");
  console.log(
    "confirmation lock: concurrent busy + server HTTP 500 / bozuk JSON / network attribution",
  );
  console.log("url:", PANEL_URL);
} catch (err) {
  if (browser) await browser.close().catch(() => {});
  fail(String(err && err.stack ? err.stack : err));
} finally {
  await closeServer(server);
}
