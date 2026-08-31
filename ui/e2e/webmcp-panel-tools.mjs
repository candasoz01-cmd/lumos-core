/**
 * WebMCP panel tool E2E — 2026-08-25 sonrası eklendi (WebMCP Challenge dilimi).
 *
 * Doğrulanan sözleşme:
 *  1. Panel yüklendiğinde 3 tool `document.modelContext.registerTool()` ile kaydedilir.
 *  2. `lumos-list-tasks` okuma yapar, onay istemez.
 *  3. `lumos-propose-task` panelin insan onay modalini açar; "Vazgeç" seçilirse
 *     HİÇBİR görev yazılmaz (onay kapısı ajan tarafından atlanamaz).
 *  4. Aynı tool "Onayla" ile gerçekten görev oluşturur ve panelde görünür.
 *  5. `lumos-complete-task` yine onay kapısından geçerek görevi tamamlar.
 *
 * Not: Headless Chromium'da tarayıcının WebMCP uygulaması yok. Test yalnızca
 * TARAYICI TARAFINI (agent harness) taklit eder — sayfanın kendi kayıt ve
 * execute kodu gerçek olarak çalışır.
 */
import { chromium } from "playwright";
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

/** Ajan tool çağrısı: sonucu JSON payload'a çevirir. */
const CALL_TOOL = function (payload) {
  return document.modelContext
    .executeTool(payload.name, payload.args)
    .then(function (res) {
      const text = res && res.content && res.content[0] ? res.content[0].text : "";
      return JSON.parse(text);
    });
};

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

  // 2) Okuma — onay istemez
  const before = await page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} });
  if (!before.ok || !Array.isArray(before.tasks)) {
    fail("lumos-list-tasks beklenen payload'ı döndürmedi: " + JSON.stringify(before));
  }
  const baselineCount = before.count;

  const TITLE_REJECT = "WebMCP reddedilen " + Date.now();
  const TITLE_APPROVE = "WebMCP onaylanan " + Date.now();

  // 3) Reddetme yolu — onay kapısı atlanamaz
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

  // 4) Onaylama yolu — gerçek görev oluşur
  const approvePromise = pending(
    page.evaluate(CALL_TOOL, {
      name: "lumos-propose-task",
      args: { title: TITLE_APPROVE, priority: "yuksek", when: "Yarın 14:00" },
    }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-approve");
  const approved = await approvePromise;
  assertNoToolError("lumos-propose-task (onayla)", approved);
  if (!approved.ok || approved.approved !== true || !approved.task) {
    fail("Onaylı oluşturma başarısız: " + JSON.stringify(approved));
  }
  if (approved.task.title !== TITLE_APPROVE || approved.task.priority !== "yuksek") {
    fail("Oluşan görev alanları hatalı: " + JSON.stringify(approved.task));
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

  // 5) Tamamlama — yine onay kapısından geçer
  const completeRejectPromise = pending(
    page.evaluate(CALL_TOOL, { name: "lumos-complete-task", args: { ref: TITLE_APPROVE } }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
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

  await browser.close();
  browser = null;
  console.log("WEBMCP_PANEL_E2E_RESULT: PASS");
  console.log("surface: ui/dist static + document.modelContext");
  console.log("tools:", EXPECTED_TOOLS.join(", "));
  console.log("url:", PANEL_URL);
} catch (err) {
  if (browser) await browser.close().catch(() => {});
  fail(String(err && err.stack ? err.stack : err));
} finally {
  await closeServer(server);
}
