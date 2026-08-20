/**
 * Observe-slice evidence: one card (bridge.llm) follows dashboard-health-v1.
 * Other nav pills stay static. Domain is not handed to Lumos.
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

const CARD = '[data-health-card="bridge.llm"]';
const GOREVLER_READY = 'button[data-module="gorevler"] .lumos-status-pill--ready';
const ROOT_STATUS = "#panel-root-status";

function fail(reason) {
  console.error("DASHBOARD_HEALTH_BRIDGE_LLM: FAIL");
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
let browser;

async function fulfillHealth(page, status, body) {
  await page.unroute("**/api/bridge/health*").catch(() => {});
  await page.route("**/api/bridge/health*", async (route) => {
    await route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
}

async function abortHealth(page) {
  await page.unroute("**/api/bridge/health*").catch(() => {});
  await page.route("**/api/bridge/health*", async (route) => {
    await route.abort("failed");
  });
}

async function loadWithHealth(page, status, body) {
  await fulfillHealth(page, status, body);
  await page.goto(PANEL_URL, { waitUntil: "domcontentloaded", timeout: PANEL_READY_MS });
  await waitForPanelDom(page, PANEL_READY_MS);
}

async function assertGorevlerUntouched(page, where) {
  const n = await page.locator(GOREVLER_READY).count();
  if (n < 1) fail(`gorevler static ready pill missing (${where})`);
}

try {
  server = await startStaticServer(DIST_DIR, port);
  await waitForServer(PANEL_URL, PANEL_READY_MS);
  // Gerçek "hiç kontrol edilmedi" hali JS'ten ÖNCEKİ sunucu HTML'idir.
  const shippedHtml = await (await fetch(PANEL_URL)).text();
  const shippedPill = (shippedHtml.match(/<span[^>]*data-health-card[^>]*>[\s\S]*?<\/span>/) || [""])[0];
  if (!shippedPill) fail("health card missing from server HTML");
  if (/🟢/.test(shippedPill)) fail("unmeasured card shipped green");
  if (!/data-health-state="unknown"/.test(shippedPill)) {
    fail("card must ship unknown, got: " + shippedPill.slice(0, 160));
  }

  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await abortHealth(page);
  await page.goto(PANEL_URL, { waitUntil: "domcontentloaded", timeout: PANEL_READY_MS });
  await waitForPanelDom(page, PANEL_READY_MS);
  await page.waitForSelector(`${CARD}[data-health-state="unknown"]`, { timeout: PANEL_READY_MS });
  const unmeasured = await page.getAttribute(CARD, "data-health-state");
  if (unmeasured === "healthy") fail("unmeasured/missing probe painted healthy");
  if (unmeasured !== "unknown") fail("unmeasured probe must stay unknown, got " + unmeasured);
  // §4 — ağ hatası da checked_at=null verir, AMA probe çalışmıştır.
  // "hiç kontrol edilmedi" yerine "sonuçsuz kaldı" denmelidir; ölçüm
  // yapılmadı ile ölçüm sonuçsuz kaldı aynı cümle değildir.
  const abortedAria = await page.getAttribute(CARD, "aria-label");
  if (!abortedAria || !/sonuçsuz|inconclusive/i.test(abortedAria)) {
    fail("aborted probe must say the check was inconclusive, aria=" + abortedAria);
  }
  if (/hiç kontrol edilmedi|never checked/i.test(abortedAria)) {
    fail("aborted probe ran; it must not claim never-checked, aria=" + abortedAria);
  }
  await assertGorevlerUntouched(page, "unmeasured");

  await loadWithHealth(page, 200, { status: "ok", llm: true });
  await page.waitForSelector(`${CARD}[data-health-state="healthy"]`, { timeout: PANEL_READY_MS });
  const healthyAria = await page.getAttribute(CARD, "aria-label");
  if (!healthyAria || !/Çalışıyor|Running/.test(healthyAria)) {
    fail("healthy aria missing running text: " + healthyAria);
  }
  const headerHealthy = await page.locator(ROOT_STATUS).innerText();
  await assertGorevlerUntouched(page, "healthy");

  await page.evaluate(() => {
    const api = window.LumosBridgeLlmHealth;
    if (!api || typeof api.paintCard !== "function") {
      throw new Error("LumosBridgeLlmHealth observe helper missing");
    }
    const old = new Date(Date.now() - 121000).toISOString().replace(/\.\d{3}Z$/, "Z");
    api.paintCard({
      id: "bridge.llm",
      state: "healthy",
      checked_at: old,
      ttl_seconds: 120,
      last_known: null,
      reason_code: null,
      evidence: "GET /api/bridge/health → 200",
    });
  });
  await page.waitForSelector(`${CARD}[data-health-state="stale"]`, { timeout: 5000 });
  const staleAria = await page.getAttribute(CARD, "aria-label");
  if (!staleAria || !/doğrulanmadı|Unverified/i.test(staleAria)) {
    fail("stale aria missing unverified text: " + staleAria);
  }
  if (!/çalışıyor|running/i.test(staleAria)) {
    fail("stale must keep last_known in aria: " + staleAria);
  }

  await loadWithHealth(page, 503, { status: "unconfigured" });
  await page.waitForSelector(`${CARD}[data-health-state="not_configured"]`, { timeout: PANEL_READY_MS });
  const notConfiguredAria = await page.getAttribute(CARD, "aria-label");
  if (!notConfiguredAria || !/Kurulmadı|Not configured/.test(notConfiguredAria)) {
    fail("not_configured aria mismatch: " + notConfiguredAria);
  }
  if (/Bilinmiyor|Unknown/.test(notConfiguredAria)) {
    fail("not_configured must not share unknown aria: " + notConfiguredAria);
  }

  await loadWithHealth(page, 500, { error: "controlled_probe_failure" });
  await page.waitForSelector(
    `${CARD}[data-health-state="failed"][data-health-reason="probe_rejected"]`,
    { timeout: PANEL_READY_MS },
  );
  const failedAria = await page.getAttribute(CARD, "aria-label");
  if (!failedAria || !/Çalışmıyor|Not running/.test(failedAria)) {
    fail("failed aria mismatch: " + failedAria);
  }
  const headerFailed = await page.locator(ROOT_STATUS).innerText();
  if (headerFailed !== headerHealthy) {
    fail("card failed must not rewrite #panel-root-status");
  }

  await loadWithHealth(page, 401, { error: "unauthorized" });
  await page.waitForSelector(
    `${CARD}[data-health-state="unknown"][data-health-reason="unauthorized"]`,
    { timeout: PANEL_READY_MS },
  );

  // §4 dar tanım — aracı/erişim belirsizliği arıza suçlaması değildir.
  for (const gwStatus of [502, 504]) {
    await loadWithHealth(page, gwStatus, { error: "gateway" });
    await page.waitForSelector(
      `${CARD}[data-health-state="unknown"][data-health-reason="probe_inconclusive"]`,
      { timeout: PANEL_READY_MS },
    );
    const gwState = await page.getAttribute(CARD, "data-health-state");
    if (gwState === "failed") fail(gwStatus + " must never accuse a fault");
    const gwAria = await page.getAttribute(CARD, "aria-label");
    if (!gwAria || !/sonuçsuz|inconclusive/i.test(gwAria)) {
      fail(gwStatus + " aria must say the check was inconclusive: " + gwAria);
    }
    if (/hiç kontrol edilmedi|never checked/i.test(gwAria)) {
      fail(gwStatus + " must not claim the card was never checked: " + gwAria);
    }
  }

  // Gövdesiz 503: ne arıza ne 'kurulmamış' hükmü.
  await loadWithHealth(page, 503, { error: "edge" });
  await page.waitForSelector(
    `${CARD}[data-health-state="unknown"][data-health-reason="probe_inconclusive"]`,
    { timeout: PANEL_READY_MS },
  );

  await assertGorevlerUntouched(page, "end");
  const extraCards = await page.locator("[data-health-card]").count();
  if (extraCards !== 1) fail("expected exactly one health card, got " + extraCards);

  await browser.close();
  await closeServer(server);
  console.log("DASHBOARD_HEALTH_BRIDGE_LLM: PASS");
  console.log(
    "loop: abort=unknown 200=healthy stale=last_known 503+unconfigured=not_configured 500=failed 502/504/bare-503=unknown(probe_inconclusive) 401=unknown; header unchanged; other pills untouched",
  );
} catch (err) {
  if (browser) await browser.close().catch(() => {});
  if (server) await closeServer(server).catch(() => {});
  fail(String(err && err.stack ? err.stack : err));
}
