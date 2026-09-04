/**
 * MCP/WebMCP closeout — NATIVE + API-BACKED interaktif sürücü.
 *
 * #818'de açık bırakılan tek boşluğu kapatmak için: mevcut
 * `webmcp-native-verify.mjs` native Chrome kanıtını ui/dist STATİK sunucu
 * üzerinde üretir; yazmalar panelin localStorage yoluna düşer. Bu betik aynı
 * native ortamı kurar ama paneli CANLI `panel_tasks_server.py` REST yüzeyine
 * bağlar.
 *
 * Hangi tool hangi yoldan gider (koşumla doğrulandı):
 *   - `lumos-propose-task`  → API-backed: POST /lumos-confirm/request → POST /tasks
 *   - `lumos-complete-task` → API-backed: POST /lumos-confirm/request → POST /tasks/complete
 *   - `lumos-list-tasks`    → API'ye GİTMEZ; panelin bellekteki `panelGorevlerTasks`
 *                             projeksiyonunu döndürür. Yani okuma yolu sunucu
 *                             tarafı policy/confirmation kapılarından geçmez.
 * Reddedilen çağrılar da API'ye gitmez — sunucuda arama yapılmadan reddedilirler.
 *
 * Bu betik BİR TEST DEĞİLDİR, otomatik onay vermez. Onay/ret kararlarını
 * tarayıcı penceresinde İNSAN verir. Betik yalnızca ajan tarafını sürer.
 *
 *  - `document.modelContext` HİÇBİR YERDE tanımlanmaz; addInitScript yok.
 *  - Sayfaya tek satır shim/harness enjekte edilmez.
 *  - Tool çağrıları native imza ile: executeTool(RegisteredTool, argsJson).
 *
 * Komutlar (stdin):
 *   proof              native modelContext kanıtını yazdır
 *   tools              tarayıcının gördüğü tool listesi
 *   consent            panel izin rozetinin durumu
 *   list               lumos-list-tasks  (izin yoksa panelde izin diyaloğu açar)
 *   propose <başlık>   lumos-propose-task (onay diyaloğu açar)
 *   complete <ref>     lumos-complete-task (onay diyaloğu açar)
 *   revoke             panelin "İzni geri al" düğmesine basar
 *   api                sunucu tarafı gerçeği: GET /tasks
 *   net                son ağ isteklerini yazdır (API'ye gerçekten gidildi mi)
 *   quit
 */
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import readline from "node:readline";
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
import {
  buildTasksApiBase,
  createTempLumosBase,
  fetchTasksDoc,
  startTasksServer,
  stopTasksServer,
  waitForTasksApi,
} from "./lib/tasks-server.mjs";

const CHROME_BIN =
  process.env.CHROME_BIN || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const WEBMCP_FEATURES = "WebMCP";
const WEBMCP_BLINK_FEATURES = "DocumentModelcontext";
const CDP_PORT = Number(process.env.WEBMCP_CDP_PORT || 9413);

/**
 * panel.astro API tabanını BUILD ZAMANI gömer:
 *   import.meta.env.PUBLIC_LUMOS_PANEL_TASKS_URL || "http://127.0.0.1:8766"
 * Varsayılanı kullanıyoruz ki sayfaya hiçbir şey enjekte etmek zorunda
 * kalmayalım — tasks server tam olarak o portta ayağa kalkar.
 */
const TASKS_PORT = process.env.LUMOS_PANEL_TASKS_E2E_PORT || "8766";

/** Native ajan çağrısı — Chrome'un gerçek imzası. */
const NATIVE_CALL_TOOL = async function (payload) {
  const tools = await document.modelContext.getTools();
  const tool = tools.find((t) => t.name === payload.name);
  if (!tool) throw new Error("tool native olarak kayıtlı değil: " + payload.name);
  const raw = await document.modelContext.executeTool(tool, JSON.stringify(payload.args || {}));
  const envelope = typeof raw === "string" ? JSON.parse(raw) : raw;
  const text = envelope && envelope.content && envelope.content[0] ? envelope.content[0].text : "";
  return JSON.parse(text);
};

const NATIVE_PROOF = function () {
  const mc = document.modelContext;
  const desc = Object.getOwnPropertyDescriptor(Document.prototype, "modelContext");
  return {
    chromeUserAgent: navigator.userAgent,
    present: !!mc,
    brandString: Object.prototype.toString.call(mc),
    constructorName: mc && mc.constructor ? mc.constructor.name : null,
    prototypeMembers: mc ? Object.getOwnPropertyNames(Object.getPrototypeOf(mc)).sort() : [],
    registerToolSource: mc && mc.registerTool ? String(mc.registerTool) : null,
    executeToolSource: mc && mc.executeTool ? String(mc.executeTool) : null,
    documentPrototypeGetter: desc && desc.get ? String(desc.get) : null,
    ownPropertyOnDocument: Object.prototype.hasOwnProperty.call(document, "modelContext"),
    globalInterfaces: ["ModelContext", "WebMCPEvent"].filter((n) => n in window),
    pageStatus: window.__lumosWebMcpStatus ? { ...window.__lumosWebMcpStatus } : null,
  };
};

const CONSENT_STATE = function () {
  const box = document.getElementById("gorevler-webmcp-consent");
  const btn = document.getElementById("gorevler-webmcp-consent-revoke");
  let stored = null;
  try {
    stored = window.sessionStorage.getItem("lumos_panel_webmcp_read_consent_v1");
  } catch (_) {
    stored = "<erişilemedi>";
  }
  return {
    granted: box ? box.getAttribute("data-granted") : null,
    revokeVisible: !!btn && btn.hidden === false,
    sessionStorage: stored,
  };
};

/** Panelin API tabanı gerçekten canlı sunucuya mı bakıyor? */
const API_WIRING = function () {
  return {
    apiBase: typeof window.LUMOS_PANEL_TASKS_API_BASE === "undefined"
      ? "<tanımsız>"
      : window.LUMOS_PANEL_TASKS_API_BASE,
    origin: window.location.origin,
  };
};

assertPanelDistBuilt();

const { port, PANEL_URL } = getDefaultServerTargets();
const apiBase = buildTasksApiBase(TASKS_PORT);
const tmpBase = createTempLumosBase("lumos-mcp-closeout-");
const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lumos-webmcp-native-api-"));

let staticServer;
let tasksProc;
let chrome;
let browser;
let page;
const netLog = [];

function log(...a) {
  console.log(...a);
}

async function shutdown(code = 0) {
  try { if (browser) await browser.close(); } catch (_) {}
  try { if (chrome) chrome.kill("SIGTERM"); } catch (_) {}
  stopTasksServer(tasksProc);
  await closeServer(staticServer);
  log("\n[kapatıldı] geçici LUMOS_BASE_DIR: " + tmpBase);
  process.exit(code);
}

try {
  if (!fs.existsSync(CHROME_BIN)) {
    console.error("Chrome bulunamadı: " + CHROME_BIN);
    process.exit(1);
  }

  // ── 1) Canlı tasks API ──────────────────────────────────────────────────
  tasksProc = startTasksServer(tmpBase, TASKS_PORT, { confirmationEnabled: true });
  let tasksStderr = "";
  if (tasksProc.stderr) tasksProc.stderr.on("data", (d) => { tasksStderr += String(d); });
  try {
    await waitForTasksApi(apiBase, 20000);
  } catch (err) {
    console.error("panel_tasks_server ayağa kalkmadı: " + err.message + "\n" + tasksStderr);
    await shutdown(1);
  }
  log("[ok] tasks API: " + apiBase + "  (LUMOS_BASE_DIR=" + tmpBase + ")");
  log("[ok] env: LUMOS_MODE=online LUMOS_PROFILE=guvenli_yurut "
      + "LUMOS_SESSION_UNLOCKED=true LUMOS_CONFIRMATION_ENABLED=true");

  // ── 2) Panel (ui/dist) ──────────────────────────────────────────────────
  staticServer = await startStaticServer(DIST_DIR, port);
  await waitForServer(PANEL_URL, PANEL_READY_MS);
  log("[ok] panel: " + PANEL_URL);

  // ── 3) Native WebMCP Chrome ─────────────────────────────────────────────
  const chromeArgs = [
    "--user-data-dir=" + userDataDir,
    "--remote-debugging-port=" + CDP_PORT,
    "--enable-features=" + WEBMCP_FEATURES,
    "--enable-blink-features=" + WEBMCP_BLINK_FEATURES,
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "about:blank",
  ];
  chrome = spawn(CHROME_BIN, chromeArgs, { stdio: ["ignore", "pipe", "pipe"] });
  let chromeStderr = "";
  chrome.stderr.on("data", (d) => { chromeStderr += String(d); });

  const deadline = Date.now() + 30000;
  while (Date.now() < deadline && !browser) {
    try {
      browser = await chromium.connectOverCDP("http://127.0.0.1:" + CDP_PORT);
    } catch {
      await new Promise((r) => setTimeout(r, 400));
    }
  }
  if (!browser) {
    console.error("CDP bağlanamadı (port " + CDP_PORT + ")\n" + chromeStderr);
    await shutdown(1);
  }

  const ctx = browser.contexts()[0];
  page = ctx.pages()[0] || (await ctx.newPage());
  // DİKKAT: addInitScript YOK — sayfaya hiçbir şey enjekte edilmiyor.

  page.on("request", (r) => {
    const u = r.url();
    if (u.startsWith(apiBase)) netLog.push(r.method() + " " + u.slice(apiBase.length));
  });

  await page.goto(PANEL_URL, { waitUntil: "domcontentloaded", timeout: PANEL_READY_MS });
  await waitForPanelDom(page, PANEL_READY_MS);
  await page.waitForFunction(
    () => document.documentElement.dataset.lumosWebmcp === "registered",
    null,
    { timeout: PANEL_READY_MS },
  );

  const proof = await page.evaluate(NATIVE_PROOF);
  if (!proof.present) {
    console.error("document.modelContext yok — bayrak tutmadı\n" + chromeStderr);
    await shutdown(1);
  }
  if (proof.ownPropertyOnDocument) {
    console.error("modelContext own property — native değil");
    await shutdown(1);
  }
  log("[ok] native modelContext doğrulandı (" + proof.brandString + ")");
  log("[ok] wiring: " + JSON.stringify(await page.evaluate(API_WIRING)));
  log("\nHazır. Onay/ret kararlarını Chrome penceresinde SEN veriyorsun.\n");

  // ── 4) İnteraktif sürücü ────────────────────────────────────────────────
  const rl = readline.createInterface({ input: process.stdin, terminal: false });
  rl.on("line", async (raw) => {
    const line = String(raw || "").trim();
    if (!line) return;
    const sp = line.indexOf(" ");
    const cmd = (sp === -1 ? line : line.slice(0, sp)).toLowerCase();
    const rest = sp === -1 ? "" : line.slice(sp + 1).trim();
    try {
      if (cmd === "quit" || cmd === "exit") return void (await shutdown(0));
      if (cmd === "proof") return log(JSON.stringify(await page.evaluate(NATIVE_PROOF), null, 2));
      if (cmd === "tools") {
        const t = await page.evaluate(async () =>
          (await document.modelContext.getTools()).map((x) => x.name).sort());
        return log(JSON.stringify(t));
      }
      if (cmd === "consent") return log(JSON.stringify(await page.evaluate(CONSENT_STATE)));
      if (cmd === "api") return log(JSON.stringify(await fetchTasksDoc(apiBase), null, 2));
      if (cmd === "net") return log(netLog.length ? netLog.join("\n") : "(API'ye istek yok)");
      if (cmd === "revoke") {
        await page.click("#gorevler-webmcp-consent-revoke");
        await page.waitForTimeout(150);
        return log("revoke sonrası: " + JSON.stringify(await page.evaluate(CONSENT_STATE)));
      }
      let payload = null;
      if (cmd === "list") payload = { name: "lumos-list-tasks", args: {} };
      if (cmd === "propose") {
        payload = { name: "lumos-propose-task", args: { title: rest || "Closeout smoke", priority: "yuksek", when: "Yarın 14:00" } };
      }
      if (cmd === "complete") payload = { name: "lumos-complete-task", args: rest ? { ref: rest } : {} };
      if (!payload) return log("bilinmeyen komut: " + cmd);

      log("→ " + payload.name + " " + JSON.stringify(payload.args) + "   (panelde karar bekleniyor…)");
      const before = netLog.length;
      const out = await page.evaluate(NATIVE_CALL_TOOL, payload);
      log("← " + JSON.stringify(out));
      const used = netLog.slice(before);
      log("   API istekleri: "
          + (used.length ? used.join(", ") : "YOK (bu çağrıda Tasks API kullanılmadı)"));
    } catch (err) {
      log("HATA: " + String((err && err.message) || err));
    }
  });
  rl.on("close", () => { void shutdown(0); });
} catch (err) {
  console.error("Kurulum hatası: " + String((err && err.stack) || err));
  await shutdown(1);
}
