/**
 * OD-046 minimum v1 — ui/dist static serve smoke: /panel loads, basic DOM.
 * Requires: npm run build (ui/dist/panel/index.html).
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, extname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import http from "node:http";
import { chromium } from "playwright";

const __dirname = dirname(fileURLToPath(import.meta.url));
const UI_DIR = resolve(join(__dirname, ".."));
const DIST_DIR = join(UI_DIR, "dist");
const PANEL_INDEX = join(DIST_DIR, "panel", "index.html");
const PORT = process.env.LUMOS_UI_SMOKE_PORT
  ? String(process.env.LUMOS_UI_SMOKE_PORT).trim()
  : String(21300 + (process.pid % 6000));
const BASE = `http://127.0.0.1:${PORT}`;
const PANEL_URL = `${BASE}/panel/`;
const READY_MS = 30000;

function fail(reason) {
  console.error("SMOKE_UI_RESULT: FAIL");
  console.error(reason);
  process.exit(1);
}

if (!existsSync(PANEL_INDEX)) {
  fail("ui/dist/panel/index.html yok — önce: cd ui && npm run build");
}

function mimeType(filePath) {
  const ext = extname(filePath).toLowerCase();
  if (ext === ".html") return "text/html; charset=utf-8";
  if (ext === ".js") return "text/javascript; charset=utf-8";
  if (ext === ".css") return "text/css; charset=utf-8";
  if (ext === ".json") return "application/json; charset=utf-8";
  if (ext === ".svg") return "image/svg+xml";
  if (ext === ".png") return "image/png";
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  if (ext === ".webp") return "image/webp";
  if (ext === ".webmanifest") return "application/manifest+json";
  return "application/octet-stream";
}

function resolveStaticPath(root, urlPath) {
  const dec = decodeURIComponent(urlPath.split("?")[0]);
  let rel = dec === "/" || dec === "" ? "index.html" : dec.replace(/^\//, "");
  if (rel.endsWith("/")) rel += "index.html";
  let absPath = resolve(root, rel);
  if (existsSync(absPath) && !absPath.endsWith(".html")) {
    const indexCandidate = join(absPath, "index.html");
    if (existsSync(indexCandidate)) absPath = indexCandidate;
  }
  const relToRoot = relative(root, absPath);
  if (relToRoot.startsWith("..") || relToRoot === "..") return null;
  if (!existsSync(absPath)) return null;
  return absPath;
}

function startStaticServer(rootDir, portStr) {
  const root = resolve(rootDir);
  const server = http.createServer(function (req, res) {
    const absPath = resolveStaticPath(root, req.url || "/");
    if (!absPath) {
      res.writeHead(404);
      res.end();
      return;
    }
    try {
      const buf = readFileSync(absPath);
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
  const deadline = Date.now() + ms;
  return new Promise(function (resolve, reject) {
    function tryOnce() {
      http
        .get(url, function (res) {
          res.resume();
          if (res.statusCode === 200) return resolve();
          if (Date.now() >= deadline) return reject(new Error("HTTP " + res.statusCode));
          setTimeout(tryOnce, 200);
        })
        .on("error", function () {
          if (Date.now() >= deadline) return reject(new Error("unreachable"));
          setTimeout(tryOnce, 200);
        });
    }
    tryOnce();
  });
}

let server;
try {
  server = await startStaticServer(DIST_DIR, PORT);
  await waitForServer(PANEL_URL, READY_MS);

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto(PANEL_URL, { waitUntil: "domcontentloaded", timeout: READY_MS });

  const title = await page.title();
  if (!title.includes("Lumos Panel")) {
    await browser.close();
    fail("Beklenen başlık yok; title=" + JSON.stringify(title));
  }

  const chatThread = await page.locator("#chat-thread").count();
  const connBadge = await page.locator("#panel-conn-badge").count();
  if (chatThread < 1 || connBadge < 1) {
    await browser.close();
    fail("Temel panel DOM eksik (#chat-thread veya #panel-conn-badge)");
  }

  await browser.close();
  console.log("SMOKE_UI_RESULT: PASS");
  console.log("surface: ui/dist static");
  console.log("url:", PANEL_URL);
} catch (err) {
  fail(String(err && err.message ? err.message : err));
} finally {
  if (server) server.close();
}
