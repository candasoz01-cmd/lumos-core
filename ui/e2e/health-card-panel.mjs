/**
 * dashboard-health-v1 — `bridge.llm` kartının uçtan uca doğrulaması.
 * Sözleşme: docs/contracts/dashboard-health-v1.md
 *
 * Zincir: literal backend state → sözleşme → UI → freshness → test.
 * `/api/bridge/health` gerçek cevapları taklit edilerek her yol sürülür;
 * `failed` için kontrollü probe-failure senaryosu kullanılır (dış servis yok).
 *
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

const CARD = '[data-health-card="bridge.llm"]';
const HEADER_BADGE = "#panel-conn-badge";

let failures = 0;
let checks = 0;

function ok(cond, label) {
  checks += 1;
  if (!cond) {
    failures += 1;
    console.error(`  ✗ ${label}`);
  }
}
function eq(actual, expected, label) {
  ok(actual === expected, `${label} — beklenen ${JSON.stringify(expected)}, gelen ${JSON.stringify(actual)}`);
}
function fail(reason) {
  console.error("HEALTH_CARD_RESULT: FAIL");
  console.error(reason);
  process.exit(1);
}

try {
  assertPanelDistBuilt();
} catch (err) {
  fail(String((err && err.message) || err));
}

const { port, PANEL_URL } = getDefaultServerTargets();
let server;
let browser;

/** Sunucudan gelen HAM HTML — JS hiç çalışmasa ne görünüyor? */
async function shippedPillHtml() {
  const res = await fetch(PANEL_URL);
  const html = await res.text();
  const m = html.match(/<span[^>]*data-health-card="bridge\.llm"[^>]*>[\s\S]*?<\/span>/);
  return m ? m[0] : "";
}

async function readCard(page) {
  return page.$eval(CARD, (el) => ({
    state: el.getAttribute("data-health-state"),
    tone: el.getAttribute("data-health-tone"),
    reason: el.getAttribute("data-health-reason"),
    text: (el.textContent || "").trim(),
    aria: el.getAttribute("aria-label") || "",
  }));
}

/** Uç cevabını sabitleyip kartı yeniden ölçtür. */
async function probeWith(page, handler) {
  await page.route("**/api/bridge/health", handler);
  await page.click(CARD);
  await page.waitForTimeout(400);
  const card = await readCard(page);
  await page.unroute("**/api/bridge/health");
  return card;
}

const json = (status, body) => (route) =>
  route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

try {
  server = await startStaticServer(DIST_DIR, port);
  await waitForServer(PANEL_URL);

  // ── §8.1 — sunucudan gelen ilk hal ölçülmemiş; yeşil OLAMAZ ──────────────
  console.log("§8.1 ölçülmeyen şey yeşil gösterilmez (JS öncesi ham HTML)");
  const shipped = await shippedPillHtml();
  ok(shipped.length > 0, "kart sunucu HTML'inde var");
  ok(shipped.includes('data-health-state="unknown"'), "ham HTML'de kart unknown başlıyor");
  ok(!shipped.includes("🟢"), "ham HTML'de yeşil glif yok");
  ok(!/\d+\s*dk önce/.test(shipped), "ham HTML'de sahte göreli zaman yok");

  browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(PANEL_URL, { waitUntil: "domcontentloaded" });
  await waitForPanelDom(page, PANEL_READY_MS);

  // ── §4 türetme → UI ──────────────────────────────────────────────────────
  console.log("§4 backend state → sözleşme → UI");

  const healthy = await probeWith(page, json(200, { status: "ok", llm: true, mode: "hosted_secure" }));
  eq(healthy.state, "healthy", "200 ok → healthy");
  eq(healthy.tone, "positive", "healthy → positive ton");
  ok(healthy.text.startsWith("🟢"), "healthy → 🟢 glifi");

  const notConfigured = await probeWith(page, json(503, { status: "unconfigured" }));
  eq(notConfigured.state, "not_configured", "503 unconfigured → not_configured");
  eq(notConfigured.reason, "unconfigured", "reason_code unconfigured");
  ok(notConfigured.text.startsWith("⚪"), "not_configured → ⚪ glifi");

  // §6 — 401 kart durumu değil: unknown olur, failed OLMAZ
  const unauthorized = await probeWith(page, json(401, { error: "unauthorized" }));
  eq(unauthorized.state, "unknown", "401 → unknown");
  ok(unauthorized.state !== "failed", "401 asla failed üretmez");
  eq(unauthorized.reason, "unauthorized", "reason_code unauthorized");

  // failed — kontrollü probe-failure (dış servis yok)
  const failedCard = await probeWith(page, json(500, { error: "bridge_error" }));
  eq(failedCard.state, "failed", "5xx → failed");
  eq(failedCard.tone, "negative", "failed → negative ton");
  ok(failedCard.text.startsWith("🔴"), "failed → 🔴 glifi");

  // §4 dar tanım — aracı hatası arıza suçlaması değildir
  const gateway = await probeWith(page, json(502, { error: "bad_gateway" }));
  eq(gateway.state, "unknown", "502 → unknown (failed DEĞİL)");
  eq(gateway.reason, "probe_inconclusive", "502 → probe_inconclusive");
  ok(gateway.text.startsWith("◌"), "502 → unknown glifi");

  // ağ hatası → unknown (bilgi yokluğu)
  const unreachable = await probeWith(page, (route) => route.abort("failed"));
  eq(unreachable.state, "unknown", "ağ hatası → unknown");
  eq(unreachable.reason, "probe_unreachable", "reason_code probe_unreachable");

  // beklenmeyen gövde → healthy DEĞİL
  const weird = await probeWith(page, json(200, { status: "belki" }));
  ok(weird.state !== "healthy", "beklenmeyen gövde asla healthy olmaz");
  eq(weird.reason, "unmapped_value", "reason_code unmapped_value");

  // ── §9.3 — not_configured ile unknown görsel olarak ezilmez ──────────────
  console.log("§9.3 not_configured ≠ unknown (görsel + erişilebilir)");
  ok(notConfigured.text.slice(0, 2) !== unauthorized.text.slice(0, 2), "glifleri farklı");
  ok(notConfigured.tone !== unauthorized.tone, "renk rolleri farklı");
  ok(notConfigured.aria !== unauthorized.aria, "erişilebilir etiketleri farklı");

  // ── §3.4 — null freshness göreli zamana çevrilmez ────────────────────────
  console.log("§3.4 null freshness sahte zamana çevrilmez");
  // Ölçüm YAPILMADI ile ölçüm SONUÇ VERMEDİ ayrımı — ikisi de checked_at=null.
  ok(/sonuç vermedi/.test(unauthorized.aria), "401: 'sonuç vermedi' der ('hiç kontrol edilmedi' DEĞİL)");
  ok(!/hiç kontrol edilmedi/.test(unauthorized.aria), "401 kartı yanlışlıkla 'hiç kontrol edilmedi' demez");
  ok(/sonuç vermedi/.test(unreachable.aria), "ağ hatası: 'sonuç vermedi' der");
  ok(!/\d+\s*dk önce/.test(unauthorized.aria), "401 kartında göreli zaman yok");
  ok(!/\d+\s*dk önce/.test(unreachable.aria), "ağ hatası kartında göreli zaman yok");
  ok(/kontrol edildi/.test(healthy.aria), "healthy kartı gerçek ölçüm zamanını söyler");

  // ── §3.1 / §9.7 — freshness UI'da: yeni probe olmadan stale'e geçiş ──────
  // Zamanı ileri sar (yalnız sayfa içinde), tick'in kartı yaşlandırmasını bekle.
  console.log("§3.1 freshness → UI'da stale (yeni probe yok)");
  await probeWith(page, json(200, { status: "ok" }));
  const ttlMs = await page.$eval(CARD, () => 120 * 1000);
  await page.evaluate((skip) => {
    const realNow = Date.now.bind(Date);
    Date.now = () => realNow() + skip;
  }, ttlMs + 5000);
  await page.waitForFunction(
    (sel) => document.querySelector(sel)?.getAttribute("data-health-state") === "stale",
    CARD,
    { timeout: 25000 },
  );
  const staleCard = await readCard(page);
  eq(staleCard.state, "stale", "bütçe aşımı → UI stale gösterir");
  eq(staleCard.tone, "warning", "stale → warning ton");
  eq(staleCard.reason, "freshness_expired", "reason_code freshness_expired");
  ok(staleCard.text.startsWith("🟡"), "stale → 🟡 glifi");
  ok(/son bilinen: çalışıyor/.test(staleCard.aria), "stale son bilinen sonucu korur");
  ok(/doğrulanmadı/i.test(staleCard.aria), "stale metni doğrulanmama süresini söyler");
  await page.evaluate(() => { /* zaman yamasını bırak */ });

  // ── §9.5 / §6 — kart failed iken başlık DEĞİŞMEZ ─────────────────────────
  console.log("§9.5 başlık kart sağlığından türetilmez");
  const headerExists = (await page.$(HEADER_BADGE)) !== null;
  if (headerExists) {
    const before = await page.$eval(HEADER_BADGE, (el) => el.getAttribute("data-state"));
    await probeWith(page, json(500, { error: "bridge_error" }));
    const after = await page.$eval(HEADER_BADGE, (el) => el.getAttribute("data-state"));
    eq(after, before, "kart failed olduğunda başlık rozeti değişmedi");
  } else {
    console.log("  (başlık rozeti bu görünümde yok — kontrol atlandı)");
  }

  console.log("");
  if (failures > 0) {
    fail(`${failures}/${checks} kontrol başarısız`);
  }
  console.log(`HEALTH_CARD_RESULT: PASS (${checks} kontrol)`);
} catch (err) {
  fail(String((err && err.stack) || err));
} finally {
  if (browser) await browser.close().catch(() => {});
  if (server) await closeServer(server).catch(() => {});
}
