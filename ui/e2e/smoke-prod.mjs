/**
 * A3 prod smoke — read-only HTTPS check for live /panel (default welockai.com).
 * No writes, secrets, or bridge tokens. Override: LUMOS_PROD_PANEL_URL.
 */
import { chromium } from "playwright";
import { waitForPanelDom, PANEL_READY_MS } from "./lib/panel-helpers.mjs";

const PROD_URL = (process.env.LUMOS_PROD_PANEL_URL || "https://welockai.com/panel").replace(/\/$/, "");

function fail(reason) {
  console.error("SMOKE_PROD_RESULT: FAIL");
  console.error(reason);
  process.exit(1);
}

const consoleErrors = [];

function isIgnorableConsoleError(text) {
  const t = String(text || "");
  if (/ERR_CONNECTION_REFUSED|127\.0\.0\.1|localhost|8766|503/.test(t)) return true;
  if (/Failed to load resource/i.test(t)) return true;
  return false;
}

try {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.on("pageerror", (err) => consoleErrors.push(String(err)));
  page.on("console", (msg) => {
    if (msg.type() === "error" && !isIgnorableConsoleError(msg.text())) {
      consoleErrors.push(msg.text());
    }
  });

  const resp = await page.goto(PROD_URL, { waitUntil: "domcontentloaded", timeout: PANEL_READY_MS });
  if (!resp || resp.status() !== 200) {
    await browser.close();
    fail("HTTP status not 200: " + (resp ? resp.status() : "null"));
  }

  const title = await page.title();
  if (!title.includes("Lumos Panel")) {
    await browser.close();
    fail("Beklenen başlık yok; title=" + JSON.stringify(title));
  }

  try {
    await waitForPanelDom(page, PANEL_READY_MS);
  } catch (domErr) {
    await browser.close();
    fail("Temel panel DOM eksik: " + String(domErr.message || domErr));
  }

  if (consoleErrors.length) {
    await browser.close();
    fail("Kırıcı console.error: " + consoleErrors.slice(0, 3).join(" | "));
  }

  await browser.close();
  console.log("SMOKE_PROD_RESULT: PASS");
  console.log("URL:", PROD_URL);
} catch (err) {
  fail(String(err && err.message ? err.message : err));
}
