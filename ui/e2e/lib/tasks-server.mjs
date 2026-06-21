/**
 * OD-046 Faz 3 — panel_tasks_server.py spawn/stop for ui/dist E2E.
 */
import { existsSync } from "node:fs";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import http from "node:http";
import { waitForServer } from "./static-server.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));

export const REPO_ROOT = resolve(join(__dirname, "..", "..", ".."));
export const PY_SCRIPT = join(REPO_ROOT, "panel/scripts/panel_tasks_server.py");

const TASKS_PORT_ENV_KEYS = ["LUMOS_UI_TASKS_E2E_PORT", "LUMOS_PANEL_TASKS_E2E_PORT"];
const TASKS_PORT_BASE = 31400;
const TASKS_PORT_SPAN = 5000;

export function resolveTasksApiPort() {
  for (const key of TASKS_PORT_ENV_KEYS) {
    const raw = process.env[key];
    if (raw && String(raw).trim()) return String(raw).trim();
  }
  return String(TASKS_PORT_BASE + (process.pid % TASKS_PORT_SPAN));
}

export function buildTasksApiBase(port) {
  return `http://127.0.0.1:${port}`;
}

export function assertTasksServerScript() {
  if (!existsSync(PY_SCRIPT)) {
    throw new Error("panel_tasks_server.py yok — " + PY_SCRIPT);
  }
}

export function createTempLumosBase(prefix = "lumos-ui-e2e-") {
  return mkdtempSync(join(tmpdir(), prefix));
}

export function startTasksServer(tmpBaseDir, portStr) {
  assertTasksServerScript();
  return spawn("python3", [PY_SCRIPT], {
    env: Object.assign({}, process.env, {
      LUMOS_BASE_DIR: tmpBaseDir,
      LUMOS_PANEL_TASKS_PORT: String(portStr),
      LUMOS_PANEL_TASKS_HOST: "127.0.0.1",
      // ADR-012: panel mutations require online policy; delete needs session unlock signal in E2E.
      LUMOS_MODE: process.env.LUMOS_MODE || "online",
      LUMOS_PROFILE: process.env.LUMOS_PROFILE || "guvenli_yurut",
      LUMOS_SESSION_UNLOCKED: process.env.LUMOS_SESSION_UNLOCKED || "true",
    }),
    stdio: "pipe",
  });
}

export function stopTasksServer(proc) {
  if (!proc) return;
  try {
    proc.kill("SIGTERM");
  } catch (_) {
    /* ignore */
  }
}

export async function waitForTasksApi(baseUrl, ms = 20000) {
  const base = String(baseUrl || "").replace(/\/$/, "");
  return waitForServer(`${base}/tasks`, ms);
}

export function fetchTasksDoc(baseUrl) {
  const base = String(baseUrl || "").replace(/\/$/, "");
  return new Promise(function (resolveFetch, rejectFetch) {
    http
      .get(`${base}/tasks`, function (res) {
        let body = "";
        res.on("data", function (chunk) {
          body += chunk;
        });
        res.on("end", function () {
          if (res.statusCode !== 200) {
            rejectFetch(new Error("GET /tasks HTTP " + res.statusCode));
            return;
          }
          try {
            resolveFetch(JSON.parse(body));
          } catch (err) {
            rejectFetch(err);
          }
        });
      })
      .on("error", rejectFetch);
  });
}

export function tasksDocHasTitle(doc, title) {
  const needle = String(title || "").trim();
  if (!needle || !doc || !Array.isArray(doc.tasks)) return false;
  return doc.tasks.some(function (t) {
    return t && String(t.title || "").trim() === needle && String(t.status || "") !== "deleted";
  });
}
