/**
 * OD-046 minimum v1 — ui/dist static serve smoke: /panel loads, basic DOM.
 * Requires: npm run build (ui/dist/panel/index.html).
 */
import { chromium } from "playwright";
import { waitForPanelDom, PANEL_READY_MS } from "./lib/panel-helpers.mjs";
import {
  closeServer,
  DIST_DIR,
  getDefaultServerTargets,
  startStaticServer,
  assertPanelDistBuilt,
  waitForServer,
} from "./lib/static-server.mjs";

function fail(reason) {
  console.error("SMOKE_UI_RESULT: FAIL");
  console.error(reason);
  process.exit(1);
}

try {
  assertPanelDistBuilt();
} catch (err) {
  fail(String(err && err.message ? err.message : err));
}

const { port, PANEL_URL } = getDefaultServerTargets();
let server;

try {
  server = await startStaticServer(DIST_DIR, port);
  await waitForServer(PANEL_URL, PANEL_READY_MS);

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto(PANEL_URL, { waitUntil: "domcontentloaded", timeout: PANEL_READY_MS });

  const title = await page.title();
  if (!title.includes("Lumos Panel")) {
    await browser.close();
    fail("Beklenen başlık yok; title=" + JSON.stringify(title));
  }

  try {
    await waitForPanelDom(page, PANEL_READY_MS);
  } catch (domErr) {
    await browser.close();
    fail("Temel panel DOM eksik (#chat-thread veya #panel-conn-badge): " + String(domErr.message || domErr));
  }

  await browser.close();
  console.log("SMOKE_UI_RESULT: PASS");
  console.log("surface: ui/dist static");
  console.log("url:", PANEL_URL);
} catch (err) {
  fail(String(err && err.message ? err.message : err));
} finally {
  await closeServer(server);
}
