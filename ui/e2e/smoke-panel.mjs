/**
 * OD-046 minimum v1 — ui/dist static serve smoke: /panel loads, basic DOM.
 * Requires: npm run build (ui/dist/panel/index.html).
 */
import { chromium } from "playwright";
import {
  CHAT_INPUT_SELECTOR,
  waitForPanelDom,
  PANEL_READY_MS,
} from "./lib/panel-helpers.mjs";
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
  if (!title.includes("Lumos")) {
    await browser.close();
    fail("Beklenen başlık yok; title=" + JSON.stringify(title));
  }

  try {
    await waitForPanelDom(page, PANEL_READY_MS);
  } catch (domErr) {
    await browser.close();
    fail("Temel panel DOM eksik (#chat-thread veya #panel-conn-badge): " + String(domErr.message || domErr));
  }

  const heroQuery = "landing-hero-smoke-" + Date.now();
  await page.goto(PANEL_URL + "?q=" + encodeURIComponent(heroQuery), {
    waitUntil: "domcontentloaded",
    timeout: PANEL_READY_MS,
  });
  try {
    await waitForPanelDom(page, PANEL_READY_MS);
  } catch (domErr) {
    await browser.close();
    fail("?q= ile panel DOM eksik: " + String(domErr.message || domErr));
  }
  const prefilled = await page.inputValue(CHAT_INPUT_SELECTOR);
  if (prefilled !== heroQuery) {
    await browser.close();
    fail(
      "?q= sohbet alanına yazılmadı; beklenen=" +
        JSON.stringify(heroQuery) +
        " alınan=" +
        JSON.stringify(prefilled),
    );
  }

  await page.goto(PANEL_URL + "?source=desktop", {
    waitUntil: "domcontentloaded",
    timeout: PANEL_READY_MS,
  });
  try {
    await waitForPanelDom(page, PANEL_READY_MS);
  } catch (domErr) {
    await browser.close();
    fail("desktop girişiyle panel DOM eksik: " + String(domErr.message || domErr));
  }
  const desktopContract = await page.evaluate(() => ({
    appMode: document.documentElement.dataset.lumosApp === "true",
    visibleModules: Array.from(document.querySelectorAll('.panel-nav__primary button[data-module]'))
      .filter((el) => getComputedStyle(el).display !== "none")
      .map((el) => el.getAttribute("data-module")),
    headerLogo: document.querySelector(".panel-header-brand img.lumos-mark")?.getAttribute("src") || "",
    modePickerHidden:
      getComputedStyle(document.querySelector(".panel-user-mode-wrap")).display === "none",
  }));
  if (!desktopContract.appMode) {
    await browser.close();
    fail("desktop giriş modu etkinleşmedi");
  }
  if (desktopContract.visibleModules.join(",") !== "sohbet,gorevler,dosyalar") {
    await browser.close();
    fail("desktop görünür modülleri hatalı: " + JSON.stringify(desktopContract.visibleModules));
  }
  if (desktopContract.headerLogo !== "/lumos-skull-mark.svg") {
    await browser.close();
    fail("desktop başlığında Lumos logosu yok");
  }
  if (!desktopContract.modePickerHidden) {
    await browser.close();
    fail("desktop görünümünde teknik mod seçici gizlenmedi");
  }

  const demoShareCount = await page.locator('[data-panel-share-demo="true"]').count();
  if (demoShareCount < 3) {
    await browser.close();
    fail("Medya/Sosyal/Posta demo paylaşım blokları eksik; count=" + demoShareCount);
  }
  const planPendingSnippet = 'panelT("panel.modules.tasks.plan.notPending")';
  const panelHtml = await page.content();
  if (!panelHtml.includes(planPendingSnippet)) {
    await browser.close();
    fail("Görev planı bekleme metni panel HTML'de yok");
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
