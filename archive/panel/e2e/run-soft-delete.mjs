/**
 * Happy path: görev oluştur → görev sil → listede yok → refresh sonrası yok → logs’ta task_deleted.
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, extname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import http from "node:http";
import { chromium } from "playwright";
import { lumosE2EPatchPolicyAllowTasks } from "./package-flow-shared.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PANEL_DIR = resolve(join(__dirname, ".."));
const PORT = process.env.LUMOS_PANEL_E2E_PORT
  ? String(process.env.LUMOS_PANEL_E2E_PORT).trim()
  : String(20200 + (process.pid % 7000));
const BASE = `http://127.0.0.1:${PORT}`;
const READY_MS = 30000;
/* Örnek başlık kalıbı: sil-test-1 (benzersiz sonek) */
const MARK = "sil-test-1-" + Date.now();

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
          if (Date.now() > deadline) return reject(new Error("waitForServer status " + res.statusCode));
          setTimeout(tryOnce, 80);
        })
        .on("error", function () {
          if (Date.now() > deadline) return reject(new Error("server timeout"));
          setTimeout(tryOnce, 80);
        });
    }
    tryOnce();
  });
}

async function run() {
  var server = await startPanelStaticServer(PANEL_DIR, PORT);
  await waitForServer(BASE + "/index.html", 15000);
  var browser = await chromium.launch({ headless: true });
  var page = await browser.newPage();
  await page.addInitScript(function () {
    window.LUMOS_PANEL_TASKS_API_BASE = false;
  });
  try {
    await page.goto(BASE + "/index.html#chat", { waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: READY_MS });
    await lumosE2EPatchPolicyAllowTasks(page);
    await page.evaluate(function () {
      try {
        localStorage.removeItem("lumos_dot_lumos_tasks_json_v1");
        localStorage.removeItem("lumos_panel_chat_messages_v1");
      } catch (_) {}
    });

    await page.fill("#lumos-chat-input", "görev oluştur " + MARK);
    await page.click("#lumos-chat-send");
    await page.waitForFunction(
      function () {
        return document.querySelectorAll(".lumos-chat-msg").length >= 2;
      },
      { timeout: 20000 }
    );

    page.on("dialog", (d) => d.accept());
    await page.fill("#lumos-chat-input", "görev sil " + MARK);
    await page.click("#lumos-chat-send");
    await page.waitForFunction(
      function () {
        return document.querySelectorAll(".lumos-chat-msg").length >= 4;
      },
      { timeout: 20000 }
    );

    var silOk = await page.evaluate(function () {
      var nodes = document.querySelectorAll(".lumos-chat-msg--assistant .lumos-chat-bubble");
      if (!nodes.length) return { ok: false, reason: "assistant yok" };
      var last = nodes[nodes.length - 1];
      var txt = last ? last.textContent || "" : "";
      if (txt.indexOf("bulunamadı") !== -1) return { ok: false, reason: "sil başarısız: " + txt.slice(0, 80) };
      if (txt.indexOf("silindi") === -1) return { ok: false, reason: "silindi yanıtı yok: " + txt.slice(0, 80) };
      return { ok: true };
    });
    if (!silOk.ok) throw new Error(silOk.reason || "sil chat yanıtı");

    var filterIds = ["all", "active", "pending", "completed", "failed", "blocked"];

    async function assertDeletedHiddenEveryTaskFilter() {
      await page.goto(BASE + "/index.html#tasks", { waitUntil: "load", timeout: READY_MS });
      await page.waitForSelector(".task-filters", { state: "attached", timeout: READY_MS });
      var fi;
      for (fi = 0; fi < filterIds.length; fi++) {
        await page.locator('[data-task-filter="' + filterIds[fi] + '"]').click();
        await page.waitForTimeout(250);
        var body = await page.locator("#main-content").innerText();
        if (body.indexOf(MARK) !== -1) throw new Error("filtre " + filterIds[fi] + " içinde MARK göründü");
      }
    }

    await assertDeletedHiddenEveryTaskFilter();

    var pack = await page.evaluate(function (title) {
      var raw = localStorage.getItem("lumos_dot_lumos_tasks_json_v1");
      if (!raw) return { err: "no storage" };
      var o = JSON.parse(raw);
      var row = (o.tasks || []).filter(function (t) {
        return t && String(t.title) === title;
      });
      return { count: row.length, status: row[0] && row[0].status };
    }, MARK);
    if (pack.err) throw new Error(pack.err);
    if (pack.count !== 1 || pack.status !== "deleted") throw new Error("persist: beklenen 1 deleted, " + JSON.stringify(pack));

    await page.goto(BASE + "/index.html#logs", { waitUntil: "load", timeout: READY_MS });
    await page.waitForTimeout(200);
    var logsBody = await page.locator("#main-content").innerText();
    if (logsBody.indexOf("[task_deleted]") === -1 || logsBody.indexOf(MARK) === -1) {
      throw new Error("logs’ta task_deleted yok");
    }

    await page.goto(BASE + "/index.html#trash", { waitUntil: "load", timeout: READY_MS });
    await page.waitForTimeout(800);
    var trashBody = await page.locator("#main-content").innerText();
    if (trashBody.indexOf(MARK) === -1) throw new Error("Silinenler ekranında soft görev başlığı yok");
    var softRows = await page.locator('[data-soft-deleted-task="1"]').count();
    if (softRows < 1) throw new Error("data-soft-deleted-task satırı yok");

    await page.goto(BASE + "/index.html#tasks", { waitUntil: "load", timeout: READY_MS });
    await page.reload({ waitUntil: "load", timeout: READY_MS });
    await assertDeletedHiddenEveryTaskFilter();

    await page.goto(BASE + "/index.html#trash", { waitUntil: "load", timeout: READY_MS });
    await page.waitForTimeout(400);
    var trashAfter = await page.locator("#main-content").innerText();
    if (trashAfter.indexOf(MARK) === -1) throw new Error("reload sonrası trash’ta görev yok");
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
    console.log("SOFT_DELETE_E2E: PASS");
    process.exit(0);
  })
  .catch(function (err) {
    console.error("SOFT_DELETE_E2E: FAIL");
    console.error(String(err && err.message ? err.message : err));
    process.exit(1);
  });
