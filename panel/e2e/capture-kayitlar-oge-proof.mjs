/**
 * Kayıtlar: öğe bazlı liste + timeline kanıtı — PNG üretir (CI dışı, yerel doğrulama).
 * Kullanım: node panel/e2e/capture-kayitlar-oge-proof.mjs
 */
import { existsSync, mkdirSync, readFileSync } from "node:fs";
import { dirname, extname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import http from "node:http";
import { chromium } from "playwright";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PANEL_DIR = resolve(join(__dirname, ".."));
const PORT = String(20400 + (process.pid % 5000));
const BASE = `http://127.0.0.1:${PORT}`;
const LS_KEY = "lumos_dot_lumos_tasks_json_v1";
const OUT_DIR = resolve(join(__dirname, "artifacts"));
const OUT_PNG = join(OUT_DIR, "kayitlar-oge-bazli-timeline.png");

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
  return new Promise(function (resolveFn, rejectFn) {
    function tryOnce() {
      http
        .get(url, function (res) {
          res.resume();
          if (res.statusCode === 200) return resolveFn();
          if (Date.now() > deadline) return rejectFn(new Error("timeout"));
          setTimeout(tryOnce, 80);
        })
        .on("error", function () {
          if (Date.now() > deadline) return rejectFn(new Error("timeout"));
          setTimeout(tryOnce, 80);
        });
    }
    tryOnce();
  });
}

async function run() {
  if (!existsSync(PANEL_DIR + "/index.html")) {
    throw new Error("panel index.html yok");
  }
  mkdirSync(OUT_DIR, { recursive: true });

  var baseTs = Date.now();
  var iso = function (deltaSec) {
    return new Date(baseTs + deltaSec * 1000).toISOString();
  };
  /** Aynı görev: 5 motor olayı, çoğunda taskId boş — gruplama task_created + başlık ile tek satır olmalı. */
  var doc = {
    v: 1,
    tasks: [],
    events: [
      {
        id: "proof_e1",
        type: "task_created",
        taskId: "tsk_kanit_1",
        text: "Kanıt Görevi",
        ts: iso(-400),
      },
      {
        id: "proof_e2",
        type: "task_completed",
        taskId: "",
        text: "Kanıt Görevi",
        ts: iso(-300),
      },
      {
        id: "proof_e3",
        type: "task_deleted",
        taskId: "",
        text: "Kanıt Görevi",
        ts: iso(-200),
      },
      {
        id: "proof_e4",
        type: "task_completed",
        taskId: "",
        text: "Kanıt Görevi",
        ts: iso(-150),
      },
      {
        id: "proof_e5",
        type: "task_permanently_deleted",
        taskId: "tsk_kanit_1",
        text: "Görev kalıcı silindi: Kanıt Görevi",
        ts: iso(-50),
      },
    ],
  };

  var server = await startPanelStaticServer(PANEL_DIR, PORT);
  await waitForServer(BASE + "/index.html", 15000);

  var browser = await chromium.launch({ headless: true });
  var page = await browser.newPage();
  await page.addInitScript(function () {
    window.LUMOS_PANEL_TASKS_API_BASE = false;
  });

  await page.goto(BASE + "/index.html", { waitUntil: "load", timeout: 30000 });
  await page.evaluate(
    function (payload) {
      localStorage.setItem(payload.key, JSON.stringify(payload.doc));
    },
    { key: LS_KEY, doc: doc }
  );
  await page.goto(BASE + "/index.html#logs", { waitUntil: "load", timeout: 30000 });
  await page.waitForSelector(".kayitlar-timeline-row", { timeout: 15000 });

  var counts = await page.evaluate(function () {
    var rows = document.querySelectorAll(".kayitlar-timeline-row");
    var withTitle = 0;
    var i;
    for (i = 0; i < rows.length; i++) {
      if (rows[i].innerText && rows[i].innerText.indexOf("Kanıt Görevi") !== -1) withTitle++;
    }
    return { totalRows: rows.length, rowsWithKanıtGörevi: withTitle };
  });

  if (counts.rowsWithKanıtGörevi !== 1) {
    await browser.close();
    server.close();
    throw new Error(
      "Beklenen: Kanıt Görevi için tek satır; bulunan: " + JSON.stringify(counts)
    );
  }

  var row = page.locator(".kayitlar-timeline-row", { hasText: "Kanıt Görevi" }).first();
  await row.click();
  await page.waitForSelector(".kayitlar-timeline-process li", { timeout: 5000 });

  var stepCount = await page.locator(".kayitlar-timeline-process li").count();
  if (stepCount !== 5) {
    await browser.close();
    server.close();
    throw new Error("Beklenen 5 timeline adımı, bulunan: " + stepCount);
  }

  await page.locator("#main-content").screenshot({ path: OUT_PNG });
  await browser.close();
  await new Promise(function (r) {
    server.close(function () {
      r();
    });
  });

  console.log("KAYITLAR_OGE_PROOF_OK");
  console.log("PNG:", OUT_PNG);
  console.log(JSON.stringify({ totalRows: counts.totalRows, kanitRows: counts.rowsWithKanıtGörevi, timelineSteps: stepCount }));
}

run().catch(function (err) {
  console.error("KAYITLAR_OGE_PROOF_FAIL");
  console.error(String(err && err.message ? err.message : err));
  process.exit(1);
});
