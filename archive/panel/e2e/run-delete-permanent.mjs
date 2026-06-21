/**
 * Trash kalıcı sil: onay modalı yok → istek yok; onay + confirm:true → POST başarılı.
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, extname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import http from "node:http";
import { chromium } from "playwright";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PANEL_DIR = resolve(join(__dirname, ".."));
const PANEL_PORT = String(20800 + (process.pid % 3500));
const API_PORT = String(30800 + (process.pid % 3500));
const BASE = `http://127.0.0.1:${PANEL_PORT}`;
const API_BASE = `http://127.0.0.1:${API_PORT}`;
const READY_MS = 30000;
const TASK_ID = "tsk_perm_e2e_" + Date.now();

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

function startMockTrashApiServer(portStr) {
  var posts = [];
  function cors(res) {
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type, Accept");
  }
  var server = http.createServer(function (req, res) {
    cors(res);
    if (req.method === "OPTIONS") {
      res.writeHead(204);
      res.end();
      return;
    }
    var path = (req.url || "").split("?")[0];
    if (path === "/tasks/delete-permanent" && req.method === "POST") {
      var chunks = [];
      req.on("data", function (c) {
        chunks.push(c);
      });
      req.on("end", function () {
        var raw = Buffer.concat(chunks).toString("utf8");
        var body = {};
        try {
          body = raw ? JSON.parse(raw) : {};
        } catch (_) {
          body = {};
        }
        posts.push(body);
        if (body.confirm !== true) {
          res.writeHead(409, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ ok: false, error: "confirm_required" }));
          return;
        }
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: true }));
      });
      return;
    }
    if (path === "/lumos-read-state" && req.method === "GET") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          trash: {
            trash_items: [
              {
                id: TASK_ID,
                name: "e2e-perm-" + TASK_ID,
                payload: { id: TASK_ID, title: "e2e-perm-" + TASK_ID },
                moved_at: new Date().toISOString(),
                scope: "task",
              },
            ],
            trash_item_count: 1,
            trash_dir_exists: true,
          },
          guidance: { mode: "online", lock: "UNLOCKED", consent: true },
        })
      );
      return;
    }
    res.writeHead(404);
    res.end();
  });
  return new Promise(function (resolveListen, rejectListen) {
    server.on("error", rejectListen);
    server.listen(Number(portStr), "127.0.0.1", function () {
      resolveListen({ server: server, getPosts: function () { return posts.slice(); } });
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

async function run() {
  if (!existsSync(join(PANEL_DIR, "index.html"))) throw new Error("index.html yok");

  var panelServer = await startPanelStaticServer(PANEL_DIR, PANEL_PORT);
  var api = await startMockTrashApiServer(API_PORT);
  await waitForServer(BASE + "/index.html", 15000);

  var browser = await chromium.launch({ headless: true });
  var page = await browser.newPage();
  await page.addInitScript(function (apiOrigin, taskId) {
    window.LUMOS_PANEL_TASKS_API_BASE = false;
    window.LUMOS_PANEL_TRASH_ACTION_API_BASE = apiOrigin;
    window.LUMOS_PANEL_LIVE_STATE_URL = apiOrigin + "/lumos-read-state";
  }, API_BASE, TASK_ID);

  try {
    await page.goto(BASE + "/index.html#trash", { waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector('[data-trash-task-action="delete-permanent"]:not([disabled])', {
      state: "attached",
      timeout: READY_MS,
    });

    /* İptal: modal reddedilince POST olmamalı */
    page.once("dialog", function (d) {
      return d.dismiss();
    });
    await page.locator('[data-trash-task-action="delete-permanent"]').click();
    await page.waitForTimeout(400);
    var postsAfterDismiss = api.getPosts();
    if (postsAfterDismiss.length !== 0) {
      throw new Error("iptal sonrası POST beklenmiyordu, sayı=" + postsAfterDismiss.length);
    }

    /* Onay: confirm:true ile POST */
    page.once("dialog", function (d) {
      return d.accept();
    });
    await page.locator('[data-trash-task-action="delete-permanent"]').click();
    await page.waitForFunction(
      function () {
        var el = document.querySelector(".trash-deletion-hub");
        return el && el.innerText.indexOf("kalıcı silindi") !== -1;
      },
      { timeout: 10000 }
    );

    var postsAfterAccept = api.getPosts();
    if (postsAfterAccept.length !== 1) {
      throw new Error("onay sonrası tek POST bekleniyordu, sayı=" + postsAfterAccept.length);
    }
    if (postsAfterAccept[0].id !== TASK_ID || postsAfterAccept[0].confirm !== true) {
      throw new Error("POST gövdesi hatalı: " + JSON.stringify(postsAfterAccept[0]));
    }
  } finally {
    await browser.close();
    await new Promise(function (r) {
      api.server.close(function () {
        panelServer.close(function () {
          r();
        });
      });
    });
  }
}

run()
  .then(function () {
    console.log("DELETE_PERMANENT_E2E: PASS");
    process.exit(0);
  })
  .catch(function (err) {
    console.error("DELETE_PERMANENT_E2E: FAIL");
    console.error(String(err && err.message ? err.message : err));
    process.exit(1);
  });
