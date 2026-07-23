import { chromium } from "playwright";
import { closeServer, startUiDistServer } from "./lib/static-server.mjs";

let server;
let browser;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

try {
  const started = await startUiDistServer();
  server = started.server;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto(`${started.BASE_URL}/cyber/`, { waitUntil: "domcontentloaded" });

  const body = page.locator("body");
  assert((await body.getAttribute("data-demo")) === "off", "Cyber varsayılanı demo kapalı olmalı");
  assert((await body.getAttribute("data-threat-level")) === "0", "Cyber varsayılan tehdit seviyesi 0 olmalı");
  assert((await body.getAttribute("data-threat-state")) === "safe", "Cyber varsayılan durumu safe olmalı");
  assert((await page.locator("[data-demo-only]:visible").count()) === 0, "Demo olayları varsayılan görünmemeli");

  await page.locator("#cyber-demo-toggle").click();
  assert((await body.getAttribute("data-demo")) === "on", "Demo düğmesi demo modunu açmalı");
  assert((await body.getAttribute("data-threat-level")) === "68", "Demo başlangıç seviyesi 68 olmalı");
  assert((await body.getAttribute("data-threat-state")) === "high", "68 puan high sınıfına girmeli");
  assert((await page.locator("[data-demo-only]:visible").count()) === 1, "Demo olay tablosu görünmeli");

  await page.locator("#cyber-threat-range").fill("92");
  assert((await body.getAttribute("data-threat-state")) === "critical", "92 puan critical sınıfına girmeli");
  assert((await page.locator("#cyber-threat-score").textContent()) === "92", "Sayısal tehdit puanı güncellenmeli");
  const flameHeight = await body.evaluate((node) => node.style.getPropertyValue("--lumos-flame-height"));
  assert(flameHeight === "92%", `Alev yüksekliği 92% olmalı; alınan=${flameHeight}`);

  await page.emulateMedia({ reducedMotion: "reduce" });
  const animationName = await page.locator(".threat-flame__tongues").evaluate((node) => getComputedStyle(node).animationName);
  assert(animationName === "none", "Reduce Motion açıkken alev animasyonu durmalı");

  await page.locator("#cyber-demo-toggle").click();
  assert((await body.getAttribute("data-threat-level")) === "0", "Demo kapanınca tehdit seviyesi 0 olmalı");
  assert((await body.getAttribute("data-threat-state")) === "safe", "Demo kapanınca durum safe olmalı");

  console.log("CYBER_THREAT_E2E_RESULT: PASS");
} catch (error) {
  console.error("CYBER_THREAT_E2E_RESULT: FAIL");
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  await closeServer(server);
}
