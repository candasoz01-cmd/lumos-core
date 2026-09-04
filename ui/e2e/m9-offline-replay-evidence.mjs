/**
 * TD-25 KANIT dosyası — çevrimdışı panel mutasyonunun bugünkü replay davranışı.
 *
 * DİKKAT: Bu bir hedef davranış sözleşmesi DEĞİLDİR. Açık bir borcun (TD-25)
 * bugün nasıl davrandığını kayda geçirir. Buradaki assertion'lar "olması
 * gereken"i değil "şu an olan"ı sabitler; borç kapatıldığında güncellenmeleri
 * beklenir. Bu yüzden CI'a veya npm script'ine BAĞLANMAZ; elle koşulur.
 *
 * TD-25 iddiası: çevrimdışı yazılan bir mutasyon sunucu policy'sinden ANCAK
 * replay anında geçer; sunucu reddederse yerel kayıt kullanıcıda kalır ve
 * ayrışma kullanıcıya bildirilmez. Bu bir yetki aşımı DEĞİL, tutarlılık ve
 * görünürlük borcudur.
 *
 * Doğrulanan üç sonuç:
 *
 *  A) CONFIRMATION AÇIK + sunucu erişilemez
 *     → fail-closed: yerel kayıt yok, kuyruk yok, replay yok, sunucuda yok.
 *
 *  B) CONFIRMATION KAPALI (varsayılan) + izin veren sunucu
 *     → çevrimdışı yerel yazılır + kuyruğa girer; bağlantı dönünce replay
 *       HTTP 200 alır, sunucuya yazılır, kuyruk boşalır.
 *
 *  C) CONFIRMATION KAPALI + REDDEDEN sunucu (LUMOS_MODE=offline, rapor)
 *     → replay HTTP 409 alır, sunucuya YAZILMAZ, yerel kayıt kullanıcıda
 *       KALIR ve retry sayacı artar. Policy replay'de gerçekten çalışır.
 *
 * Ayrıca (C) sırasında `#gorevler-sync-badge` ölçülür.
 *
 *   ┌─ BİLİNÇLİ BORÇ ASSERTION'I (TD-25) ────────────────────────────────┐
 *   │ Badge'in reddedilen replay'de GİZLİ kaldığı assert edilir.        │
 *   │ Bu istenen davranış DEĞİL, bugünkü davranıştır: badge yalnızca    │
 *   │ `shouldSkipGorevlerTasksApi()`'ye bağlı (PanelRuntime.astro:1717) │
 *   │ ve `scheduleEvidenceQueueFlush` hatayı `.catch(() => {})` ile     │
 *   │ yutuyor (:3288). TD-25 kapatıldığında bu assertion "uyarı VAR"    │
 *   │ olarak ÇEVRİLMELİDİR; testin yeşil kalması borcun kapandığı       │
 *   │ anlamına gelmez.                                                   │
 *   └────────────────────────────────────────────────────────────────────┘
 *
 * Kullanım: node e2e/m9-offline-replay-evidence.mjs
 */
import { spawn } from "node:child_process";
import { chromium } from "playwright";
import {
  clearPanelGorevlerStorage,
  clickModule,
  PACKAGE_FLOW_MS,
  patchPolicyAllowTasks,
  sendChatMessage,
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
  PY_SCRIPT,
  startTasksServer,
  stopTasksServer,
  waitForTasksApi,
} from "./lib/tasks-server.mjs";

const PENDING_OPS_LS_KEY = "lumos_panel_evidence_pending_ops_v1";
const GOREVLER_LS_KEY = "lumos_panel_gorevler_list_v1";

/* Koşullu bekleme sınırları — sonsuz bekleme yok, hepsi timeout'lu. */
const WAIT_TIMEOUT_MS = 25000;
const WAIT_POLL_MS = 150;
const STABLE_FOR_MS = 1200;

/* Port çakışmasını önlemek için pid tabanlı taban (repo deseni). */
const PORT_BASE = 24000 + (process.pid % 900);
const TASKS_PORT_BASE = 34000 + (process.pid % 900);

const failures = [];
const lines = [];

function log(s = "") {
  lines.push(s);
  console.log(s);
}

function check(name, actual, expected) {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  log((ok ? "  ok   " : "  FAIL ") + name
      + "  →  " + JSON.stringify(actual)
      + (ok ? "" : "   (beklenen: " + JSON.stringify(expected) + ")"));
  if (!ok) failures.push(name + ": " + JSON.stringify(actual) + " ≠ " + JSON.stringify(expected));
  return ok;
}

/* Bekleme hataları (waitFor / waitUntilStable zaman aşımı) sessizce yutulmaz:
   temiz bir FAIL satırı basılır ve koşum exit 1 ile biter. */
function bailOut(err) {
  console.error("M9_OFFLINE_REPLAY_EVIDENCE: FAIL");
  console.error("  " + String((err && err.message) || err));
  process.exit(1);
}
process.on("unhandledRejection", bailOut);
process.on("uncaughtException", bailOut);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** Koşul sağlanana kadar bekler; süre dolarsa hata atar (sonsuz bekleme yok). */
async function waitFor(label, pred, timeoutMs = WAIT_TIMEOUT_MS) {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    if (await pred()) return;
    if (Date.now() >= deadline) {
      throw new Error("waitFor zaman aşımı (" + timeoutMs + "ms): " + label);
    }
    await sleep(WAIT_POLL_MS);
  }
}

/**
 * Gözlenen değer STABLE_FOR_MS boyunca değişmeyene kadar bekler.
 * "Bir şeyin OLMADIĞINI" doğrulayan senaryolar (A'nın replay fazı) için
 * gerekli: beklenecek pozitif olay yok, durumun oturması gözlenir.
 *
 * Süre dolarsa HATA ATAR. Stabilize olmamış bir ölçüm kanıt sayılmaz:
 * hâlâ değişen bir durumdan okunan değer, koşumun o anki zamanlamasını
 * yansıtır, sistemin davranışını değil. Son değere düşüp devam etmek
 * kanıtı sessizce güvenilmez kılardı.
 */
async function waitUntilStable(label, read, timeoutMs = WAIT_TIMEOUT_MS) {
  const deadline = Date.now() + timeoutMs;
  let last = JSON.stringify(await read());
  let stableSince = Date.now();
  for (;;) {
    await sleep(WAIT_POLL_MS);
    const now = JSON.stringify(await read());
    if (now !== last) {
      last = now;
      stableSince = Date.now();
    } else if (Date.now() - stableSince >= STABLE_FOR_MS) {
      return JSON.parse(now);
    }
    if (Date.now() >= deadline) {
      throw new Error(
        "waitUntilStable zaman aşımı (" + timeoutMs + "ms): " + label
        + " — ölçüm " + STABLE_FOR_MS + "ms boyunca sabitlenmedi; son gözlenen değer: "
        + now + ". Stabil olmayan ölçüm kanıt kabul edilmez.",
      );
    }
  }
}

/** Sunucu policy'sinin mutasyonu reddettiği env. */
function startDenyingServer(tmpBaseDir, portStr) {
  return spawn("python3", [PY_SCRIPT], {
    env: Object.assign({}, process.env, {
      LUMOS_BASE_DIR: tmpBaseDir,
      LUMOS_PANEL_TASKS_PORT: String(portStr),
      LUMOS_PANEL_TASKS_HOST: "127.0.0.1",
      LUMOS_MODE: "offline",
      LUMOS_PROFILE: "rapor",
      LUMOS_SESSION_UNLOCKED: "false",
    }),
    stdio: "pipe",
  });
}

/** Tek senaryo koşucusu. Deterministik: sabit bekleme yerine durum bekler. */
async function scenario(opts) {
  const { title, confirmationEnabled, offset, restartWith } = opts;
  log("");
  log("── " + title + " " + "─".repeat(Math.max(0, 66 - title.length)));

  const port = String(PORT_BASE + offset);
  const tasksPort = String(TASKS_PORT_BASE + offset);
  const { PANEL_URL } = getDefaultServerTargets(port);
  const apiBase = buildTasksApiBase(tasksPort);
  const tmpBase = createTempLumosBase("lumos-td25-");

  let py = startTasksServer(tmpBase, tasksPort, { confirmationEnabled });
  const staticServer = await startStaticServer(DIST_DIR, port);
  await waitForTasksApi(apiBase, 20000);
  await waitForServer(PANEL_URL, PACKAGE_FLOW_MS);

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.addInitScript((b) => { window.LUMOS_PANEL_TASKS_API_BASE = b; }, apiBase);

  let phase = "setup";
  const posts = [];
  page.on("request", (r) => {
    if (!r.url().startsWith(apiBase) || r.method() !== "POST") return;
    let body = null;
    try { body = r.postData() ? JSON.parse(r.postData()) : null; } catch { body = r.postData(); }
    posts.push({ phase, path: r.url().slice(apiBase.length), body, status: null });
  });
  page.on("response", (res) => {
    if (!res.url().startsWith(apiBase)) return;
    const hit = posts.find((p) => p.status === null && res.url().endsWith(p.path));
    if (hit) hit.status = res.status();
  });
  page.on("requestfailed", (r) => {
    const hit = posts.find((p) => p.status === null && r.url().endsWith(p.path));
    if (hit) hit.status = "NETFAIL";
  });

  const readLocal = () => page.evaluate((k) => {
    try { return JSON.parse(localStorage.getItem(k) || "[]"); } catch { return []; }
  }, GOREVLER_LS_KEY);
  const readQueue = () => page.evaluate((k) => {
    try { return JSON.parse(localStorage.getItem(k) || "[]"); } catch { return []; }
  }, PENDING_OPS_LS_KEY);

  const mark = "td25-" + offset + "-" + Date.now();
  let out = null;

  try {
    await page.goto(PANEL_URL, { waitUntil: "domcontentloaded", timeout: PACKAGE_FLOW_MS });
    await waitForPanelDom(page, PACKAGE_FLOW_MS);
    await patchPolicyAllowTasks(page, { userMode: "full" });
    await clearPanelGorevlerStorage(page);
    await page.reload({ waitUntil: "domcontentloaded", timeout: PACKAGE_FLOW_MS });
    await waitForPanelDom(page, PACKAGE_FLOW_MS);
    await patchPolicyAllowTasks(page, { userMode: "full" });
    await clickModule(page, "gorevler", PACKAGE_FLOW_MS);

    /* Onay modali çıkarsa otomatik onayla — ölçülen iddia "insan onayladı"
       değil, "replay ne gönderiyor / ne kalıyor". */
    const autoApprove = setInterval(() => {
      page.evaluate(() => {
        const b = document.getElementById("lumos-confirm-approve");
        if (b && b.offsetParent !== null) b.click();
      }).catch(() => {});
    }, 200);

    // ── çevrimdışı ────────────────────────────────────────────────────────
    phase = "offline";
    stopTasksServer(py);
    py = null;
    await page.waitForFunction(
      (b) => fetch(b + "/tasks").then(() => false).catch(() => true),
      apiBase,
      { timeout: PACKAGE_FLOW_MS },
    );

    await clickModule(page, "sohbet", PACKAGE_FLOW_MS);
    await sendChatMessage(page, "görev oluştur " + mark);

    /* Çevrimdışı faz oturdu mu? Önce gözlenebilir olayı bekle: panelin
       denediği en az bir istek sonuçlansın (ağ hatası da bir sonuçtur).
       Ardından yerel kayıt + kuyruk çifti değişmez olana kadar bekle. */
    await waitFor(
      "çevrimdışı: en az bir POST sonuçlandı",
      () => posts.some((p) => p.phase === "offline" && p.status !== null),
    );
    await waitUntilStable("çevrimdışı yerel/kuyruk", async () => ({
      local: (await readLocal()).length,
      queue: (await readQueue()).length,
    }));
    clearInterval(autoApprove);

    const localOffline = await readLocal();
    const queueOffline = await readQueue();
    const offlinePosts = posts.filter((p) => p.phase === "offline");

    log("  [çevrimdışı] denenen POST: "
        + (offlinePosts.map((p) => p.path + "→" + p.status).join(", ") || "yok"));

    // ── sunucu geri geliyor ───────────────────────────────────────────────
    phase = "replay";
    py = restartWith === "deny"
      ? startDenyingServer(tmpBase, tasksPort)
      : startTasksServer(tmpBase, tasksPort, { confirmationEnabled });
    await waitForTasksApi(apiBase, 20000);
    await page.evaluate(() => window.dispatchEvent(new Event("online")));
    await clickModule(page, "gorevler", PACKAGE_FLOW_MS);

    /* Replay fazı: senaryoya özgü POZİTİF koşulu bekle. A'da beklenecek bir
       olay yok (hiç POST olmamalı) — orada yalnız durum stabilizasyonu var. */
    if (opts.expectReplayPost) {
      await waitFor(
        "replay: /tasks POST'u sonuçlandı",
        () => posts.some((p) => p.phase === "replay" && p.path === "/tasks" && p.status !== null),
      );
    }
    await waitUntilStable("replay yerel/kuyruk/deneme", async () => {
      const q = await readQueue();
      return {
        local: (await readLocal()).length,
        queue: q.length,
        attempts: q.map((x) => Number(x.attempts) || 0),
        posts: posts.filter((p) => p.phase === "replay").map((p) => p.path + ":" + p.status),
      };
    });

    const replayPosts = posts.filter((p) => p.phase === "replay" && p.path === "/tasks");
    const doc = await fetchTasksDoc(apiBase);
    const serverTitles = (doc.tasks || []).map((t) => String(t.title || "").trim());
    const localAfter = await readLocal();
    const queueAfter = await readQueue();
    const listText = await page.locator("#gorevler-list").innerText().catch(() => "");
    const badge = await page.evaluate(() => {
      const el = document.getElementById("gorevler-sync-badge");
      if (!el) return { exists: false };
      return {
        exists: true,
        hidden: el.hidden === true,
        visible: !!(el.offsetWidth || el.offsetHeight),
        text: (el.textContent || "").trim(),
      };
    });

    out = {
      mark,
      offline: {
        localCount: localOffline.length,
        queueCount: queueOffline.length,
        posts: offlinePosts.map((p) => ({ path: p.path, status: p.status })),
      },
      replay: {
        posts: replayPosts.map((p) => ({
          path: p.path,
          status: p.status,
          hasConfirmationId: !!(p.body && p.body.confirmation_id),
        })),
        serverHasMark: serverTitles.includes(mark),
        serverCount: serverTitles.length,
        localCount: localAfter.length,
        queueCount: queueAfter.length,
        attempts: queueAfter.map((q) => Number(q.attempts) || 0),
        visibleToUser: listText.includes(mark),
        badge,
      },
    };
  } finally {
    await browser.close();
    stopTasksServer(py);
    await closeServer(staticServer);
  }
  return out;
}

assertPanelDistBuilt();

log("TD-25 — çevrimdışı mutasyon replay kanıt koşumu");
log("=".repeat(72));

// ── A ───────────────────────────────────────────────────────────────────────
const a = await scenario({
  title: "A) CONFIRMATION AÇIK + sunucu erişilemez → fail-closed",
  confirmationEnabled: true,
  offset: 0,
  expectReplayPost: false,   // beklenen: hiç POST olmamalı
});
check("A/çevrimdışı: yerel kayıt oluşmaz", a.offline.localCount, 0);
check("A/çevrimdışı: kuyruk oluşmaz", a.offline.queueCount, 0);
check("A/çevrimdışı: onay isteği ağda başarısız",
      a.offline.posts.map((p) => p.path + ":" + p.status), ["/lumos-confirm/request:NETFAIL"]);
check("A/replay: hiç /tasks POST'u yok", a.replay.posts.length, 0);
check("A/sunucu: görev yok", a.replay.serverCount, 0);

// ── B ───────────────────────────────────────────────────────────────────────
const b = await scenario({
  title: "B) CONFIRMATION KAPALI + izin veren sunucu → replay 200, kuyruk boşalır",
  confirmationEnabled: false,
  offset: 1,
  expectReplayPost: true,
});
check("B/çevrimdışı: yerel kayıt oluşur", b.offline.localCount, 1);
check("B/çevrimdışı: kuyruğa girer", b.offline.queueCount, 1);
check("B/replay: tek POST /tasks, HTTP 200",
      b.replay.posts.map((p) => p.path + ":" + p.status), ["/tasks:200"]);
check("B/replay: confirmation_id taşımaz",
      b.replay.posts.map((p) => p.hasConfirmationId), [false]);
check("B/sunucu: görev yazıldı", b.replay.serverHasMark, true);
check("B/kuyruk: boşaldı", b.replay.queueCount, 0);

// ── C ───────────────────────────────────────────────────────────────────────
const c = await scenario({
  title: "C) CONFIRMATION KAPALI + REDDEDEN sunucu → replay 409, ayrışma kalır",
  confirmationEnabled: false,
  offset: 2,
  restartWith: "deny",
  expectReplayPost: true,
});
check("C/çevrimdışı: yerel kayıt oluşur", c.offline.localCount, 1);
check("C/replay: POST /tasks HTTP 409",
      c.replay.posts.map((p) => p.path + ":" + p.status), ["/tasks:409"]);
check("C/sunucu: görev YAZILMAZ (policy replay'de çalışır)", c.replay.serverHasMark, false);
check("C/sunucu: görev sayısı 0", c.replay.serverCount, 0);
check("C/yerel: kayıt kullanıcıda KALIR", c.replay.localCount, 1);
check("C/panel: kullanıcı görevi görmeye devam eder", c.replay.visibleToUser, true);
check("C/kuyruk: kayıt durur", c.replay.queueCount, 1);
check("C/kuyruk: retry sayacı arttı", c.replay.attempts.every((n) => n >= 1), true);

// ── C: sync badge — BİLİNÇLİ BORÇ ASSERTION'I (TD-25) ───────────────────────
log("");
log("  ── sync badge ölçümü (TD-25 borç assertion'ı) ──");
log("  badge DOM'da: " + JSON.stringify(c.replay.badge));
check("C/badge: DOM'da var", c.replay.badge.exists, true);
/* Bugünkü davranış: badge YALNIZCA shouldSkipGorevlerTasksApi() ile sürülüyor
   (PanelRuntime.astro:1717); reddedilen replay ile ilgisi yok ve
   scheduleEvidenceQueueFlush hatayı yutuyor (:3288). Bu yüzden gizli kalır.
   TD-25 kapandığında AŞAĞIDAKİ İKİ SATIR "uyarı VAR" olarak çevrilmelidir. */
check("C/badge: kullanıcıya GÖRÜNMÜYOR (bilinçli borç — TD-25)",
      c.replay.badge.visible, false);
check("C/badge: hidden (bilinçli borç — TD-25)", c.replay.badge.hidden, true);
log("  ⚠ Reddedilen replay kullanıcıya HİÇBİR görünür uyarı üretmiyor.");
log("    Bu test bunu doğruluyor; borç TD-25'te AÇIK kalır.");

// ── sonuç ───────────────────────────────────────────────────────────────────
log("");
log("=".repeat(72));
if (failures.length) {
  log("M9_OFFLINE_REPLAY_EVIDENCE: FAIL (" + failures.length + ")");
  failures.forEach((f) => log("  - " + f));
  process.exit(1);
}
log("M9_OFFLINE_REPLAY_EVIDENCE: PASS");
log("surface: ui/dist static + panel_tasks_server (gerçek REST)");
log("not: 'badge görünmüyor' assertion'ı bilinçli borç kaydıdır, hedef davranış değildir.");
process.exit(0);
