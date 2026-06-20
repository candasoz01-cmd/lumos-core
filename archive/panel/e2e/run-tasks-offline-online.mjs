/**
 * Görev API: online → API kapanınca offline-cache → mutasyon yok → API dönünce online.
 */
import { existsSync, readFileSync } from "node:fs";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, extname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import http from "node:http";
import { chromium } from "playwright";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PANEL_DIR = resolve(join(__dirname, ".."));
const REPO_ROOT = resolve(join(PANEL_DIR, ".."));
const PY_SCRIPT = join(REPO_ROOT, "panel/scripts/panel_tasks_server.py");

const PANEL_PORT = String(20600 + (process.pid % 3900));
const TASK_API_PORT = String(30600 + (process.pid % 3900));
const BASE = `http://127.0.0.1:${PANEL_PORT}`;
const TASK_API_ORIGIN = `http://127.0.0.1:${TASK_API_PORT}`;
const READY_MS = 45000;
const ASYNC_MS = 20000;

function parseUrl(u) {
  try {
    return new URL(u);
  } catch (_) {
    return null;
  }
}

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
          if (Date.now() > deadline) return reject(new Error("wait " + url));
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

async function run() {
  if (!existsSync(PY_SCRIPT)) throw new Error("panel_tasks_server.py yok");

  var tmpBase = mkdtempSync(join(tmpdir(), "lumos-offline-online-"));
  var pyProc = startPythonTasksServer(tmpBase, TASK_API_PORT);
  var panelServer = await startPanelStaticServer(PANEL_DIR, PANEL_PORT);
  try {
    await waitForServer(TASK_API_ORIGIN + "/tasks", 20000);
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

  var postWhileOffline = 0;

  var browser = await chromium.launch({ headless: true });
  var page = await browser.newPage();

  page.on("request", function (req) {
    var u = parseUrl(req.url());
    if (!u || u.origin !== TASK_API_ORIGIN) return;
    var path = (u.pathname || "").replace(/\/$/, "") || "/";
    if (path === "/tasks" && req.method() === "POST") postWhileOffline++;
  });

  await page.addInitScript(function (args) {
    window.LUMOS_PANEL_TASKS_API_BASE = args.base;
  }, { base: TASK_API_ORIGIN });

  try {
    await page.goto(BASE + "/index.html#tasks", { waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector(".task-filters", { state: "attached", timeout: READY_MS });
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
    await page.waitForSelector(".task-filters", { state: "attached", timeout: READY_MS });

    await page.waitForFunction(
      function () {
        return document.documentElement.getAttribute("data-lumos-task-source") === "online";
      },
      { timeout: ASYNC_MS }
    );

    try {
      pyProc.kill("SIGTERM");
    } catch (_) {}
    pyProc = null;
    await page.waitForTimeout(400);

    await page.evaluate(function () {
      window.location.hash = "#dashboard";
    });
    await page.waitForTimeout(200);
    await page.evaluate(function () {
      window.location.hash = "#tasks";
    });

    await page.waitForFunction(
      function () {
        return document.documentElement.getAttribute("data-lumos-task-source") === "offline-cache";
      },
      { timeout: ASYNC_MS }
    );

    await page.goto(BASE + "/index.html#chat", { waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: READY_MS });

    var offlineMark = "offline-try-" + Date.now();
    await page.fill("#lumos-chat-input", "görev oluştur " + offlineMark);
    await page.click("#lumos-chat-send");
    await page.waitForTimeout(600);

    var lastAssistant = await page.evaluate(function () {
      var nodes = document.querySelectorAll(".lumos-chat-msg--assistant");
      var last = nodes[nodes.length - 1];
      return last ? last.textContent || "" : "";
    });
    if (lastAssistant.indexOf("Görev oluşturuldu") !== -1) {
      throw new Error("offline iken sahte başarı metni");
    }
    if (lastAssistant.indexOf("gönderilmedi") === -1 && lastAssistant.indexOf("salt okunur") === -1) {
      throw new Error("offline cevap beklenen net red yok: " + lastAssistant.slice(0, 200));
    }
    if (postWhileOffline > 0) {
      throw new Error("offline iken POST /tasks gitmemeli, sayı=" + postWhileOffline);
    }

    pyProc = startPythonTasksServer(tmpBase, TASK_API_PORT);
    await waitForServer(TASK_API_ORIGIN + "/tasks", 20000);

    await page.evaluate(function () {
      window.location.hash = "#dashboard";
    });
    await page.waitForTimeout(200);
    await page.evaluate(function () {
      window.location.hash = "#chat";
    });

    await page.waitForFunction(
      function () {
        return document.documentElement.getAttribute("data-lumos-task-source") === "online";
      },
      { timeout: ASYNC_MS }
    );
  } finally {
    await browser.close();
    if (pyProc) {
      try {
        pyProc.kill("SIGTERM");
      } catch (_) {}
    }
    await new Promise(function (r) {
      panelServer.close(function () {
        r();
      });
    });
  }
}

run()
  .then(function () {
    console.log("RESULT: PASS");
    process.exit(0);
  })
  .catch(function (err) {
    console.error("RESULT: FAIL");
    console.error(String(err && err.message ? err.message : err));
    process.exit(1);
  });
