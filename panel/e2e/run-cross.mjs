/**
 * Çapraz kalıcılık: Chat + Task motoru + Kayıtlar/Dashboard olayları.
 * Node statik sunucu (Python yok); FAIL → exit 1.
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, extname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import http from "node:http";
import { chromium } from "playwright";
import { lumosE2EPatchPolicyAllowTasks } from "./package-flow-shared.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PANEL_DIR = resolve(join(__dirname, ".."));
if (!existsSync(join(PANEL_DIR, "index.html"))) {
  console.error("E2E_RESULT: FAIL");
  console.error("BROKEN_PART: panel kökünde index.html yok:", PANEL_DIR);
  process.exit(1);
}

const PORT = process.env.LUMOS_PANEL_E2E_PORT
  ? String(process.env.LUMOS_PANEL_E2E_PORT).trim()
  : String(20100 + (process.pid % 8000));
const BASE = `http://127.0.0.1:${PORT}`;
const CHAT_READY_MS = 45000;
const MARK = `oto test ${Date.now()}`;

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
          if (Date.now() > deadline) return reject(new Error("waitForServer: beklenmeyen status " + res.statusCode));
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

function countSubstring(s, sub) {
  if (!sub) return 0;
  var n = 0;
  var i = 0;
  while (true) {
    var j = s.indexOf(sub, i);
    if (j === -1) break;
    n++;
    i = j + sub.length;
  }
  return n;
}

async function assertStorageConsistency(page, label) {
  var pack = await page.evaluate(function (keys) {
    var chat = localStorage.getItem(keys.chat);
    var tasks = localStorage.getItem(keys.tasks);
    return { chat: chat, tasks: tasks };
  }, { chat: "lumos_panel_chat_messages_v1", tasks: "lumos_dot_lumos_tasks_json_v1" });

  if (!pack.chat) throw new Error(label + ": chat localStorage yok");
  if (!pack.tasks) throw new Error(label + ": tasks localStorage yok");

  var chatDoc = JSON.parse(pack.chat);
  var tasksDoc = JSON.parse(pack.tasks);
  if (chatDoc.v !== 1 || !Array.isArray(chatDoc.messages)) throw new Error(label + ": chat doc şekli");
  if (tasksDoc.v !== 1 || !Array.isArray(tasksDoc.tasks) || !Array.isArray(tasksDoc.events)) {
    throw new Error(label + ": tasks doc şekli");
  }

  var title = MARK;
  var taskRows = tasksDoc.tasks.filter(function (t) {
    return t && String(t.title || "") === title;
  });
  if (taskRows.length !== 1) throw new Error(label + ": beklenen tek görev satırı, sayı=" + taskRows.length);
  if (taskRows[0].status !== "done") throw new Error(label + ": görev done değil");

  var created = tasksDoc.events.filter(function (e) {
    return e && e.type === "task_created" && String(e.text || "") === title;
  });
  var completed = tasksDoc.events.filter(function (e) {
    return e && e.type === "task_completed" && String(e.text || "") === title;
  });
  if (created.length !== 1) throw new Error(label + ": task_created sayısı " + created.length);
  if (completed.length !== 1) throw new Error(label + ": task_completed sayısı " + completed.length);

  var chatText = JSON.stringify(chatDoc.messages);
  if (!chatText.includes("görev oluştur " + title)) throw new Error(label + ": chat create yok");
  if (!chatText.includes("görev tamamla " + title)) throw new Error(label + ": chat complete yok");
}

async function assertUi(page, label) {
  var title = MARK;

  await page.goto(BASE + "/index.html#chat", { waitUntil: "load", timeout: CHAT_READY_MS });
  await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: CHAT_READY_MS });
  var chatBody = await page.locator("#main-content").innerText();
  if (!chatBody.includes("görev oluştur " + title)) throw new Error(label + ": UI chat create yok");
  if (!chatBody.includes("görev tamamla " + title)) throw new Error(label + ": UI chat complete yok");

  await page.goto(BASE + "/index.html#tasks", { waitUntil: "load", timeout: CHAT_READY_MS });
  await page.waitForSelector(".task-filters", { state: "attached", timeout: CHAT_READY_MS });
  var tasksBody = await page.locator("#main-content").innerText();
  if (!tasksBody.includes(title)) throw new Error(label + ": tasks ekranında başlık yok");
  await page.locator('[data-task-filter="completed"]').click();
  await page.waitForTimeout(350);
  var completedView = await page.locator("#main-content").innerText();
  if (!completedView.includes(title)) throw new Error(label + ": tamamlandı filtresinde yok");

  await page.goto(BASE + "/index.html#logs", { waitUntil: "load", timeout: CHAT_READY_MS });
  await page.waitForTimeout(200);
  var logsBody = await page.locator("#main-content").innerText();
  if (!logsBody.includes("[task_created]") || !logsBody.includes(title)) {
    throw new Error(label + ": logs task_created yok");
  }
  if (!logsBody.includes("[task_completed]")) throw new Error(label + ": logs task_completed yok");
  if (countSubstring(logsBody, "[task_completed] " + title) !== 1) {
    throw new Error(label + ": logs task_completed tekrar veya eksik");
  }

  var evPack = await page.evaluate(function () {
    var raw = localStorage.getItem("lumos_dot_lumos_tasks_json_v1");
    if (!raw) return { err: "no tasks storage" };
    var o = JSON.parse(raw);
    if (!o || o.v !== 1 || !Array.isArray(o.events)) return { err: "events yok" };
    return { events: o.events };
  });
  if (evPack.err) throw new Error(label + ": " + evPack.err);
  var motor = evPack.events.filter(function (e) {
    return (
      e &&
      (e.type === "task_created" || e.type === "task_completed" || e.type === "task_deleted")
    );
  });
  var tags = logsBody.match(/\[task_(?:created|completed|deleted)\]/g);
  if (!tags || tags.length !== motor.length) {
    throw new Error(label + ": log motor satır sayısı storage ile uyuşmuyor " + (tags ? tags.length : 0) + " vs " + motor.length);
  }
  var ei;
  for (ei = 0; ei < motor.length; ei++) {
    var ev = motor[ei];
    var ttag = "[" + String(ev.type) + "]";
    if (logsBody.indexOf(ttag) === -1) throw new Error(label + ": storage’daki " + ttag + " log UI’da yok");
    var etx = String(ev.text || "").trim();
    if (etx && logsBody.indexOf(etx) === -1) throw new Error(label + ": storage olay metni log’da yok");
  }

  await page.goto(BASE + "/index.html#dashboard", { waitUntil: "load", timeout: CHAT_READY_MS });
  await page.waitForTimeout(200);
  var dash = await page.locator("#main-content").innerText();
  if (!dash.includes("[task_created]") || !dash.includes("[task_completed]")) {
    throw new Error(label + ": dashboard olayları eksik");
  }
}

async function run() {
  var server = await startPanelStaticServer(PANEL_DIR, PORT);
  try {
    await waitForServer(BASE + "/index.html", 15000);
  } catch (e) {
    await new Promise(function (r) {
      server.close(function () {
        r();
      });
    });
    throw e;
  }

  var browser = await chromium.launch({ headless: true });
  var page = await browser.newPage();
  await page.addInitScript(function () {
    window.LUMOS_PANEL_TASKS_API_BASE = false;
  });

  try {
    await page.goto(BASE + "/index.html#chat", { waitUntil: "load", timeout: CHAT_READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: CHAT_READY_MS });
    await lumosE2EPatchPolicyAllowTasks(page);

    var beforeEmpty = await page.evaluate(function () {
      return localStorage.getItem("lumos_panel_chat_messages_v1");
    });
    await page.fill("#lumos-chat-input", "   ");
    await page.click("#lumos-chat-send");
    await page.waitForTimeout(200);
    var afterEmpty = await page.evaluate(function () {
      return localStorage.getItem("lumos_panel_chat_messages_v1");
    });
    if (beforeEmpty !== afterEmpty) throw new Error("boş mesaj persist oldu");

    await page.fill("#lumos-chat-input", "görev oluştur " + MARK);
    await page.click("#lumos-chat-send");
    await page.waitForFunction(
      function () {
        return document.querySelectorAll(".lumos-chat-msg").length >= 2;
      },
      { timeout: 20000 }
    );

    await page.fill("#lumos-chat-input", "görev tamamla " + MARK);
    await page.click("#lumos-chat-send");
    await page.waitForFunction(
      function () {
        return document.querySelectorAll(".lumos-chat-msg").length >= 4;
      },
      { timeout: 20000 }
    );

    await assertUi(page, "pre-reload");
    await assertStorageConsistency(page, "pre-reload");

    /* assertUi biterken hash #dashboard; reload aynı hash ile kalır — chat input yok. Tam sayfa yenileme + chat rotası. */
    await page.goto(BASE + "/index.html#chat", { waitUntil: "load", timeout: CHAT_READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: CHAT_READY_MS });
    await page.reload({ waitUntil: "load", timeout: CHAT_READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: CHAT_READY_MS });

    await assertUi(page, "post-reload");
    await assertStorageConsistency(page, "post-reload");

    var msgCount = await page.evaluate(function () {
      try {
        var raw = localStorage.getItem("lumos_panel_chat_messages_v1");
        if (!raw) return -1;
        var o = JSON.parse(raw);
        return Array.isArray(o.messages) ? o.messages.length : -1;
      } catch (_) {
        return -1;
      }
    });
    if (msgCount !== 4) throw new Error("chat mesaj sayısı beklenen 4, bulunan " + msgCount);
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
    console.log("E2E_RESULT: PASS");
    process.exit(0);
  })
  .catch(function (err) {
    console.error("E2E_RESULT: FAIL");
    console.error(String(err && err.message ? err.message : err));
    process.exit(1);
  });
