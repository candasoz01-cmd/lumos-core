/**
 * OD-046 Faz 2 — ui/dist package-local E2E (LUMOS_PANEL_TASKS_API_BASE=false).
 * Flow: chat create → görevler list → UI complete → UI delete → reload persistence.
 */
import { chromium } from "playwright";
import {
  clickModule,
  clearPanelGorevlerStorage,
  PACKAGE_FLOW_MS,
  PANEL_GOREVLER_LS_KEY,
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

const MARK = "pkg-local-" + Date.now();
const CREATE_CMD = "görev oluştur " + MARK;

function fail(step, msg) {
  throw new Error("[package-local-e2e] " + step + ": " + msg);
}

function logFail(err) {
  console.error("PACKAGE_LOCAL_E2E_RESULT: FAIL");
  console.error(String(err && err.message ? err.message : err));
  process.exit(1);
}

try {
  assertPanelDistBuilt();
} catch (err) {
  logFail(err);
}

const { port, PANEL_URL } = getDefaultServerTargets();
let server;

async function assertGorevlerListHasMark(page, step, expectPresent) {
  const listText = await page.locator("#gorevler-list").innerText();
  const has = listText.indexOf(MARK) !== -1;
  if (expectPresent && !has) fail(step, "görev listesinde başlık yok");
  if (!expectPresent && has) fail(step, "görev listesinde başlık hâlâ görünüyor");
}

async function assertGorevlerStorage(page, step) {
  const pack = await page.evaluate(
    function (payload) {
      var raw = localStorage.getItem(payload.lsKey);
      var rows = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(rows)) return { err: "storage not array" };
      var matches = rows.filter(function (t) {
        return t && String(t.title || "") === payload.title;
      });
      return { count: matches.length, rows: matches };
    },
    { lsKey: PANEL_GOREVLER_LS_KEY, title: MARK },
  );

  if (pack.err) fail(step, pack.err);
  if (pack.count !== 0) {
    fail(step, "lumos_panel_gorevler_list_v1 içinde görev kaldı; count=" + pack.count);
  }
}

async function waitForGorevlerModuleActive(page) {
  await page.waitForSelector('[data-module-panel="gorevler"][data-active="true"]', {
    state: "attached",
    timeout: PACKAGE_FLOW_MS,
  });
}

async function openGorevlerTaskByMark(page, options = {}) {
  const expectAction = options.expectAction === "delete" ? "delete" : "complete";
  const actionSelector =
    expectAction === "delete" ? "#gorevler-detail-delete:not([hidden])" : "#gorevler-detail-complete:not([hidden])";

  await waitForGorevlerModuleActive(page);
  const card = page.locator("#gorevler-list .gorevler-task-card", { hasText: MARK }).first();
  await card.waitFor({ state: "visible", timeout: PACKAGE_FLOW_MS });
  await card.scrollIntoViewIfNeeded();
  await card.click();
  await page.waitForFunction(
    function () {
      var detail = document.getElementById("gorevler-detail");
      if (!detail) return false;
      if (typeof detail.open === "boolean") return detail.open;
      return detail.hidden === false;
    },
    { timeout: PACKAGE_FLOW_MS },
  );
  await page.waitForFunction(
    function (mark) {
      var title = document.getElementById("gorevler-detail-title");
      return !!(title && title.textContent && title.textContent.indexOf(mark) !== -1);
    },
    MARK,
    { timeout: PACKAGE_FLOW_MS },
  );
  await page.waitForSelector(actionSelector, {
    state: "visible",
    timeout: PACKAGE_FLOW_MS,
  });
}

async function run() {
  server = await startStaticServer(DIST_DIR, port);
  await waitForServer(PANEL_URL, PACKAGE_FLOW_MS);

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  page.on("dialog", async (dialog) => {
    await dialog.accept();
  });

  await page.addInitScript(function () {
    window.LUMOS_PANEL_TASKS_API_BASE = false;
  });

  try {
    await page.goto(PANEL_URL, { waitUntil: "domcontentloaded", timeout: PACKAGE_FLOW_MS });
    await waitForPanelDom(page, PACKAGE_FLOW_MS);
    await patchPolicyAllowTasks(page, { userMode: "offline" });
    await clearPanelGorevlerStorage(page);
    await page.reload({ waitUntil: "domcontentloaded", timeout: PACKAGE_FLOW_MS });
    await waitForPanelDom(page, PACKAGE_FLOW_MS);
    await patchPolicyAllowTasks(page, { userMode: "offline" });

    await sendChatMessage(page, CREATE_CMD);
    await waitForChatContains(page, "Görev eklendi", PACKAGE_FLOW_MS);
    await waitForChatContains(page, MARK, PACKAGE_FLOW_MS);

    await clickModule(page, "gorevler", PACKAGE_FLOW_MS);
    await waitForGorevlerModuleActive(page);
    await page.waitForSelector("#gorevler-list", { state: "attached", timeout: PACKAGE_FLOW_MS });
    await assertGorevlerListHasMark(page, "after-create/list", true);

    await openGorevlerTaskByMark(page);
    await page.click("#gorevler-detail-complete");
    await page.locator('[data-gorevler-filter="done"]').click();
    await page.waitForFunction(
      function (mark) {
        var list = document.getElementById("gorevler-list");
        return !!(list && list.innerText && list.innerText.indexOf(mark) !== -1);
      },
      MARK,
      { timeout: PACKAGE_FLOW_MS },
    );
    await assertGorevlerListHasMark(page, "after-complete/done-filter", true);

    await openGorevlerTaskByMark(page, { expectAction: "delete" });
    await page.click("#gorevler-detail-delete");
    await page.waitForTimeout(300);
    await assertGorevlerListHasMark(page, "after-delete/list-all", false);

    await page.locator('[data-gorevler-filter="pending"]').click();
    await assertGorevlerListHasMark(page, "after-delete/pending-filter", false);
    await page.locator('[data-gorevler-filter="done"]').click();
    await assertGorevlerListHasMark(page, "after-delete/done-filter", false);

    const chatBeforeReload = await page.locator("#chat-thread").innerText();
    if (chatBeforeReload.indexOf(CREATE_CMD) === -1) {
      fail("pre-reload/chat", "sohbette create komutu yok");
    }
    if (chatBeforeReload.indexOf("görev tamamla") !== -1) {
      fail("pre-reload/chat", "sohbette görev tamamla komutu olmamalı (UI tamamla kullanıldı)");
    }

    await page.reload({ waitUntil: "domcontentloaded", timeout: PACKAGE_FLOW_MS });
    await waitForPanelDom(page, PACKAGE_FLOW_MS);
    await clickModule(page, "gorevler", PACKAGE_FLOW_MS);
    await waitForGorevlerModuleActive(page);
    await assertGorevlerListHasMark(page, "post-reload/list", false);
    await assertGorevlerStorage(page, "post-reload/storage");
  } finally {
    await browser.close();
  }
}

run()
  .then(function () {
    console.log("PACKAGE_LOCAL_E2E_RESULT: PASS");
    console.log("surface: ui/dist static");
    console.log("mark:", MARK);
    console.log("url:", PANEL_URL);
    process.exit(0);
  })
  .catch(function (err) {
    logFail(err);
  })
  .finally(async function () {
    await closeServer(server);
  });
