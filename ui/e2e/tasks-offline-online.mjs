/**
 * OD-046 Faz 3 — ui/dist görev API: online → API down → local fallback → API back.
 * UI-appropriate asserts (fetch /tasks, pending-op queue); NOT legacy data-lumos-task-source.
 */
import { chromium } from "playwright";
import {
  clickModule,
  clearPanelGorevlerStorage,
  PACKAGE_FLOW_MS,
  patchPolicyAllowTasks,
  sendChatMessage,
  waitForChatContains,
  waitForPanelDom,
} from "./lib/panel-helpers.mjs";
import {
  assertPanelDistBuilt,
  closeServer,
  DIST_DIR,
  getDefaultServerTargets,
  startStaticServer,
  waitForServer,
} from "./lib/static-server.mjs";
import {
  buildTasksApiBase,
  createTempLumosBase,
  fetchTasksDoc,
  PANEL_TASKS_E2E_SECRET,
  resolveTasksApiPort,
  startTasksServer,
  stopTasksServer,
  tasksDocHasTitle,
  waitForTasksApi,
} from "./lib/tasks-server.mjs";

const PENDING_OPS_LS_KEY = "lumos_panel_evidence_pending_ops_v1";

function fail(step, msg) {
  throw new Error("[tasks-offline-online-e2e] " + step + ": " + msg);
}

function logFail(err) {
  console.error("TASKS_OFFLINE_ONLINE_E2E_RESULT: FAIL");
  console.error(String(err && err.message ? err.message : err));
  process.exit(1);
}

try {
  assertPanelDistBuilt();
} catch (err) {
  logFail(err);
}

const { port, PANEL_URL } = getDefaultServerTargets();
const tasksPort = resolveTasksApiPort();
const TASK_API_BASE = buildTasksApiBase(tasksPort);
const tmpBase = createTempLumosBase("lumos-offline-online-");
let server;
let pyProc;

async function pageFetchTasksOk(page) {
  return page.evaluate(async function (base) {
    try {
      const token = String(window.LUMOS_PANEL_TASKS_TOKEN || "").trim();
      const headers = { Accept: "application/json" };
      if (token) headers["X-Kando-Token"] = token;
      const r = await fetch(base + "/tasks", { headers });
      if (!r.ok) return { ok: false, status: r.status };
      const doc = await r.json();
      return { ok: !!(doc && Array.isArray(doc.tasks)), status: r.status };
    } catch {
      return { ok: false, status: 0 };
    }
  }, TASK_API_BASE);
}

async function waitForPageTasksApi(page, expectOk, step) {
  await page.waitForFunction(
    function (payload) {
      const token = String(window.LUMOS_PANEL_TASKS_TOKEN || "").trim();
      const headers = { Accept: "application/json" };
      if (token) headers["X-Kando-Token"] = token;
      return fetch(payload.base + "/tasks", { headers })
        .then(function (r) {
          return r.ok === payload.expectOk;
        })
        .catch(function () {
          return payload.expectOk === false;
        });
    },
    { base: TASK_API_BASE, expectOk },
    { timeout: PACKAGE_FLOW_MS },
  );
  const probe = await pageFetchTasksOk(page);
  if (expectOk && !probe.ok) fail(step, "API erişilebilir olmalı; status=" + probe.status);
  if (!expectOk && probe.ok) fail(step, "API erişilemez olmalı; status=" + probe.status);
}

async function pendingOpsCount(page) {
  return page.evaluate(function (lsKey) {
    try {
      const raw = localStorage.getItem(lsKey);
      const rows = raw ? JSON.parse(raw) : [];
      return Array.isArray(rows) ? rows.length : 0;
    } catch {
      return 0;
    }
  }, PENDING_OPS_LS_KEY);
}

async function waitForGorevlerModuleActive(page) {
  await page.waitForSelector('[data-module-panel="gorevler"][data-active="true"]', {
    state: "attached",
    timeout: PACKAGE_FLOW_MS,
  });
}

async function waitForServerTitle(title, step) {
  const deadline = Date.now() + PACKAGE_FLOW_MS;
  while (Date.now() < deadline) {
    try {
      const doc = await fetchTasksDoc(TASK_API_BASE);
      if (tasksDocHasTitle(doc, title)) return;
    } catch (_) {
      /* retry */
    }
    await new Promise(function (r) {
      setTimeout(r, 250);
    });
  }
  fail(step, "API dönünce bekleyen create sunucuya yansımadı");
}

async function waitForPendingQueueEmpty(page, step) {
  await page.waitForFunction(
    function (lsKey) {
      try {
        const raw = localStorage.getItem(lsKey);
        const rows = raw ? JSON.parse(raw) : [];
        return !Array.isArray(rows) || rows.length === 0;
      } catch {
        return false;
      }
    },
    PENDING_OPS_LS_KEY,
    { timeout: PACKAGE_FLOW_MS },
  );
  const count = await pendingOpsCount(page);
  if (count > 0) fail(step, "API dönünce bekleyen kuyruk boşalmalı; count=" + count);
}

async function run() {
  pyProc = startTasksServer(tmpBase, tasksPort);
  server = await startStaticServer(DIST_DIR, port);
  try {
    await waitForTasksApi(TASK_API_BASE, 20000);
    await waitForServer(PANEL_URL, PACKAGE_FLOW_MS);
  } catch (err) {
    stopTasksServer(pyProc);
    await closeServer(server);
    throw err;
  }

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.addInitScript(function (args) {
    window.LUMOS_PANEL_TASKS_API_BASE = args.base;
    window.LUMOS_PANEL_TASKS_TOKEN = args.token;
  }, { base: TASK_API_BASE, token: PANEL_TASKS_E2E_SECRET });

  try {
    await page.goto(PANEL_URL, { waitUntil: "domcontentloaded", timeout: PACKAGE_FLOW_MS });
    await waitForPanelDom(page, PACKAGE_FLOW_MS);
    await patchPolicyAllowTasks(page, { userMode: "full" });
    await clearPanelGorevlerStorage(page);
    await page.reload({ waitUntil: "domcontentloaded", timeout: PACKAGE_FLOW_MS });
    await waitForPanelDom(page, PACKAGE_FLOW_MS);
    await patchPolicyAllowTasks(page, { userMode: "full" });

    await clickModule(page, "gorevler", PACKAGE_FLOW_MS);
    await waitForGorevlerModuleActive(page);
    await waitForPageTasksApi(page, true, "online/initial-fetch");

    stopTasksServer(pyProc);
    pyProc = null;
    await page.waitForTimeout(400);

    await clickModule(page, "sohbet", PACKAGE_FLOW_MS);
    await clickModule(page, "gorevler", PACKAGE_FLOW_MS);
    await waitForGorevlerModuleActive(page);
    await waitForPageTasksApi(page, false, "offline/api-unreachable");

    const offlineMark = "offline-try-" + Date.now();
    await clickModule(page, "sohbet", PACKAGE_FLOW_MS);
    await sendChatMessage(page, "görev oluştur " + offlineMark);
    await waitForChatContains(page, "Görev eklendi", PACKAGE_FLOW_MS);
    await waitForChatContains(page, offlineMark, PACKAGE_FLOW_MS);

    const pendingAfterCreate = await pendingOpsCount(page);
    if (pendingAfterCreate < 1) {
      fail("offline/pending-queue", "bekleyen kanıt kuyruğu boş; en az 1 create bekleniyordu");
    }

    await clickModule(page, "gorevler", PACKAGE_FLOW_MS);
    await waitForGorevlerModuleActive(page);
    const listWhileOffline = await page.locator("#gorevler-list").innerText();
    if (listWhileOffline.indexOf(offlineMark) === -1) {
      fail("offline/local-list", "API kapalıyken yerel listede görev görünmüyor");
    }

    let serverHasOfflineMark = false;
    try {
      const doc = await fetchTasksDoc(TASK_API_BASE);
      serverHasOfflineMark = tasksDocHasTitle(doc, offlineMark);
    } catch {
      serverHasOfflineMark = false;
    }
    if (serverHasOfflineMark) {
      fail("offline/server-doc", "API kapalıyken sunucuda görev oluşmamalı");
    }

    pyProc = startTasksServer(tmpBase, tasksPort);
    await waitForTasksApi(TASK_API_BASE, 20000);

    await page.evaluate(function () {
      window.dispatchEvent(new Event("online"));
    });
    await clickModule(page, "sohbet", PACKAGE_FLOW_MS);
    await clickModule(page, "gorevler", PACKAGE_FLOW_MS);
    await waitForGorevlerModuleActive(page);
    await waitForPageTasksApi(page, true, "online/restored-fetch");

    await waitForServerTitle(offlineMark, "online/server-sync");
    await waitForPendingQueueEmpty(page, "online/pending-drained");
  } finally {
    await browser.close();
  }
}

let exitCode = 0;

run()
  .then(function () {
    console.log("TASKS_OFFLINE_ONLINE_E2E_RESULT: PASS");
    console.log("surface: ui/dist static + panel_tasks_server");
    console.log("url:", PANEL_URL);
    console.log("tasks_api:", TASK_API_BASE);
  })
  .catch(function (err) {
    console.error("TASKS_OFFLINE_ONLINE_E2E_RESULT: FAIL");
    console.error(String(err && err.message ? err.message : err));
    exitCode = 1;
  })
  .finally(async function () {
    stopTasksServer(pyProc);
    await closeServer(server);
  })
  .then(function () {
    process.exit(exitCode);
  });
