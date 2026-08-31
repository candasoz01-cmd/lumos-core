/**
 * WebMCP panel tool E2E — 2026-08-25 sonrası eklendi (WebMCP Challenge dilimi).
 *
 * Doğrulanan sözleşme:
 *  1. Panel yüklendiğinde 3 tool `document.modelContext.registerTool()` ile kaydedilir.
 *  2. OKUMA İZNİ: `lumos-list-tasks` kullanıcı görev tahtasını paylaşmayı açıkça
 *     onaylamadan HİÇBİR görev içeriği döndürmez; ajana `read_consent_required`
 *     reddi verilir. İzin verilince içerik gelir, panelde görünür duruma geçer,
 *     "İzni geri al" ile kapatılınca okuma yine reddedilir.
 *  3. ONAY EKRANI: `lumos-propose-task` onay diyaloğu, yazılacak HER alanı
 *     çağrıdaki gerçek değeriyle gösterir (başlık, öncelik, zaman, durum,
 *     kaynak). Verilmeyen alan "belirtilmedi (varsayılan: …)" olarak yazılır.
 *  4. "Vazgeç" seçilirse HİÇBİR görev yazılmaz (onay kapısı atlanamaz).
 *  5. Aynı tool "Onayla" ile gerçekten görev oluşturur ve panelde görünür.
 *  6. `lumos-complete-task` yine onay kapısından geçer ve durum değişikliğini
 *     (neyi neye çevirdiğini) ekranda yazar.
 *
 * Not: Headless Chromium'da tarayıcının WebMCP uygulaması yok. Test yalnızca
 * TARAYICI TARAFINI (agent harness) taklit eder — sayfanın kendi kayıt ve
 * execute kodu gerçek olarak çalışır. Native WebMCP doğrulaması ayrı yapılır;
 * bkz. docs/webmcp-challenge-2026.md.
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

const EXPECTED_TOOLS = ["lumos-list-tasks", "lumos-propose-task", "lumos-complete-task"];

function fail(reason) {
  console.error("WEBMCP_PANEL_E2E_RESULT: FAIL");
  console.error(reason);
  process.exit(1);
}

/** Onay beklerken askıda kalan tool çağrısı: reddi yutup sonuca çevirir. */
function pending(promise) {
  return promise.catch((e) => ({ __err: String((e && e.message) || e) }));
}

function assertNoToolError(label, result) {
  if (result && result.__err) fail(label + " tool çağrısı hata verdi: " + result.__err);
}

/** Tarayıcı tarafı taklidi: document.modelContext (registerTool/getTools/executeTool). */
const AGENT_HARNESS = function () {
  const registry = new Map();
  const modelContext = {
    registerTool(tool) {
      if (!tool || typeof tool.name !== "string" || typeof tool.execute !== "function") {
        return Promise.reject(new TypeError("invalid tool"));
      }
      registry.set(tool.name, tool);
      return Promise.resolve();
    },
    getTools() {
      return Promise.resolve(
        Array.from(registry.values()).map(function (t) {
          return {
            name: t.name,
            description: t.description,
            inputSchema: t.inputSchema,
            origin: location.origin,
          };
        }),
      );
    },
    executeTool(tool, args) {
      const name = typeof tool === "string" ? tool : tool && tool.name;
      const entry = registry.get(name);
      if (!entry) return Promise.reject(new Error("unknown tool: " + name));
      return Promise.resolve(entry.execute(args || {}));
    },
  };
  Object.defineProperty(document, "modelContext", {
    value: modelContext,
    configurable: true,
  });
  // Panel yerel modda kalsın: tasks REST yok, mutasyon yerel listeye yazılır.
  window.LUMOS_PANEL_TASKS_API_BASE = false;
};

/** Ajan tool çağrısı: sonucu JSON payload'a çevirir. */
const CALL_TOOL = function (payload) {
  return document.modelContext
    .executeTool(payload.name, payload.args)
    .then(function (res) {
      const text = res && res.content && res.content[0] ? res.content[0].text : "";
      return JSON.parse(text);
    });
};

/** Onay diyaloğunun "Yazılacak alanlar" bölümünü ekrandan aynen okur. */
const READ_CONFIRM_FIELDS = function () {
  const wrap = document.getElementById("lumos-confirm-preview-fields-wrap");
  const dl = document.getElementById("lumos-confirm-preview-fields");
  if (!wrap || !dl) return { present: false, hidden: true, byKey: {}, order: [] };
  const byKey = {};
  const order = [];
  const nodes = Array.prototype.slice.call(dl.children);
  for (let i = 0; i + 1 < nodes.length; i += 2) {
    if (nodes[i].tagName !== "DT" || nodes[i + 1].tagName !== "DD") continue;
    const dd = nodes[i + 1];
    const key = dd.getAttribute("data-field") || "";
    const entry = {
      key,
      label: (nodes[i].textContent || "").trim(),
      value: (dd.textContent || "").trim(),
      unset: dd.getAttribute("data-unset") === "true",
    };
    order.push(entry);
    if (key) byKey[key] = entry;
  }
  return { present: true, hidden: wrap.hidden === true, byKey, order };
};

/** İzin durumunu panelin görünür yüzeyinden okur (iç değişkenden değil). */
const READ_CONSENT_CHIP = function () {
  const box = document.getElementById("gorevler-webmcp-consent");
  const text = document.getElementById("gorevler-webmcp-consent-text");
  const btn = document.getElementById("gorevler-webmcp-consent-revoke");
  return {
    present: !!box,
    granted: box ? box.getAttribute("data-granted") : null,
    text: text ? (text.textContent || "").trim() : "",
    revokeVisible: !!btn && btn.hidden === false,
    stored: (function () {
      try {
        return window.sessionStorage.getItem("lumos_panel_webmcp_read_consent_v1");
      } catch (_) {
        return null;
      }
    })(),
  };
};

function requireField(label, snapshot, key) {
  const f = snapshot.byKey[key];
  if (!f) {
    fail(
      label + ": onay ekranında '" + key + "' alanı YOK. Görünen alanlar="
      + JSON.stringify(snapshot.order.map((e) => e.key)),
    );
  }
  return f;
}

function requireContains(label, actual, needle) {
  if (String(actual).indexOf(needle) === -1) {
    fail(label + ": beklenen metin yok. beklenen=" + needle + " görünen=" + JSON.stringify(actual));
  }
}

assertPanelDistBuilt();

const { port, PANEL_URL } = getDefaultServerTargets();
let server;
let browser;

try {
  server = await startStaticServer(DIST_DIR, port);
  await waitForServer(PANEL_URL, PANEL_READY_MS);

  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.addInitScript(AGENT_HARNESS);
  await page.goto(PANEL_URL, { waitUntil: "domcontentloaded", timeout: PANEL_READY_MS });
  await waitForPanelDom(page, PANEL_READY_MS);

  // 1) Kayıt
  await page.waitForFunction(
    () => document.documentElement.dataset.lumosWebmcp === "registered",
    null,
    { timeout: PANEL_READY_MS },
  );
  const discovered = await page.evaluate(() => document.modelContext.getTools());
  const names = discovered.map((t) => t.name).sort();
  if (names.join(",") !== [...EXPECTED_TOOLS].sort().join(",")) {
    fail("Beklenen tool'lar kayıtlı değil; bulunan=" + JSON.stringify(names));
  }
  for (const t of discovered) {
    if (!t.description || String(t.description).length < 20) {
      fail("Tool açıklaması eksik: " + t.name);
    }
    if (!t.inputSchema || t.inputSchema.type !== "object") {
      fail("Tool inputSchema eksik/hatalı: " + t.name);
    }
  }
  // Okuma tool'u ajana iznin gerekli olduğunu söylemeli (sessiz boş liste değil).
  const listDesc = discovered.find((t) => t.name === "lumos-list-tasks").description;
  requireContains("lumos-list-tasks açıklaması", listDesc, "read_consent_required");

  // ── 2) MAHREMİYET: okuma izni olmadan görev içeriği DÖNMEZ ─────────────────
  const chip0 = await page.evaluate(READ_CONSENT_CHIP);
  if (!chip0.present) fail("Panelde görünür izin durumu satırı yok (#gorevler-webmcp-consent)");
  if (chip0.granted !== "false") {
    fail("Açılışta izin kapalı olmalı; görünen=" + JSON.stringify(chip0));
  }
  if (chip0.revokeVisible) fail("İzin yokken 'İzni geri al' düğmesi görünmemeli");

  const refusePromise = pending(
    page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  // İzin ekranı: kullanıcı ne paylaştığını, kapsamı ve geri almayı görür.
  const consentFields = await page.evaluate(READ_CONFIRM_FIELDS);
  if (consentFields.hidden) fail("İzin ekranı alan listesi gizli kalmış");
  requireField("izin ekranı", consentFields, "shared_fields");
  requireContains(
    "izin ekranı kapsam",
    requireField("izin ekranı", consentFields, "scope").value,
    "oturum",
  );
  requireField("izin ekranı", consentFields, "revoke");
  requireContains(
    "izin ekranı kaynak",
    requireField("izin ekranı", consentFields, "source").value,
    "lumos-list-tasks",
  );
  await page.click("#lumos-confirm-cancel");

  const refused = await refusePromise;
  assertNoToolError("lumos-list-tasks (izin reddi)", refused);
  if (refused.ok !== false || refused.approved !== false) {
    fail("İzin reddinde ok/approved false olmalı: " + JSON.stringify(refused));
  }
  if (refused.reason !== "read_consent_required") {
    fail("İzin reddinde net sebep dönmedi: " + JSON.stringify(refused));
  }
  // En kritik iddia: ret cevabı hiçbir görev verisi taşımaz.
  if ("tasks" in refused || "count" in refused) {
    fail("İzinsiz okumada görev içeriği sızmış: " + JSON.stringify(refused));
  }
  const refusedBlob = JSON.stringify(refused);
  if (refusedBlob.indexOf("title") !== -1) {
    fail("İzinsiz ret cevabında görev başlığı alanı görünüyor: " + refusedBlob);
  }
  const chipAfterRefuse = await page.evaluate(READ_CONSENT_CHIP);
  if (chipAfterRefuse.granted !== "false") fail("Ret sonrası izin açık görünüyor");

  // İzin verilince içerik gelir ve panel bunu görünür durum olarak gösterir.
  const allowPromise = pending(
    page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-approve");
  const before = await allowPromise;
  assertNoToolError("lumos-list-tasks (izin verildi)", before);
  if (!before.ok || !Array.isArray(before.tasks)) {
    fail("İzin verildikten sonra liste dönmedi: " + JSON.stringify(before));
  }
  if (!before.consent || before.consent.granted !== true || before.consent.scope !== "session") {
    fail("Liste cevabı izin durumunu taşımıyor: " + JSON.stringify(before.consent));
  }
  const chipOn = await page.evaluate(READ_CONSENT_CHIP);
  if (chipOn.granted !== "true") fail("İzin sonrası görünür durum açık değil: " + JSON.stringify(chipOn));
  if (!chipOn.revokeVisible) fail("İzin açıkken 'İzni geri al' düğmesi görünmüyor");
  if (!chipOn.stored) fail("İzin oturum düzeyinde kalıcı değil (sessionStorage boş)");
  const baselineCount = before.count;

  // İkinci okuma tekrar sormaz (tek seferlik oturum izni).
  const secondRead = await page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} });
  if (!secondRead.ok) fail("İzin verildikten sonra ikinci okuma reddedildi");
  if (await page.isVisible("#lumos-confirm-dialog[open]")) {
    fail("İzin verilmişken okuma yine onay sordu (tek seferlik değil)");
  }

  // Geri alınabilirlik: kullanıcı düğmeye basınca okuma yine reddedilir.
  await page.click("#gorevler-webmcp-consent-revoke");
  const chipOff = await page.evaluate(READ_CONSENT_CHIP);
  if (chipOff.granted !== "false") fail("Geri alma sonrası izin hâlâ açık: " + JSON.stringify(chipOff));
  if (chipOff.stored) fail("Geri alma sonrası oturum izni silinmemiş");
  const afterRevokePromise = pending(
    page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-cancel");
  const afterRevoke = await afterRevokePromise;
  if (afterRevoke.reason !== "read_consent_required" || "tasks" in afterRevoke) {
    fail("Geri alma sonrası okuma engellenmedi: " + JSON.stringify(afterRevoke));
  }

  // Testin kalanı için izni yeniden ver.
  const regrantPromise = pending(
    page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-approve");
  const regranted = await regrantPromise;
  if (!regranted.ok) fail("İzin yeniden verilemedi: " + JSON.stringify(regranted));

  const TITLE_REJECT = "WebMCP reddedilen " + Date.now();
  const TITLE_APPROVE = "WebMCP onaylanan " + Date.now();
  const TITLE_DEFAULTS = "WebMCP varsayilan " + Date.now();

  // ── 3) ONAY EKRANI: yazılacak her alan gerçek değeriyle görünür ────────────
  // Sohbet sekmesindeyken çağrılır: onay modali kullanıcıya görünür hale gelmeli.
  await page.click('.panel-body button[data-module="sohbet"]');
  const rejectPromise = pending(
    page.evaluate(CALL_TOOL, {
      name: "lumos-propose-task",
      args: { title: TITLE_REJECT, priority: "yuksek" },
    }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  const gorevlerActive = await page.getAttribute(
    '[data-module-panel="gorevler"]',
    "data-active",
  );
  if (gorevlerActive !== "true") {
    fail("Onay modali açılırken Görevler modülü öne alınmadı (modal görünmez kalır)");
  }
  const previewWhere = await page.textContent("#lumos-confirm-preview-where");
  if (String(previewWhere || "").trim() !== TITLE_REJECT) {
    fail("Onay önizlemesi görev başlığını göstermiyor: " + JSON.stringify(previewWhere));
  }

  const rejectFields = await page.evaluate(READ_CONFIRM_FIELDS);
  if (!rejectFields.present) fail("Onay ekranında 'Yazılacak alanlar' bölümü yok");
  if (rejectFields.hidden) fail("Onay ekranında alan listesi gizli kalmış");
  if (requireField("öneri (ret)", rejectFields, "title").value !== TITLE_REJECT) {
    fail("Onay ekranı başlığı gerçek değeri göstermiyor");
  }
  // priority ajanın verdiği GERÇEK değerden türemeli — sabit metin değil.
  const rejPriority = requireField("öneri (ret)", rejectFields, "priority");
  requireContains("öncelik alanı", rejPriority.value, "yuksek");
  if (rejPriority.unset) fail("Açıkça verilen öncelik 'belirtilmedi' işaretlenmiş");
  // when verilmedi: boş olduğu AÇIKÇA yazılmalı, gizlenmemeli.
  const rejWhen = requireField("öneri (ret)", rejectFields, "when");
  if (!rejWhen.unset) fail("Verilmeyen 'when' alanı belirtilmedi olarak işaretlenmemiş");
  requireContains("zaman alanı", rejWhen.value, "belirtilmedi");
  requireContains(
    "durum alanı",
    requireField("öneri (ret)", rejectFields, "status").value,
    "bekliyor",
  );
  requireContains(
    "kaynak alanı",
    requireField("öneri (ret)", rejectFields, "source").value,
    "lumos-propose-task",
  );

  await page.click("#lumos-confirm-cancel");
  const rejected = await rejectPromise;
  assertNoToolError("lumos-propose-task (reddet)", rejected);
  if (rejected.approved !== false || rejected.ok !== false || rejected.reason !== "user_rejected") {
    fail("Reddetme sonucu hatalı: " + JSON.stringify(rejected));
  }
  const afterReject = await page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} });
  if (afterReject.count !== baselineCount) {
    fail("Vazgeç sonrası görev yazılmış — onay kapısı atlanmış!");
  }
  if (afterReject.tasks.some((t) => t.title === TITLE_REJECT)) {
    fail("Reddedilen görev listeye sızmış: " + TITLE_REJECT);
  }

  // 3b) Hiç alan verilmeyen çağrı: varsayılanlar da ekranda YAZILI olmalı.
  const defaultsPromise = pending(
    page.evaluate(CALL_TOOL, {
      name: "lumos-propose-task",
      args: { title: TITLE_DEFAULTS },
    }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  const defaultFields = await page.evaluate(READ_CONFIRM_FIELDS);
  const defPriority = requireField("öneri (varsayılan)", defaultFields, "priority");
  if (!defPriority.unset) fail("Verilmeyen öncelik 'belirtilmedi' işaretlenmemiş");
  requireContains("varsayılan öncelik", defPriority.value, "belirtilmedi");
  requireContains("varsayılan öncelik", defPriority.value, "varsayılan");
  requireContains("varsayılan öncelik", defPriority.value, "orta");
  await page.click("#lumos-confirm-cancel");
  const defaultsRejected = await defaultsPromise;
  if (defaultsRejected.ok !== false) fail("Varsayılan senaryosunda vazgeç yazmış olmalı değil");

  // ── 4) Onaylama yolu — gerçek görev oluşur, when gerçek değeriyle görünür ──
  const approvePromise = pending(
    page.evaluate(CALL_TOOL, {
      name: "lumos-propose-task",
      args: { title: TITLE_APPROVE, priority: "yuksek", when: "Yarın 14:00" },
    }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  const approveFields = await page.evaluate(READ_CONFIRM_FIELDS);
  const appWhen = requireField("öneri (onay)", approveFields, "when");
  if (appWhen.value !== "Yarın 14:00") {
    fail("Zaman alanı gerçek değeri göstermiyor: " + JSON.stringify(appWhen.value));
  }
  if (appWhen.unset) fail("Verilen 'when' alanı belirtilmedi işaretlenmiş");
  requireContains(
    "öncelik alanı (onay)",
    requireField("öneri (onay)", approveFields, "priority").value,
    "yuksek",
  );
  await page.click("#lumos-confirm-approve");
  const approved = await approvePromise;
  assertNoToolError("lumos-propose-task (onayla)", approved);
  if (!approved.ok || approved.approved !== true || !approved.task) {
    fail("Onaylı oluşturma başarısız: " + JSON.stringify(approved));
  }
  if (approved.task.title !== TITLE_APPROVE || approved.task.priority !== "yuksek") {
    fail("Oluşan görev alanları hatalı: " + JSON.stringify(approved.task));
  }
  // Ekranda gösterilen ile yazılan aynı olmalı.
  if (approved.task.when !== "Yarın 14:00") {
    fail("Onaylanan zaman yazılana eşit değil: " + JSON.stringify(approved.task));
  }
  const afterApprove = await page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} });
  if (afterApprove.count !== baselineCount + 1) {
    fail("Onay sonrası görev sayısı artmadı: " + afterApprove.count);
  }
  const panelHasRow = await page.evaluate((title) => {
    const raw = localStorage.getItem("lumos_panel_gorevler_list_v1");
    if (!raw) return false;
    try {
      return JSON.parse(raw).some((t) => t && t.title === title);
    } catch {
      return false;
    }
  }, TITLE_APPROVE);
  if (!panelHasRow) fail("Görev panelin kendi kalıcı listesine yazılmadı");

  // ── 5) Tamamlama — aynı kapı + durum değişikliği ekranda yazılı ────────────
  const completeRejectPromise = pending(
    page.evaluate(CALL_TOOL, { name: "lumos-complete-task", args: { ref: TITLE_APPROVE } }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  const completeFields = await page.evaluate(READ_CONFIRM_FIELDS);
  const change = requireField("tamamlama", completeFields, "status_change");
  requireContains("durum değişikliği", change.value, "bekliyor");
  requireContains("durum değişikliği", change.value, "tamamlandi");
  requireContains("durum değişikliği", change.value, "→");
  if (requireField("tamamlama", completeFields, "task").value !== TITLE_APPROVE) {
    fail("Tamamlama ekranı görev başlığını göstermiyor");
  }
  requireContains(
    "tamamlama zaman alanı",
    requireField("tamamlama", completeFields, "when").value,
    "Yarın 14:00",
  );
  requireContains(
    "tamamlama kaynak alanı",
    requireField("tamamlama", completeFields, "source").value,
    "lumos-complete-task",
  );
  await page.click("#lumos-confirm-cancel");
  const completeRejected = await completeRejectPromise;
  assertNoToolError("lumos-complete-task (reddet)", completeRejected);
  if (completeRejected.approved !== false || completeRejected.reason !== "user_rejected") {
    fail("Tamamlama reddi hatalı: " + JSON.stringify(completeRejected));
  }
  const stillOpen = await page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} });
  const stillOpenRow = stillOpen.tasks.find((t) => t.title === TITLE_APPROVE);
  if (!stillOpenRow || stillOpenRow.status === "tamamlandi") {
    fail("Vazgeç sonrası görev tamamlanmış — onay kapısı atlanmış!");
  }

  const completePromise = pending(
    page.evaluate(CALL_TOOL, { name: "lumos-complete-task", args: { ref: TITLE_APPROVE } }),
  );
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-approve");
  const completed = await completePromise;
  assertNoToolError("lumos-complete-task (onayla)", completed);
  if (!completed.ok || completed.approved !== true) {
    fail("Onaylı tamamlama başarısız: " + JSON.stringify(completed));
  }
  if (!completed.task || completed.task.status !== "tamamlandi") {
    fail("Görev durumu tamamlandı değil: " + JSON.stringify(completed.task));
  }

  // 6) Bilinmeyen referans — onay modali hiç açılmamalı
  const notFound = await page.evaluate(CALL_TOOL, {
    name: "lumos-complete-task",
    args: { ref: "olmayan-gorev-" + Date.now() },
  });
  if (notFound.reason !== "task_not_found") {
    fail("Bilinmeyen görev referansı beklenen hatayı vermedi: " + JSON.stringify(notFound));
  }

  // 6b) Yan kanal: "zaten tamamlandı" kısayolu onay ekranı açmaz. İzin
  //     geri alınmışken görev içeriği bu yoldan da SIZMAMALI.
  await page.click("#gorevler-webmcp-consent-revoke");
  const alreadyNoConsent = await page.evaluate(CALL_TOOL, {
    name: "lumos-complete-task",
    args: { ref: TITLE_APPROVE },
  });
  if (alreadyNoConsent.reason !== "already_completed") {
    fail("Beklenen already_completed değil: " + JSON.stringify(alreadyNoConsent));
  }
  if ("task" in alreadyNoConsent) {
    fail("İzin yokken already_completed görev içeriği sızdırdı: " + JSON.stringify(alreadyNoConsent));
  }
  // İzin geri verilince aynı yol içeriği döndürebilir.
  const regrant2 = pending(page.evaluate(CALL_TOOL, { name: "lumos-list-tasks", args: {} }));
  await page.waitForSelector("#lumos-confirm-dialog[open]", { timeout: PANEL_READY_MS });
  await page.click("#lumos-confirm-approve");
  await regrant2;
  const alreadyWithConsent = await page.evaluate(CALL_TOOL, {
    name: "lumos-complete-task",
    args: { ref: TITLE_APPROVE },
  });
  if (!alreadyWithConsent.task || alreadyWithConsent.task.title !== TITLE_APPROVE) {
    fail("İzin varken already_completed içerik döndürmedi: " + JSON.stringify(alreadyWithConsent));
  }

  // 7) İzin oturuma bağlı: yeni oturum (yeni context) izni devralmaz.
  const freshContext = await browser.newContext();
  await freshContext.addInitScript(AGENT_HARNESS);
  const freshPage = await freshContext.newPage();
  await freshPage.goto(PANEL_URL, { waitUntil: "domcontentloaded", timeout: PANEL_READY_MS });
  await waitForPanelDom(freshPage, PANEL_READY_MS);
  await freshPage.waitForFunction(
    () => document.documentElement.dataset.lumosWebmcp === "registered",
    null,
    { timeout: PANEL_READY_MS },
  );
  const freshChip = await freshPage.evaluate(READ_CONSENT_CHIP);
  if (freshChip.granted !== "false") {
    fail("Yeni oturum izni devralmış: " + JSON.stringify(freshChip));
  }
  await freshContext.close();

  await browser.close();
  browser = null;
  console.log("WEBMCP_PANEL_E2E_RESULT: PASS");
  console.log("surface: ui/dist static + document.modelContext");
  console.log("tools:", EXPECTED_TOOLS.join(", "));
  console.log("read consent: refused without approval, granted on approval, revocable");
  console.log("confirm dialog: title, priority, when, status, source rendered from real args");
  console.log("url:", PANEL_URL);
} catch (err) {
  if (browser) await browser.close().catch(() => {});
  fail(String(err && err.stack ? err.stack : err));
} finally {
  await closeServer(server);
}
