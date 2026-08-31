/**
 * NATIVE WebMCP doğrulaması — WebMCP Challenge kanıtı.
 *
 * `webmcp-panel-tools.mjs` sayfanın kendi kodunu doğrular ama
 * `document.modelContext`'i TEST enjekte eder (harness). Yarışma kanıtı için
 * bu yeterli değildir. Bu betik farkı kapatır:
 *
 *  - Sistemdeki gerçek Google Chrome, WebMCP bayrağı açık ve AYRI bir
 *    user-data-dir ile başlatılır (kullanıcının profiline dokunulmaz).
 *  - Bu betik `document.modelContext`'i HİÇBİR YERDE tanımlamaz; sayfaya
 *    tek satır shim/harness enjekte edilmez. `addInitScript` kullanılmaz.
 *  - `document.modelContext`'in TARAYICI tarafından sağlandığı kanıtlanır:
 *    Document.prototype üstünde native getter, [object ModelContext] etiketi,
 *    `[native code]` gövdeli metotlar ve document üstünde own property OLMAMASI.
 *  - Akış native ortamda uçtan uca sürülür: okuma izni reddi → içerik yok,
 *    izin → içerik var, öneri → diyalogda priority/when görünür →
 *    Vazgeç'te yazılmaz → Onayla'da yazılır, tamamlama aynı kapıdan geçer.
 *
 * Kullanım:  node e2e/webmcp-native-verify.mjs
 * Bayraklar: CHROME_BIN, WEBMCP_HEADED=1, WEBMCP_CDP_PORT
 */
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
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

const CHROME_BIN =
  process.env.CHROME_BIN
  || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

/**
 * Chrome 152 WebMCP yüzeyi:
 *   base::Feature   kWebMCP                 → --enable-features=WebMCP
 *   blink RE feature kDocumentModelcontext  → --enable-blink-features=DocumentModelcontext
 * (İkisi de Chrome ikilisindeki sembollerden doğrulandı.)
 */
const WEBMCP_FEATURES = "WebMCP";
const WEBMCP_BLINK_FEATURES = "DocumentModelcontext";

const CDP_PORT = Number(process.env.WEBMCP_CDP_PORT || 9412);
const HEADED = process.env.WEBMCP_HEADED === "1";

function fail(reason) {
  console.error("WEBMCP_NATIVE_RESULT: FAIL");
  console.error(reason);
  process.exit(1);
}

function requireContains(label, actual, needle) {
  if (String(actual).indexOf(needle) === -1) {
    fail(label + ": beklenen metin yok. beklenen=" + needle + " görünen=" + JSON.stringify(actual));
  }
}

/**
 * Native ajan çağrısı. `getTools()` ile keşfedip aynı RegisteredTool nesnesiyle
 * `executeTool(tool, argsJsonString)` çağırır — Chrome'un gerçek imzası.
 * Sonuç JSON *string* döner; iki kat çözülür.
 */
const NATIVE_CALL_TOOL = async function (payload) {
  const tools = await document.modelContext.getTools();
  const tool = tools.find((t) => t.name === payload.name);
  if (!tool) throw new Error("tool not registered natively: " + payload.name);
  const raw = await document.modelContext.executeTool(tool, JSON.stringify(payload.args || {}));
  const envelope = typeof raw === "string" ? JSON.parse(raw) : raw;
  const text = envelope && envelope.content && envelope.content[0] ? envelope.content[0].text : "";
  return JSON.parse(text);
};

const READ_CONFIRM_FIELDS = function () {
  const dl = document.getElementById("lumos-confirm-preview-fields");
  const wrap = document.getElementById("lumos-confirm-preview-fields-wrap");
  const byKey = {};
  if (!dl || !wrap) return { hidden: true, byKey };
  const nodes = Array.prototype.slice.call(dl.children);
  for (let i = 0; i + 1 < nodes.length; i += 2) {
    const dd = nodes[i + 1];
    const key = dd.getAttribute("data-field") || "";
    if (key) {
      byKey[key] = {
        label: (nodes[i].textContent || "").trim(),
        value: (dd.textContent || "").trim(),
        unset: dd.getAttribute("data-unset") === "true",
      };
    }
  }
  return { hidden: wrap.hidden === true, byKey };
};

/** Kanıt: modelContext'i tarayıcı mı sağladı, sayfa mı? */
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
    /* Sayfa/harness enjekte etseydi bu true olurdu (Object.defineProperty(document,…)). */
    ownPropertyOnDocument: Object.prototype.hasOwnProperty.call(document, "modelContext"),
    globalInterfaces: ["ModelContext", "WebMCPEvent"].filter((n) => n in window),
    /**
     * Chrome 152'de ajan tarafını taklit eden bir TEST yüzeyi
     * (`navigator.modelContextTesting`) YOKTUR. Bunu kayda geçiriyoruz ki
     * ileride eklendiğinde fark edilsin; çağrılar `document.modelContext`
     * üstünden yapılır.
     */
    modelContextTestingType: typeof navigator.modelContextTesting,
    modelContextTestingInNavigator: "modelContextTesting" in navigator,
    /* Sayfanın kendi kayıt durumu — shim yok, gerçek kayıt. */
    pageStatus: window.__lumosWebMcpStatus ? { ...window.__lumosWebMcpStatus } : null,
  };
};

assertPanelDistBuilt();

const { port, PANEL_URL } = getDefaultServerTargets();
const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lumos-webmcp-native-"));
let server;
let chrome;
let browser;

const chromeArgs = [
  "--user-data-dir=" + userDataDir,
  "--remote-debugging-port=" + CDP_PORT,
  "--enable-features=" + WEBMCP_FEATURES,
  "--enable-blink-features=" + WEBMCP_BLINK_FEATURES,
  "--no-first-run",
  "--no-default-browser-check",
  "--disable-background-networking",
];
if (!HEADED) chromeArgs.push("--headless=new");
chromeArgs.push("about:blank");

try {
  if (!fs.existsSync(CHROME_BIN)) {
    fail("Chrome bulunamadı: " + CHROME_BIN + " (CHROME_BIN ile yol verin)");
  }
  server = await startStaticServer(DIST_DIR, port);
  await waitForServer(PANEL_URL, PANEL_READY_MS);

  chrome = spawn(CHROME_BIN, chromeArgs, { stdio: ["ignore", "pipe", "pipe"] });
  let chromeStderr = "";
  chrome.stderr.on("data", (d) => {
    chromeStderr += String(d);
  });

  // CDP hazır olana kadar bekle.
  const deadline = Date.now() + 30000;
  let connected = null;
  while (Date.now() < deadline && !connected) {
    try {
      connected = await chromium.connectOverCDP("http://127.0.0.1:" + CDP_PORT);
    } catch {
      await new Promise((r) => setTimeout(r, 400));
    }
  }
  if (!connected) {
    fail(
      "Chrome CDP'ye bağlanılamadı (port " + CDP_PORT + ").\nchrome stderr:\n" + chromeStderr,
    );
  }
  browser = connected;

  const ctx = browser.contexts()[0];
  const page = ctx.pages()[0] || (await ctx.newPage());
  // DİKKAT: addInitScript YOK. Bu betik sayfaya hiçbir şey enjekte etmez.

  await page.goto(PANEL_URL, { waitUntil: "domcontentloaded", timeout: PANEL_READY_MS });
  await waitForPanelDom(page, PANEL_READY_MS);

  // ── 1) NATIVE KANIT ────────────────────────────────────────────────────────
  const proof = await page.evaluate(NATIVE_PROOF);
  if (!proof.present) {
    fail(
      "document.modelContext yok — bayrak tutmadı.\nargs=" + chromeArgs.join(" ")
      + "\nchrome stderr:\n" + chromeStderr,
    );
  }
  if (proof.ownPropertyOnDocument) {
    fail("modelContext document üstünde own property — sayfa/harness enjekte etmiş, native değil");
  }
  if (proof.brandString !== "[object ModelContext]") {
    fail("Brand string native değil: " + proof.brandString);
  }
  requireContains("registerTool", proof.registerToolSource, "[native code]");
  requireContains("executeTool", proof.executeToolSource, "[native code]");
  requireContains("Document.prototype getter", proof.documentPrototypeGetter, "[native code]");
  if (!proof.globalInterfaces.includes("ModelContext")) {
    fail("Global ModelContext arayüzü yok — native yüzey eksik");
  }

  await page.waitForFunction(
    () => document.documentElement.dataset.lumosWebmcp === "registered",
    null,
    { timeout: PANEL_READY_MS },
  );
  const tools = await page.evaluate(async () =>
    (await document.modelContext.getTools()).map((t) => t.name).sort(),
  );
  const expected = ["lumos-complete-task", "lumos-list-tasks", "lumos-propose-task"];
  if (tools.join(",") !== expected.join(",")) {
    fail("Native kayıtta beklenen tool'lar yok: " + JSON.stringify(tools));
  }

  // ── 2) OKUMA İZNİ — native ortamda ────────────────────────────────────────
  const refusePromise = page
    .evaluate(NATIVE_CALL_TOOL, { name: "lumos-list-tasks", args: {} })
    .catch((e) => ({ __err: String(e && e.message) }));
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-cancel");
  const refused = await refusePromise;
  if (refused.__err) fail("Native okuma çağrısı hata verdi: " + refused.__err);
  if (refused.reason !== "read_consent_required" || "tasks" in refused || "count" in refused) {
    fail("Native ortamda izinsiz okuma içerik döndürdü: " + JSON.stringify(refused));
  }

  const allowPromise = page
    .evaluate(NATIVE_CALL_TOOL, { name: "lumos-list-tasks", args: {} })
    .catch((e) => ({ __err: String(e && e.message) }));
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-approve");
  const listed = await allowPromise;
  if (!listed.ok || !Array.isArray(listed.tasks)) {
    fail("Native ortamda izin verilince liste gelmedi: " + JSON.stringify(listed));
  }
  const baselineCount = listed.count;
  const chipOn = await page.getAttribute("#gorevler-webmcp-consent", "data-granted");
  if (chipOn !== "true") fail("Native ortamda görünür izin durumu açılmadı");

  // ── 3) ÖNERİ — diyalogda priority/when görünür, Vazgeç yazmaz ─────────────
  const TITLE = "Native WebMCP " + Date.now();
  const rejectPromise = page
    .evaluate(NATIVE_CALL_TOOL, {
      name: "lumos-propose-task",
      args: { title: TITLE, priority: "yuksek", when: "Yarın 14:00" },
    })
    .catch((e) => ({ __err: String(e && e.message) }));
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  const shownFields = await page.evaluate(READ_CONFIRM_FIELDS);
  if (shownFields.hidden) fail("Native ortamda alan listesi gizli");
  if (!shownFields.byKey.priority) fail("Native onay ekranında priority alanı yok");
  if (!shownFields.byKey.when) fail("Native onay ekranında when alanı yok");
  requireContains("native priority", shownFields.byKey.priority.value, "yuksek");
  if (shownFields.byKey.when.value !== "Yarın 14:00") {
    fail("Native when alanı gerçek değeri göstermiyor: " + shownFields.byKey.when.value);
  }
  await page.click("#lumos-confirm-cancel");
  const rejected = await rejectPromise;
  if (rejected.approved !== false || rejected.reason !== "user_rejected") {
    fail("Native ret sonucu hatalı: " + JSON.stringify(rejected));
  }
  const afterReject = await page.evaluate(NATIVE_CALL_TOOL, {
    name: "lumos-list-tasks",
    args: {},
  });
  if (afterReject.count !== baselineCount) fail("Native: Vazgeç sonrası görev yazılmış!");

  // ── 4) ÖNERİ — Onayla yazar ───────────────────────────────────────────────
  const approvePromise = page
    .evaluate(NATIVE_CALL_TOOL, {
      name: "lumos-propose-task",
      args: { title: TITLE, priority: "yuksek", when: "Yarın 14:00" },
    })
    .catch((e) => ({ __err: String(e && e.message) }));
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-approve");
  const approved = await approvePromise;
  if (!approved.ok || approved.approved !== true || approved.task.title !== TITLE) {
    fail("Native onaylı oluşturma başarısız: " + JSON.stringify(approved));
  }

  // ── 5) TAMAMLAMA — aynı kapı ──────────────────────────────────────────────
  const completePromise = page
    .evaluate(NATIVE_CALL_TOOL, { name: "lumos-complete-task", args: { ref: TITLE } })
    .catch((e) => ({ __err: String(e && e.message) }));
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  const completeShown = await page.evaluate(READ_CONFIRM_FIELDS);
  if (!completeShown.byKey.status_change) fail("Native tamamlama ekranında durum değişikliği yok");
  requireContains("native durum değişikliği", completeShown.byKey.status_change.value, "→");
  await page.click("#lumos-confirm-approve");
  const completed = await completePromise;
  if (!completed.ok || completed.task.status !== "tamamlandi") {
    fail("Native tamamlama başarısız: " + JSON.stringify(completed));
  }

  // ── 6) MUTASYON ONAYI OKUMA İZNİ DEĞİLDİR ─────────────────────────────────
  // Ajan bir başlığı TAHMİN edip yalnızca "tamamla"/"oluştur" onayı alarak
  // okuma kapısını atlayamamalı. İzin, panelin kendi düğmesiyle geri alınır;
  // ardından hiçbir yol (already_completed, onaylı tamamlama, onaylı oluşturma,
  // hata yolları) görev içeriği taşımamalı.
  await page.click("#gorevler-webmcp-consent-revoke");
  if ((await page.getAttribute("#gorevler-webmcp-consent", "data-granted")) !== "false") {
    fail("Native: okuma izni geri alınamadı");
  }

  /** Zarfta ne `task` ne de herhangi bir görev alanı/değeri bulunmalı. */
  const LEAK_KEYS = ["task", "title", "priority", "when", "id", "status", "tasks", "count"];
  function assertNoTaskData(label, payload, needles) {
    for (const k of LEAK_KEYS) {
      if (k in payload) {
        fail(label + ": izin yokken zarfta '" + k + "' var → " + JSON.stringify(payload));
      }
    }
    const serialized = JSON.stringify(payload);
    for (const n of needles) {
      if (n && serialized.indexOf(n) !== -1) {
        fail(label + ": izin yokken görev verisi sızdı (" + n + ") → " + serialized);
      }
    }
  }

  /** Yazma gerçekten oldu mu? Ajan yüzeyinden değil, panelin kendi listesinden. */
  const panelHasTitle = (title) =>
    page.evaluate((t) => {
      try {
        const raw = localStorage.getItem("lumos_panel_gorevler_list_v1");
        return raw ? JSON.parse(raw).some((r) => r && r.title === t) : false;
      } catch {
        return false;
      }
    }, title);

  // 6a) izin YOK + görev ZATEN TAMAMLANMIŞ → onay ekranı açılmaz, veri dönmez.
  const alreadyNoConsent = await page.evaluate(NATIVE_CALL_TOOL, {
    name: "lumos-complete-task",
    args: { ref: TITLE },
  });
  if (alreadyNoConsent.reason !== "already_completed") {
    fail("Native: already_completed beklenirken " + JSON.stringify(alreadyNoConsent));
  }
  assertNoTaskData("native already_completed (izinsiz)", alreadyNoConsent, [
    TITLE,
    "yuksek",
    "Yarın 14:00",
  ]);

  // 6b) izin YOK + görev BEKLİYOR + kullanıcı yazmayı ONAYLADI → yine veri yok.
  const PENDING_TITLE = "Native bekleyen " + Date.now();
  const makePendingPromise = page
    .evaluate(NATIVE_CALL_TOOL, {
      name: "lumos-propose-task",
      args: { title: PENDING_TITLE, priority: "dusuk", when: "Cuma 09:00" },
    })
    .catch((e) => ({ __err: String(e && e.message) }));
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-approve");
  const madePending = await makePendingPromise;
  if (madePending.ok !== true || madePending.approved !== true) {
    fail("Native izinsiz oluşturma yazmadı: " + JSON.stringify(madePending));
  }
  assertNoTaskData("native propose onaylı (izinsiz)", madePending, [
    PENDING_TITLE,
    "dusuk",
    "Cuma 09:00",
  ]);
  if (!(await panelHasTitle(PENDING_TITLE))) {
    fail("Native: onaylanan görev panelin listesine yazılmamış — ok:true yanıltıcı");
  }

  const completeNoConsentPromise = page
    .evaluate(NATIVE_CALL_TOOL, { name: "lumos-complete-task", args: { ref: PENDING_TITLE } })
    .catch((e) => ({ __err: String(e && e.message) }));
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-approve");
  const completedNoConsent = await completeNoConsentPromise;
  if (completedNoConsent.ok !== true || completedNoConsent.approved !== true) {
    fail("Native izinsiz tamamlama başarısız: " + JSON.stringify(completedNoConsent));
  }
  assertNoTaskData("native complete onaylı (izinsiz)", completedNoConsent, [
    PENDING_TITLE,
    "dusuk",
    "Cuma 09:00",
    "tamamlandi",
  ]);

  // 6c) izin YOK + hata yolları da veri taşımaz.
  const notFound = await page.evaluate(NATIVE_CALL_TOOL, {
    name: "lumos-complete-task",
    args: { ref: "native-olmayan-" + Date.now() },
  });
  if (notFound.reason !== "task_not_found") {
    fail("Native task_not_found beklenirken: " + JSON.stringify(notFound));
  }
  assertNoTaskData("native task_not_found", notFound, [TITLE, PENDING_TITLE]);
  const refRequired = await page.evaluate(NATIVE_CALL_TOOL, {
    name: "lumos-complete-task",
    args: {},
  });
  if (refRequired.reason !== "ref_required") {
    fail("Native ref_required beklenirken: " + JSON.stringify(refRequired));
  }
  assertNoTaskData("native ref_required", refRequired, [TITLE, PENDING_TITLE]);

  // 6d) REGRESYON: izin geri verilince aynı yol içeriği yeniden döndürür.
  const regrantPromise = page
    .evaluate(NATIVE_CALL_TOOL, { name: "lumos-list-tasks", args: {} })
    .catch((e) => ({ __err: String(e && e.message) }));
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-approve");
  const regranted = await regrantPromise;
  if (!regranted.ok) fail("Native: izin yeniden verilemedi: " + JSON.stringify(regranted));
  const withConsent = await page.evaluate(NATIVE_CALL_TOOL, {
    name: "lumos-complete-task",
    args: { ref: TITLE },
  });
  if (!withConsent.task || withConsent.task.title !== TITLE) {
    fail("Native: izin varken içerik dönmedi (regresyon): " + JSON.stringify(withConsent));
  }
  if (withConsent.task.priority !== "yuksek" || withConsent.task.when !== "Yarın 14:00") {
    fail("Native: izinli zarf eksik alan döndürdü: " + JSON.stringify(withConsent));
  }

  console.log("WEBMCP_NATIVE_RESULT: PASS");
  console.log("chrome binary:  " + CHROME_BIN);
  console.log("chrome flags:   --enable-features=" + WEBMCP_FEATURES
    + " --enable-blink-features=" + WEBMCP_BLINK_FEATURES);
  console.log("user-data-dir:  " + userDataDir + "  (kullanıcı profiline dokunulmadı)");
  console.log("page injection: NONE (addInitScript kullanılmadı)");
  console.log("--- native modelContext kanıtı ---");
  console.log(JSON.stringify(
    {
      chromeUserAgent: proof.chromeUserAgent,
      brandString: proof.brandString,
      constructorName: proof.constructorName,
      prototypeMembers: proof.prototypeMembers,
      registerToolSource: proof.registerToolSource,
      executeToolSource: proof.executeToolSource,
      documentPrototypeGetter: proof.documentPrototypeGetter,
      ownPropertyOnDocument: proof.ownPropertyOnDocument,
      globalInterfaces: proof.globalInterfaces,
      modelContextTestingType: proof.modelContextTestingType,
      modelContextTestingInNavigator: proof.modelContextTestingInNavigator,
      pageRegistered: proof.pageStatus && proof.pageStatus.registered,
    },
    null,
    2,
  ));
  console.log("--- uçtan uca akış ---");
  console.log("read without consent : refused (" + refused.reason + "), no task data");
  console.log("read with consent    : " + listed.count + " task(s)");
  console.log("propose declined     : nothing written");
  console.log("propose approved     : " + approved.task.title);
  console.log("complete approved    : " + completed.task.status);
  console.log("--- izin geri alındıktan sonra (mutasyon onayı ≠ okuma izni) ---");
  console.log("already_completed    : " + JSON.stringify(alreadyNoConsent));
  console.log("propose approved     : " + JSON.stringify(madePending) + "  (yazıldı, içerik yok)");
  console.log("complete approved    : " + JSON.stringify(completedNoConsent));
  console.log("task_not_found       : " + JSON.stringify(notFound));
  console.log("ref_required         : " + JSON.stringify(refRequired));
  console.log("izin geri verilince  : task.title=" + withConsent.task.title
    + " priority=" + withConsent.task.priority + " when=" + withConsent.task.when);
  console.log("url: " + PANEL_URL);

  await browser.close();
  browser = null;
} catch (err) {
  if (browser) await browser.close().catch(() => {});
  fail(String(err && err.stack ? err.stack : err));
} finally {
  if (chrome) {
    const exited = new Promise((r) => chrome.once("exit", r));
    try {
      chrome.kill("SIGTERM");
    } catch {
      /* zaten kapandı */
    }
    /* Chrome profil dizinine hâlâ yazıyor olabilir: çıkmasını bekle. */
    await Promise.race([exited, new Promise((r) => setTimeout(r, 5000))]);
  }
  await closeServer(server);
  /* Geçici profil temizliği kanıtı geçersiz kılmaz — başarısızlığı yutuyoruz. */
  try {
    fs.rmSync(userDataDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
  } catch {
    console.warn("not: geçici profil silinemedi, elle silinebilir: " + userDataDir);
  }
}
