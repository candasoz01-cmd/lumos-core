/**
 * OD-046 Faz 1 — ui/dist static server for E2E (Playwright).
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, extname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import http from "node:http";

const __dirname = dirname(fileURLToPath(import.meta.url));

export const UI_DIR = resolve(join(__dirname, "..", ".."));
export const DIST_DIR = join(UI_DIR, "dist");
export const PANEL_INDEX = join(DIST_DIR, "panel", "index.html");
export const DEFAULT_READY_MS = 30000;

const PORT_ENV_KEYS = ["LUMOS_UI_E2E_PORT", "LUMOS_UI_SMOKE_PORT"];
const PORT_BASE = 21300;
const PORT_SPAN = 6000;

export function resolveE2EPort() {
  for (const key of PORT_ENV_KEYS) {
    const raw = process.env[key];
    if (raw && String(raw).trim()) return String(raw).trim();
  }
  return String(PORT_BASE + (process.pid % PORT_SPAN));
}

export function buildBaseUrl(port) {
  return `http://127.0.0.1:${port}`;
}

export function buildPanelUrl(baseUrl) {
  const base = String(baseUrl || "").replace(/\/$/, "");
  return `${base}/panel/`;
}

export function getDefaultServerTargets(port = resolveE2EPort()) {
  const BASE_URL = buildBaseUrl(port);
  return {
    port,
    BASE_URL,
    PANEL_URL: buildPanelUrl(BASE_URL),
  };
}

export function assertPanelDistBuilt() {
  if (!existsSync(PANEL_INDEX)) {
    throw new Error("ui/dist/panel/index.html yok — önce: cd ui && npm run build");
  }
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

export function startStaticServer(rootDir, portStr) {
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

export function waitForServer(url, ms = DEFAULT_READY_MS) {
  const deadline = Date.now() + ms;
  return new Promise(function (resolveReady, rejectReady) {
    function tryOnce() {
      http
        .get(url, function (res) {
          res.resume();
          if (res.statusCode === 200) return resolveReady();
          if (Date.now() >= deadline) return rejectReady(new Error("HTTP " + res.statusCode));
          setTimeout(tryOnce, 200);
        })
        .on("error", function () {
          if (Date.now() >= deadline) return rejectReady(new Error("unreachable"));
          setTimeout(tryOnce, 200);
        });
    }
    tryOnce();
  });
}

export function closeServer(server) {
  if (!server) return Promise.resolve();
  return new Promise(function (resolveClose) {
    server.close(function () {
      resolveClose();
    });
  });
}

export async function startUiDistServer(options = {}) {
  const rootDir = options.rootDir || DIST_DIR;
  const port = options.port || resolveE2EPort();
  const readyMs = options.readyMs || DEFAULT_READY_MS;
  const targets = getDefaultServerTargets(port);
  assertPanelDistBuilt();
  const server = await startStaticServer(rootDir, port);
  await waitForServer(targets.PANEL_URL, readyMs);
  return { server, ...targets, readyMs };
}
