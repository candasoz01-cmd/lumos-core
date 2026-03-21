/**
 * Lumos Panel v1 — operatör paneli.
 * Veri adapter katmanı: ekranlar normalize veri ile beslenir; kaynak şu an mockState (backend yok).
 * Ortak bileşenler, hash routing. Gerçek API entegrasyonu sonraki aşamada adapter üzerinden eklenecek.
 */

(function () {
  "use strict";

  var DEFAULT_HASH = "#dashboard";

  var SCREENS = {
    chat: { id: "chat", label: "Chat", hash: "#chat" },
    dashboard: { id: "dashboard", label: "Gösterge Paneli", hash: "#dashboard" },
    feed: { id: "feed", label: "Akış", hash: "#feed" },
    tasks: { id: "tasks", label: "Görevler", hash: "#tasks" },
    sandbox: { id: "sandbox", label: "Korumalı Alan", hash: "#sandbox" },
    config: { id: "config", label: "Yapılandırma", hash: "#config" },
    identity: { id: "identity", label: "Kimlik", hash: "#identity" },
    keystore: { id: "keystore", label: "Anahtar Kasası", hash: "#keystore" },
    trash: { id: "trash", label: "Silinenler", hash: "#trash" },
    logs: { id: "logs", label: "Kayıtlar", hash: "#logs" },
    system: { id: "system", label: "Sistem Durumu", hash: "#system" },
  };

  var LC = typeof LumosContracts !== "undefined" ? LumosContracts : {};
  var EMPTY_DESC_DEFAULT = LC.EMPTY_DESC_DEFAULT || "Mock veri; canlı entegrasyon sonraki aşamada açılacak.";
  var formatTime = LC.formatTime || function (s) { return s || "—"; };
  var EMPTY_FALLBACK =
    '<div class="empty-state">' +
    '<p class="empty-title">Henüz veri yok</p>' +
    '<p class="empty-desc">' + EMPTY_DESC_DEFAULT + "</p>" +
    "</div>";

  // ——— Merkezi mock state (tek kaynak; adapter dışında doğrudan okunmaz) ———
  var mockState = {
    appMode: "offline",
    sandboxMode: false,
    sandboxSource: "varsayılan",
    writingBaseDir: "canlı",
    workspaceName: "lumos-core",
    branchName: "kando/main",
    basePath: ".lumos",
    guardStatus: "KORUMA AKTİF",
    recentEvents: [
      { id: "e1", kind: "görev", text: "Görev t2 güncellendi", ts: "2025-03-14T10:05:00" },
      { id: "e2", kind: "sandbox", text: "Korumalı alan kapalı", ts: "2025-03-14T09:00:00" },
      { id: "e3", kind: "config", text: "config okundu", ts: "2025-03-14T08:55:00" },
    ],
    warnings: ["Mock veri; canlı bağlantı yok."],
    trashItems: [
      { id: "tr1", name: "eski_tasks_backup.json", originalPath: ".lumos/tasks_backup.json", trashPath: ".lumos/trash/eski_tasks_backup.json", movedAt: "2025-03-12T14:00:00", scope: "tasks" },
      { id: "tr2", name: "notlar_eski.md", originalPath: ".lumos/notlar_eski.md", trashPath: ".lumos/trash/notlar_eski.md", movedAt: "2025-03-11T11:00:00", scope: "notes" },
    ],
    trashLocation: ".lumos/trash",
    trashLastMove: "2025-03-12T14:00:00",
    logItems: [
      { id: "L1", kind: "görev", text: "Görev t2 güncellendi", ts: "2025-03-14T10:05:00" },
      { id: "L2", kind: "sandbox", text: "Korumalı alan kapalı", ts: "2025-03-14T09:00:00" },
      { id: "L3", kind: "config", text: "config okundu", ts: "2025-03-14T08:55:00" },
      { id: "L4", kind: "trash", text: "Öğe taşındı: eski_tasks_backup.json", ts: "2025-03-12T14:00:00" },
      { id: "L5", kind: "identity", text: "Kimlik sorgulandı", ts: "2025-03-14T08:00:00" },
      { id: "L6", kind: "keystore", text: "Keystore kilitli", ts: "2025-03-14T07:55:00" },
      { id: "L7", kind: "guard", text: "Guard: yazım hedefi canlı", ts: "2025-03-14T07:50:00" },
    ],
    configSnapshot: {
      profil: "guvenli_yurut",
      workspace_root: ".lumos",
      writeStatus: "Yazım uygun",
      lastActivity: "2025-03-14T08:55:00",
      lastActivityText: "config okundu",
    },
    identityState: "mevcut değil",
    identityLastWrite: "2025-03-14T08:00:00",
    identityTargetScope: "çekirdek kimlik alanı",
    identityGuardResult: "Korunuyor",
    keystoreState: "Kilitli",
    keystoreReady: false,
    keystoreLastUpdate: "2025-03-14T07:55:00",
    keystoreWriteScope: "Kilit açılmadan hassas yazım yapılmaz",
    systemHealth: {
      workspace_contract: { status: "ok", note: "Sözleşme yüklü; çekirdek path'ler tanımlı." },
      task_engine: { status: "ok", note: "Görev motoru çalışıyor." },
      sandbox_source: { status: "ok", note: "Sandbox kaynağı çözümlendi." },
      trash_contract: { status: "ok", note: "Trash konumu sözleşmeyle sabit." },
      config_sink: { status: "ok", note: "Config sink yazım hattı hazır." },
      identity_sink: { status: "uyarı", note: "Kimlik mevcut değil; hassas işlem yok." },
      keystore_sink: { status: "uyarı", note: "Keystore kilitli; hassas yazım kapalı." },
      general: { status: "ok", note: "Çekirdek parçalar operasyonel; 2 uyarı (identity, keystore)." },
    },
    taskList: [
      { id: "t1", title: "Panel iskeleti genişlet", status: "aktif", updated: "2025-03-14T10:00:00", lastRun: "2025-03-14T10:05:00", guardResult: "İzinli", outputSummary: "Panel bileşenleri güncellendi; test geçti." },
      { id: "t2", title: "Mock state birleştir", status: "bekleyen", updated: "2025-03-14T09:30:00", lastRun: null, guardResult: "—", outputSummary: "—" },
      { id: "t3", title: "README güncelle", status: "tamamlandı", updated: "2025-03-13T16:00:00", lastRun: "2025-03-13T16:00:00", guardResult: "İzinli", outputSummary: "README güncellendi." },
      { id: "t4", title: "Guard kuralı doğrula", status: "başarısız", updated: "2025-03-14T08:00:00", lastRun: "2025-03-14T08:00:00", guardResult: "Reddedildi", outputSummary: "Hedef path sözleşme dışı; çalıştırma durduruldu." },
      { id: "t5", title: "Dış API çağrısı", status: "engellenen", updated: "2025-03-14T07:30:00", lastRun: null, guardResult: "Engelli", outputSummary: "Profil dışı; işlem yapılmadı." },
    ],
    taskFilter: "all",
    /**
     * Merkezi görev motoru durumu (chat komutları; tek kaynak — görev ekranı buradan).
     * Şekil: { id, title, status: "active"|"done", createdAt, completedAt }
     */
    engineTasks: [],
    /**
     * Tek kaynak (chat → panel): saf olaylar { id, type, taskId, text, ts }.
     * Kayıt / dashboard bu hattı okur; görev güncel durumu engineTasks’tır.
     */
    chatTaskCreations: [],
    selectedTaskId: null,
    selectedTrashId: null,
    logFilter: "all",
    guidance: {
      mode: "offline",
      lock: "LOCKED",
      consent: false,
      blocked_reason: null,
      next_step: null,
    },
  };

  // ——— Demo senaryolar (override; adapter tek kaynak olarak getEffectiveState kullanır) ———
  var currentScenario = "normal_operasyon";
  var useFixtureData = false;
  var DEMO_SCENARIOS = {
    normal_operasyon: {},
    sandbox_aktif: {
      sandboxMode: true,
      writingBaseDir: "sandbox",
      sandboxSource: "CLI",
      recentEvents: [
        { id: "e1", kind: "sandbox", text: "Korumalı alan açık; yazım sandbox base'e", ts: "2025-03-14T10:05:00" },
        { id: "e2", kind: "görev", text: "Görev t2 güncellendi", ts: "2025-03-14T10:00:00" },
        { id: "e3", kind: "config", text: "config okundu", ts: "2025-03-14T08:55:00" },
      ],
      warnings: ["Korumalı alan açık; yazım .lumos/sandbox (veya sözleşme base) altına gidiyor."],
      logItems: [
        { id: "L1", kind: "sandbox", text: "Korumalı alan açık; yazım sandbox base'e", ts: "2025-03-14T10:05:00" },
        { id: "L2", kind: "görev", text: "Görev t2 güncellendi", ts: "2025-03-14T10:00:00" },
        { id: "L3", kind: "config", text: "config okundu", ts: "2025-03-14T08:55:00" },
        { id: "L4", kind: "trash", text: "Öğe taşındı: eski_tasks_backup.json", ts: "2025-03-12T14:00:00" },
        { id: "L5", kind: "guard", text: "Guard: yazım hedefi sandbox", ts: "2025-03-14T07:50:00" },
      ],
    },
    guard_bloklu: {
      guardStatus: "ENGELLENDİ",
      recentEvents: [
        { id: "e1", kind: "guard", text: "Yazım engellendi: hedef path sözleşme dışı", ts: "2025-03-14T10:05:00" },
        { id: "e2", kind: "görev", text: "Görev t4 guard reddi", ts: "2025-03-14T09:30:00" },
        { id: "e3", kind: "guard", text: "Dış API çağrısı engelli", ts: "2025-03-14T09:00:00" },
      ],
      warnings: ["Guard: bazı aksiyonlar engellendi.", "Hedef path sözleşme dışı; yazım yapılmadı."],
      logItems: [
        { id: "L1", kind: "guard", text: "Yazım engellendi: hedef path sözleşme dışı", ts: "2025-03-14T10:05:00" },
        { id: "L2", kind: "görev", text: "Görev t4 guard reddi", ts: "2025-03-14T09:30:00" },
        { id: "L3", kind: "guard", text: "Dış API çağrısı engelli", ts: "2025-03-14T09:00:00" },
        { id: "L4", kind: "config", text: "config okundu", ts: "2025-03-14T08:55:00" },
        { id: "L5", kind: "guard", text: "Guard: yazım hedefi kontrolü başarısız", ts: "2025-03-14T08:00:00" },
      ],
      taskList: [
        { id: "t1", title: "Panel iskeleti genişlet", status: "aktif", updated: "2025-03-14T10:00:00", lastRun: "2025-03-14T10:05:00", guardResult: "İzinli", outputSummary: "Panel bileşenleri güncellendi." },
        { id: "t2", title: "Mock state birleştir", status: "bekleyen", updated: "2025-03-14T09:30:00", lastRun: null, guardResult: "—", outputSummary: "—" },
        { id: "t3", title: "README güncelle", status: "tamamlandı", updated: "2025-03-13T16:00:00", lastRun: "2025-03-13T16:00:00", guardResult: "İzinli", outputSummary: "README güncellendi." },
        { id: "t4", title: "Guard kuralı doğrula", status: "başarısız", updated: "2025-03-14T08:00:00", lastRun: "2025-03-14T08:00:00", guardResult: "Reddedildi", outputSummary: "Hedef path sözleşme dışı; çalıştırma durduruldu." },
        { id: "t5", title: "Dış API çağrısı", status: "engellenen", updated: "2025-03-14T07:30:00", lastRun: null, guardResult: "Engelli", outputSummary: "Profil dışı; işlem yapılmadı." },
        { id: "t6", title: "Dış dizine yaz", status: "engellenen", updated: "2025-03-14T07:00:00", lastRun: null, guardResult: "Engelli", outputSummary: "Guard: hedef sözleşme dışı." },
      ],
      systemHealth: {
        workspace_contract: { status: "ok", note: "Sözleşme yüklü." },
        task_engine: { status: "ok", note: "Görev motoru çalışıyor." },
        sandbox_source: { status: "ok", note: "Sandbox kaynağı çözümlendi." },
        trash_contract: { status: "ok", note: "Trash konumu sabit." },
        config_sink: { status: "ok", note: "Config sink hazır." },
        identity_sink: { status: "uyarı", note: "Kimlik mevcut değil." },
        keystore_sink: { status: "uyarı", note: "Keystore kilitli." },
        general: { status: "hata", note: "Guard engellemeleri var; bazı aksiyonlar reddedildi." },
      },
    },
    config_uyari: {
      warnings: ["Config dosyasında dikkat edilmesi gereken alan var.", "Profil sınırı: guvenli_yurut; kritik işlem kapalı."],
      configSnapshot: {
        profil: "guvenli_yurut",
        workspace_root: ".lumos",
        writeStatus: "Uyarı: dikkat edilmesi gereken alan var",
        lastActivity: "2025-03-14T08:55:00",
        lastActivityText: "Config okundu; uyarı alanı işaretlendi.",
      },
      recentEvents: [
        { id: "e1", kind: "görev", text: "Görev t2 güncellendi", ts: "2025-03-14T10:05:00" },
        { id: "e2", kind: "config", text: "Config uyarı: dikkat alanı", ts: "2025-03-14T09:30:00" },
        { id: "e3", kind: "config", text: "config okundu", ts: "2025-03-14T08:55:00" },
      ],
      logItems: [
        { id: "L1", kind: "görev", text: "Görev t2 güncellendi", ts: "2025-03-14T10:05:00" },
        { id: "L2", kind: "config", text: "Config uyarı: dikkat alanı", ts: "2025-03-14T09:30:00" },
        { id: "L3", kind: "config", text: "config okundu", ts: "2025-03-14T08:55:00" },
        { id: "L4", kind: "trash", text: "Öğe taşındı: eski_tasks_backup.json", ts: "2025-03-12T14:00:00" },
      ],
    },
    trash_dolu: {
      trashItems: [
        { id: "tr1", name: "eski_tasks_backup.json", originalPath: ".lumos/tasks_backup.json", trashPath: ".lumos/trash/eski_tasks_backup.json", movedAt: "2025-03-14T11:00:00", scope: "tasks" },
        { id: "tr2", name: "notlar_eski.md", originalPath: ".lumos/notlar_eski.md", trashPath: ".lumos/trash/notlar_eski.md", movedAt: "2025-03-14T10:30:00", scope: "notes" },
        { id: "tr3", name: "config_eski.json", originalPath: ".lumos/config_eski.json", trashPath: ".lumos/trash/config_eski.json", movedAt: "2025-03-14T10:00:00", scope: "config" },
        { id: "tr4", name: "log_eski.txt", originalPath: ".lumos/log_eski.txt", trashPath: ".lumos/trash/log_eski.txt", movedAt: "2025-03-13T18:00:00", scope: "logs" },
        { id: "tr5", name: "deneme_notu.md", originalPath: ".lumos/deneme_notu.md", trashPath: ".lumos/trash/deneme_notu.md", movedAt: "2025-03-13T15:00:00", scope: "notes" },
        { id: "tr6", name: "backup_eski.json", originalPath: ".lumos/backup_eski.json", trashPath: ".lumos/trash/backup_eski.json", movedAt: "2025-03-12T14:00:00", scope: "tasks" },
      ],
      trashLastMove: "2025-03-14T11:00:00",
      logItems: [
        { id: "L1", kind: "trash", text: "Öğe taşındı: eski_tasks_backup.json", ts: "2025-03-14T11:00:00" },
        { id: "L2", kind: "trash", text: "Öğe taşındı: notlar_eski.md", ts: "2025-03-14T10:30:00" },
        { id: "L3", kind: "trash", text: "Öğe taşındı: config_eski.json", ts: "2025-03-14T10:00:00" },
        { id: "L4", kind: "görev", text: "Görev t2 güncellendi", ts: "2025-03-14T10:05:00" },
        { id: "L5", kind: "config", text: "config okundu", ts: "2025-03-14T08:55:00" },
      ],
    },
  };

  function getEffectiveState() {
    var out = {};
    for (var k in mockState) out[k] = mockState[k];
    var over = DEMO_SCENARIOS[currentScenario];
    if (over) for (var k in over) out[k] = over[k];
    return out;
  }

  function getScenarioList() {
    return [
      { id: "normal_operasyon", label: "Normal operasyon" },
      { id: "sandbox_aktif", label: "Korumalı alan açık" },
      { id: "guard_bloklu", label: "Guard engelli" },
      { id: "config_uyari", label: "Config uyarı" },
      { id: "trash_dolu", label: "Silinenler dolu" },
    ];
  }

  // Contract/stub: LumosContracts (js/contracts.js) — CONTRACTS, build*Stub, normalize* orada; LC yukarıda tanımlı.

  function getBadgeVariant(label) {
    var v = {
      CANLI: "badge-live",
      "KORUMALI ALAN": "badge-sandbox",
      "KORUMA AKTİF": "badge-guard",
      "SALT OKUNUR": "badge-readonly",
      UYARI: "badge-warning",
      ENGELLENDİ: "badge-blocked",
      "Çevrimdışı": "badge-offline",
      Açık: "badge-offline",
    };
    return v[label] || "badge-mode";
  }

  function getBadgeLabel(key, value) {
    if (key === "mode") return value === "online" ? "CANLI" : "Çevrimdışı";
    if (key === "lock") return value === "LOCKED" ? "KORUMA AKTİF" : "Açık";
    if (key === "sandbox") return "KORUMALI ALAN";
    return value;
  }

  function getTaskStatusVariant(status) {
    var v = { aktif: "badge-live", bekleyen: "badge-offline", tamamlandı: "badge-live", başarısız: "badge-warning", engellenen: "badge-blocked" };
    return v[status] || "badge-mode";
  }

  function getHealthStatusVariant(status) {
    var v = { ok: "badge-live", uyarı: "badge-warning", hata: "badge-blocked" };
    return v[status] || "badge-mode";
  }

  // ——— Veri kaynağı soyutlaması (Phase 1: Dashboard, Sandbox, System, Config, Identity, Keystore) ———
  var Bridge = typeof LumosBackendBridge !== "undefined" ? LumosBackendBridge : {};
  function getDashboardSourceData() {
    var backend = Bridge.readBackendDashboardState && Bridge.readBackendDashboardState();
    if (backend != null) return { type: "backend", data: backend };
    if (useFixtureData && window.LumosFixtures && window.LumosFixtures.payloads) return { type: "fixture", data: window.LumosFixtures.payloads.dashboard };
    return { type: "demo", data: getEffectiveState() };
  }
  function getSandboxSourceData() {
    var backend = Bridge.readBackendSandboxState && Bridge.readBackendSandboxState();
    if (backend != null) return { type: "backend", data: backend };
    if (useFixtureData && window.LumosFixtures && window.LumosFixtures.payloads) return { type: "fixture", data: window.LumosFixtures.payloads.sandbox };
    return { type: "demo", data: getEffectiveState() };
  }
  /** System: Phase 2 ilk gerçek backend okuma hedefi; backend → mapper → normalizeSystem. */
  function getSystemSourceData() {
    var backend = Bridge.readBackendSystemState && Bridge.readBackendSystemState();
    if (backend != null) return { type: "backend", data: backend };
    if (useFixtureData && window.LumosFixtures && window.LumosFixtures.payloads) return { type: "fixture", data: window.LumosFixtures.payloads.system };
    return { type: "demo", data: getEffectiveState() };
  }
  function getConfigSourceData() {
    var backend = Bridge.readBackendConfigState && Bridge.readBackendConfigState();
    if (backend != null) return { type: "backend", data: backend };
    if (useFixtureData && window.LumosFixtures && window.LumosFixtures.payloads) return { type: "fixture", data: window.LumosFixtures.payloads.config };
    return { type: "demo", data: getEffectiveState() };
  }
  function getIdentitySourceData() {
    var backend = Bridge.readBackendIdentityState && Bridge.readBackendIdentityState();
    if (backend != null) return { type: "backend", data: backend };
    if (useFixtureData && window.LumosFixtures && window.LumosFixtures.payloads) return { type: "fixture", data: window.LumosFixtures.payloads.identity };
    return { type: "demo", data: getEffectiveState() };
  }
  function getKeystoreSourceData() {
    var backend = Bridge.readBackendKeystoreState && Bridge.readBackendKeystoreState();
    if (backend != null) return { type: "backend", data: backend };
    if (useFixtureData && window.LumosFixtures && window.LumosFixtures.payloads) return { type: "fixture", data: window.LumosFixtures.payloads.keystore };
    return { type: "demo", data: getEffectiveState() };
  }
  function getTasksSourceData() {
    var backend = Bridge.readBackendTasksState && Bridge.readBackendTasksState();
    if (backend != null) return { type: "backend", data: backend };
    if (useFixtureData && window.LumosFixtures && window.LumosFixtures.payloads) return { type: "fixture", data: window.LumosFixtures.payloads.tasks };
    return { type: "demo", data: getEffectiveState() };
  }
  function getTrashSourceData() {
    var backend = Bridge.readBackendTrashState && Bridge.readBackendTrashState();
    if (backend != null) return { type: "backend", data: backend };
    if (useFixtureData && window.LumosFixtures && window.LumosFixtures.payloads) return { type: "fixture", data: window.LumosFixtures.payloads.trash };
    return { type: "demo", data: getEffectiveState() };
  }
  function getLogsSourceData() {
    var backend = Bridge.readBackendLogsState && Bridge.readBackendLogsState();
    if (backend != null) return { type: "backend", data: backend };
    if (useFixtureData && window.LumosFixtures && window.LumosFixtures.payloads) return { type: "fixture", data: window.LumosFixtures.payloads.logs };
    return { type: "demo", data: getEffectiveState() };
  }
  function getGuidanceSourceData() {
    var backend = Bridge.readBackendGuidanceState && Bridge.readBackendGuidanceState();
    if (backend != null) return { type: "backend", data: backend };
    return { type: "demo", data: getEffectiveState().guidance || { mode: "offline", lock: "LOCKED", consent: false, blocked_reason: null, next_step: null } };
  }

  /**
   * Minimum task engine — stability contract (execution layer hooks here later):
   * - Görev güncel durumu: mockState.engineTasks (status "active" | "done"). UI satırı toTaskRow ile; olaydan türetilmez.
   * - Denetim zaman çizelgesi: append-only mockState.chatTaskCreations (task_created | task_completed);
   *   taskId + text (başlık) mutasyondaki görevle hizalı olmalı; yazım yolu: appendPanelEngineEvent (persist dahil).
   * - Birleşik olay okuma (Kayıtlar + Dashboard Son Olaylar): yalnızca getMergedPanelEventsList().
   * - Görevler ekranı: demo’da fullList = motor satırları; backend/fixture’da mergeBackendTaskRowsWithEngine (çakışan id’de backend öncelikli).
   * - Kalıcılık: localStorage `lumos_panel_min_task_engine_v1` (v:1); hydratePanelEngineFromStorage yüklemede, persistPanelEngineState olay eklendikten sonra.
   */
  // ——— Adapter + minimum görev motoru ———
  var PANEL_ENGINE_STORAGE_KEY = "lumos_panel_min_task_engine_v1";

  function persistPanelEngineState() {
    try {
      if (typeof localStorage === "undefined") return;
      localStorage.setItem(
        PANEL_ENGINE_STORAGE_KEY,
        JSON.stringify({
          v: 1,
          engineTasks: mockState.engineTasks,
          chatTaskCreations: mockState.chatTaskCreations,
        })
      );
    } catch (_) {
      /* quota / private mode */
    }
  }

  function newEngineEventId() {
    return "ev_" + Date.now() + "_" + Math.random().toString(36).slice(2, 9);
  }

  function newEngineTaskId() {
    return "tsk_" + Date.now() + "_" + Math.random().toString(36).slice(2, 9);
  }

  function isPanelMotorEventType(type) {
    return type === "task_created" || type === "task_completed";
  }

  function hydratePanelEngineFromStorage() {
    try {
      if (typeof localStorage === "undefined") return;
      var raw = localStorage.getItem(PANEL_ENGINE_STORAGE_KEY);
      if (!raw) return;
      var o = JSON.parse(raw);
      if (!o || typeof o !== "object" || o.v !== 1) return;
      if (Array.isArray(o.engineTasks)) {
        var tasks = [];
        for (var i = 0; i < o.engineTasks.length; i++) {
          var t = o.engineTasks[i];
          if (!t || typeof t !== "object") continue;
          if (t.id == null || String(t.id) === "") continue;
          if (t.status !== "active" && t.status !== "done") continue;
          tasks.push({
            id: String(t.id),
            title: t.title != null ? String(t.title) : "—",
            status: t.status,
            createdAt: t.createdAt != null ? String(t.createdAt) : "",
            completedAt: t.completedAt != null && t.completedAt !== "" ? String(t.completedAt) : null,
          });
        }
        mockState.engineTasks = tasks;
      }
      if (Array.isArray(o.chatTaskCreations)) {
        var evs = [];
        for (var j = 0; j < o.chatTaskCreations.length; j++) {
          var e = o.chatTaskCreations[j];
          if (!e || typeof e !== "object") continue;
          if (!isPanelMotorEventType(e.type)) continue;
          evs.push({
            id: e.id != null ? String(e.id) : newEngineEventId(),
            type: e.type,
            taskId: String(e.taskId || ""),
            text: e.text != null ? String(e.text) : "",
            ts: e.ts != null ? String(e.ts) : new Date().toISOString(),
          });
        }
        mockState.chatTaskCreations = evs;
      }
    } catch (_) {
      /* corrupt JSON */
    }
  }

  function buildPanelTaskEvent(type, taskId, taskTitle) {
    return {
      id: newEngineEventId(),
      type: type,
      taskId: String(taskId || ""),
      text: String(taskTitle || "").trim(),
      ts: new Date().toISOString(),
    };
  }

  function findActiveEngineTaskByRef(ref) {
    var r = String(ref || "").trim();
    var tasks = mockState.engineTasks || [];
    var rLow = r.toLowerCase();
    var i;
    var t;
    for (i = 0; i < tasks.length; i++) {
      t = tasks[i];
      if (t.status !== "active") continue;
      if (String(t.id) === r) return t;
    }
    for (i = 0; i < tasks.length; i++) {
      t = tasks[i];
      if (t.status !== "active") continue;
      if (String(t.title).toLowerCase() === rLow) return t;
    }
    return null;
  }

  function appendPanelEngineEvent(ev) {
    if (!ev || !isPanelMotorEventType(ev.type)) return;
    mockState.chatTaskCreations.push(ev);
    persistPanelEngineState();
  }

  var LumosMinTaskEngine = {
    createTask: function (title) {
      var t = String(title || "").trim();
      if (!t) return null;
      var now = new Date().toISOString();
      var task = {
        id: newEngineTaskId(),
        title: t,
        status: "active",
        createdAt: now,
        completedAt: null,
      };
      mockState.engineTasks.push(task);
      return task;
    },
    completeTask: function (ref) {
      var r = String(ref || "").trim();
      if (!r) return { ok: false, reason: "empty" };
      var task = findActiveEngineTaskByRef(r);
      if (!task) return { ok: false, reason: "not_found" };
      task.status = "done";
      task.completedAt = new Date().toISOString();
      return { ok: true, task: task };
    },
    getTasksData: function () {
      return (mockState.engineTasks || []).slice();
    },
  };

  function createTaskCreatedEvent(taskId, taskTitle) {
    return buildPanelTaskEvent("task_created", taskId, taskTitle);
  }

  function createTaskCompletedEvent(taskId, taskTitle) {
    return buildPanelTaskEvent("task_completed", taskId, taskTitle);
  }

  /** Eski oturumlarda kalan `time` alanını okurken ts ile hizala (yazmada yalnız ts). */
  function eventTimestamp(ev) {
    if (!ev) return null;
    if (ev.ts != null) return ev.ts;
    if (ev.time != null) return ev.time;
    return null;
  }

  function isTaskCreatedEvent(ev) {
    return !!(ev && (ev.type === "task_created" || ev.kind === "task_created"));
  }

  function isTaskCompletedEvent(ev) {
    return !!(ev && (ev.type === "task_completed" || ev.kind === "task_completed"));
  }

  // ——— UI adapter: motor görevi → Görevler stub satırı (filterTaskList: aktif / tamamlandı) ———
  function toTaskRow(task) {
    if (!task || task.id == null) return null;
    var done = task.status === "done";
    return {
      id: String(task.id),
      title: task.title || "—",
      status: done ? "tamamlandı" : "aktif",
      updated: done && task.completedAt ? task.completedAt : task.createdAt || null,
      lastRun: null,
      guardResult: "—",
      outputSummary: done ? "Tamamlandı." : "—",
    };
  }

  /** Kayıtlar / EventList için { ts, kind, text } */
  function toLogRow(event) {
    if (!event) return null;
    var ts = eventTimestamp(event);
    var kind = event.kind != null ? event.kind : "";
    if (!kind && event.type === "task_created") kind = "task_created";
    if (!kind && event.type === "task_completed") kind = "task_completed";
    if (!kind && event.type != null) kind = String(event.type);
    var text = event.text != null ? String(event.text) : "";
    if (!kind && text === "") return null;
    return { ts: ts, kind: kind, text: text };
  }

  function toDashboardItem(event) {
    return toLogRow(event);
  }

  function toActivityNote(event) {
    if (!event) return "Henüz kayıt yok.";
    if (isTaskCreatedEvent(event)) return "Görev oluşturuldu: " + (event.text || "—");
    if (isTaskCompletedEvent(event)) return "Görev tamamlandı: " + (event.text || "—");
    return event.text || "—";
  }

  /**
   * Birleşik liste tabanı: backend/fixture log yükü. Demo’da boş; panel olayları chatTaskCreations ile eklenir.
   */
  function getBasePanelEventsFromSource() {
    var src = getLogsSourceData();
    if ((src.type === "backend" || src.type === "fixture") && window.LumosFixtures && LC.normalizeLogs) {
      var data = LC.normalizeLogs(LumosFixtures.mapLogsPayloadToPanelData(src.data), {});
      return Array.isArray(data.events) ? data.events.slice() : [];
    }
    return [];
  }

  /** Chat motor olayları: birleşik listede en yeni üstte. */
  function chatEngineEventsNewestFirst(chatList) {
    var arr = chatList || [];
    var out = [];
    for (var j = arr.length - 1; j >= 0; j--) {
      var rec = arr[j];
      if (!rec || !isPanelMotorEventType(rec.type)) continue;
      out.push(rec);
    }
    return out;
  }

  /**
   * Kayıtlar + Dashboard: ham olay nesneleri. Sıra: chat motor olayları (en yeni üstte) + backend/fixture log.
   */
  function getMergedPanelEventsList() {
    var base = getBasePanelEventsFromSource();
    var fromChat = chatEngineEventsNewestFirst(mockState.chatTaskCreations);
    return fromChat.concat(base);
  }

  /** Demo: Görevler yalnızca engineTasks (kayıt olaylarından türetilmez). */
  function getEngineTaskRowsForTasksScreen() {
    return (mockState.engineTasks || []).map(toTaskRow).filter(Boolean);
  }

  /** Son Olaylar = toDashboardItem; Son Aktivite = ham listedeki ilk olay + toActivityNote. */
  function applyDashboardFromMergedEvents(data) {
    if (!data || !data.sections) return data;
    if (!data.sections[0]) data.sections[0] = { title: "Son Olaylar", events: [] };
    var merged = getMergedPanelEventsList();
    data.sections[0].events = merged.map(toDashboardItem).filter(Boolean);
    var lastEv = merged[0] || null;
    if (data.metrics && data.metrics.length) {
      for (var mi = 0; mi < data.metrics.length; mi++) {
        if (data.metrics[mi].title === "Son Aktivite") {
          data.metrics[mi].value = lastEv ? formatTime(eventTimestamp(lastEv)) : "—";
          data.metrics[mi].note = toActivityNote(lastEv);
          break;
        }
      }
    }
    return data;
  }

  function getDashboardData() {
    var src = getDashboardSourceData();
    var data;
    if ((src.type === "backend" || src.type === "fixture") && window.LumosFixtures && LC.normalizeDashboard) {
      data = LC.normalizeDashboard(LumosFixtures.mapDashboardPayloadToPanelData(src.data), {});
    } else {
      data = LC.normalizeDashboard(LC.buildDashboardStub(src.data), src.data);
    }
    return applyDashboardFromMergedEvents(data);
  }
  /** Görevler: backend/fixture = API listesi; demo = yalnızca engineTasks satırları. Seçim fullList üzerinden. */
  function taskIdEquals(a, b) {
    return String(a == null ? "" : a) === String(b == null ? "" : b);
  }

  function applyTasksViewFromMergedFullList(data, fullList, activeFilter) {
    var af = activeFilter || "all";
    var filtered = LC.filterTaskList ? LC.filterTaskList(fullList, af) : fullList;
    var selId = mockState.selectedTaskId != null ? mockState.selectedTaskId : data.selectedId;
    data.activeFilter = af;
    data.listItems = filtered;
    data.taskCount = filtered.length;
    data.selectedId = selId;
    data.selectedTask =
      selId != null && selId !== ""
        ? (fullList.filter(function (t) { return taskIdEquals(t.id, selId); })[0] || null)
        : null;
    return data;
  }

  /** Backend/fixture satırlarına motor görevlerini ekle (aynı id varsa backend satırı kalır). */
  function mergeBackendTaskRowsWithEngine(backendRows) {
    var fromBackend = Array.isArray(backendRows) ? backendRows.slice() : [];
    var ids = {};
    var bi;
    for (bi = 0; bi < fromBackend.length; bi++) {
      if (fromBackend[bi] && fromBackend[bi].id != null) ids[String(fromBackend[bi].id)] = true;
    }
    var fullList = fromBackend.slice();
    var eng = getEngineTaskRowsForTasksScreen();
    var ei;
    for (ei = 0; ei < eng.length; ei++) {
      var er = eng[ei];
      if (!er || er.id == null) continue;
      var sid = String(er.id);
      if (ids[sid]) continue;
      fullList.push(er);
      ids[sid] = true;
    }
    return fullList;
  }

  function getTasksViewData() {
    var src = getTasksSourceData();
    if ((src.type === "backend" || src.type === "fixture") && window.LumosFixtures && LC.normalizeTasks) {
      var data = LC.normalizeTasks(LumosFixtures.mapTasksPayloadToPanelData(src.data), {});
      var fullList = mergeBackendTaskRowsWithEngine(data.listItems || []);
      var af = mockState.taskFilter || data.activeFilter || "all";
      return applyTasksViewFromMergedFullList(data, fullList, af);
    }
    var s = getEffectiveState();
    var fullList = getEngineTaskRowsForTasksScreen();
    var sMerged = {};
    for (var sk in s) sMerged[sk] = s[sk];
    sMerged.taskList = fullList;
    var data = LC.normalizeTasks(LC.buildTasksStub(sMerged), sMerged);
    var af = mockState.taskFilter || data.activeFilter || "all";
    return applyTasksViewFromMergedFullList(data, fullList, af);
  }
  function getSandboxData() {
    var src = getSandboxSourceData();
    if ((src.type === "backend" || src.type === "fixture") && window.LumosFixtures && LC.normalizeSandbox) return LC.normalizeSandbox(LumosFixtures.mapSandboxPayloadToPanelData(src.data), {});
    return LC.normalizeSandbox(LC.buildSandboxStub(src.data), src.data);
  }
  function getConfigData() {
    var src = getConfigSourceData();
    if ((src.type === "backend" || src.type === "fixture") && window.LumosFixtures && LC.normalizeConfig) return LC.normalizeConfig(LumosFixtures.mapConfigPayloadToPanelData(src.data), {});
    return LC.normalizeConfig(LC.buildConfigStub(src.data), src.data);
  }
  function getIdentityData() {
    var src = getIdentitySourceData();
    if ((src.type === "backend" || src.type === "fixture") && window.LumosFixtures && LC.normalizeIdentity) return LC.normalizeIdentity(LumosFixtures.mapIdentityPayloadToPanelData(src.data), {});
    return LC.normalizeIdentity(LC.buildIdentityStub(src.data), src.data);
  }
  function getKeystoreData() {
    var src = getKeystoreSourceData();
    if ((src.type === "backend" || src.type === "fixture") && window.LumosFixtures && LC.normalizeKeystore) return LC.normalizeKeystore(LumosFixtures.mapKeystorePayloadToPanelData(src.data), {});
    return LC.normalizeKeystore(LC.buildKeystoreStub(src.data), src.data);
  }
  function getTrashData() {
    var src = getTrashSourceData();
    if ((src.type === "backend" || src.type === "fixture") && window.LumosFixtures && LC.normalizeTrash) {
      var data = LC.normalizeTrash(LumosFixtures.mapTrashPayloadToPanelData(src.data), {});
      data.selectedId = mockState.selectedTrashId || data.selectedId;
      data.selectedItem = (data.listItems || []).filter(function (i) { return i.id === (mockState.selectedTrashId || data.selectedId); })[0] || data.selectedItem;
      return data;
    }
    var s = getEffectiveState();
    return LC.normalizeTrash(LC.buildTrashStub(s), s);
  }

  /** Sekme süzgeci: Görevler sekmesi task_created ve task_completed satırlarını da gösterir. */
  function filterMergedLogEventsForKayitlar(merged, activeFilterId) {
    if (!activeFilterId || activeFilterId === "all") return merged;
    var logFilters = LC.LOG_FILTERS || [];
    var kf = null;
    for (var fi = 0; fi < logFilters.length; fi++) {
      if (logFilters[fi].id === activeFilterId) {
        kf = logFilters[fi].kind;
        break;
      }
    }
    if (kf == null) return merged;
    return merged.filter(function (e) {
      if (!e) return false;
      if (e.kind === kf) return true;
      if (kf !== "görev") return false;
      return e.kind === "task_created" || e.kind === "task_completed";
    });
  }

  /** Kayıtlar: birleşik olaylar → toLogRow → sekme süzgeci → görünen liste. */
  function applyLogsViewFromMerged(data, mergedEvents, activeFilterId) {
    var logRows = mergedEvents.map(toLogRow).filter(Boolean);
    var af = activeFilterId || "all";
    var shown = filterMergedLogEventsForKayitlar(logRows, af);
    data.activeFilter = af;
    data.events = shown;
    data.logLineCount = shown.length;
    return data;
  }

  function getLogsData() {
    var src = getLogsSourceData();
    var mergedEvents = getMergedPanelEventsList();
    if ((src.type === "backend" || src.type === "fixture") && window.LumosFixtures && LC.normalizeLogs) {
      var data = LC.normalizeLogs(LumosFixtures.mapLogsPayloadToPanelData(src.data), {});
      var af = mockState.logFilter || data.activeFilter || "all";
      return applyLogsViewFromMerged(data, mergedEvents, af);
    }
    var s = getEffectiveState();
    var data = LC.normalizeLogs(LC.buildLogsStub(s), s);
    var af = mockState.logFilter || data.activeFilter || "all";
    return applyLogsViewFromMerged(data, mergedEvents, af);
  }
  function getSystemStatusData() {
    var src = getSystemSourceData();
    if ((src.type === "backend" || src.type === "fixture") && window.LumosFixtures && LC.normalizeSystem) return LC.normalizeSystem(LumosFixtures.mapSystemPayloadToPanelData(src.data), {});
    return LC.normalizeSystem(LC.buildSystemStub(src.data), src.data);
  }

  function getTopbarData() {
    var m = getEffectiveState();
    var badges = [
      { label: getBadgeLabel("mode", m.appMode), variant: getBadgeVariant(getBadgeLabel("mode", m.appMode)) },
      { label: getBadgeLabel("lock", m.keystoreState === "Kilitli" ? "LOCKED" : "UNLOCKED"), variant: getBadgeVariant(getBadgeLabel("lock", m.keystoreState === "Kilitli" ? "LOCKED" : "UNLOCKED")) },
    ];
    if (m.sandboxMode) badges.push({ label: "KORUMALI ALAN", variant: "badge-sandbox" });
    return { basePath: m.basePath || "—", badges: badges };
  }

  function getSidebarData() {
    var m = getEffectiveState();
    return { workspaceName: m.workspaceName || "—", branchName: m.branchName || "—" };
  }

  // ——— Build helpers (adapter çıktısını HTML'e çevirir) ———
  function buildMetric(m) {
    var value = m.value;
    if (m.valueBadge) value = StatusBadge(m.valueBadge.label, m.valueBadge.variant) + (value != null && value !== "" ? value : "");
    if (value == null || value === "") value = "—";
    return MetricCard(m.title, value, m.note);
  }

  function buildMetricCards(metrics) {
    var html = "";
    for (var i = 0; i < metrics.length; i++) html += buildMetric(metrics[i]);
    return html;
  }

  function buildSection(title, bodyHtml) {
    return SectionCard(title, bodyHtml);
  }

  function buildBadge(label, variant) {
    return StatusBadge(label, variant || getBadgeVariant(label));
  }

  function buildEmptyState(title, desc) {
    return EmptyState(title || "Henüz veri yok", desc || EMPTY_DESC_DEFAULT);
  }

  function buildDetailRows(rows) {
    var html = "";
    for (var i = 0; i < rows.length; i++) html += "<p><strong>" + rows[i].label + ":</strong> " + (rows[i].value != null ? rows[i].value : "—") + "</p>";
    return html;
  }

  function buildDetailPanel(title, bodyHtml) {
    return DetailPanel(title, bodyHtml);
  }

  // ——— Ortak bileşenler (UI primitives) ———
  function renderMetricCards(items) {
    var html = "";
    for (var i = 0; i < items.length; i++) {
      var it = items[i];
      html += MetricCard(it.title, it.value, it.techNote);
    }
    return html;
  }

  function renderSection(title, bodyHtml) {
    return SectionCard(title, bodyHtml);
  }

  function renderEmptyState(title, desc) {
    return EmptyState(title, desc);
  }

  // ——— Ortak bileşenler (tekrar kullanılabilir; kopyala-yapıştır yok) ———
  function ViewHeader(title, subtitle) {
    var sub = subtitle ? '<p class="view-subtitle">' + subtitle + "</p>" : "";
    return '<div class="view-header"><h1>' + title + "</h1>" + sub + "</div>";
  }

  function EmptyState(title, desc) {
    title = title || "Henüz veri yok";
    desc = desc || EMPTY_DESC_DEFAULT;
    return '<div class="empty-state"><p class="empty-title">' + title + "</p><p class=\"empty-desc\">" + desc + "</p></div>";
  }

  function StatusBadge(label, variant) {
    var cls = "badge " + (variant || getBadgeVariant(label));
    return '<span class="' + cls + '">' + label + "</span>";
  }

  function MetricCard(title, value, techNote) {
    var note = techNote ? '<p class="text-muted-small">' + techNote + "</p>" : "";
    return '<div class="metric-card"><div class="metric-title">' + title + "</div><div class=\"metric-value\">" + value + "</div>" + note + "</div>";
  }

  function SectionCard(title, bodyHtml) {
    return '<div class="section-card"><h2 class="section-title">' + title + "</h2><div class=\"section-body\">" + bodyHtml + "</div></div>";
  }

  function EventList(events) {
    if (!events || events.length === 0) return '<ul class="event-list"><li>—</li></ul>';
    var html = '<ul class="event-list">';
    for (var i = 0; i < events.length; i++) {
      var e = events[i];
      html += "<li><span class=\"event-time\">" + formatTime(e.ts) + "</span> [" + (e.kind || "") + "] " + (e.text || "") + "</li>";
    }
    return html + "</ul>";
  }

  function DetailPanel(title, bodyHtml) {
    return '<div class="detail-panel"><div class="detail-title">' + title + "</div><div class=\"detail-body\">" + bodyHtml + "</div></div>";
  }

  // ——— Sidebar (adapter verisi) ———
  function renderSidebar() {
    var nav = document.getElementById("nav-menu");
    if (!nav) return;
    var current = getCurrentScreen();
    nav.innerHTML = Object.keys(SCREENS)
      .map(function (key) {
        var s = SCREENS[key];
        var active = current.id === s.id ? ' class="active"' : "";
        return '<a href="' + s.hash + '"' + active + ">" + s.label + "</a>";
      })
      .join("");
    var data = getSidebarData();
    var ws = document.getElementById("sidebar-workspace");
    if (ws) ws.textContent = "Çalışma Alanı: " + data.workspaceName;
    var meta = document.getElementById("sidebar-meta");
    if (meta) meta.textContent = "Dal: " + data.branchName + " · Mod: DEV";
  }

  /** Veri kaynağı (tek satır); teknik endpoint listesi yok */
  function renderPostsApiBaseLine(F) {
    if (!F || !F.getBase) return "";
    return (
      '<p class="posts-api-base-line">' +
      '<span class="posts-api-base-label">Bağlantı</span> ' +
      '<code>' +
      F.escapeHtml(F.getBase()) +
      "</code></p>"
    );
  }

  // ——— Topbar (adapter verisi + demo senaryo seçici) ———
  function renderTopbar() {
    var screen = getCurrentScreen();
    var titleEl = document.getElementById("topbar-pagetitle");
    if (titleEl) titleEl.textContent = screen.label || "—";
    var data = getTopbarData();
    var baseEl = document.getElementById("topbar-base-label");
    if (baseEl) {
      var apiPart = "";
      if (typeof window.LumosFeedApi !== "undefined" && window.LumosFeedApi.getBase) {
        apiPart = " · API: " + window.LumosFeedApi.getBase();
      }
      baseEl.textContent = "Temel: " + data.basePath + apiPart;
    }
    var wrap = document.getElementById("topbar-badges");
    if (wrap) {
      var html = "";
      for (var i = 0; i < data.badges.length; i++) html += buildBadge(data.badges[i].label, data.badges[i].variant);
      wrap.innerHTML = html;
    }
    var actionsEl = document.getElementById("topbar-actions");
    if (actionsEl) {
      var list = getScenarioList();
      var opts = list.map(function (s) {
        return '<option value="' + s.id + '"' + (s.id === currentScenario ? ' selected' : '') + ">" + s.label + "</option>";
      }).join("");
      var dataSourceOpts = '<option value="demo"' + (useFixtureData ? '' : ' selected') + '>Demo</option><option value="fixture"' + (useFixtureData ? ' selected' : '') + '>Fixture</option>';
      actionsEl.innerHTML =
        '<div class="topbar-actions-dev">' +
        '<span class="topbar-demo-label">DEV</span>' +
        '<select id="demo-scenario-select" class="demo-scenario-select" aria-label="Demo senaryosu">' +
        opts +
        "</select>" +
        '<select id="data-source-select" class="demo-scenario-select" aria-label="Veri kaynağı" title="Veri kaynağı">' +
        dataSourceOpts +
        "</select></div>";
      var sel = document.getElementById("demo-scenario-select");
      if (sel) sel.addEventListener("change", function () { currentScenario = sel.value; refresh(); });
      var dataSel = document.getElementById("data-source-select");
      if (dataSel) dataSel.addEventListener("change", function () { useFixtureData = dataSel.value === "fixture"; refresh(); });
    }
  }

  // ——— Routing ———
  /** #feed | #rated-high | #rated-low → Akış ekranı + sekme (SCREENS.feed ile aynı view) */
  function feedTabFromLocationHash() {
    var raw = window.location.hash || "";
    var h = raw.toLowerCase();
    if (h === "#rated-high" || h === "#rated_high") return "rated-high";
    if (h === "#rated-low" || h === "#rated_low") return "rated-low";
    if (h === "#feed") return "feed";
    return null;
  }

  function getCurrentScreen() {
    var hash = (window.location.hash || DEFAULT_HASH).toLowerCase();
    if (hash.length <= 1) return SCREENS.dashboard;
    var id = hash.slice(1);
    if (SCREENS[id]) return SCREENS[id];
    var ft = feedTabFromLocationHash();
    if (ft) {
      return { id: "feed", label: SCREENS.feed.label, hash: window.location.hash || "#feed", feedTab: ft };
    }
    return { id: "_empty", label: "", hash: hash };
  }

  // ——— Guidance card (Durum / Engel / Sonraki adım) ———
  function buildGuidanceCard() {
    var g = getGuidanceSourceData().data;
    if (!g) g = { mode: "—", lock: "—", consent: false, blocked_reason: null, next_step: null };
    var modeLabel = g.mode === "online" ? "Çevrimiçi" : "Çevrimdışı";
    var lockLabel = (g.lock || "").toUpperCase() === "UNLOCKED" ? "Açık" : "Kilitli";
    var consentLabel = g.consent ? "Açık" : "Kapalı";
    var durumHtml = "<p class=\"text-muted-small\"><strong>Mod:</strong> " + modeLabel + " · <strong>Kilit:</strong> " + lockLabel + " · <strong>Genel onay:</strong> " + consentLabel + "</p>";
    var engelHtml = (g.blocked_reason && g.blocked_reason.trim()) ? ("<p>" + g.blocked_reason + "</p>") : "<p class=\"text-muted-small\">Şu anda engel yok.</p>";
    var nextHtml = (g.next_step && g.next_step.trim()) ? ("<p>" + g.next_step + "</p>") : "<p class=\"text-muted-small\">Hazır.</p>";
    return SectionCard("Durum", durumHtml) + SectionCard("Engel", engelHtml) + SectionCard("Sonraki adım", nextHtml);
  }

  // ——— Ekran: Gösterge Paneli (adapter + build) ———
  function renderDashboard() {
    var data = getDashboardData();
    var cards = buildMetricCards(data.metrics);
    var warningsHtml = "";
    if (data.sections[1].warnings && data.sections[1].warnings.length > 0) {
      warningsHtml = "<ul class=\"event-list\">";
      for (var w = 0; w < data.sections[1].warnings.length; w++) {
        warningsHtml += "<li>" + buildBadge("UYARI", "badge-warning") + " " + data.sections[1].warnings[w] + "</li>";
      }
      warningsHtml += "</ul>";
    } else {
      warningsHtml = "<p class=\"text-muted-small\">Uyarı veya not yok.</p>";
    }
    var guidanceHtml = '<div class="guidance-cards">' + buildGuidanceCard() + "</div>";
    var sections =
      buildSection("Son Olaylar", EventList(data.sections[0].events)) +
      buildSection("Uyarılar ve notlar", warningsHtml) +
      buildSection("Durum ve rehber", guidanceHtml) +
      buildSection("Hızlı geçişler", '<p><a href="#feed" class="inline-link">Akış</a> (API) · <a href="#tasks" class="inline-link">Görevler</a> · <a href="#sandbox" class="inline-link">Korumalı Alan</a> · <a href="#config" class="inline-link">Yapılandırma</a> · <a href="#logs" class="inline-link">Kayıtlar</a></p><p class="text-muted-small">Hash ile sayfa yenilenmeden geçiş.</p>');
    return ViewHeader(data.title, data.subtitle) + '<div class="cards-grid">' + cards + "</div>" + sections;
  }

  // ——— Ekran: Görevler (adapter + build) ———
  function renderTasks() {
    var data = getTasksViewData();
    var listUpdatedLine = (data.listUpdatedText || (data.listUpdated ? formatTime(data.listUpdated) : null))
      ? '<p class="text-muted-small">' + (data.listUpdatedText || ("Liste son güncelleme: " + formatTime(data.listUpdated))) + "</p>" : "";
    var taskCountLine = (data.taskCount != null && data.taskCount !== undefined) ? '<p class="text-muted-small">Görev sayısı: ' + data.taskCount + "</p>" : "";
    var tasksFilePathLine = data.tasksFilePath ? '<p class="text-muted-small">Görev dosyası: ' + (data.tasksFilePath || "—") + "</p>" : "";
    var tabsHtml = data.filters.map(function (f) {
      var active = f.id === data.activeFilter ? " active" : "";
      return '<button type="button" class="log-tab task-filter-tab' + active + '" data-task-filter="' + f.id + '">' + f.label + "</button>";
    }).join("");
    var listBody = (listUpdatedLine || taskCountLine || tasksFilePathLine ? (listUpdatedLine || "") + (taskCountLine || "") + (tasksFilePathLine || "") : "") + '<div class="task-filters" id="task-filters">' + tabsHtml + "</div>";
    if (data.listItems.length === 0) {
      listBody += buildEmptyState(data.emptyListTitle, data.emptyListDesc);
    } else {
      var listItems = "";
      data.listItems.forEach(function (t) {
        var sel = data.selectedId === t.id ? " selected" : "";
        var badge = buildBadge(t.status, getTaskStatusVariant(t.status));
        listItems += '<li class="list-item' + sel + '" data-task-id="' + t.id + '"><span class="task-list-badge">' + badge + "</span> " + t.title + "</li>";
      });
      listBody += '<ul class="list-selectable" id="task-list">' + listItems + "</ul>";
    }
    var listSection = buildSection("Görev Listesi", listBody);

    var detailContent;
    if (!data.selectedTask) {
      detailContent = buildEmptyState("Görev seçilmedi", "Listeden bir görev seçin.");
    } else {
      var t = data.selectedTask;
      var lastRunVal = t.lastRun ? formatTime(t.lastRun) : "—";
      var lastRunNote = t.lastRun ? "Son çalıştırma (mock)." : "Henüz çalıştırılmadı.";
      var outVal = (t.outputSummary || "—").slice(0, 120);
      if ((t.outputSummary || "").length > 120) outVal += "…";
      var metricRows = buildMetricCards([
        { title: "Son çalıştırma", value: lastRunVal, note: lastRunNote },
        { title: "Guard sonucu", value: t.guardResult || "—", note: "Guard: izinli / reddedildi / engelli." },
        { title: "Çıktı özeti", value: outVal, note: "Çıktı özeti." },
      ]);
      detailContent =
        "<p><strong>" + t.title + "</strong></p>" +
        "<p>Durum: " + buildBadge(t.status, getTaskStatusVariant(t.status)) + " · Güncelleme: " + formatTime(t.updated) + "</p>" +
        '<div class="detail-metrics">' + metricRows + "</div>";
    }
    var detail = buildDetailPanel(data.detailTitle, detailContent);
    var runNoteSection = buildSection(data.runNoteTitle, "<p class=\"text-muted-small\">" + data.runNoteBody + "</p>");
    return ViewHeader(data.title, data.subtitle) + '<div class="split-view">' + listSection + detail + "</div>" + runNoteSection;
  }

  // ——— Ekran: Korumalı Alan (adapter + build) ———
  function renderSandbox() {
    var data = getSandboxData();
    var cards = buildMetricCards(data.metrics);
    var sectionsHtml = "";
    for (var i = 0; i < data.sections.length; i++) sectionsHtml += buildSection(data.sections[i].title, data.sections[i].body);
    return ViewHeader(data.title, data.subtitle) + '<div class="cards-grid">' + cards + "</div>" + sectionsHtml;
  }

  // ——— Ekran: Yapılandırma (adapter + build) ———
  function renderConfig() {
    var data = getConfigData();
    var cards = buildMetricCards(data.metrics);
    var sectionsHtml = "";
    for (var i = 0; i < data.sections.length; i++) sectionsHtml += buildSection(data.sections[i].title, data.sections[i].body);
    return ViewHeader(data.title, data.subtitle) + '<div class="cards-grid">' + cards + "</div>" + sectionsHtml;
  }

  // ——— Ekran: Kimlik (adapter + build) ———
  function renderIdentity() {
    var data = getIdentityData();
    var cards = buildMetricCards(data.metrics);
    var sectionsHtml = "";
    for (var i = 0; i < data.sections.length; i++) sectionsHtml += buildSection(data.sections[i].title, data.sections[i].body);
    return ViewHeader(data.title, data.subtitle) + '<div class="cards-grid">' + cards + "</div>" + sectionsHtml;
  }

  // ——— Ekran: Anahtar Kasası (adapter + build) ———
  function renderKeystore() {
    var data = getKeystoreData();
    var cards = buildMetricCards(data.metrics);
    var sectionsHtml = "";
    for (var i = 0; i < data.sections.length; i++) sectionsHtml += buildSection(data.sections[i].title, data.sections[i].body);
    return ViewHeader(data.title, data.subtitle) + '<div class="cards-grid">' + cards + "</div>" + sectionsHtml;
  }

  /** GET /posts/trash — yalnızca backend yanıtı (trashPosts); başka kaynak yok */
  var trashViewState = {
    status: "idle",
    trashPosts: [],
    error: "",
    loadId: 0,
    actionBusyByPostId: {},
    actionBusyAll: false,
    flash: null,
  };

  function trashPreviewText(s) {
    var t = s == null ? "" : String(s).trim();
    if (t.length <= 70) return t;
    return t.slice(0, 67) + "…";
  }

  /** Trash için API teknik mesajları (seçim/liste uyumsuzluğunda) kullanıcıya gösterme */
  function isTrashFlashTechnicalNotFound(msg) {
    var low = String(msg || "").toLowerCase();
    return low.indexOf("post not found in trash") !== -1 || low.indexOf("not found in trash") !== -1;
  }

  /** @param {*} F LumosFeedApi */
  function trashFlashHtml(F, ctx) {
    ctx = ctx || {};
    if (!trashViewState.flash || !trashViewState.flash.text) return "";
    if (trashViewState.flash.kind === "error") {
      var msg = trashViewState.flash.text;
      if (isTrashFlashTechnicalNotFound(msg)) {
        if (ctx.isLoading) return "";
        if (typeof ctx.postsLength === "number" && ctx.postsLength > 0) return "";
      }
    }
    var kind = trashViewState.flash.kind === "error" ? "error" : "ok";
    return (
      '<p class="feed-action-flash feed-action-flash--' +
      kind +
      '" role="' +
      (kind === "error" ? "alert" : "status") +
      '">' +
      F.escapeHtml(trashViewState.flash.text) +
      "</p>"
    );
  }

  /** Seçili id listede yoksa null; otomatik ilk öğe seçilmez */
  function syncTrashSelectionToList(trashPosts) {
    var safePosts = Array.isArray(trashPosts) ? trashPosts : [];
    if (safePosts.length === 0) {
      mockState.selectedTrashId = null;
      return;
    }
    var selectedId = String(mockState.selectedTrashId || "");
    if (!selectedId) return;
    var exists = false;
    for (var i = 0; i < safePosts.length; i++) {
      if (String(safePosts[i].id) === selectedId) {
        exists = true;
        break;
      }
    }
    if (!exists) mockState.selectedTrashId = null;
  }

  /** API /posts/trash gövdesini panel trash satırına çevir; en yeni taşınan üstte */
  function mapTrashItemsFromApiData(data) {
    var rawItems = Array.isArray(data)
      ? data
      : data && Array.isArray(data.items)
        ? data.items
        : [];
    var rows = rawItems.map(function (item) {
      return {
        id: item && item.id != null ? String(item.id) : "",
        content: item && item.content != null ? String(item.content) : "",
        username:
          item &&
          item.user &&
          typeof item.user === "object" &&
          item.user.username != null
            ? String(item.user.username)
            : "",
        deletedAt:
          item && item.deletedAt != null
            ? String(item.deletedAt)
            : item && item.deleted_at != null
              ? String(item.deleted_at)
              : "",
      };
    });
    rows.sort(function (a, b) {
      var ta = new Date(a.deletedAt || 0).getTime();
      var tb = new Date(b.deletedAt || 0).getTime();
      if (Number.isNaN(ta)) ta = 0;
      if (Number.isNaN(tb)) tb = 0;
      return tb - ta;
    });
    return rows;
  }

  /**
   * Çöpü Boşalt: DELETE → fetchTrash → fetchFeed; state yalnızca GET yanıtlarıyla dolar.
   */
  function handleEmptyTrash() {
    var F = window.LumosFeedApi;
    if (!F || !F.getBase) {
      return;
    }
    if (trashViewState.actionBusyAll) {
      return;
    }
    if (!window.confirm("Çöpteki tüm kayıtlar kalıcı silinecek. Emin misin?")) return;
    trashViewState.actionBusyAll = true;
    trashViewState.flash = null;
    renderMain();

    if (!F.emptyTrash || typeof F.emptyTrash !== "function" || !F.getTrashList) {
      trashViewState.actionBusyAll = false;
      trashViewState.flash = { kind: "error", text: "Çöp boşaltılamadı (istemci güncel değil)" };
      renderMain();
      return;
    }
    F.emptyTrash()
      .then(function () {
        console.log("ACTION_EMPTY", { url: F.getBase() + "/posts/trash" });
        return fetchTrash();
      })
      .then(function () {
        return fetchFeed({ forceTab: "feed" });
      })
      .then(function () {
        trashViewState.actionBusyAll = false;
        mockState.selectedTrashId = null;
        trashViewState.flash = { kind: "ok", text: "Çöp boşaltıldı" };
        renderMain();
      })
      .catch(function (err) {
        trashViewState.actionBusyAll = false;
        trashViewState.flash = {
          kind: "error",
          text: "Çöp boşaltılamadı: " + ((err && err.message) || String(err)),
        };
        renderMain();
      });
  }

  /**
   * GET /posts/trash — tam replace; trashPosts yalnızca bu yanıt.
   * @returns {Promise<void>}
   */
  function fetchTrash() {
    var F = window.LumosFeedApi;
    if (!F || !F.getTrashList) {
      return Promise.reject(new Error("feed-api yok"));
    }
    var url = F.getBase() + "/posts/trash";
    trashViewState.loadId = (trashViewState.loadId || 0) + 1;
    var myLoad = trashViewState.loadId;
    trashViewState.status = "loading";
    trashViewState.error = "";
    trashViewState.trashPosts = [];
    console.log("FETCH_TRASH", { url: url });
    return F.getTrashList()
      .then(function (data) {
        if (myLoad !== trashViewState.loadId) return;
        trashViewState.trashPosts = mapTrashItemsFromApiData(data);
        syncTrashSelectionToList(trashViewState.trashPosts);
        if (trashViewState.flash && trashViewState.flash.kind === "error") trashViewState.flash = null;
        trashViewState.status = "ok";
        if (getCurrentScreen().id === "trash") renderMain();
      })
      .catch(function (e) {
        if (myLoad !== trashViewState.loadId) return;
        trashViewState.error = e.message || String(e);
        trashViewState.status = "error";
        trashViewState.trashPosts = [];
        if (getCurrentScreen().id === "trash") renderMain();
      });
  }

  // ——— Ekran: Silinenler (adapter + build) ———
  function renderTrash() {
    var F = window.LumosFeedApi;
    if (!F) return renderEmptyState("Silinenler", "feed-api.js yüklenmedi.");

    if (trashViewState.status === "idle") {
      fetchTrash();
    }

    if (trashViewState.status === "loading") {
      return (
        ViewHeader("Silinenler", "Liste yükleniyor") +
        renderPostsApiBaseLine(F) +
        trashFlashHtml(F, { isLoading: true }) +
        '<div class="feed-loading">Yükleniyor…</div>'
      );
    }

    if (trashViewState.status === "error") {
      return (
        ViewHeader("Silinenler", "Bağlantı sorunu") +
        renderPostsApiBaseLine(F) +
        trashFlashHtml(F, { postsLength: 0 }) +
        '<div class="feed-panel-error" role="alert">' +
        '<p class="feed-panel-error-title">İstek tamamlanamadı</p>' +
        '<p class="feed-panel-error-detail">' +
        F.escapeHtml(trashViewState.error) +
        "</p>" +
        "</div>"
      );
    }

    var posts = trashViewState.trashPosts || [];
    syncTrashSelectionToList(posts);
    var allActionDisabled = posts.length === 0 || trashViewState.actionBusyAll;
    var emptyTrashBtnDisabledAttr = allActionDisabled ? " disabled" : "";
    var topActionsHtml =
      '<div class="feed-toolbar log-tabs">' +
      '<button type="button" id="lumos-trash-empty-all" class="log-tab" data-trash-action-all="empty"' +
      emptyTrashBtnDisabledAttr +
      ">Çöpü Boşalt</button>" +
      "</div>";
    var latestDeletedAt = "";
    for (var i = 0; i < posts.length; i++) {
        var d = posts[i] && posts[i].deletedAt ? String(posts[i].deletedAt) : "";
      if (!d) continue;
      if (!latestDeletedAt || new Date(d).getTime() > new Date(latestDeletedAt).getTime()) {
        latestDeletedAt = d;
      }
    }
    var metrics = [
      { title: "Öğe Sayısı", value: String(posts.length), note: "Çöp kutusunda" },
      {
        title: "Son Taşıma",
        value: latestDeletedAt ? feedFormatCreatedAtReadable(latestDeletedAt) : "—",
        note: "En son taşınan",
      },
    ];
    var summary = buildMetricCards(metrics);

    var selectedId = mockState.selectedTrashId;
    var selectedPost = null;
    if (selectedId) {
      for (var si = 0; si < posts.length; si++) {
        if (String(posts[si].id) === String(selectedId)) {
          selectedPost = posts[si];
          break;
        }
      }
    }

    var listSection;
    if (posts.length === 0) {
      listSection = buildSection(
        "Liste",
        buildEmptyState("Silinen kayıt yok", "Çöp kutusu boş.")
      );
    } else {
      var listHtml = "";
      for (var li = 0; li < posts.length; li++) {
        var p = posts[li] || {};
        var pid = p.id != null ? String(p.id) : "";
        var uname = p.username ? String(p.username) : "—";
        var movedAt = p.deletedAt ? feedFormatCreatedAtReadable(p.deletedAt) : "—";
        var preview = trashPreviewText(p.content || "");
        var sel = selectedPost && String(selectedPost.id) === pid ? " selected" : "";
        var busy = !!trashViewState.actionBusyByPostId[pid] || trashViewState.actionBusyAll;
        var disabledAttr = busy ? " disabled" : "";
        listHtml +=
          '<li class="list-item' +
          sel +
          '" data-trash-id="' +
          F.escapeHtml(pid) +
          '">@' +
          F.escapeHtml(uname) +
          " · " +
          F.escapeHtml(preview) +
          " · " +
          F.escapeHtml(movedAt) +
          '<div class="trash-item-actions">' +
          '<button type="button" class="post-feed-action-btn post-feed-action-btn--restore" data-trash-action="restore" data-trash-post-id="' +
          F.escapeHtml(pid) +
          '"' +
          disabledAttr +
          ">Geri Yükle</button>" +
          '<button type="button" class="post-feed-action-btn post-feed-action-btn--danger" data-trash-action="permanent-delete" data-trash-post-id="' +
          F.escapeHtml(pid) +
          '"' +
          disabledAttr +
          ">Kalıcı Sil</button>" +
          "</div>" +
          "</li>";
      }
      listSection = buildSection("Liste", '<ul class="list-selectable" id="trash-list">' + listHtml + "</ul>");
    }

    var detailBody = selectedPost
      ? buildDetailRows([
          {
            label: "Kullanıcı",
            value: selectedPost.username ? String(selectedPost.username) : "—",
          },
          { label: "İçerik", value: selectedPost.content != null ? String(selectedPost.content) : "—" },
          {
            label: "Taşınma",
            value: selectedPost.deletedAt ? feedFormatCreatedAtReadable(selectedPost.deletedAt) : "—",
          },
          { label: "Post ID", value: selectedPost.id != null ? String(selectedPost.id) : "—" },
        ])
      : "<p class=\"screen-placeholder\">Detay için listeden bir kayıt seçin.</p>";
    var detail = buildDetailPanel("Kayıt Detayı", detailBody);
    return (
      ViewHeader("Silinenler", posts.length ? posts.length + " kayıt" : "Silinen gönderiler") +
      renderPostsApiBaseLine(F) +
      topActionsHtml +
      trashFlashHtml(F, { postsLength: posts.length }) +
      '<div class="cards-grid">' +
      summary +
      "</div>" +
      '<div class="split-view">' +
      listSection +
      detail +
      "</div>"
    );
  }

  // ——— Ekran: Kayıtlar (adapter + build) ———
  function renderLogs() {
    var data = getLogsData();
    var metaLine = "";
    if (data.logUpdatedText || data.logFileUpdated) metaLine += '<p class="text-muted-small">' + (data.logUpdatedText || ("Kayıt dosyası son güncelleme: " + formatTime(data.logFileUpdated))) + "</p>";
    if (data.logLocation) metaLine += '<p class="text-muted-small">Dosya: ' + (data.logLocation || "") + "</p>";
    if (data.logLineCount != null && data.logLineCount !== undefined) metaLine += '<p class="text-muted-small">Görüntülenen satır: ' + data.logLineCount + "</p>";
    var tabsHtml = data.filters.map(function (f) {
      var active = f.id === data.activeFilter ? " active" : "";
      return '<button type="button" class="log-tab' + active + '" data-log-filter="' + f.id + '">' + f.label + "</button>";
    }).join("");
    return ViewHeader(data.title, data.subtitle) + (metaLine ? metaLine : "") + '<div class="log-tabs" id="log-tabs">' + tabsHtml + "</div>" + buildSection(data.sectionTitle, EventList(data.events));
  }

  // ——— Ekran: Sistem Durumu (adapter + build) ———
  function renderSystem() {
    var data = getSystemStatusData();
    var cards = "";
    for (var i = 0; i < data.healthCards.length; i++) {
      var c = data.healthCards[i];
      var value = c.status === "—" ? "—" : buildBadge(c.status, getHealthStatusVariant(c.status));
      cards += MetricCard(c.title, value, c.note);
    }
    return ViewHeader(data.title, data.subtitle) + '<div class="cards-grid">' + cards + "</div>";
  }

  function escapeHtmlYanit(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /** Oturum içi sohbet (sayfa yenilenene kadar bellekte; hash değişince sıfırlanmaz). */
  var chatViewState = {
    messages: [],
  };

  /** Sadece "görev oluştur" komutu (sonrasında boşluk, iki nokta veya satır sonu); "görev oluşturum" eşleşmez. */
  var GOREV_OLUSTUR_PREFIX_RE = /^görev oluştur(?=\s|:|$)/i;
  var GOREV_TAMAMLA_PREFIX_RE = /^görev tamamla(?=\s|:|$)/i;

  /**
   * @returns {{ taskName: string } | null} null = bu bir görev oluştur komutu değil; taskName = önek çıkarılmış ad (boş olabilir)
   */
  function parseGorevOlusturCommand(raw) {
    var t = String(raw || "").trim();
    var m = GOREV_OLUSTUR_PREFIX_RE.exec(t);
    if (!m) return null;
    var rest = t.slice(m[0].length).replace(/^\s*:?\s*/, "").trim();
    return { taskName: rest };
  }

  /**
   * @returns {{ ref: string } | null} ref = id veya başlık (boş olabilir)
   */
  function parseGorevTamamlaCommand(raw) {
    var t = String(raw || "").trim();
    var m = GOREV_TAMAMLA_PREFIX_RE.exec(t);
    if (!m) return null;
    var rest = t.slice(m[0].length).replace(/^\s*:?\s*/, "").trim();
    return { ref: rest };
  }

  /**
   * Görev motoru komutları: state + olay kuyruğu.
   * @returns {{ text: string, depth?: string, blocks?: object } | null} null → genel asistan yanıtına düş
   */
  function tryHandleTaskEngineChatCommand(userText) {
    var trimmed = String(userText || "").trim();
    var parsedCreate = parseGorevOlusturCommand(trimmed);
    if (parsedCreate) {
      if (!parsedCreate.taskName) {
        return { text: "Görev adı eksik. Örnek: görev oluştur alışveriş", depth: "simple" };
      }
      var task = LumosMinTaskEngine.createTask(parsedCreate.taskName);
      if (!task) {
        return { text: "Görev adı eksik. Örnek: görev oluştur alışveriş", depth: "simple" };
      }
      appendPanelEngineEvent(createTaskCreatedEvent(task.id, task.title));
      return { text: 'Görev oluşturuldu: "' + task.title + '".', depth: "simple" };
    }
    var parsedDone = parseGorevTamamlaCommand(trimmed);
    if (parsedDone) {
      if (!parsedDone.ref) {
        return { text: "Görev adı eksik. Örnek: görev tamamla alışveriş", depth: "simple" };
      }
      var result = LumosMinTaskEngine.completeTask(parsedDone.ref);
      if (!result.ok) {
        return { text: "Tamamlanacak görev bulunamadı.", depth: "simple" };
      }
      appendPanelEngineEvent(createTaskCompletedEvent(result.task.id, result.task.title));
      return { text: 'Görev tamamlandı: "' + result.task.title + '".', depth: "simple" };
    }
    return null;
  }

  /**
   * @param {string} userText
   * @returns {{ text: string, depth?: string, blocks?: object }}
   */
  function buildAssistantReply(userText) {
    var trimmed = String(userText || "").trim();
    var lower = trimmed.toLowerCase();
    var engineReply = tryHandleTaskEngineChatCommand(trimmed);
    if (engineReply) return engineReply;
    if (lower.indexOf("görev") !== -1) {
      return {
        text: "Görevler ekranından listeyi görebilirsin. Yeni görev eklemek için mesajın tam olarak görev oluştur ile başlamalı (ör. görev oluştur başlık).",
        depth: "simple",
      };
    }
    if (lower.indexOf("kayıt") !== -1) {
      return {
        text: "Kayıtlar ekranına geçip son çıktıyı inceleyebilirsin.",
        depth: "simple",
      };
    }
    if (lower.indexOf("akış") !== -1) {
      return {
        text: "Akış ekranına geçip güncel listeyi görebilirsin.",
        depth: "simple",
      };
    }
    return {
      text: "Görevler, Kayıtlar veya Akış ekranlarından durumu kontrol edebilirsin; burada yalnızca sohbet var.",
      depth: "simple",
    };
  }

  function submitChatFromComposer() {
    var ta = document.getElementById("lumos-chat-input");
    if (!ta) return;
    var text = ta.value != null ? String(ta.value).trim() : "";
    if (!text) return;
    ta.value = "";
    chatViewState.messages.push({ role: "user", text: text });
    var reply = buildAssistantReply(text);
    chatViewState.messages.push({
      role: "assistant",
      text: reply.text,
      depth: reply.depth,
      blocks: reply.blocks,
    });
    renderMain();
    requestAnimationFrame(function () {
      var t2 = document.getElementById("lumos-chat-input");
      if (t2) {
        t2.focus();
        try {
          var len = t2.value.length;
          t2.setSelectionRange(len, len);
        } catch (e2) {
          /* ignore */
        }
      }
    });
  }

  function renderChatUl(items) {
    return (
      "<ul class=\"lumos-msg-block-list\">" +
      items
        .map(function (x) {
          return "<li>" + escapeHtmlYanit(x) + "</li>";
        })
        .join("") +
      "</ul>"
    );
  }

  /**
   * Yardımcı bloklar. depth: simple = hiçbiri; medium = tek blok (öneri > özet > anladım sırası);
   * complex veya yok = dolu alanların tamamı.
   */
  function renderLumosBlocksHtml(b, depth) {
    if (!b || typeof b !== "object") return "";
    var d = depth || "complex";
    if (d === "simple") return "";

    /** Yalnızca trim sonrası dolu satırlar; boş / null / anlamsız liste → blok yok */
    function recommendationItemsForRender() {
      if (!Array.isArray(b.recommendation)) return [];
      var out = [];
      for (var ri = 0; ri < b.recommendation.length; ri++) {
        var raw = b.recommendation[ri];
        if (raw == null) continue;
        var t = String(raw).trim();
        if (t) out.push(t);
      }
      return out;
    }

    function blockSummary() {
      if (!b.summary || !String(b.summary).trim()) return "";
      return (
        '<div class="lumos-msg-block">' +
        '<div class="lumos-msg-block-title">Kısa özet</div>' +
        '<div class="lumos-msg-block-body">' +
        escapeHtmlYanit(String(b.summary).trim()) +
        "</div></div>"
      );
    }
    function blockUnderstood() {
      if (!b.understood || !b.understood.length) return "";
      return (
        '<div class="lumos-msg-block">' +
        '<div class="lumos-msg-block-title">Ne anladım</div>' +
        renderChatUl(b.understood) +
        "</div>"
      );
    }
    function blockRecommendation() {
      var recItems = recommendationItemsForRender();
      if (!recItems.length) return "";
      return (
        '<div class="lumos-msg-block">' +
        '<div class="lumos-msg-block-title">Ne öneriyorum</div>' +
        renderChatUl(recItems) +
        "</div>"
      );
    }

    if (d === "medium") {
      var one = "";
      if (recommendationItemsForRender().length) one = blockRecommendation();
      else if (b.summary && String(b.summary).trim()) one = blockSummary();
      else if (b.understood && b.understood.length) one = blockUnderstood();
      return one ? '<div class="lumos-msg-blocks" style="margin-top:0.85rem">' + one + "</div>" : "";
    }

    var parts = blockSummary() + blockUnderstood() + blockRecommendation();
    return parts ? '<div class="lumos-msg-blocks" style="margin-top:0.85rem">' + parts + "</div>" : "";
  }

  function renderChat() {
    var msgs = chatViewState.messages;
    var logHtml = "";
    if (msgs.length === 0) {
      logHtml =
        '<div class="lumos-chat-empty" role="status">' +
        '<p class="lumos-chat-empty-hint">Henüz mesaj yok. Aşağıya yazıp Gönder’e basın veya Enter ile gönderin.</p>' +
        "</div>";
    }
    for (var i = 0; i < msgs.length; i++) {
      var m = msgs[i];
      if (m.role === "user") {
        logHtml +=
          '<div class="lumos-chat-msg lumos-chat-msg--user">' +
          '<div class="lumos-chat-bubble">' +
          escapeHtmlYanit(m.text) +
          "</div></div>";
      } else {
        var plain = m.text != null ? String(m.text).trim() : "";
        var bubbleHtml = plain ? '<div class="lumos-chat-bubble">' + escapeHtmlYanit(plain) + "</div>" : "";
        var blocksHtml = renderLumosBlocksHtml(m.blocks, m.depth);
        if (!bubbleHtml && !blocksHtml) continue;
        logHtml += '<div class="lumos-chat-msg lumos-chat-msg--assistant">' + bubbleHtml + blocksHtml + "</div>";
      }
    }
    return (
      '<div class="lumos-chat-root">' +
      '<div class="lumos-chat-log" role="log" aria-live="polite">' +
      logHtml +
      "</div>" +
      '<div class="lumos-chat-composer">' +
      '<div class="lumos-chat-composer-row">' +
      '<textarea id="lumos-chat-input" class="lumos-chat-input" rows="2" placeholder="Mesaj yazın…" aria-label="Mesaj girişi"></textarea>' +
      '<button type="button" id="lumos-chat-send" class="lumos-chat-send">Gönder</button>' +
      "</div></div></div>"
    );
  }

  /**
   * Sekmeye göre tek GET: feed → feedUrl; rated-high → ratedHighUrl; rated-low → ratedLowUrl (tam replace).
   */
  var feedViewState = {
    status: "idle",
    /** Son başarılı feed GET → normalize + dedupe tam liste */
    posts: [],
    error: "",
    tab: "feed",
    loadId: 0,
    actionBusyByPostId: {},
    flash: null,
  };

  function feedFlashHtml(F) {
    if (!feedViewState.flash || !feedViewState.flash.text) return "";
    var kind = feedViewState.flash.kind === "error" ? "error" : "ok";
    return (
      '<p class="feed-action-flash feed-action-flash--' +
      kind +
      '" role="' +
      (kind === "error" ? "alert" : "status") +
      '">' +
      F.escapeHtml(feedViewState.flash.text) +
      "</p>"
    );
  }

  function feedTabLabel(tab) {
    if (tab === "rated-high") return "Rated High";
    if (tab === "rated-low") return "Rated Low";
    return "Feed";
  }

  function normalizeFeedListPayload(data) {
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.items)) return data.items;
    if (data && Array.isArray(data.posts)) return data.posts;
    return [];
  }

  /** Aynı post id ikinci kez listelenmesin (backend feed bileşimi veya hatalı yanıtta mümkün) */
  function dedupeFeedPostsByIdPreserveOrder(arr) {
    var seen = new Set();
    var out = [];
    for (var i = 0; i < arr.length; i++) {
      var row = arr[i];
      if (!row || typeof row !== "object") continue;
      var id = row.id != null ? String(row.id) : "";
      if (!id) {
        out.push(row);
        continue;
      }
      if (seen.has(id)) continue;
      seen.add(id);
      out.push(row);
    }
    return out;
  }

  /** Tek normalize katmanı: GET → dedupe → LumosFeedApi.normalizePostForPanel */
  function buildFeedDisplayListFromResponse(data, F) {
    var list = dedupeFeedPostsByIdPreserveOrder(normalizeFeedListPayload(data));
    if (!F || typeof F.normalizePostForPanel !== "function") {
      return list;
    }
    var mapped = [];
    for (var j = 0; j < list.length; j++) {
      mapped.push(F.normalizePostForPanel(list[j]));
    }
    return mapped;
  }

  /**
   * Aktif sekmeye göre tek GET: feed | /posts/rated-high | /posts/rated-low (tam replace; client süzgeç yok).
   * @param {{ forceTab?: string }} [opts] — trash/restore sonrası feed listesini tazelemek için forceTab: "feed"
   * @returns {Promise<void>}
   */
  function fetchFeed(opts) {
    var F = window.LumosFeedApi;
    if (!F) {
      return Promise.reject(new Error("feed-api yok"));
    }
    var tab = opts && opts.forceTab != null ? opts.forceTab : feedViewState.tab || "feed";
    var url;
    if (tab === "rated-high" && typeof F.ratedHighUrl === "function") {
      url = F.ratedHighUrl(20);
    } else if (tab === "rated-low" && typeof F.ratedLowUrl === "function") {
      url = F.ratedLowUrl(20);
    } else {
      url = F.feedUrl(20);
    }
    feedViewState.loadId = (feedViewState.loadId || 0) + 1;
    var myLoad = feedViewState.loadId;
    feedViewState.status = "loading";
    feedViewState.error = "";
    feedViewState.posts = [];
    if (typeof console !== "undefined" && console.log) {
      console.log("FETCH_FEED", { tab: tab, url: url });
    }
    if (getCurrentScreen().id === "feed") renderMain();
    return fetch(url, F.feedFetchInit())
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (myLoad !== feedViewState.loadId) return;
        feedViewState.posts = buildFeedDisplayListFromResponse(data, F);
        feedViewState.status = "ok";
        if (getCurrentScreen().id === "feed") renderMain();
      })
      .catch(function (e) {
        if (myLoad !== feedViewState.loadId) return;
        feedViewState.error = e.message || String(e);
        feedViewState.status = "error";
        feedViewState.posts = [];
        if (getCurrentScreen().id === "feed") renderMain();
      });
  }

  /** Okunur tarih (feed-api’ye dokunmadan; yalnız panel) */
  function feedFormatCreatedAtReadable(iso) {
    if (iso == null || iso === "") return "—";
    var d = new Date(iso);
    if (Number.isNaN(d.getTime())) return String(iso);
    try {
      return d.toLocaleString("tr-TR", { dateStyle: "medium", timeStyle: "short" });
    } catch (e2) {
      return d.toISOString().replace("T", " ").replace(/\.\d{3}Z$/, "").replace("Z", "");
    }
  }

  function feedToolbarHtml(activeTab) {
    function tabButton(id, label) {
      var active = activeTab === id ? " active" : "";
      return (
        '<button type="button" class="log-tab' +
        active +
        '" data-feed-tab="' +
        id +
        '" aria-pressed="' +
        (activeTab === id ? "true" : "false") +
        '">' +
        label +
        "</button>"
      );
    }
    return (
      '<div class="feed-toolbar log-tabs feed-source-tabs" role="tablist" aria-label="Liste kaynağı">' +
      tabButton("feed", "Feed") +
      tabButton("rated-high", "Rated High") +
      tabButton("rated-low", "Rated Low") +
      '<button type="button" class="log-tab" data-feed-refresh="1">Yenile</button>' +
      "</div>"
    );
  }

  function renderPostFeedCard(F, rawPost) {
    var p =
      F.normalizePostForPanel && typeof F.normalizePostForPanel === "function"
        ? F.normalizePostForPanel(rawPost)
        : F.pickPostCardProps(rawPost);
    var busy = !!feedViewState.actionBusyByPostId[p.id];
    var avgStr =
      p.ratingAvg != null && !Number.isNaN(Number(p.ratingAvg))
        ? Number(p.ratingAvg).toFixed(1)
        : "—";
    var idFooter = p.id
      ? '<div class="post-feed-id post-feed-id--footer"><code>' + F.escapeHtml(p.id) + "</code></div>"
      : "";
    var actionDisabled = busy ? " disabled" : "";
    var actionBusyClass = busy ? " is-busy" : "";
    return (
      '<article class="post-feed-card' + actionBusyClass + '">' +
      '<div class="post-feed-user">@' +
      F.escapeHtml(p.username || "—") +
      "</div>" +
      '<div class="post-feed-content">' +
      F.escapeHtml(p.content) +
      "</div>" +
      '<div class="post-feed-meta">' +
      '<div class="post-feed-badges" aria-label="Oylama özeti">' +
      '<span class="post-feed-badge post-feed-badge--avg" title="ratingAvg">⭐ ' +
      F.escapeHtml(avgStr) +
      "</span>" +
      '<span class="post-feed-badge post-feed-badge--count" title="ratingCount">' +
      F.escapeHtml(String(p.ratingCount)) +
      " oy</span>" +
      '<span class="post-feed-badge post-feed-badge--high" title="highRatingCount">' +
      F.escapeHtml(String(p.highRatingCount)) +
      "</span>" +
      '<span class="post-feed-badge post-feed-badge--low" title="lowRatingCount">' +
      F.escapeHtml(String(p.lowRatingCount)) +
      "</span>" +
      "</div>" +
      '<div class="post-feed-time">' +
      '<span class="post-feed-time-full">' +
      F.escapeHtml(feedFormatCreatedAtReadable(p.createdAt)) +
      "</span>" +
      '<span class="post-feed-time-rel"> · ' +
      F.escapeHtml(F.formatRelativeTime(p.createdAt)) +
      "</span>" +
      "</div>" +
      "</div>" +
      '<div class="post-feed-actions" aria-label="Hızlı aksiyonlar">' +
      '<button type="button" class="post-feed-action-btn post-feed-action-btn--high" data-post-action="rate-high" data-post-id="' +
      F.escapeHtml(p.id) +
      '"' +
      actionDisabled +
      ">Yüksek Puan</button>" +
      '<button type="button" class="post-feed-action-btn post-feed-action-btn--low" data-post-action="rate-low" data-post-id="' +
      F.escapeHtml(p.id) +
      '"' +
      actionDisabled +
      ">Düşük Puan</button>" +
      '<button type="button" class="post-feed-action-btn post-feed-action-btn--trash" data-post-action="trash" data-post-id="' +
      F.escapeHtml(p.id) +
      '"' +
      actionDisabled +
      ">Çöpe Taşı</button>" +
      "</div>" +
      idFooter +
      "</article>"
    );
  }

  function renderFeed() {
    var F = window.LumosFeedApi;
    if (!F) return renderEmptyState("Akış", "feed-api.js yüklenmedi.");

    var tab = feedViewState.tab || "feed";

    if (feedViewState.status === "idle") {
      fetchFeed();
      return (
        ViewHeader("Akış", feedTabLabel(tab)) +
        feedToolbarHtml(tab) +
        feedFlashHtml(F) +
        renderPostsApiBaseLine(F) +
        '<div class="feed-loading">Yükleniyor…</div>'
      );
    }

    if (feedViewState.status === "loading") {
      return (
        ViewHeader("Akış", feedTabLabel(tab)) +
        feedToolbarHtml(tab) +
        feedFlashHtml(F) +
        renderPostsApiBaseLine(F) +
        '<div class="feed-loading">Yükleniyor…</div>'
      );
    }

    if (feedViewState.status === "error") {
      return (
        ViewHeader("Akış", "Bağlantı hatası · " + feedTabLabel(tab)) +
        feedToolbarHtml(tab) +
        feedFlashHtml(F) +
        renderPostsApiBaseLine(F) +
        '<div class="feed-panel-error" role="alert">' +
        '<p class="feed-panel-error-title">İstek tamamlanamadı</p>' +
        '<p class="feed-panel-error-detail">' +
        F.escapeHtml(feedViewState.error) +
        "</p>" +
        '<div class="feed-panel-error-hint">' +
        "<p><strong>Ne kontrol edilir?</strong> Backend çalışıyor mu (<code>cd backend && npm run dev</code>), adres doğru mu.</p>" +
        "<p class=\"feed-panel-error-hint-sub\">Özel taban için konsol: <code>LUMOS_POSTS_API_BASE</code> veya <code>localStorage.lumos_posts_api_base</code>.</p>" +
        "</div></div>"
      );
    }

    var displayPosts = feedViewState.posts || [];
    var cards = "";
    if (displayPosts.length === 0) {
      cards =
        '<div class="empty-state feed-panel-empty" role="status">' +
        '<p class="empty-title">Hiç içerik yok</p>' +
        '<p class="empty-desc"><strong>' +
        F.escapeHtml(feedTabLabel(tab)) +
        "</strong> için şu an gösterilecek gönderi yok (bu sekme kendi GET yanıtıyla dolar).</p>" +
        "</div>";
    } else {
      for (var i = 0; i < displayPosts.length; i++) {
        cards += renderPostFeedCard(F, displayPosts[i]);
      }
    }
    return (
      ViewHeader("Akış", displayPosts.length + " gönderi · " + feedTabLabel(tab)) +
      feedToolbarHtml(tab) +
      feedFlashHtml(F) +
      renderPostsApiBaseLine(F) +
      '<div class="post-feed-list">' +
      cards +
      "</div>"
    );
  }

  var renderers = {
    chat: renderChat,
    dashboard: renderDashboard,
    feed: renderFeed,
    tasks: renderTasks,
    sandbox: renderSandbox,
    config: renderConfig,
    identity: renderIdentity,
    keystore: renderKeystore,
    trash: renderTrash,
    logs: renderLogs,
    system: renderSystem,
  };

  function renderMain() {
    var main = document.getElementById("main-content");
    if (!main) return;
    var screen = getCurrentScreen();
    var fn = renderers[screen.id];
    main.innerHTML = fn ? fn() : renderEmptyState("Geçersiz sayfa", "Menüden bir ekran seçin.");
  }

  // ——— Etkileşimler (delegation) ———
  function onMainClick(e) {
    var rawTarget = e.target;
    var t = rawTarget && rawTarget.nodeType === 1 ? rawTarget : rawTarget && rawTarget.parentElement;
    var F = window.LumosFeedApi;
    if (t && (t.id === "lumos-chat-send" || (t.closest && t.closest("#lumos-chat-send")))) {
      e.preventDefault();
      submitChatFromComposer();
      return;
    }
    function closestByDataAttr(el, attrName) {
      var cur = el;
      while (cur && cur !== document && cur !== null) {
        if (cur.dataset && cur.dataset[attrName] != null) return cur;
        cur = cur.parentElement;
      }
      return null;
    }
    if (!t) return;
    // Önce: Çöpü Boşalt (liste satırındaki data-trash-id ile çakışmasın)
    var emptyTrashBtn =
      (t.id === "lumos-trash-empty-all" && t) ||
      (t.closest && t.closest("#lumos-trash-empty-all")) ||
      (t.closest && t.closest("[data-trash-action-all]"));
    if (emptyTrashBtn) {
      var emptyAttr =
        emptyTrashBtn.getAttribute && emptyTrashBtn.getAttribute("data-trash-action-all");
      if (emptyAttr === "empty" || emptyTrashBtn.id === "lumos-trash-empty-all") {
        handleEmptyTrash();
        return;
      }
    }
    if (t.dataset && t.dataset.taskId) {
      mockState.selectedTaskId = t.dataset.taskId;
      renderMain();
      return;
    }
    if (t.dataset && t.dataset.taskFilter) {
      mockState.taskFilter = t.dataset.taskFilter;
      renderMain();
      return;
    }
    if (t.dataset && t.dataset.trashId) {
      mockState.selectedTrashId = t.dataset.trashId;
      renderMain();
      return;
    }
    var trashActionBtn = t.closest && t.closest("[data-trash-action][data-trash-post-id]");
    if (trashActionBtn && trashActionBtn.dataset) {
      if (!F) return;
      var trashPostId = trashActionBtn.dataset.trashPostId || "";
      var trashAction = trashActionBtn.dataset.trashAction || "";
      if (
        !trashPostId ||
        !trashAction ||
        trashViewState.actionBusyByPostId[trashPostId] ||
        trashViewState.actionBusyAll
      ) return;
      trashViewState.actionBusyByPostId[trashPostId] = true;
      trashViewState.flash = null;
      renderMain();
      var trashActionPromise;
      if (trashAction === "restore") {
        trashActionPromise = F.restorePost(trashPostId);
      } else if (trashAction === "permanent-delete") {
        trashActionPromise = F.permanentDeletePost(trashPostId);
      } else {
        trashActionPromise = Promise.reject(new Error("unsupported trash action"));
      }

      trashActionPromise
        .then(function () {
          if (trashAction === "restore") {
            console.log("ACTION_RESTORE", { postId: trashPostId });
          }
          if (trashAction === "restore") {
            return fetchTrash().then(function () {
              return fetchFeed({ forceTab: "feed" });
            });
          }
          return fetchTrash();
        })
        .then(function () {
          delete trashViewState.actionBusyByPostId[trashPostId];
          trashViewState.flash = {
            kind: "ok",
            text: trashAction === "restore" ? "Gönderi geri yüklendi" : "Kalıcı olarak silindi",
          };
          renderMain();
        })
        .catch(function (err) {
          delete trashViewState.actionBusyByPostId[trashPostId];
          var rawErr = (err && err.message) || "İşlem başarısız.";
          if (isTrashFlashTechnicalNotFound(rawErr)) {
            trashViewState.flash = null;
            fetchTrash()
              .then(function () {
                renderMain();
              })
              .catch(function () {
                renderMain();
              });
          } else {
            trashViewState.flash = { kind: "error", text: rawErr };
            renderMain();
          }
        });
      return;
    }
    if (t.dataset && t.dataset.logFilter) {
      mockState.logFilter = t.dataset.logFilter;
      renderMain();
      return;
    }
    var feedTabBtn = t.closest && t.closest("[data-feed-tab]");
    if (feedTabBtn && feedTabBtn.dataset && feedTabBtn.dataset.feedTab) {
      var nextTab = feedTabBtn.dataset.feedTab;
      if (nextTab !== feedViewState.tab) {
        feedViewState.tab = nextTab;
        feedViewState.flash = null;
        feedViewState.status = "idle";
        feedViewState.posts = [];
        try {
          if (window.history && window.history.replaceState) {
            var frag = nextTab === "feed" ? "feed" : nextTab;
            window.history.replaceState(null, "", "#" + frag);
          }
        } catch (e1) {}
        renderMain();
      }
      return;
    }
    if (t.dataset && t.dataset.feedRefresh) {
      feedViewState.flash = null;
      feedViewState.status = "idle";
      feedViewState.posts = [];
      renderMain();
      return;
    }
    var postActionBtn = null;
    if (t && t.closest) {
      postActionBtn = t.closest("[data-post-action][data-post-id]");
    }
    if (!postActionBtn) {
      var byAction = closestByDataAttr(t, "postAction");
      if (byAction && byAction.dataset && byAction.dataset.postId != null) {
        postActionBtn = byAction;
      }
    }
    if (postActionBtn && postActionBtn.dataset) {
      if (!F) return;
      var postId = postActionBtn.dataset.postId || "";
      var action = postActionBtn.dataset.postAction || "";
      if (!postId || !action || feedViewState.actionBusyByPostId[postId]) return;
      feedViewState.actionBusyByPostId[postId] = true;
      feedViewState.flash = null;
      renderMain();
      var actionPromise;
      if (action === "rate-high") actionPromise = F.rateHigh(postId);
      else if (action === "rate-low") actionPromise = F.rateLow(postId);
      else if (action === "trash") actionPromise = (F.moveToTrash || F.trashPost).call(F, postId);
      else actionPromise = Promise.reject(new Error("unsupported action"));

      actionPromise
        .then(function () {
          if (action === "rate-high" && typeof console !== "undefined" && console.log) {
            console.log("ACTION_RATE_HIGH", { postId: postId });
          }
          if (action === "rate-low" && typeof console !== "undefined" && console.log) {
            console.log("ACTION_RATE_LOW", { postId: postId });
          }
          if (action === "trash") {
            console.log("ACTION_TRASH", { postId: postId });
            return fetchFeed().then(function () {
              return fetchTrash();
            });
          }
          return fetchFeed();
        })
        .then(function () {
          delete feedViewState.actionBusyByPostId[postId];
          if (action === "trash") {
            feedViewState.flash = { kind: "ok", text: "Çöpe taşındı" };
          } else {
            feedViewState.flash = {
              kind: "ok",
              text: action === "rate-high" ? "Yüksek oy kaydedildi" : "Düşük oy kaydedildi",
            };
          }
          renderMain();
        })
        .catch(function (err) {
          delete feedViewState.actionBusyByPostId[postId];
          feedViewState.flash = {
            kind: "error",
            text: (err && err.message) || "İşlem başarısız.",
          };
          renderMain();
        });
      return;
    }
  }

  var _lastRouteScreenId = "";

  function refresh() {
    var cur = getCurrentScreen();
    if (_lastRouteScreenId === "feed" && cur.id !== "feed") {
      feedViewState.flash = null;
    }
    if (_lastRouteScreenId === "trash" && cur.id !== "trash") {
      trashViewState.flash = null;
    }
    _lastRouteScreenId = cur.id;

    if (cur.id === "trash") {
      trashViewState.status = "idle";
      trashViewState.trashPosts = [];
      trashViewState.flash = null;
    }
    if (cur.id === "feed") {
      feedViewState.flash = null;
      var tabFromRoute = cur.feedTab != null ? cur.feedTab : feedTabFromLocationHash();
      feedViewState.tab = tabFromRoute != null ? tabFromRoute : "feed";
      feedViewState.status = "idle";
      feedViewState.posts = [];
    }
    renderSidebar();
    renderTopbar();
    renderMain();
  }

  function onHashChange() {
    refresh();
  }

  function onMainKeydown(e) {
    var t = e.target;
    if (!t || t.id !== "lumos-chat-input") return;
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitChatFromComposer();
    }
  }

  var mainEl = document.getElementById("main-content");
  if (mainEl) {
    mainEl.addEventListener("click", onMainClick);
    mainEl.addEventListener("keydown", onMainKeydown);
  }

  hydratePanelEngineFromStorage();

  window.addEventListener("hashchange", onHashChange);
  if (!window.location.hash) {
    window.location.hash = DEFAULT_HASH;
  } else {
    refresh();
  }

})();
