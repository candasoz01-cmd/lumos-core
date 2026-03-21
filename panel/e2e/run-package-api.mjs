/**
 * Paket kapısı (REST API): panel_tasks_server + GET /tasks + POST mutasyonlar.
 */
import { existsSync, readFileSync } from "node:fs";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, extname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import http from "node:http";
import { chromium } from "playwright";
import { createPackageFlowAssertions, lumosE2EPatchPolicyAllowTasks } from "./package-flow-shared.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PANEL_DIR = resolve(join(__dirname, ".."));
const REPO_ROOT = resolve(join(PANEL_DIR, ".."));
const PY_SCRIPT = join(REPO_ROOT, "panel/scripts/panel_tasks_server.py");

const PANEL_PORT = process.env.LUMOS_PANEL_E2E_PORT
  ? String(process.env.LUMOS_PANEL_E2E_PORT).trim()
  : String(20400 + (process.pid % 5000));
const TASK_API_PORT = process.env.LUMOS_PANEL_TASKS_E2E_PORT
  ? String(process.env.LUMOS_PANEL_TASKS_E2E_PORT).trim()
  : String(30400 + (process.pid % 5000));

const BASE = `http://127.0.0.1:${PANEL_PORT}`;
const TASK_API_BASE = `http://127.0.0.1:${TASK_API_PORT}`;
const READY_MS = 45000;
const ASYNC_CHAT_MS = 35000;
const MARK = "pkg-api-" + Date.now();

const flow = createPackageFlowAssertions({ MARK, BASE, READY_MS });
const fail = flow.fail;

if (!existsSync(join(PANEL_DIR, "index.html"))) {
  console.error("PACKAGE_E2E_API_RESULT: FAIL");
  console.error("BROKEN_PART: panel kökünde index.html yok:", PANEL_DIR);
  process.exit(1);
}
if (!existsSync(PY_SCRIPT)) {
  console.error("PACKAGE_E2E_API_RESULT: FAIL");
  console.error("BROKEN_PART: panel_tasks_server.py yok:", PY_SCRIPT);
  process.exit(1);
}

function mimeType(filePath) {
  var ext = extname(filePath).toLowerCase();
  if (ext === ".html") return "text/html; charset=utf-8";
  if (ext === ".js") return "text/javascript; charset=utf-8";
  if (ext === ".css") return "text/css; charset=utf-8";
  if (ext === ".json") return "application/json; charset=utf-8";
  return "application/octet-stream";
}

function startPanelStaticServer(rootDir, portStr) {
  var root = resolve(rootDir);
  var server = http.createServer(function (req, res) {
    var rawPath = (req.url || "/").split("?")[0];
    var dec = decodeURIComponent(rawPath);
    var relFile = dec === "/" || dec === "" ? "index.html" : dec.replace(/^\//, "");
    var absPath = resolve(root, relFile);
    var relToRoot = relative(root, absPath);
    if (relToRoot.startsWith("..") || relToRoot === "..") {
      res.writeHead(403);
      res.end();
      return;
    }
    if (!existsSync(absPath)) {
      res.writeHead(404);
      res.end();
      return;
    }
    try {
      var buf = readFileSync(absPath);
      res.writeHead(200, { "Content-Type": mimeType(absPath) });
      res.end(buf);
    } catch (_) {
      res.writeHead(500);
      res.end();
    }
  });
  return new Promise(function (resolveListen, rejectListen) {
    server.on("error", rejectListen);
    server.listen(Number(portStr), "127.0.0.1", function () {
      resolveListen(server);
    });
  });
}

function waitForServer(url, ms) {
  var deadline = Date.now() + ms;
  return new Promise(function (resolve, reject) {
    function tryOnce() {
      http
        .get(url, function (res) {
          res.resume();
          if (res.statusCode === 200) return resolve();
          if (Date.now() > deadline) return reject(new Error("waitForServer status " + res.statusCode + " " + url));
          setTimeout(tryOnce, 80);
        })
        .on("error", function () {
          if (Date.now() > deadline) return reject(new Error("server timeout " + url));
          setTimeout(tryOnce, 80);
        });
    }
    tryOnce();
  });
}

function startPythonTasksServer(tmpBaseDir, portStr) {
  var proc = spawn("python3", [PY_SCRIPT], {
    env: Object.assign({}, process.env, {
      LUMOS_BASE_DIR: tmpBaseDir,
      LUMOS_PANEL_TASKS_PORT: String(portStr),
      LUMOS_PANEL_TASKS_HOST: "127.0.0.1",
    }),
    stdio: "pipe",
  });
  proc.stderr.on("data", function () {
    /* sunucu logları gürültü olmasın */
  });
  return proc;
}

async function run() {
  var tmpBase = mkdtempSync(join(tmpdir(), "lumos-pkg-api-"));
  var pyProc = startPythonTasksServer(tmpBase, TASK_API_PORT);

  var panelServer = await startPanelStaticServer(PANEL_DIR, PANEL_PORT);
  try {
    await waitForServer(TASK_API_BASE + "/tasks", 20000);
    await waitForServer(BASE + "/index.html", 15000);
  } catch (e) {
    try {
      pyProc.kill("SIGTERM");
    } catch (_) {}
    await new Promise(function (r) {
      panelServer.close(function () {
        r();
      });
    });
    throw e;
  }

  var browser = await chromium.launch({ headless: true });
  var page = await browser.newPage();
  await page.addInitScript(function (args) {
    window.LUMOS_PANEL_TASKS_API_BASE = args.base;
  }, { base: TASK_API_BASE });

  try {
    await page.goto(BASE + "/index.html#chat", { waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: READY_MS });
    await page.evaluate(
      function (keys) {
        try {
          localStorage.removeItem(keys.tasks);
          localStorage.removeItem(keys.chat);
        } catch (_) {}
      },
      { tasks: "lumos_dot_lumos_tasks_json_v1", chat: "lumos_panel_chat_messages_v1" }
    );
    await page.reload({ waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: READY_MS });
    await lumosE2EPatchPolicyAllowTasks(page);

    await page.fill("#lumos-chat-input", "görev oluştur " + MARK);
    await page.click("#lumos-chat-send");
    await page.waitForFunction(
      function () {
        return document.querySelectorAll(".lumos-chat-msg").length >= 2;
      },
      { timeout: ASYNC_CHAT_MS }
    );

    await page.goto(BASE + "/index.html#tasks", { waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector(".task-filters", { state: "attached", timeout: READY_MS });
    var tasksAfterCreate = await page.locator("#main-content").innerText();
    if (tasksAfterCreate.indexOf(MARK) === -1) fail("api/after-create/tasks-list", "başlık yok");

    await page.goto(BASE + "/index.html#chat", { waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: READY_MS });
    await page.fill("#lumos-chat-input", "görev tamamla " + MARK);
    await page.click("#lumos-chat-send");
    await page.waitForFunction(
      function () {
        return document.querySelectorAll(".lumos-chat-msg").length >= 4;
      },
      { timeout: ASYNC_CHAT_MS }
    );

    await page.goto(BASE + "/index.html#tasks", { waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector(".task-filters", { state: "attached", timeout: READY_MS });
    await page.locator('[data-task-filter="completed"]').click();
    await page.waitForTimeout(350);
    var completedView = await page.locator("#main-content").innerText();
    if (completedView.indexOf(MARK) === -1) fail("api/after-complete/completed-filter", "tamamlandı filtresinde yok");

    await page.goto(BASE + "/index.html#chat", { waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: READY_MS });
    await page.fill("#lumos-chat-input", "görev sil " + MARK);
    await page.click("#lumos-chat-send");
    await page.waitForFunction(
      function () {
        return document.querySelectorAll(".lumos-chat-msg").length >= 6;
      },
      { timeout: ASYNC_CHAT_MS }
    );

    var silOk = await page.evaluate(function () {
      var nodes = document.querySelectorAll(".lumos-chat-msg--assistant .lumos-chat-bubble");
      if (!nodes.length) return { ok: false, reason: "assistant balonu yok" };
      var last = nodes[nodes.length - 1];
      var txt = last ? last.textContent || "" : "";
      if (txt.indexOf("bulunamadı") !== -1) return { ok: false, reason: "sil başarısız: " + txt.slice(0, 120) };
      if (txt.indexOf("silindi") === -1) return { ok: false, reason: "silindi yok: " + txt.slice(0, 120) };
      return { ok: true };
    });
    if (!silOk.ok) fail("api/after-delete/chat-reply", silOk.reason || "sil");

    await flow.assertDeletedHiddenAllTaskFilters(page, "api/after-delete/tasks-filters");
    await flow.assertTrashVisible(page, "api/after-delete/trash");
    await flow.assertLogsFullChain(page, "api/after-delete/logs");
    await flow.assertDashboardChain(page, "api/after-delete/dashboard");

    await page.goto(BASE + "/index.html#chat", { waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: READY_MS });
    await page.reload({ waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: READY_MS });

    await flow.assertPostReload(page, "api/post-reload");
  } finally {
    await browser.close();
    try {
      pyProc.kill("SIGTERM");
    } catch (_) {}
    await new Promise(function (r) {
      panelServer.close(function () {
        r();
      });
    });
  }
}

run()
  .then(function () {
    console.log("PACKAGE_E2E_API_RESULT: PASS");
    process.exit(0);
  })
  .catch(function (err) {
    console.error("PACKAGE_E2E_API_RESULT: FAIL");
    console.error(String(err && err.message ? err.message : err));
    process.exit(1);
  });
