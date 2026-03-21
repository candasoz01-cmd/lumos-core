/**
 * Paket e2e ortak assert'leri (local + api mod).
 */
export const LS_CHAT = "lumos_panel_chat_messages_v1";
export const LS_TASKS = "lumos_dot_lumos_tasks_json_v1";

/**
 * Panel index.html yükler state_inject (çevrimdışı + kilit). Görev sohbet e2e’leri politika için online+kilitsiz+consent yamalar.
 */
export async function lumosE2EPatchPolicyAllowTasks(page) {
  await page.evaluate(function () {
    var rs = window.__LUMOS_READ_STATE__;
    if (!rs || typeof rs !== "object") return;
    if (!rs.guidance) rs.guidance = {};
    rs.guidance.mode = "online";
    rs.guidance.lock = "UNLOCKED";
    rs.guidance.consent = true;
    if (rs.keystore && typeof rs.keystore === "object") {
      rs.keystore.keystore_state = "Açık";
      rs.keystore.keystore_ready = true;
    }
    if (rs.dashboard && typeof rs.dashboard === "object") {
      rs.dashboard.guard_status = "Açık";
    }
  });
}

export function countSubstring(s, sub) {
  if (!sub) return 0;
  var n = 0;
  var i = 0;
  while (true) {
    var j = s.indexOf(sub, i);
    if (j === -1) break;
    n++;
    i = j + sub.length;
  }
  return n;
}

/**
 * @param {{ MARK: string, BASE: string, READY_MS: number }} ctx
 */
export function createPackageFlowAssertions(ctx) {
  var MARK = ctx.MARK;
  var BASE = ctx.BASE;
  var READY_MS = ctx.READY_MS;

  function fail(step, msg) {
    throw new Error("[package-e2e] " + step + ": " + msg);
  }

  async function assertStorageDocument(page, step) {
    var pack = await page.evaluate(
      function (keys) {
        var chat = localStorage.getItem(keys.chat);
        var tasks = localStorage.getItem(keys.tasks);
        return { chat: chat, tasks: tasks };
      },
      { chat: LS_CHAT, tasks: LS_TASKS }
    );
    if (!pack.chat) fail(step, "chat localStorage yok");
    if (!pack.tasks) fail(step, "tasks localStorage yok");
    var chatDoc = JSON.parse(pack.chat);
    var tasksDoc = JSON.parse(pack.tasks);
    if (chatDoc.v !== 1 || !Array.isArray(chatDoc.messages)) fail(step, "chat doc şekli");
    if (tasksDoc.v !== 1 || !Array.isArray(tasksDoc.tasks) || !Array.isArray(tasksDoc.events)) {
      fail(step, "tasks doc şekli");
    }
    var title = MARK;
    var rows = tasksDoc.tasks.filter(function (t) {
      return t && String(t.title || "") === title;
    });
    if (rows.length !== 1) fail(step, "beklenen tek görev satırı, sayı=" + rows.length);
    if (rows[0].status !== "deleted") fail(step, "görev status deleted değil: " + String(rows[0].status));

    var c = tasksDoc.events.filter(function (e) {
      return e && e.type === "task_created" && String(e.text || "") === title;
    });
    var d = tasksDoc.events.filter(function (e) {
      return e && e.type === "task_completed" && String(e.text || "") === title;
    });
    var del = tasksDoc.events.filter(function (e) {
      return e && e.type === "task_deleted" && String(e.text || "") === title;
    });
    if (c.length !== 1) fail(step, "task_created olayı sayısı " + c.length);
    if (d.length !== 1) fail(step, "task_completed olayı sayısı " + d.length);
    if (del.length !== 1) fail(step, "task_deleted olayı sayısı " + del.length);

    var chatText = JSON.stringify(chatDoc.messages);
    if (!chatText.includes("görev oluştur " + title)) fail(step, "chat’ta create komutu yok");
    if (!chatText.includes("görev tamamla " + title)) fail(step, "chat’ta complete komutu yok");
    if (!chatText.includes("görev sil " + title)) fail(step, "chat’ta sil komutu yok");
    if (chatDoc.messages.length !== 6) fail(step, "chat mesaj sayısı 6 değil: " + chatDoc.messages.length);
  }

  async function assertDeletedHiddenAllTaskFilters(page, step) {
    var filterIds = ["all", "active", "pending", "completed", "failed", "blocked"];
    await page.goto(BASE + "/index.html#tasks", { waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector(".task-filters", { state: "attached", timeout: READY_MS });
    var fi;
    for (fi = 0; fi < filterIds.length; fi++) {
      await page.locator('[data-task-filter="' + filterIds[fi] + '"]').click();
      await page.waitForTimeout(250);
      var body = await page.locator("#main-content").innerText();
      if (body.indexOf(MARK) !== -1) fail(step, "filtre " + filterIds[fi] + " içinde başlık göründü");
    }
  }

  async function assertTrashVisible(page, step) {
    await page.goto(BASE + "/index.html#trash", { waitUntil: "load", timeout: READY_MS });
    await page.waitForTimeout(500);
    var trashBody = await page.locator("#main-content").innerText();
    if (trashBody.indexOf(MARK) === -1) fail(step, "Silinenler ekranında başlık yok");
    var softRows = await page.locator('[data-soft-deleted-task="1"]').count();
    if (softRows < 1) fail(step, "data-soft-deleted-task satırı yok");
  }

  async function assertLogsFullChain(page, step) {
    await page.goto(BASE + "/index.html#logs", { waitUntil: "load", timeout: READY_MS });
    await page.waitForTimeout(200);
    var logsBody = await page.locator("#main-content").innerText();
    if (!logsBody.includes("[task_created]") || !logsBody.includes(MARK)) fail(step, "logs task_created / başlık eksik");
    if (!logsBody.includes("[task_completed]")) fail(step, "logs task_completed yok");
    if (!logsBody.includes("[task_deleted]")) fail(step, "logs task_deleted yok");
    if (countSubstring(logsBody, "[task_completed] " + MARK) !== 1) fail(step, "task_completed satırı tekrar veya eksik");

    var evPack = await page.evaluate(function () {
      var raw = localStorage.getItem("lumos_dot_lumos_tasks_json_v1");
      if (!raw) return { err: "no tasks storage" };
      var o = JSON.parse(raw);
      if (!o || o.v !== 1 || !Array.isArray(o.events)) return { err: "events yok" };
      return { events: o.events };
    });
    if (evPack.err) fail(step, evPack.err);
    var motor = evPack.events.filter(function (e) {
      return (
        e &&
        (e.type === "task_created" || e.type === "task_completed" || e.type === "task_deleted")
      );
    });
    var tags = logsBody.match(/\[task_(?:created|completed|deleted)\]/g);
    if (!tags || tags.length !== motor.length) {
      fail(
        step,
        "log motor satır sayısı storage ile uyuşmuyor " + (tags ? tags.length : 0) + " vs " + motor.length
      );
    }
    var ei;
    for (ei = 0; ei < motor.length; ei++) {
      var ev = motor[ei];
      var ttag = "[" + String(ev.type) + "]";
      if (logsBody.indexOf(ttag) === -1) fail(step, "storage’daki " + ttag + " log UI’da yok");
      var etx = String(ev.text || "").trim();
      if (etx && logsBody.indexOf(etx) === -1) fail(step, "storage olay metni log’da yok");
    }
  }

  async function assertDashboardChain(page, step) {
    await page.goto(BASE + "/index.html#dashboard", { waitUntil: "load", timeout: READY_MS });
    await page.waitForTimeout(200);
    var dash = await page.locator("#main-content").innerText();
    if (!dash.includes("[task_created]")) fail(step, "dashboard task_created yok");
    if (!dash.includes("[task_completed]")) fail(step, "dashboard task_completed yok");
    if (!dash.includes("[task_deleted]")) fail(step, "dashboard task_deleted yok");
    if (!dash.includes(MARK)) fail(step, "dashboard’da başlık yok");
  }

  async function assertChatUiShowsCommands(page, step) {
    await page.goto(BASE + "/index.html#chat", { waitUntil: "load", timeout: READY_MS });
    await page.waitForSelector("#lumos-chat-input", { state: "attached", timeout: READY_MS });
    var chatBody = await page.locator("#main-content").innerText();
    if (!chatBody.includes("görev oluştur " + MARK)) fail(step, "UI’da create komutu yok");
    if (!chatBody.includes("görev tamamla " + MARK)) fail(step, "UI’da complete komutu yok");
    if (!chatBody.includes("görev sil " + MARK)) fail(step, "UI’da sil komutu yok");
  }

  async function assertPostReload(page, phase) {
    await assertChatUiShowsCommands(page, phase + "/chat-ui");
    await assertStorageDocument(page, phase + "/storage");
    await assertDeletedHiddenAllTaskFilters(page, phase + "/tasks-filters");
    await assertTrashVisible(page, phase + "/trash");
    await assertLogsFullChain(page, phase + "/logs");
    await assertDashboardChain(page, phase + "/dashboard");
  }

  return {
    fail,
    assertStorageDocument,
    assertDeletedHiddenAllTaskFilters,
    assertTrashVisible,
    assertLogsFullChain,
    assertDashboardChain,
    assertChatUiShowsCommands,
    assertPostReload,
  };
}
