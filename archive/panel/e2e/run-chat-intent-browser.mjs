/**
 * Tarayıcı: chat intent/dispatch (görevler, durum, kilit aç komutu, görev oluştur, fallback).
 * panel_tasks_server + statik panel; Playwright headless.
 */
import { existsSync, readFileSync } from "node:fs";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, extname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import http from "node:http";
import { chromium } from "playwright";
import { lumosE2EPatchPolicyAllowTasks } from "./package-flow-shared.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PANEL_DIR = resolve(join(__dirname, ".."));
const REPO_ROOT = resolve(join(PANEL_DIR, ".."));
const PY_SCRIPT = join(REPO_ROOT, "panel/scripts/panel_tasks_server.py");

const PANEL_PORT = process.env.LUMOS_PANEL_E2E_PORT
  ? String(process.env.LUMOS_PANEL_E2E_PORT).trim()
  : String(20600 + (process.pid % 4000));
const TASK_API_PORT = process.env.LUMOS_PANEL_TASKS_E2E_PORT
  ? String(process.env.LUMOS_PANEL_TASKS_E2E_PORT).trim()
  : String(30600 + (process.pid % 4000));

const BASE = `http://127.0.0.1:${PANEL_PORT}`;
const TASK_API_BASE = `http://127.0.0.1:${TASK_API_PORT}`;
const READY_MS = 45000;
const CHAT_MS = 25000;

function mimeType(filePath) {
  var ext = extname(filePath).toLowerCase();
  if (ext === ".html") return "text/html; charset=utf-8";
  if (ext === ".js") return "text/javascript; charset=utf-8";
  if (ext === ".css") return "text/css; charset=utf-8";
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
          if (Date.now() > deadline) return reject(new Error("waitForServer " + url + " " + res.statusCode));
          setTimeout(tryOnce, 80);
        })
        .on("error", function () {
          if (Date.now() > deadline) return reject(new Error("timeout " + url));
          setTimeout(tryOnce, 80);
        });
    }
    tryOnce();
  });
}

function startPythonTasksServer(tmpBaseDir, portStr) {
  return spawn("python3", [PY_SCRIPT], {
    env: Object.assign({}, process.env, {
      LUMOS_BASE_DIR: tmpBaseDir,
      LUMOS_PANEL_TASKS_PORT: String(portStr),
      LUMOS_PANEL_TASKS_HOST: "127.0.0.1",
    }),
    stdio: "pipe",
  });
}

/** Hash değişen komutlar: sohbet DOM’u kaybolabilir; yalnızca location.hash doğrulanır. */
async function sendChatExpectHash(page, text, expectedHashLower) {
  await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: READY_MS });
  await page.fill("#lumos-chat-input", text);
  await page.click("#lumos-chat-send");
  await page.waitForFunction(
    function (want) {
      return ((window.location.hash || "").split("?")[0].toLowerCase() === want);
    },
    expectedHashLower,
    { timeout: CHAT_MS }
  );
}

/** #chat üzerinde kalınan komutlar: son asistan balonunu bekle. */
async function sendChatExpectAssistant(page, text) {
  await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: READY_MS });
  var asstBefore = await page.locator(".lumos-chat-msg--assistant").count();
  await page.fill("#lumos-chat-input", text);
  await page.click("#lumos-chat-send");
  await page.waitForFunction(
    function (prev) {
      return document.querySelectorAll(".lumos-chat-msg--assistant").length > prev;
    },
    asstBefore,
    { timeout: CHAT_MS }
  );
}

async function lastAssistantBubbleText(page) {
  return page.evaluate(function () {
    var nodes = document.querySelectorAll(".lumos-chat-msg--assistant .lumos-chat-bubble");
    var last = nodes[nodes.length - 1];
    return last ? (last.textContent || "").trim() : "";
  });
}

async function run() {
  if (!existsSync(PY_SCRIPT)) {
    console.error("CHAT_INTENT_BROWSER: FAIL — panel_tasks_server.py yok");
    process.exit(1);
  }
  var tmpBase = mkdtempSync(join(tmpdir(), "lumos-chat-intent-"));
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

  var results = [];

  try {
    await page.goto(BASE + "/index.html#chat", { waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: READY_MS });
    await page.evaluate(function (keys) {
      try {
        localStorage.removeItem(keys.tasks);
        localStorage.removeItem(keys.chat);
      } catch (_) {}
    }, { tasks: "lumos_dot_lumos_tasks_json_v1", chat: "lumos_panel_chat_messages_v1" });
    await page.reload({ waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: READY_MS });
    await lumosE2EPatchPolicyAllowTasks(page);

    // 1) görevler → #tasks
    await sendChatExpectHash(page, "görevler", "#tasks");
    results.push({ step: "1_görevler", ok: true, hash: await page.evaluate(() => window.location.hash) });

    // 2) durum → #system
    await page.goto(BASE + "/index.html#chat", { waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: READY_MS });
    await sendChatExpectHash(page, "durum", "#system");
    results.push({
      step: "2_durum",
      ok: true,
      hash: await page.evaluate(() => window.location.hash),
    });

    // 3) kilit aç → unlock modal → host mock → Kilit açıldı
    await page.goto(BASE + "/index.html#chat", { waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: READY_MS });
    var users3 = await page.locator(".lumos-chat-msg--user").count();
    var asst3 = await page.locator(".lumos-chat-msg--assistant").count();
    await page.fill("#lumos-chat-input", "kilit aç");
    await page.click("#lumos-chat-send");
    await page.waitForSelector("#unlock-pass", { state: "visible", timeout: CHAT_MS });
    await page.fill("#unlock-pass", "1770");
    await page.click("#lumos-unlock-submit");
    await page.waitForFunction(
      function () {
        var inp = document.getElementById("lumos-chat-input");
        return inp && String(inp.value || "").trim() === "";
      },
      { timeout: CHAT_MS }
    );
    await page.waitForFunction(
      function () {
        return ((window.location.hash || "").split("?")[0].toLowerCase() === "#chat");
      },
      { timeout: CHAT_MS }
    );
    await page.waitForFunction(
      function () {
        var nodes = document.querySelectorAll(".lumos-chat-msg--assistant .lumos-chat-bubble");
        var last = nodes[nodes.length - 1];
        return last && (last.textContent || "").indexOf("Kilit açıldı") !== -1;
      },
      { timeout: CHAT_MS }
    );
    var users3b = await page.locator(".lumos-chat-msg--user").count();
    var asst3b = await page.locator(".lumos-chat-msg--assistant").count();
    var t3 = await lastAssistantBubbleText(page);
    results.push({
      step: "3_kilit_aç",
      ok:
        users3b === users3 + 1 &&
        asst3b === asst3 + 1 &&
        t3.indexOf("Kilit açıldı") !== -1 &&
        t3.indexOf("onay") === -1,
      hash: await page.evaluate(function () {
        return window.location.hash || "";
      }),
      snippet: t3.slice(0, 160),
    });

    // 4) görev oluştur test (ekran #chat kalır; asistan balonu görünür)
    await page.goto(BASE + "/index.html#chat", { waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: READY_MS });
    await sendChatExpectAssistant(page, "görev oluştur test");
    var t4 = await lastAssistantBubbleText(page);
    results.push({
      step: "4_görev_oluştur_test",
      ok: t4.indexOf("oluşturuldu") !== -1 || t4.indexOf("Görev") !== -1,
      snippet: t4.slice(0, 200),
    });

    // 5) fallback
    await page.goto(BASE + "/index.html#chat", { waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: READY_MS });
    await sendChatExpectAssistant(page, "quantum zebra unrelated random");
    var t5 = await lastAssistantBubbleText(page);
    results.push({
      step: "5_fallback",
      ok: t5.indexOf("yalnızca sohbet") !== -1,
      snippet: t5.slice(0, 200),
    });

    var allOk = results.every(function (r) {
      return r.ok === true;
    });
    console.log("CHAT_INTENT_BROWSER_RESULT: " + (allOk ? "PASS" : "FAIL"));
    console.log(JSON.stringify(results, null, 2));
    if (!allOk) process.exit(1);
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

run().catch(function (err) {
  console.error("CHAT_INTENT_BROWSER_RESULT: FAIL");
  console.error(String(err && err.message ? err.message : err));
  process.exit(1);
});
