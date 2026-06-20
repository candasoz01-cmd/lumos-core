/**
 * Politika: çevrimdışı → create red; online+yamalı → create OK; kilit → sil red + policy_blocked kayıt satırı.
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, extname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import http from "node:http";
import { chromium } from "playwright";
import { lumosE2EPatchPolicyAllowTasks } from "./package-flow-shared.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PANEL_DIR = resolve(join(__dirname, ".."));
const PORT = String(20700 + (process.pid % 3500));
const BASE = `http://127.0.0.1:${PORT}`;
const READY_MS = 30000;

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
    var rawPath = (req.url || "").split("?")[0];
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
          if (Date.now() > deadline) return reject(new Error("timeout"));
          setTimeout(tryOnce, 80);
        });
    }
    tryOnce();
  });
}

async function lastAssistantText(page) {
  return page.evaluate(function () {
    var nodes = document.querySelectorAll(".lumos-chat-msg--assistant .lumos-chat-bubble");
    var last = nodes[nodes.length - 1];
    return last ? last.textContent || "" : "";
  });
}

async function run() {
  if (!existsSync(join(PANEL_DIR, "index.html"))) throw new Error("index.html yok");

  var server = await startPanelStaticServer(PANEL_DIR, PORT);
  await waitForServer(BASE + "/index.html", 15000);

  var browser = await chromium.launch({ headless: true });
  var page = await browser.newPage();
  await page.addInitScript(function () {
    window.LUMOS_PANEL_TASKS_API_BASE = false;
  });

  try {
    /* — A: çevrimdışı create red — */
    await page.goto(BASE + "/index.html#chat", { waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: READY_MS });
    await page.evaluate(function (keys) {
      try {
        localStorage.removeItem(keys.tasks);
        localStorage.removeItem(keys.chat);
      } catch (_) {}
    }, { tasks: "lumos_dot_lumos_tasks_json_v1", chat: "lumos_panel_chat_messages_v1" });

    var offMark = "pol-off-" + Date.now();
    await page.fill("#lumos-chat-input", "görev oluştur " + offMark);
    await page.click("#lumos-chat-send");
    await page.waitForFunction(
      function () {
        return document.querySelectorAll(".lumos-chat-msg").length >= 2;
      },
      { timeout: 15000 }
    );
    var a1 = await lastAssistantText(page);
    if (a1.toLowerCase().indexOf("çevrimdışı") === -1) {
      throw new Error("offline create beklenen red yok: " + a1.slice(0, 120));
    }

    var hasBlockEv = await page.evaluate(function () {
      var raw = localStorage.getItem("lumos_dot_lumos_tasks_json_v1");
      if (!raw) return false;
      try {
        var o = JSON.parse(raw);
        var evs = o && o.events ? o.events : [];
        var i;
        for (i = 0; i < evs.length; i++) {
          if (evs[i] && evs[i].type === "policy_blocked") return true;
        }
      } catch (_) {}
      return false;
    });
    if (hasBlockEv) throw new Error("policy_blocked kalıcı depoya yazılmamalıydı");

    /* — B: online + allow → create OK — */
    await lumosE2EPatchPolicyAllowTasks(page);
    var okMark = "pol-ok-" + Date.now();
    await page.fill("#lumos-chat-input", "görev oluştur " + okMark);
    await page.click("#lumos-chat-send");
    await page.waitForFunction(
      function () {
        return document.querySelectorAll(".lumos-chat-msg").length >= 4;
      },
      { timeout: 15000 }
    );
    var a2 = await lastAssistantText(page);
    if (a2.indexOf("oluşturuldu") === -1) throw new Error("online create başarı yok: " + a2.slice(0, 120));

    /* — C: kilit → sil red + bellekte policy_blocked — */
    await page.evaluate(function () {
      var rs = window.__LUMOS_READ_STATE__;
      if (rs && rs.guidance) rs.guidance.lock = "LOCKED";
      if (rs && rs.keystore) rs.keystore.keystore_state = "Kilitli";
    });
    await page.fill("#lumos-chat-input", "görev sil " + okMark);
    await page.click("#lumos-chat-send");
    await page.waitForFunction(
      function () {
        return document.querySelectorAll(".lumos-chat-msg").length >= 6;
      },
      { timeout: 15000 }
    );
    var a3 = await lastAssistantText(page);
    if (a3.toLowerCase().indexOf("koruma") === -1 && a3.toLowerCase().indexOf("kilit") === -1) {
      throw new Error("koruma sil red bekleniyordu: " + a3.slice(0, 120));
    }

    await page.goto(BASE + "/index.html#logs", { waitUntil: "load", timeout: READY_MS });
    await page.waitForTimeout(400);
    var logsBody = await page.locator("#main-content").innerText();
    var logsLower = logsBody.toLowerCase();
    if (logsLower.indexOf("policy_blocked") === -1) {
      throw new Error("Kayıtlar’da policy_blocked satırı yok");
    }
    if (
      logsBody.indexOf("actionCode=task_deleted") === -1 ||
      logsBody.indexOf("reasonCode=koruma_aktif_delete") === -1
    ) {
      throw new Error("Kayıtlar’da actionCode=task_deleted / reasonCode=koruma_aktif_delete yok");
    }
  } finally {
    await browser.close();
    await new Promise(function (r) {
      server.close(function () {
        r();
      });
    });
  }
}

run()
  .then(function () {
    console.log("POLICY_E2E_RESULT: PASS");
    process.exit(0);
  })
  .catch(function (err) {
    console.error("POLICY_E2E_RESULT: FAIL");
    console.error(String(err && err.message ? err.message : err));
    process.exit(1);
  });
