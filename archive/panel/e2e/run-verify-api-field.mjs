/**
 * Sahada doğrulama: varsayılan API modunda ağda GET /tasks + POST mutasyonlar;
 * PUT/GET tasks.json olmamalı; en az bir GET /tasks 200.
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

const PANEL_PORT = String(20500 + (process.pid % 4000));
const TASK_API_PORT = String(30500 + (process.pid % 4000));
const BASE = `http://127.0.0.1:${PANEL_PORT}`;
const TASK_API_ORIGIN = `http://127.0.0.1:${TASK_API_PORT}`;
const READY_MS = 45000;
const ASYNC_CHAT_MS = 35000;
const MARK = "field-api-" + Date.now();

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

  var net = {
    getTasks: 0,
    getTasksOk: 0,
    postTasks: 0,
    postComplete: 0,
    postDelete: 0,
    getTasksJson: 0,
    putTasksJson: 0,
  };

  var tmpBase = mkdtempSync(join(tmpdir(), "lumos-field-api-"));
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

  var browser = await chromium.launch({ headless: true });
  var page = await browser.newPage();

  page.on("request", function (req) {
    var u = parseUrl(req.url());
    if (!u || u.origin !== TASK_API_ORIGIN) return;
    var path = (u.pathname || "").replace(/\/$/, "") || "/";
    var m = req.method();
    if (path === "/tasks.json" && m === "GET") net.getTasksJson++;
    if (path === "/tasks.json" && m === "PUT") net.putTasksJson++;
    if (path === "/tasks" && m === "GET") net.getTasks++;
    if (path === "/tasks" && m === "POST") net.postTasks++;
    if (path === "/tasks/complete" && m === "POST") net.postComplete++;
    if (path === "/tasks/delete" && m === "POST") net.postDelete++;
  });

  page.on("response", function (res) {
    var u = parseUrl(res.url());
    if (!u || u.origin !== TASK_API_ORIGIN) return;
    var path = (u.pathname || "").replace(/\/$/, "") || "/";
    try {
      if (path === "/tasks" && res.request().method() === "GET" && res.status() === 200) {
        net.getTasksOk++;
      }
    } catch (_) {}
  });

  await page.addInitScript(function (args) {
    window.LUMOS_PANEL_TASKS_API_BASE = args.base;
  }, { base: TASK_API_ORIGIN });

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

    async function sendGorev(line) {
      await page.fill("#lumos-chat-input", line);
      await page.click("#lumos-chat-send");
      await page.waitForTimeout(400);
    }

    await sendGorev("görev oluştur " + MARK);
    await page.waitForFunction(
      function () {
        return document.querySelectorAll(".lumos-chat-msg").length >= 2;
      },
      { timeout: ASYNC_CHAT_MS }
    );

    await sendGorev("görev tamamla " + MARK);
    await page.waitForFunction(
      function () {
        return document.querySelectorAll(".lumos-chat-msg").length >= 4;
      },
      { timeout: ASYNC_CHAT_MS }
    );

    await sendGorev("görev sil " + MARK);
    await page.waitForFunction(
      function () {
        return document.querySelectorAll(".lumos-chat-msg").length >= 6;
      },
      { timeout: ASYNC_CHAT_MS }
    );

    var srcAttr = await page.evaluate(function () {
      return document.documentElement.getAttribute("data-lumos-task-source");
    });
    if (srcAttr !== "online") {
      throw new Error("data-lumos-task-source beklenen online, alınan: " + String(srcAttr));
    }
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

  var reasons = [];
  if (net.putTasksJson > 0 || net.getTasksJson > 0) {
    reasons.push("tasks.json HTTP kullanıldı (local/legacy yolu): GET=" + net.getTasksJson + " PUT=" + net.putTasksJson);
  }
  if (net.getTasks < 1) reasons.push("GET /tasks yok");
  if (net.getTasksOk < 1) reasons.push("GET /tasks 200 yok (API hydrate başarısız / yalnız fallback)");
  if (net.postTasks < 1) reasons.push("POST /tasks (create) yok");
  if (net.postComplete < 1) reasons.push("POST /tasks/complete yok");
  if (net.postDelete < 1) reasons.push("POST /tasks/delete yok");

  if (reasons.length) {
    throw new Error(reasons.join(" | "));
  }
  return net;
}

run()
  .then(function (net) {
    console.log(
      "FIELD_API_VERIFY: PASS | GET /tasks=" +
        net.getTasks +
        " (200=" +
        net.getTasksOk +
        ") POST /tasks=" +
        net.postTasks +
        " /complete=" +
        net.postComplete +
        " /delete=" +
        net.postDelete +
        " | tasks.json GET/PUT=" +
        net.getTasksJson +
        "/" +
        net.putTasksJson
    );
    process.exit(0);
  })
  .catch(function (err) {
    console.error("FIELD_API_VERIFY: FAIL");
    console.error(String(err && err.message ? err.message : err));
    process.exit(1);
  });
