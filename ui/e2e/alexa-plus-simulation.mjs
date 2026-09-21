import { chromium } from "playwright";
import {
  closeServer,
  DIST_DIR,
  getDefaultServerTargets,
  startStaticServer,
  waitForServer,
} from "./lib/static-server.mjs";
import { PANEL_READY_MS } from "./lib/panel-helpers.mjs";

function fail(reason) {
  console.error("ALEXA_PLUS_SIM_E2E_RESULT: FAIL");
  console.error(reason);
  process.exitCode = 1;
}

const { port } = getDefaultServerTargets();
const url = `http://127.0.0.1:${port}/alexa-plus-simulasyon`;
let server;
let browser;

try {
  server = await startStaticServer(DIST_DIR, port);
  await waitForServer(url, PANEL_READY_MS);
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: PANEL_READY_MS });
  const frame = page.frameLocator("#lumos-panel-frame");
  await frame.locator("#chat-thread").waitFor({ state: "attached", timeout: PANEL_READY_MS });
  await page.getByText("Hazır. İstek gönderildiğinde").waitFor({ timeout: PANEL_READY_MS });

  await page.locator("#sim-run").click();
  const dialog = frame.locator("#panel-confirmation-dialog");
  await dialog.waitFor({ state: "visible", timeout: PANEL_READY_MS });
  const dialogText = await dialog.textContent();
  if (!dialogText.includes("Servis ziyareti") || !dialogText.includes("Yarın 14:00")) {
    throw new Error("Onay ekranında çıkarılan başlık/zaman yok: " + dialogText);
  }
  await frame.locator("#panel-confirmation-approve").click();
  await page.getByText("Onaylandı; görev Lumos panelinde oluşturuldu.").waitFor({ timeout: PANEL_READY_MS });
  await frame.getByText("Servis ziyareti", { exact: true }).waitFor({ timeout: PANEL_READY_MS });

  const events = await page.evaluate(() => JSON.parse(localStorage.getItem("lumos_alexa_plus_simulation_events_v1") || "[]"));
  if (events.length !== 2 || events[1].type !== "proposal_approved") {
    throw new Error("Beklenen olay kaydı oluşmadı: " + JSON.stringify(events));
  }
  if (JSON.stringify(events).includes("Yarın 14:00 için servis ziyareti görevi hazırla")) {
    throw new Error("Ham konuşma olay kaydına sızdı");
  }
  console.log("ALEXA_PLUS_SIM_E2E_RESULT: PASS");
  console.log("surface:", url);
} catch (err) {
  fail(String(err && err.message ? err.message : err));
} finally {
  if (browser) await browser.close();
  await closeServer(server);
}
