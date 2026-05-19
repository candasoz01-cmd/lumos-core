
function canTransition(from, to) {
  const allowed = {
    active: ["done", "pending_delete"],
    done: [],
    pending_delete: ["deleted"],
    deleted: []
  };
  return (allowed[from] || []).includes(to);
}

/**
 * Lumos Panel v1 — operatör paneli.
 *
 * Mock vs localStorage (görev dokümanı TASKS_JSON_STORAGE_KEY, v:1):
 * 1) localStorage’ta geçerli v:1 var → kalıcı görev/events yalnız oradan okunur (motor ledger); demo stub recentEvents/logItems devreye girmez.
 * 2) yok → mockState (+ istenirse DEMO_SCENARIOS) başlangıç/fallback; runtime mutasyonları mockState’e yazılır, persist ile v:1 oluşunca (1) geçerli olur.
 * 3) policy_blocked yalnız bellekte; v:1 varken ledger’a LS events + bu satırlar (kalıcı değil) eklenir.
 */

(function () {
  var TASK_STATUS = {
    ACTIVE: "active",
    DONE: "done",
    PENDING_DELETE: "pending_delete",
    DELETED: "deleted",
    PERMANENTLY_DELETED: "task_permanently_deleted",
  };
  var SOURCE_STATUS = {
    ONLINE: "online",
    OFFLINE_CACHE: "offline-cache",
    UNREACHABLE: "unreachable",
  };
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
    /** Eski stub; Görevler ekranı yalnızca engineTasks (kalıcı depo). Boş bırakılır. */
    taskList: [],
    taskFilter: "all",
    /**
     * Merkezi görev motoru durumu (chat komutları; tek kaynak — görev ekranı buradan).
     * Şekil: { id, title, status: "active"|"done"|"deleted"|"pending_delete", createdAt, completedAt, expireAt?, restoreStatus? }
     */
    engineTasks: [],
    /**
     * Tek kaynak (chat → panel): saf olaylar { id, type, taskId, text, ts }.
     * Kayıt / dashboard bu hattı okur; görev güncel durumu engineTasks’tır.
     */
    chatTaskCreations: [],
    selectedTaskId: null,
    selectedTrashId: null,
    /** Kayıtlar: timeline ana satır seçimi (group key, decodeURIComponent ile). */
    selectedKayitlarTimelineKey: null,
    logFilter: "all",
    /**
     * REST görev API modunda (GET /tasks): null (ilk yükleme öncesi) | "online" | "offline-cache" | "unreachable".
   * Sunum: backend `product_features.panel_api` üzerinden.
     * Yerel / legacy doküman modunda kullanılmaz (null kalır; mod her zaman yerel).
     */
    taskSourceState: null,
    taskActionGate: null,
    guidance: {
      mode: "offline",
      lock: "LOCKED",
      consent: false,
      blocked_reason: null,
      next_step: null,
    },
  };

  // ——— Demo senaryolar (görev satırı taşımaz; getEffectiveState ile diğer mock alanlar) ———
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

  /**
   * __LUMOS_READ_STATE__ (read_backend_state.py) → panel alanları: mod, kilit, consent, keystore.
   * Böylece Sistem Durumu / rozetler ile politika aynı kaynağı okur.
   */
  function mergeReadStateIntoEffective(out) {
    try {
      var w = typeof window !== "undefined" ? window : null;
      var rs = w && w.__LUMOS_READ_STATE__;
      if (!rs || typeof rs !== "object") return out;
      var g = rs.guidance;
      if (g && typeof g === "object") {
        out.guidance = {
          mode: g.mode != null ? String(g.mode) : out.guidance.mode,
          lock: g.lock != null ? String(g.lock) : out.guidance.lock,
          consent: !!g.consent,
          blocked_reason: g.blocked_reason != null ? g.blocked_reason : out.guidance.blocked_reason,
          next_step: g.next_step != null ? g.next_step : out.guidance.next_step,
        };
        out.appMode = String(out.guidance.mode).toLowerCase() === SOURCE_STATUS.ONLINE ? "online" : "offline";
      }
      var ks = rs.keystore;
      if (ks && typeof ks === "object") {
        if (ks.keystore_state != null) out.keystoreState = String(ks.keystore_state);
        if (typeof ks.keystore_ready === "boolean") out.keystoreReady = ks.keystore_ready;
      }
      var dash = rs.dashboard;
      if (dash && typeof dash === "object" && dash.guard_status != null) {
        out.guardStatus = String(dash.guard_status);
      }
    } catch (_) {
      /* ignore */
    }
    return out;
  }

  function getEffectiveState() {
    var out = {};
    for (var k in mockState) out[k] = mockState[k];
    var over = DEMO_SCENARIOS[currentScenario];
    if (over) for (var k in over) out[k] = over[k];
    /** v:1 görev önbelleği varken demo recentEvents/logItems karışmasın; motor + dosya/bridge kayıtları esas. */
    if (hasLocalTasksJsonCache()) {
      out.recentEvents = [];
      out.logItems = [];
    }
    mergeReadStateIntoEffective(out);
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
    if (key === "mode") return value === SOURCE_STATUS.ONLINE ? "CANLI" : "Çevrimdışı";
    if (key === "lock") return value === "LOCKED" ? "KORUMA AKTİF" : "Açık";
    if (key === "sandbox") return "KORUMALI ALAN";
    return value;
  }

  function getTaskStatusVariant(status) {
    var v = {
      aktif: "badge-live",
      bekleyen: "badge-offline",
      tamamlandı: "badge-live",
      başarısız: "badge-warning",
      engellenen: "badge-blocked",
      Siliniyor: "badge-warning",
    };
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
    return { type: "none", data: null };
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
   * Minimum task engine — stability contract:
   * - Görev güncel durumu: mockState.engineTasks (active | done | deleted | pending_delete). UI: toTaskRow; deleted listede yok; pending_delete "Siliniyor" satırı; kalıcı silmede kayıt task_permanently_deleted.
   * - Denetim: append-only mockState.chatTaskCreations (task_* + post_permanently_deleted); finalize ile tasks.json events ile aynı; tek yazım hattı.
   * - Kayıtlar + Dashboard: görev motoru satırları yalnızca kalıcı depodaki events’ten okunur; dosya/fixture log_items yalnızca task_* dışı satırlar (çift kaynak yok).
   * - Görevler ekranı: yalnızca engineTasks → toTaskRow.
   * - Kalıcılık: `panel/scripts/panel_tasks_server.py` + localStorage yansı (v:1 tek önbellek anahtarı).
   *   Okuma sırası (ledger): v:1 LS var → events oradan; yok → mockState.chatTaskCreations. Demo stub log satırları v:1 varken getEffectiveState’ten düşer.
   *   Varsayılan: API (`LUMOS_PANEL_TASKS_MODE` / `LUMOS_PANEL_TASKS_PERSISTENCE` yoksa "api") → GET `/tasks` + POST mutasyonlar.
   *   Local/legacy: mod `local` | `demo` | `legacy` | `put` → GET/PUT `/tasks.json` (tam doküman), sohbet komutları bellek+PUT.
   *   `LUMOS_PANEL_TASKS_API_BASE === false` → tam çevrimdışı (HTTP yok, yalnız localStorage / inject).
   *   Sunucu yoksa: hydrate GET başarısız → localStorage. Boş motor + inject: __LUMOS_READ_STATE__ task_list.
   */
  // ——— Adapter + minimum görev motoru ———
  var TASKS_JSON_STORAGE_KEY = "lumos_dot_lumos_tasks_json_v1";
  var LEGACY_PANEL_ENGINE_STORAGE_KEY = "lumos_panel_min_task_engine_v1";
  var PANEL_TASKS_FETCH_MS = 1200;
  var TASKS_API_BASE = "http://127.0.0.1:8766";
  /** Silinenler ekranı: panel kayıtlarından kalıcı silinenler özeti (çöp API listesi değil). */
  var RECENT_PERMANENT_DELETES_LIMIT = 15;
  /** Silme onayı: bu süre sonunda kalıcı silme + task_permanently_deleted kaydı. */
  var PENDING_DELETE_GRACE_MS = 5000;
  /** Liste + detay + satır özeti: tek görünen durum etiketi (pending_delete UI kuralı). */
  var TASK_PENDING_DELETE_UI_LABEL = "Siliniyor…";

  function pendingDeleteGraceSecondsRounded() {
    return Math.max(1, Math.round(PENDING_DELETE_GRACE_MS / 1000));
  }
  var pendingDeleteTickerId = null;
  /** Açıkça set edilmezse görev ana yolu REST API. */
  var PANEL_TASKS_MODE_DEFAULT = "api";

  /**
   * Tek yapılandırma girişi: görev HTTP tabanı, doküman URL’leri, sohbet mutasyon yolu.
   * @returns {{ apiBase: string, documentGetUrl: string, legacyPutUrl: string, chatCommands: "api"|"local" }}
   */
  function getPanelTasksPersistenceConfig() {
    var w = typeof window !== "undefined" ? window : null;
    if (!w) {
      return { apiBase: "", documentGetUrl: "", legacyPutUrl: "", chatCommands: "local" };
    }
    if (w.LUMOS_PANEL_TASKS_API_BASE === false) {
      return { apiBase: "", documentGetUrl: "", legacyPutUrl: "", chatCommands: "local" };
    }
    var custom = w.LUMOS_PANEL_TASKS_API_BASE;
    var apiBase;
    if (custom != null && String(custom).trim() !== "") {
      apiBase = String(custom).replace(/\/$/, "");
    } else {
      /* Aynı süreçte statik panel + API (panel_tasks_server): taban = sayfa origin (port dahil).
         API başka host/port’taysa LUMOS_PANEL_TASKS_API_BASE verin (ör. statik sunucu + 8766 API). */
      try {
        var loc = w.location;
        if (loc && /^https?:$/i.test(String(loc.protocol || ""))) {
          apiBase = String(loc.origin || "").replace(/\/$/, "");
        } else {
          apiBase = "http://127.0.0.1:8766";
        }
      } catch (_) {
        apiBase = "http://127.0.0.1:8766";
      }
    }
    var rawMode = w.LUMOS_PANEL_TASKS_PERSISTENCE != null ? w.LUMOS_PANEL_TASKS_PERSISTENCE : w.LUMOS_PANEL_TASKS_MODE;
    var mode =
      rawMode != null && String(rawMode).trim() !== ""
        ? String(rawMode).trim().toLowerCase()
        : PANEL_TASKS_MODE_DEFAULT;
    var useLegacyDocument =
      mode === "local" || mode === "demo" || mode === "legacy" || mode === "put";
    if (useLegacyDocument) {
      return {
        apiBase: apiBase,
        documentGetUrl: apiBase + "/tasks.json",
        legacyPutUrl: apiBase + "/tasks.json",
        chatCommands: "local",
      };
    }
    return {
      apiBase: apiBase,
      documentGetUrl: apiBase + "/tasks",
      legacyPutUrl: "",
      chatCommands: "api",
    };
  }

  function getPanelTasksApiBaseResolved() {
    return getPanelTasksPersistenceConfig().apiBase;
  }

  function getPanelTasksDocumentGetUrl() {
    return getPanelTasksPersistenceConfig().documentGetUrl;
  }

  /** GET /tasks REST modu; yerel tasks.json doküman yolu değil. */
  function isPanelTasksApiRestMode() {
    return getPanelTasksPersistenceConfig().chatCommands === "api" && !!getPanelTasksApiBaseResolved();
  }

  function setTaskSourceDomAttribute() {
    try {
      if (!isPanelTasksApiRestMode()) {
        document.documentElement.removeAttribute("data-lumos-task-source");
        return;
      }
      var s = mockState.taskSourceState;
      if (s === SOURCE_STATUS.ONLINE || s === SOURCE_STATUS.OFFLINE_CACHE || s === SOURCE_STATUS.UNREACHABLE) {
        document.documentElement.setAttribute("data-lumos-task-source", s);
      } else {
        document.documentElement.setAttribute("data-lumos-task-source", "");
      }
    } catch (_) {
      /* ignore */
    }
  }

  /** Geçerli v:1 tasks.json localStorage’ta mı (GET başarısızken önbellek var mı). */
  function hasLocalTasksJsonCache() {
    try {
      if (typeof localStorage === "undefined") return false;
      migrateLegacyEngineStorageToTasksJson();
      var raw = localStorage.getItem(TASKS_JSON_STORAGE_KEY);
      if (!raw || !String(raw).trim()) return false;
      var o = JSON.parse(raw);
      return !!(o && typeof o === "object" && o.v === 1);
    } catch (_) {
      return false;
    }
  }

  function readPanelApiFeatureOrNull() {
    try {
      var B = typeof LumosBackendBridge !== "undefined" ? LumosBackendBridge : {};
      var pf = B.readBackendProductFeaturesState && B.readBackendProductFeaturesState();
      if (!pf || !pf.length) return null;
      for (var i = 0; i < pf.length; i++) {
        if (pf[i] && pf[i].key === "panel_api") return pf[i];
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  /**
   * Üst çubuk / kenar çubuğu rozet metni + sınıfı.
   * Panel state üretmez: sadece backend `product_features.panel_api` okur.
   * @returns {{ label: string, variant: string }}
   */
  function getPanelWorkModePresentation() {
    var f = readPanelApiFeatureOrNull();
    return { label: (f && f.durum) ? String(f.durum) : "—", variant: "badge-mode" };
  }

  /**
   * Ekran alt başlığı — tüm ana ekranlarda aynı kısa durum cümlesi.
   */
  function getPanelWorkModeStatusLine() {
    var f = readPanelApiFeatureOrNull();
    return (f && f.aciklama) ? String(f.aciklama) : "";
  }

  function applyPanelWorkModeSubtitle(data) {
    if (data && typeof data === "object") data.subtitle = getPanelWorkModeStatusLine();
    return data;
  }

  /** Canlı GET başarılı: bellek + localStorage önbellek; çakışmada sunucu doc esas. */
  function applyTasksApiOnlineSuccess(doc) {
    if (!isPanelTasksApiRestMode()) return;
    mockState.taskSourceState = SOURCE_STATUS.ONLINE;
    applyHydratedTasksAndEventsFromDoc(doc);
    persistTasksJsonDocumentLocalOnly();
    syncTaskSelectionAfterMutation();
    runPendingDeleteSweep();
    setTaskSourceDomAttribute();
  }

  /** GET başarısız / zaman aşımı: yerel önbellek varsa offline-cache, yoksa unreachable. */
  function applyTasksApiOfflineFallback() {
    if (!isPanelTasksApiRestMode()) return;
    hydrateTasksJsonPersistenceSyncFallback();
    mockState.taskSourceState = hasLocalTasksJsonCache() ? "offline-cache" : "unreachable";
    syncTaskSelectionAfterMutation();
    setTaskSourceDomAttribute();
  }

  function syncTasksDocumentFromApi() {
    var url = getPanelTasksDocumentGetUrl();
    if (!url) return Promise.reject(new Error("Görev dokümanı URL yok"));
    return fetchWithTimeout(url, { method: "GET", headers: { Accept: "application/json" } })
      .then(function (r) {
        if (!r.ok) return Promise.reject(new Error("GET görev dokümanı " + r.status));
        return r.json();
      })
      .then(function (doc) {
        if (!doc || typeof doc !== "object") return Promise.reject(new Error("geçersiz görev JSON"));
        applyTasksApiOnlineSuccess(doc);
      })
      .catch(function (err) {
        if (isPanelTasksApiRestMode()) applyTasksApiOfflineFallback();
        return Promise.reject(err);
      });
  }

  function refreshTasksDocumentFromApiStrict() {
    var url = TASKS_API_BASE + "/tasks";
    return fetchWithTimeout(url, { method: "GET", headers: { Accept: "application/json" } })
      .then(function (r) {
        if (!r.ok) return Promise.reject(new Error("GET görev dokümanı " + r.status));
        return r.json();
      })
      .then(function (doc) {
        if (!doc || typeof doc !== "object") return Promise.reject(new Error("geçersiz görev JSON"));
        applyTasksApiOnlineSuccess(doc);
      });
  }

  function findEngineTaskTitleForReply(titleOrRef, preferStatus) {
    var tasks = mockState.engineTasks || [];
    var hint = normalizeTaskCommandWhitespace(titleOrRef);
    var i;
    var t;
    for (i = tasks.length - 1; i >= 0; i--) {
      t = tasks[i];
      if (!t) continue;
      if (preferStatus && t.status !== preferStatus) continue;
      if (normalizeTaskCommandWhitespace(t.title) === hint || taskTitleMatchesRef(titleOrRef, t.title)) {
        return String(t.title || "").trim() || hint;
      }
    }
    for (i = tasks.length - 1; i >= 0; i--) {
      t = tasks[i];
      if (!t || t.status === TASK_STATUS.DELETED) continue;
      if (taskTitleMatchesRef(titleOrRef, t.title)) return String(t.title || "").trim() || hint;
    }
    return hint;
  }

  function tryHandleTaskEngineChatCommandViaApi(parsed) {
    var Adapter = typeof LumosTasksApiAdapter !== "undefined" ? LumosTasksApiAdapter : null;
    var base = getPanelTasksApiBaseResolved();
    if (!base) {
      return Promise.resolve({
        text: "Canlı mod için API adresi tanımlı değil; işlem yapılamadı.",
        depth: "simple",
      });
    }
    var apiPolicyBlock = runPanelTaskPolicyOrNull(parsed);
    if (apiPolicyBlock) {
      return Promise.resolve(apiPolicyBlock);
    }
    if (!Adapter) {
      return Promise.resolve({
        text: "Bağlantı modülü yüklenmedi; işlem yapılamadı.",
        depth: "simple",
      });
    }
    var api = new Adapter({
      baseUrl: base,
      fetchImpl: function (url, opts) {
        return fetchWithTimeout(url, opts, PANEL_TASKS_FETCH_MS);
      },
    });
    if (parsed.verb === "olustur") {
      if (!parsed.taskName) {
        return Promise.resolve({ text: "Görev adı eksik. Örnek: görev oluştur alışveriş", depth: "simple" });
      }
      return api.postTasksCreate({ title: parsed.taskName }).then(function (res) {
        if (!res.ok) {
          var er = res.body && res.body.error ? String(res.body.error) : "HTTP " + res.status;
          throw new Error(er);
        }
        return syncTasksDocumentFromApi();
      }).then(function () {
        var tit = findEngineTaskTitleForReply(parsed.taskName, "active");
        return { text: 'Görev oluşturuldu: "' + tit + '".', depth: "simple" };
      });
    }
    if (parsed.verb === "tamamla") {
      if (!parsed.ref) {
        return Promise.resolve({ text: "Görev adı eksik. Örnek: görev tamamla alışveriş", depth: "simple" });
      }
      return api.postTasksComplete({ ref: parsed.ref }).then(function (res) {
        if (res.status === 409 || (res.body && res.body.error === "already_done")) {
          return { text: "Görev zaten tamamlanmış.", depth: "simple" };
        }
        if (res.status === 404 || (res.body && res.body.error === "not_found")) {
          return { text: "Tamamlanacak görev bulunamadı.", depth: "simple" };
        }
        if (!res.ok) {
          var er2 = res.body && res.body.error ? String(res.body.error) : "HTTP " + res.status;
          throw new Error(er2);
        }
        return refreshTasksDocumentFromApiStrict().then(function () {
          var tit2 = findEngineTaskTitleForReply(parsed.ref, "done");
          return { text: 'Görev tamamlandı: "' + tit2 + '".', depth: "simple" };
        });
      });
    }
    if (parsed.verb === "sil") {
      if (!parsed.ref) {
        return Promise.resolve({ text: "Görev adı eksik. Örnek: görev sil alışveriş", depth: "simple" });
      }
      if (!window.confirm('"' + parsed.ref + '" will be deleted. Do you confirm?')) {
        return Promise.resolve({ text: "Delete cancelled.", depth: "simple" });
      }
      return api.postTasksDelete({ ref: parsed.ref }).then(function (res) {
        if (res.status === 404 || (res.body && res.body.error === "not_found")) {
          return { text: "Silinecek görev bulunamadı.", depth: "simple" };
        }
        if (!res.ok) {
          var er3 = res.body && res.body.error ? String(res.body.error) : "HTTP " + res.status;
          throw new Error(er3);
        }
        return syncTasksDocumentFromApi().then(function () {
          runPendingDeleteSweep();
          var tit3 = findEngineTaskTitleForReply(parsed.ref, null);
          var secApi = pendingDeleteGraceSecondsRounded();
          return {
            text:
              TASK_PENDING_DELETE_UI_LABEL +
              " " +
              secApi +
              " sn içinde kalıcı silinecek. İptal: listede veya detayda «Geri al» — \"" +
              tit3 +
              '".',
            depth: "simple",
          };
        });
      });
    }
    if (parsed.verb === "geri_al") {
      if (!parsed.ref) {
        return Promise.resolve({ text: "Görev adı eksik. Örnek: görev geri al alışveriş", depth: "simple" });
      }
      var pendForRestore = resolvePendingDeleteTaskByRef(parsed.ref);
      if (!pendForRestore || pendForRestore.id == null || String(pendForRestore.id).trim() === "") {
        return Promise.resolve({ text: "Geri alınacak silme bekleyen görev bulunamadı.", depth: "simple" });
      }
      var restoreBase = String(API_BASE).replace(/\/$/, "");
      var restoreUrl = restoreBase + "/tasks/restore";
      return panelTasksTrashDirectPost(restoreUrl, { id: String(pendForRestore.id) })
        .then(function (r) {
          return r.text().then(function (txt) {
            var jj = null;
            try {
              jj = txt && String(txt).trim() ? JSON.parse(txt) : null;
            } catch (_) {
              jj = null;
            }
            return { ok: r.ok, status: r.status, j: jj && typeof jj === "object" ? jj : {} };
          });
        })
        .then(function (x) {
          var ej = x.j && x.j.error != null ? String(x.j.error) : "";
          if (
            x.status === 404 ||
            ej === "not_found" ||
            ej === "missing_trash_file"
          ) {
            return { text: "Geri alınacak silme bekleyen görev bulunamadı.", depth: "simple" };
          }
          if (!x.ok || !x.j.ok) {
            var er4 = ej || "HTTP " + x.status;
            throw new Error(er4);
          }
          return syncTasksDocumentFromApi().then(function () {
            clearPendingDeleteTickerIfIdle();
            var tit4 = findEngineTaskTitleForReply(parsed.ref, null);
            return { text: 'Silme iptal edildi: "' + tit4 + '".', depth: "simple" };
          });
        });
    }
    return Promise.resolve({ text: "Görev komutu API üzerinde tanımsız.", depth: "simple" });
  }

  function fetchWithTimeout(url, options, timeoutMs) {
    var ms = timeoutMs != null ? timeoutMs : PANEL_TASKS_FETCH_MS;
    if (typeof fetch !== "function") return Promise.reject(new Error("fetch yok"));
    var ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = null;
    var opts = options ? Object.assign({}, options) : {};
    if (ctrl) {
      opts.signal = ctrl.signal;
      timer = setTimeout(function () {
        try {
          ctrl.abort();
        } catch (_) {}
      }, ms);
    }
    return Promise.resolve(fetch(url, opts)).finally(function () {
      if (timer) clearTimeout(timer);
    });
  }

  /** Çöp geri yükle / kalıcı sil: doğrudan global fetch; konsolda yalnızca URL + HTTP status. */
  function panelTasksTrashDirectPost(url, bodyObj) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(bodyObj != null ? bodyObj : {}),
    }).then(function (r) {
      if (typeof console !== "undefined" && console.log) {
        console.log("[LUMOS] panel_tasks POST url:", url, "response status:", r.status);
      }
      return r;
    });
  }

  function buildPersistDoc() {
    var raw = mockState.chatTaskCreations || [];
    var evs = raw.filter(function (e) {
      return e && e.type !== "policy_blocked";
    });
    return {
      v: 1,
      tasks: mockState.engineTasks || [],
      events: evs,
    };
  }

  function persistTasksJsonDocumentLocalOnly() {
    try {
      if (typeof localStorage === "undefined") return;
      localStorage.setItem(TASKS_JSON_STORAGE_KEY, JSON.stringify(buildPersistDoc()));
    } catch (_) {
      /* quota / private mode */
    }
  }

  function persistTasksJsonDocument() {
    persistTasksJsonDocumentLocalOnly();
    var url = getPanelTasksPersistenceConfig().legacyPutUrl;
    if (!url) return;
    fetchWithTimeout(url, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildPersistDoc()),
    }).catch(function () {
      /* sunucu kapalı; localStorage güncel */
    });
  }

  function migrateLegacyEngineStorageToTasksJson() {
    try {
      if (typeof localStorage === "undefined") return;
      if (localStorage.getItem(TASKS_JSON_STORAGE_KEY)) return;
      var raw = localStorage.getItem(LEGACY_PANEL_ENGINE_STORAGE_KEY);
      if (!raw) return;
      var o = JSON.parse(raw);
      if (!o || typeof o !== "object" || o.v !== 1) return;
      localStorage.setItem(
        TASKS_JSON_STORAGE_KEY,
        JSON.stringify({
          v: 1,
          tasks: Array.isArray(o.engineTasks) ? o.engineTasks : [],
          events: Array.isArray(o.chatTaskCreations) ? o.chatTaskCreations : [],
        })
      );
    } catch (_) {
      /* ignore */
    }
  }

  function newEngineEventId() {
    return "ev_" + Date.now() + "_" + Math.random().toString(36).slice(2, 9);
  }

  function newEngineTaskId() {
    return "tsk_" + Date.now() + "_" + Math.random().toString(36).slice(2, 9);
  }

  function isPanelMotorEventType(type) {
    return (
      type === "task_created" ||
      type === "task_completed" ||
      type === "task_deleted" ||
      type === "task_restored" ||
      type === "task_permanently_deleted" ||
      type === "policy_blocked" ||
      type === "post_permanently_deleted"
    );
  }

  /** Backend/fixture task_list satırı → engine task (salt okunur inject; boş depoda tohum). */
  function panelTaskRowToEngineTask(row) {
    if (!row || row.id == null || String(row.id) === "") return null;
    var st = String(row.status || "").toLowerCase();
    var done = st === "tamamlandı" || st === "tamamlandi";
    var updated = row.updated != null ? String(row.updated) : "";
    var lastRun = row.lastRun != null ? String(row.lastRun) : "";
    return {
      id: String(row.id),
      title: row.title != null ? String(row.title) : "—",
      status: done ? "done" : "active",
      createdAt: updated || new Date().toISOString(),
      completedAt: done ? (lastRun || updated || new Date().toISOString()) : null,
    };
  }

  function applyHydratedTasksAndEventsFromDoc(o) {
    if (!o || typeof o !== "object") return;
    if (o.action_gate && typeof o.action_gate === "object") {
      mockState.taskActionGate = o.action_gate;
    }
    if (Array.isArray(o.tasks)) {
      var tasks = [];
      for (var i = 0; i < o.tasks.length; i++) {
        var t = o.tasks[i];
        if (!t || typeof t !== "object") continue;
        if (t.id == null || String(t.id) === "") continue;
        if (
          t.status !== TASK_STATUS.ACTIVE &&
          t.status !== TASK_STATUS.DONE &&
          t.status !== TASK_STATUS.DELETED &&
          t.status !== TASK_STATUS.PENDING_DELETE
        ) {
          continue;
        }
        var expRaw = t.expireAt != null ? t.expireAt : t.expire_at;
        var rsRaw = t.restoreStatus != null ? t.restoreStatus : t.restore_status;
        var row = {
          id: String(t.id),
          title: t.title != null ? String(t.title) : "—",
          status: t.status,
          createdAt: t.createdAt != null ? String(t.createdAt) : "",
          completedAt: t.completedAt != null && t.completedAt !== "" ? String(t.completedAt) : null,
          deletedAt: t.deletedAt != null && t.deletedAt !== "" ? String(t.deletedAt) : null,
          summary: t.summary != null ? String(t.summary) : "",
          result: t.result != null ? String(t.result) : "",
          actions: {
            complete: !!(t.actions && t.actions.complete === true),
          },
        };
        if (t.status === TASK_STATUS.PENDING_DELETE) {
          row.restoreStatus = rsRaw === "done" || rsRaw === "active" ? rsRaw : row.completedAt ? "done" : "active";
          row.expireAt = expRaw != null && String(expRaw) !== "" ? String(expRaw) : new Date(Date.now() + PENDING_DELETE_GRACE_MS).toISOString();
        }
        tasks.push(row);
      }
      mockState.engineTasks = tasks;
      runPendingDeleteSweep();
    }
    if (Array.isArray(o.events)) {
      var evs = [];
      for (var j = 0; j < o.events.length; j++) {
        var e = o.events[j];
        if (!e || typeof e !== "object") continue;
        if (!isPanelMotorEventType(e.type)) continue;
        evs.push({
          id: e.id != null ? String(e.id) : newEngineEventId(),
          type: e.type,
          taskId: String(
            e.taskId != null && String(e.taskId).trim() !== ""
              ? e.taskId
              : e.task_id != null && String(e.task_id).trim() !== ""
                ? e.task_id
                : ""
          ),
          text: e.text != null ? String(e.text) : "",
          ts: e.ts != null ? String(e.ts) : new Date().toISOString(),
        });
      }
      var prevMem = mockState.chatTaskCreations || [];
      var feedTrashKeep = [];
      var fk;
      for (fk = 0; fk < prevMem.length; fk++) {
        var pfe = prevMem[fk];
        if (pfe && pfe.type === "post_permanently_deleted") feedTrashKeep.push(pfe);
      }
      var seenIds = {};
      var si;
      for (si = 0; si < evs.length; si++) {
        if (evs[si] && evs[si].id) seenIds[evs[si].id] = true;
      }
      var mergedExtra = [];
      var mx;
      for (mx = 0; mx < feedTrashKeep.length; mx++) {
        var fe = feedTrashKeep[mx];
        if (fe && fe.id && !seenIds[fe.id]) mergedExtra.push(fe);
      }
      mockState.chatTaskCreations = evs.concat(mergedExtra);
    }
  }

  /** read_backend_state inject: task_list varsa ve motor boşsa engine’i doldur; dosyaya yansıt. */
  function hydrateEngineTasksFromInjectedBackendIfEmpty() {
    var cur = mockState.engineTasks || [];
    if (cur.length > 0) return;
    var backend = Bridge.readBackendTasksState && Bridge.readBackendTasksState();
    if (!backend || !Array.isArray(backend.task_list) || !backend.task_list.length) return;
    var out = [];
    for (var i = 0; i < backend.task_list.length; i++) {
      var eng = panelTaskRowToEngineTask(backend.task_list[i]);
      if (eng) out.push(eng);
    }
    if (!out.length) return;
    mockState.engineTasks = out;
    persistTasksJsonDocument();
  }

  /** Sunucu yok / hata: yalnızca localStorage (+ legacy migrate). */
  function hydrateTasksJsonPersistenceSyncFallback() {
    try {
      if (typeof localStorage === "undefined") return;
      migrateLegacyEngineStorageToTasksJson();
      var raw = localStorage.getItem(TASKS_JSON_STORAGE_KEY);
      if (!raw) return;
      var o = JSON.parse(raw);
      if (o && typeof o === "object" && o.v === 1) {
        applyHydratedTasksAndEventsFromDoc(o);
      }
    } catch (_) {
      /* corrupt */
    }
  }

  /** Açılış: önce .lumos/tasks.json (panel_tasks_server); başarılı yanıtta dosya tek kaynak, sonra localStorage eşlenir. */
  function hydrateTasksJsonPersistenceAsync(done) {
    var url = getPanelTasksDocumentGetUrl();
    function finish() {
      hydrateEngineTasksFromInjectedBackendIfEmpty();
      if (typeof done === "function") done();
    }
    if (!url) {
      hydrateTasksJsonPersistenceSyncFallback();
      finish();
      return;
    }
    fetchWithTimeout(url, { method: "GET", headers: { Accept: "application/json" } })
      .then(function (r) {
        if (!r.ok) return Promise.reject(new Error("GET tasks.json"));
        return r.json();
      })
      .then(function (doc) {
        if (!doc || typeof doc !== "object") return Promise.reject(new Error("geçersiz JSON"));
        if (isPanelTasksApiRestMode()) {
          applyTasksApiOnlineSuccess(doc);
        } else {
          applyHydratedTasksAndEventsFromDoc(doc);
          persistTasksJsonDocumentLocalOnly();
          syncTaskSelectionAfterMutation();
        }
      })
      .catch(function () {
        if (isPanelTasksApiRestMode()) {
          applyTasksApiOfflineFallback();
        } else {
          hydrateTasksJsonPersistenceSyncFallback();
        }
      })
      .then(function () {
        finish();
      });
  }

  /**
   * Hash değişiminde tek GET: API geri geldiyse online + canlı doc; yoksa offline-cache + localStorage.
   * Tekrar deneme döngüsü yok; tek istek.
   */
  function scheduleTasksApiRevalidate() {
    if (!isPanelTasksApiRestMode()) return;
    var url = getPanelTasksDocumentGetUrl();
    if (!url) return;
    fetchWithTimeout(url, { method: "GET", headers: { Accept: "application/json" } })
      .then(function (r) {
        if (!r.ok) return Promise.reject(new Error("GET tasks"));
        return r.json();
      })
      .then(function (doc) {
        if (!doc || typeof doc !== "object") return Promise.reject(new Error("geçersiz JSON"));
        applyTasksApiOnlineSuccess(doc);
        refreshCurrentView();
      })
      .catch(function () {
        applyTasksApiOfflineFallback();
        refreshCurrentView();
      });
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

  /** Görev sohbet komutları: trim, çoklu boşluk, unicode space / nbsp. */
  function normalizeTaskCommandWhitespace(s) {
    return String(s || "")
      .replace(/[\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000\ufeff]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  /** Başlık/ref karşılaştırması için (lower-case + whitespace normalize). */
  function normalizeTaskCommandCompareKey(s) {
    return normalizeTaskCommandWhitespace(s).toLowerCase();
  }

  function taskTitleMatchesRef(ref, title) {
    var rKey = normalizeTaskCommandCompareKey(ref);
    var tKey = normalizeTaskCommandCompareKey(title);
    if (!rKey || !tKey) return false;
    if (tKey === rKey) return true;
    if (tKey.replace(/-/g, " ") === rKey.replace(/-/g, " ")) return true;
    if (tKey.replace(/\s+/g, "-") === rKey.replace(/\s+/g, "-")) return true;
    return false;
  }

  /**
   * active + done; deleted / pending_delete hariç. Önce tam id, sonra başlık (normalize + esnek tire).
   */
  function resolveEngineTaskByRef(ref) {
    var rTrim = normalizeTaskCommandWhitespace(ref);
    if (!rTrim) return null;
    var tasks = mockState.engineTasks || [];
    var i;
    var t;
    for (i = 0; i < tasks.length; i++) {
      t = tasks[i];
      if (!t || t.status === TASK_STATUS.DELETED) continue;
      if (t.status !== TASK_STATUS.ACTIVE && t.status !== TASK_STATUS.DONE) continue;
      if (String(t.id) === rTrim) return t;
    }
    for (i = 0; i < tasks.length; i++) {
      t = tasks[i];
      if (!t || t.status === TASK_STATUS.DELETED) continue;
      if (t.status !== TASK_STATUS.ACTIVE && t.status !== TASK_STATUS.DONE) continue;
      if (taskTitleMatchesRef(rTrim, t.title)) return t;
    }
    return null;
  }

  /** pending_delete; geri alma için ref çözümü. */
  function resolvePendingDeleteTaskByRef(ref) {
    var rTrim = normalizeTaskCommandWhitespace(ref);
    if (!rTrim) return null;
    var tasks = mockState.engineTasks || [];
    var i;
    var t;
    for (i = 0; i < tasks.length; i++) {
      t = tasks[i];
      if (!t || t.status !== TASK_STATUS.PENDING_DELETE) continue;
      if (String(t.id) === rTrim) return t;
    }
    for (i = 0; i < tasks.length; i++) {
      t = tasks[i];
      if (!t || t.status !== TASK_STATUS.PENDING_DELETE) continue;
      if (taskTitleMatchesRef(rTrim, t.title)) return t;
    }
    return null;
  }

  /**
   * Sil: kalıcı değil; pending_delete + expireAt. Kayıtta task_deleted yok; süre dolunca task_permanently_deleted.
   */
  function schedulePendingDeleteTask(ref) {
    var r = normalizeTaskCommandWhitespace(ref);
    if (!r) return { ok: false, reason: "empty" };
    var task = resolveEngineTaskByRef(r);
    if (!task) return { ok: false, reason: "not_found" };
    var prev = task.status === TASK_STATUS.DONE ? "done" : "active";
    task.status = TASK_STATUS.PENDING_DELETE;
    task.restoreStatus = prev;
    task.expireAt = new Date(Date.now() + PENDING_DELETE_GRACE_MS).toISOString();
    delete task.deletedAt;
    return { ok: true, task: task };
  }

  function undoPendingDeleteTask(ref) {
    var r = normalizeTaskCommandWhitespace(ref);
    if (!r) return { ok: false, reason: "empty" };
    var task = resolvePendingDeleteTaskByRef(r);
    if (!task) return { ok: false, reason: "not_found" };
    var rs = task.restoreStatus === "done" ? "done" : "active";
    task.status = rs;
    delete task.restoreStatus;
    delete task.expireAt;
    if (rs === TASK_STATUS.ACTIVE) task.completedAt = null;
    appendPanelEngineEvent({
      type: "task_restored",
      taskId: task.id,
      text: "Silme geri alındı",
    });
    return { ok: true, task: task };
  }

  /**
   * Aktif görevi tamamlar; aynı ref tamamlanmışsa already_done. Kalıcılık + UI: finalizeTaskMutation.
   */
  function completeTask(ref) {
    var r = normalizeTaskCommandWhitespace(ref);
    if (!r) return { ok: false, reason: "empty" };
    var task = resolveEngineTaskByRef(r);
    if (!task) return { ok: false, reason: "not_found" };
    if (task.status === TASK_STATUS.DONE) return { ok: false, reason: "already_done" };
    var now = new Date().toISOString();
    task.status = TASK_STATUS.DONE;
    task.completedAt = now;
    return { ok: true, task: task, completedAt: now };
  }

  /**
   * Motor olayını kuyruğa ekler (persist yok; görev mutasyonunda finalizeTaskMutation ile kapanır).
   * Minimal çağrı: { type: "task_completed", text, ts } — eksik id/taskId otomatik tamamlanır.
   */
  function appendPanelEngineEvent(ev) {
    if (!ev || !isPanelMotorEventType(ev.type)) return;
    var normalized = {
      id: ev.id != null ? String(ev.id) : newEngineEventId(),
      type: ev.type,
      taskId: ev.taskId != null ? String(ev.taskId) : "",
      text: ev.text != null ? String(ev.text).trim() : "",
      ts: ev.ts != null ? String(ev.ts) : new Date().toISOString(),
    };
    mockState.chatTaskCreations.push(normalized);
  }

  var LumosMinTaskEngine = {
    createTask: function (title) {
      var t = normalizeTaskCommandWhitespace(title);
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
    completeTask: completeTask,
    getTasksData: function () {
      return (mockState.engineTasks || []).slice();
    },
  };

  function createTaskCreatedEvent(taskId, taskTitle) {
    return buildPanelTaskEvent("task_created", taskId, taskTitle);
  }

  /** Eski oturumlarda kalan `time` alanını okurken ts ile hizala (yazmada yalnız ts). */
  function eventTimestamp(ev) {
    if (!ev) return null;
    if (ev.ts != null) return ev.ts;
    if (ev.time != null) return ev.time;
    return null;
  }

  function twoDigitNum(n) {
    n = Math.floor(Number(n));
    if (isNaN(n)) return "00";
    return n < 10 ? "0" + n : String(n);
  }

  /** Liste satırları: DD.MM HH:mm (yalnız görünüm; ham timestamp aynı kalır). */
  function formatUiListTimestamp(s) {
    if (s == null || s === "" || s === "—") return "—";
    try {
      var d = new Date(s);
      if (isNaN(d.getTime())) return formatTime(s);
      return (
        twoDigitNum(d.getDate()) +
        "." +
        twoDigitNum(d.getMonth() + 1) +
        " " +
        twoDigitNum(d.getHours()) +
        ":" +
        twoDigitNum(d.getMinutes())
      );
    } catch (_e) {
      return formatTime(s);
    }
  }

  function isTaskCreatedEvent(ev) {
    return !!(ev && (ev.type === "task_created" || ev.kind === "task_created"));
  }

  function isTaskCompletedEvent(ev) {
    return !!(ev && (ev.type === "task_completed" || ev.kind === "task_completed"));
  }

  function isTaskDeletedEvent(ev) {
    return !!(ev && (ev.type === "task_deleted" || ev.kind === "task_deleted"));
  }

  /** ISO 8601 bitiş → kalan tam saniye (0 altına düşmez). */
  function secondsRemainingUntilIso(iso) {
    var t = Date.parse(String(iso || ""));
    if (isNaN(t)) return 0;
    return Math.max(0, Math.ceil((t - Date.now()) / 1000));
  }

  /** Motor: en az bir pending_delete (ticker / görev notu / #tasks yenileme tek kaynak). */
  function engineHasPendingDeleteTasks() {
    var tasks = mockState.engineTasks || [];
    var i;
    for (i = 0; i < tasks.length; i++) {
      if (tasks[i] && tasks[i].status === TASK_STATUS.PENDING_DELETE) return true;
    }
    return false;
  }

  /**
   * Pending silme UI tek kuralı: yalnızca toTaskRow çıktısı (status Siliniyor + pendingExpireAt).
   * Liste, detay ipucu, meta; Geri al görünürlüğü busy dışında aynı row üzerinden.
   */
  function pendingDeleteUiFromRow(row) {
    if (!row || String(row.status || "") !== "Siliniyor") {
      return { active: false, secondsLeft: 0, expireAtIso: "", expireDisp: "—" };
    }
    var iso = row.pendingExpireAt != null && String(row.pendingExpireAt) !== "" ? String(row.pendingExpireAt) : "";
    var sec = iso ? secondsRemainingUntilIso(iso) : 0;
    return {
      active: true,
      secondsLeft: sec,
      expireAtIso: iso,
      expireDisp: iso ? formatTime(iso) : "—",
    };
  }

  // ——— UI adapter: motor görevi → Görevler stub satırı (filterTaskList: aktif / tamamlandı) ———
  function toTaskRow(task) {
    if (!task || task.id == null) return null;
    if (task.status === TASK_STATUS.DELETED) return null;
    if (task.status === TASK_STATUS.PENDING_DELETE) {
      var exp = task.expireAt != null ? String(task.expireAt) : "";
      var fromDone = task.restoreStatus === "done";
      return {
        id: String(task.id),
        title: task.title || "—",
        status: "Siliniyor",
        createdAt: task.createdAt || null,
        completedAt: fromDone && task.completedAt ? String(task.completedAt) : null,
        updated: task.expireAt || task.createdAt || null,
        lastRun: null,
        guardResult: "—",
        outputSummary: TASK_PENDING_DELETE_UI_LABEL,
        pendingExpireAt: exp || null,
        pendingSourceStatus: fromDone ? "tamamlandı" : "aktif",
      };
    }
    var done = task.status === TASK_STATUS.DONE;
    return {
      id: String(task.id),
      title: task.title || "—",
      status: done ? "tamamlandı" : "aktif",
      createdAt: task.createdAt || null,
      completedAt: done ? task.completedAt || null : null,
      updated: done && task.completedAt ? task.completedAt : task.createdAt || null,
      lastRun: null,
      guardResult: "—",
      outputSummary: done ? "Tamamlandı." : "—",
      summary: task.summary != null ? String(task.summary) : "",
      result: task.result != null ? String(task.result) : "",
      actions: {
        complete: !!(task.actions && task.actions.complete === true),
      },
    };
  }

  /** Kayıtlar / EventList için { ts, kind, text } */
  function toLogRow(event) {
    if (!event) return null;
    var ts = eventTimestamp(event);
    var kind = event.kind != null ? event.kind : "";
    if (!kind && event.type === "task_created") kind = "task_created";
    if (!kind && event.type === "task_completed") kind = "task_completed";
    if (!kind && event.type === "task_deleted") kind = "task_deleted";
    if (!kind && event.type === "task_permanently_deleted") kind = "permanently_deleted";
    if (!kind && event.type === "post_permanently_deleted") kind = "permanently_deleted";
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
    if (isTaskDeletedEvent(event)) return "Görev silindi (soft): " + (event.text || "—");
    if (event.type === "task_permanently_deleted") return event.text || "Görev kalıcı silindi";
    if (event.type === "post_permanently_deleted") return event.text || "Gönderi kalıcı silindi";
    return event.text || "—";
  }

  function isTaskMotorKindInLogRow(kind) {
    var k = kind != null ? String(kind) : "";
    return k === "task_created" || k === "task_completed" || k === "task_deleted";
  }

  /**
   * Backend/fixture log satırları (log.txt → log_items). task_* burada tekrarlanmasın; motor olayları yalnızca tasks.json events.
   */
  function getBasePanelEventsFromSource() {
    var src = getLogsSourceData();
    if ((src.type === "backend" || src.type === "fixture") && window.LumosFixtures && LC.normalizeLogs) {
      var data = LC.normalizeLogs(LumosFixtures.mapLogsPayloadToPanelData(src.data), {});
      var evs = Array.isArray(data.events) ? data.events.slice() : [];
      var out = [];
      var i;
      for (i = 0; i < evs.length; i++) {
        var e = evs[i];
        if (!e) continue;
        var k = e.kind != null ? String(e.kind) : "";
        if (isTaskMotorKindInLogRow(k)) continue;
        out.push(e);
      }
      return out;
    }
    return [];
  }

  /**
   * Görev motoru ledger: v:1 localStorage varsa events yalnız oradan (+ kalıcı olmayan policy_blocked bellekten).
   * v:1 yoksa mockState.chatTaskCreations (başlangıç []); mock ile LS aynı anda birleştirilmez.
   */
  function getTaskMotorEventsLedgerNewestFirst() {
    var list = [];
    var mem = mockState.chatTaskCreations || [];
    if (hasLocalTasksJsonCache()) {
      try {
        if (typeof localStorage !== "undefined") {
          var raw = localStorage.getItem(TASKS_JSON_STORAGE_KEY);
          if (raw) {
            var o = JSON.parse(raw);
            if (o && o.v === 1 && Array.isArray(o.events)) list = o.events.slice();
          }
        }
      } catch (_) {
        list = [];
      }
      var mi;
      for (mi = 0; mi < mem.length; mi++) {
        var me = mem[mi];
        if (me && me.type === "policy_blocked") list.push(me);
      }
    } else {
      list = mem.slice();
    }
    return chatEngineEventsNewestFirst(list);
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
   * Kayıtlar (tümü) + Dashboard Son Olaylar: aynı birleşik liste.
   * Motor: tasks.json events (task_* , task_permanently_deleted, post_permanently_deleted, …) + fixture/backend (task_* satırları hariç).
   */
  function getMergedPanelEventsList() {
    return getTaskMotorEventsLedgerNewestFirst().concat(getBasePanelEventsFromSource());
  }

  /**
   * Silinenler → «Kalıcı silinenler»: motor ledger’dan post_ + task_permanently_deleted (Kayıtlar’daki permanently_deleted ile aynı kaynak).
   */
  function getRecentPermanentDeleteMotorEvents(limit) {
    var n =
      typeof limit === "number" && limit > 0 ? Math.floor(limit) : RECENT_PERMANENT_DELETES_LIMIT;
    var ledger = getTaskMotorEventsLedgerNewestFirst();
    var out = [];
    var i;
    for (i = 0; i < ledger.length && out.length < n; i++) {
      if (
        ledger[i] &&
        (ledger[i].type === "post_permanently_deleted" || ledger[i].type === "task_permanently_deleted")
      ) {
        out.push(ledger[i]);
      }
    }
    return out;
  }

  /** Demo: Görevler yalnızca engineTasks (kayıt olaylarından türetilmez). deleted hiçbir filtrede listelenmez. */
  function getEngineTaskRowsForTasksScreen() {
    return (mockState.engineTasks || [])
      .filter(function (t) {
        return t && t.status !== TASK_STATUS.DELETED;
      })
      .map(toTaskRow)
      .filter(Boolean);
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
    return applyPanelWorkModeSubtitle(applyDashboardFromMergedEvents(data));
  }
  /** Görevler: backend/fixture = API listesi; demo = yalnızca engineTasks satırları. Seçim fullList üzerinden. */
  function taskIdEquals(a, b) {
    return String(a == null ? "" : a) === String(b == null ? "" : b);
  }

  /**
   * Silinenler satırı → POST /tasks/restore|delete-permanent gövdesindeki gerçek görev id'si.
   * Köprü: payload.id; yoksa task_id / taskId; son çare liste id (köprü ile aynı olmalı).
   */
  function resolveTrashListItemBackendTaskId(it) {
    if (!it || typeof it !== "object") return "";
    var pl = it.payload;
    if (pl && typeof pl === "object" && pl.id != null && String(pl.id).trim() !== "") {
      return String(pl.id).trim();
    }
    if (it.task_id != null && String(it.task_id).trim() !== "") return String(it.task_id).trim();
    if (it.taskId != null && String(it.taskId).trim() !== "") return String(it.taskId).trim();
    if (it.id != null && String(it.id).trim() !== "") return String(it.id).trim();
    return "";
  }

  /** Liste seçimi + POST { id }: sunucunun trash JSON payload.id ile aynı string. */
  function trashListRowKey(it) {
    var r = resolveTrashListItemBackendTaskId(it);
    if (r) return r;
    if (it && it.id != null && String(it.id).trim() !== "") return String(it.id).trim();
    return "";
  }

  /** Geri yükle / kalıcı sil: seçili satırdan backend id; buton dataset yalnız yedek. */
  function resolveTrashActionTaskIdForRequest(buttonDatasetId) {
    var data = getTrashData();
    var items = (data && data.listItems) || [];
    var sel = mockState.selectedTrashId != null ? String(mockState.selectedTrashId).trim() : "";
    var btn = buttonDatasetId != null ? String(buttonDatasetId).trim() : "";
    var row = null;
    var i;
    for (i = 0; i < items.length; i++) {
      var it = items[i];
      if (!it) continue;
      var key = trashListRowKey(it);
      if (sel && (taskIdEquals(it.id, sel) || taskIdEquals(key, sel))) {
        row = it;
        break;
      }
    }
    if (!row && btn) {
      for (i = 0; i < items.length; i++) {
        var it2 = items[i];
        if (!it2) continue;
        var k2 = trashListRowKey(it2);
        if (taskIdEquals(it2.id, btn) || taskIdEquals(k2, btn)) {
          row = it2;
          break;
        }
      }
    }
    if (row) {
      var tid = resolveTrashListItemBackendTaskId(row);
      if (tid) return tid;
      if (row.id != null && String(row.id).trim() !== "") return String(row.id).trim();
    }
    return btn;
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
    if (selId != null && selId !== "" && !data.selectedTask) {
      mockState.selectedTaskId = null;
      data.selectedId = null;
    }
    return data;
  }

  function getTasksViewData() {
    var src = getTasksSourceData();
    var fullList = getEngineTaskRowsForTasksScreen();
    var data;
    if ((src.type === "backend" || src.type === "fixture") && window.LumosFixtures && LC.normalizeTasks) {
      data = LC.normalizeTasks(LumosFixtures.mapTasksPayloadToPanelData(src.data), {});
    } else {
      var s = getEffectiveState();
      var sMerged = {};
      for (var sk in s) sMerged[sk] = s[sk];
      sMerged.taskList = fullList;
      data = LC.normalizeTasks(LC.buildTasksStub(sMerged), sMerged);
    }
    data.subtitle = getPanelWorkModeStatusLine();
    var af = mockState.taskFilter || data.activeFilter || "all";
    applyTasksViewFromMergedFullList(data, fullList, af);
    if (engineHasPendingDeleteTasks()) {
      var baseNote = (data.runNoteBody || "").trim();
      data.runNoteBody =
        baseNote +
        (baseNote ? " " : "") +
        "Silme bekleyen görevler listede kalır (sayaç + Geri al); süre dolunca kalıcı silinir ve Kayıtlar’da izlenebilir.";
    }
    data.taskActionGate = mockState.taskActionGate;
    return data;
  }

  function getTaskActionGate(data, action) {
    var g = data && data.taskActionGate && typeof data.taskActionGate === "object" ? data.taskActionGate : null;
    var row = g && g[action] && typeof g[action] === "object" ? g[action] : null;
    if (!row) return { enabled: false, reason: "Aksiyon durumu alınamadı" };
    return { enabled: row.enabled === true, reason: row.reason ? String(row.reason) : "İşlem şu anda kullanılamıyor" };
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

  function trashTimestampRawIsParsable(s) {
    if (s == null) return false;
    var t = String(s).trim();
    if (t === "" || t === "—") return false;
    var ms = Date.parse(t);
    return !isNaN(ms);
  }

  /** moved_at / deleted_at: "—" placeholder'ı atla; her iki alanı da dene (|| tek alanda hata yapıyordu). */
  function trashLatestTimestampFromListItems(list) {
    var arr = list || [];
    var best = null;
    var bestMs = -1;
    var i;
    for (i = 0; i < arr.length; i++) {
      var it = arr[i];
      if (!it) continue;
      var cand = [it.movedAt, it.deletedAt, it.moved_at, it.deleted_at];
      var c;
      for (c = 0; c < cand.length; c++) {
        var s = cand[c];
        if (!trashTimestampRawIsParsable(s)) continue;
        var ms = Date.parse(String(s).trim());
        if (!isNaN(ms) && ms > bestMs) {
          bestMs = ms;
          best = String(s).trim();
        }
      }
    }
    return best;
  }

  /** lumos-read-state: çöp dizini (dosya listesi boş veya satırlarda trashPath yokken tek doğru kaynak). */
  function readTrashDirectoryPathFromLumosState() {
    var w = typeof window !== "undefined" ? window : null;
    var rs = w && w.__LUMOS_READ_STATE__;
    if (!rs) return "";
    var tr = rs.trash;
    if (tr && tr.trash_location != null) {
      var a = String(tr.trash_location).trim();
      if (a && a !== "—") return a;
    }
    var sp = rs.system && rs.system.system_paths;
    if (sp && sp.trash != null) {
      var b = String(sp.trash).trim();
      if (b && b !== "—") return b;
    }
    return "";
  }

  function trashFilePathToParentDir(tp) {
    var s = tp != null ? String(tp).trim() : "";
    if (!s || s === "—") return "";
    var slash = Math.max(s.lastIndexOf("/"), s.lastIndexOf("\\"));
    return slash >= 0 ? s.slice(0, slash) : s;
  }

  /** Önce köprü trash_location / system_paths.trash; yoksa liste öğelerindeki trashPath üst dizini. */
  function resolveTrashLocationMetric(trashDirectoryFromBridge, listItems) {
    var hint = trashDirectoryFromBridge != null ? String(trashDirectoryFromBridge).trim() : "";
    if (hint && hint !== "—") return hint;
    var list = Array.isArray(listItems) ? listItems : [];
    var pi;
    for (pi = 0; pi < list.length; pi++) {
      var dir = trashFilePathToParentDir(list[pi] && list[pi].trashPath);
      if (dir) return dir;
    }
    return "—";
  }

  /** Üç üst metrik: sayım ve tarih listItems; çöp konumu köprü + liste yolu. */
  function buildTrashSummaryMetricsFromListItems(listItems, trashDirectoryFromBridge) {
    var list = Array.isArray(listItems) ? listItems : [];
    var n = list.length;
    var latestRaw = n > 0 ? trashLatestTimestampFromListItems(list) : null;
    var hint = trashDirectoryFromBridge != null ? String(trashDirectoryFromBridge).trim() : "";
    var loc = resolveTrashLocationMetric(hint, list);
    return [
      { title: "Çöp konumu", value: loc },
      { title: "Son taşıma", value: latestRaw ? formatTime(latestRaw) : "—" },
      { title: "Öğe sayısı", value: String(n) },
    ];
  }

  function trashItemRowTimestampFormatted(it) {
    if (!it) return "—";
    var cand = [it.movedAt, it.deletedAt, it.moved_at, it.deleted_at];
    var c;
    for (c = 0; c < cand.length; c++) {
      var s = cand[c];
      if (!trashTimestampRawIsParsable(s)) continue;
      return formatTime(String(s).trim());
    }
    return "—";
  }

  function applyTrashLedgerMerge(data) {
    if (!data) return data;
    if (!Array.isArray(data.listItems)) data.listItems = [];
    var n = data.listItems.length;
    data.trashItemCount = n;
    var selTrashKey = mockState.selectedTrashId || data.selectedId;
    data.selectedItem =
      (data.listItems || []).filter(function (i) {
        return (
          taskIdEquals(i.id, selTrashKey) || taskIdEquals(trashListRowKey(i), selTrashKey)
        );
      })[0] || null;
    var bridgeTrashDir =
      data.trashDirectoryPath != null && String(data.trashDirectoryPath).trim() !== ""
        ? String(data.trashDirectoryPath).trim()
        : readTrashDirectoryPathFromLumosState();
    data.trashDirectoryPath = bridgeTrashDir;
    data.summaryMetrics = buildTrashSummaryMetricsFromListItems(data.listItems, bridgeTrashDir);
    return data;
  }

  function resolveTrashOpenPathForAction(data, metricDisplayValue) {
    var v = metricDisplayValue != null ? String(metricDisplayValue).trim() : "";
    if (v && v !== "—") return v;
    if (data && data.trashDirectoryPath != null) {
      var d = String(data.trashDirectoryPath).trim();
      if (d && d !== "—") return d;
    }
    return "";
  }

  function getTrashData() {
    var src = getTrashSourceData();
    if (src.type === "backend" && src.data && window.LumosFixtures && LC.normalizeTrash) {
      var w = typeof window !== "undefined" ? window : null;
      var rs = w && w.__LUMOS_READ_STATE__;
      var tr = rs && rs.trash ? rs.trash : {};
      var br = src.data;
      var items = Array.isArray(br.items) ? br.items : [];
      if ((!items || items.length === 0) && tr && Array.isArray(tr.trash_items) && tr.trash_items.length > 0) {
        items = tr.trash_items;
      }
      var payload = {
        items: items,
        trash_items: items,
        trash_location: tr.trash_location,
        trash_last_move: tr.trash_last_move,
        trash_item_count: items.length,
        trash_dir_exists: tr.trash_dir_exists === true,
        trash_scope_fallback_note: tr.trash_scope_fallback_note != null ? String(tr.trash_scope_fallback_note) : "",
      };
      var data = LC.normalizeTrash(LumosFixtures.mapTrashPayloadToPanelData(payload), {});
      var td =
        tr.trash_location != null && String(tr.trash_location).trim() !== "" && String(tr.trash_location).trim() !== "—"
          ? String(tr.trash_location).trim()
          : "";
      if (!td && rs && rs.system && rs.system.system_paths && rs.system.system_paths.trash != null) {
        var tps = String(rs.system.system_paths.trash).trim();
        if (tps && tps !== "—") td = tps;
      }
      data.trashDirectoryPath = td;
      data.selectedId = mockState.selectedTrashId || data.selectedId;
      var selK = mockState.selectedTrashId || data.selectedId;
      data.selectedItem =
        (data.listItems || []).filter(function (i) {
          return taskIdEquals(i.id, selK) || taskIdEquals(trashListRowKey(i), selK);
        })[0] || data.selectedItem;
      return applyPanelWorkModeSubtitle(applyTrashLedgerMerge(data));
    }
    var empty = {
      items: [],
      trash_items: [],
      trash_location: null,
      trash_last_move: null,
      trash_item_count: 0,
      trash_dir_exists: false,
      trash_scope_fallback_note: "",
    };
    var rs2 = typeof window !== "undefined" && window.__LUMOS_READ_STATE__ && window.__LUMOS_READ_STATE__.trash;
    if (rs2) {
      empty.trash_location = rs2.trash_location;
      empty.trash_last_move = rs2.trash_last_move;
      empty.trash_item_count = rs2.trash_item_count;
      empty.trash_dir_exists = rs2.trash_dir_exists === true;
      empty.trash_scope_fallback_note = rs2.trash_scope_fallback_note != null ? String(rs2.trash_scope_fallback_note) : "";
      if (Array.isArray(rs2.trash_items) && rs2.trash_items.length > 0) {
        empty.items = rs2.trash_items;
        empty.trash_items = rs2.trash_items;
        empty.trash_item_count = rs2.trash_item_count != null ? rs2.trash_item_count : rs2.trash_items.length;
      }
    }
    var dataNone = LC.normalizeTrash(LumosFixtures.mapTrashPayloadToPanelData(empty), {});
    return applyPanelWorkModeSubtitle(applyTrashLedgerMerge(dataNone));
  }

  function mergedEventToLogKind(ev) {
    var lr = toLogRow(ev);
    return lr && lr.kind != null ? String(lr.kind) : "";
  }

  function compareKayitlarEventTsAsc(a, b) {
    var ta = Date.parse(String(eventTimestamp(a) || ""));
    var tb = Date.parse(String(eventTimestamp(b) || ""));
    if (isNaN(ta)) ta = 0;
    if (isNaN(tb)) tb = 0;
    return ta - tb;
  }

  /**
   * Motor gruplama: kalıcı silme satırındaki görev adını çıkar (ham metin ≠ oluşturma başlığı eşleşmesi).
   * Aynı görevin 5 event’i tek `task:<id>` altında toplansın diye title anahtarı buradan üretilir.
   */
  function extractTitleForMotorEventGrouping(ev) {
    if (!ev) return "";
    var typ = ev.type != null ? String(ev.type) : "";
    var raw = ev.text != null ? String(ev.text).trim() : "";
    if (typ === "task_permanently_deleted") {
      var ex = extractPermanentDeleteLogTitle(raw);
      if (ex && !logEventTitleIsMissing(ex)) return ex;
    }
    return raw;
  }

  /** Ledger’daki task_created: aynı ada son oluşturulan görev id’si (tek satır hedefi). */
  function buildTitleToTaskIdFromLedger(events) {
    var map = {};
    if (!events || !events.length) return map;
    var asc = events.slice().sort(compareKayitlarEventTsAsc);
    var i;
    for (i = 0; i < asc.length; i++) {
      var e = asc[i];
      if (!e || e.type !== "task_created") continue;
      var id = e.taskId != null ? String(e.taskId).trim() : "";
      if (!id) continue;
      var k = normalizeTaskCommandCompareKey(extractTitleForMotorEventGrouping(e));
      if (k) map[k] = id;
    }
    return map;
  }

  /**
   * task_completed vb. bazı kayıtlarda taskId boş; başlıktan engineTasks ile eşleştirip task:id ile birleştir.
   */
  function resolveMotorTaskGroupIdFromEvent(ev) {
    if (!ev) return "";
    var tid = ev.taskId != null ? String(ev.taskId).trim() : "";
    if (tid) return tid;
    var typ = ev.type != null ? String(ev.type) : "";
    if (
      typ !== "task_completed" &&
      typ !== "task_deleted" &&
      typ !== "task_permanently_deleted" &&
      typ !== "task_restored"
    ) {
      return "";
    }
    var title = extractTitleForMotorEventGrouping(ev);
    if (!title) return "";
    var keyCmp = normalizeTaskCommandCompareKey(title);
    if (!keyCmp) return "";
    var tasks = mockState.engineTasks || [];
    var i;
    var found = null;
    for (i = 0; i < tasks.length; i++) {
      var t = tasks[i];
      if (!t || t.id == null || String(t.id) === "") continue;
      if (normalizeTaskCommandCompareKey(t.title) === keyCmp) {
        if (found) return "";
        found = String(t.id);
      }
    }
    return found || "";
  }

  /**
   * Aynı görev / öğe satırı: motor taskId (+ başlıktan çözülen id); yoksa başlık anahtarı.
   * Diğer kayıtlar: tek satır = tek grup.
   */
  function kayitlarTimelineGroupKey(ev, titleToTaskIdMap) {
    if (!ev) return "single:empty";
    var typ = ev.type != null ? String(ev.type) : "";
    var knd = ev.kind != null ? String(ev.kind) : "";
    var tid = ev.taskId != null ? String(ev.taskId).trim() : "";
    if (
      typ === "task_created" ||
      typ === "task_completed" ||
      typ === "task_deleted" ||
      typ === "task_restored" ||
      typ === "task_permanently_deleted"
    ) {
      if (tid) return "task:" + tid;
      var resolved = resolveMotorTaskGroupIdFromEvent(ev);
      if (resolved) return "task:" + resolved;
      var titleKey = normalizeTaskCommandCompareKey(extractTitleForMotorEventGrouping(ev));
      if (titleKey && titleToTaskIdMap && titleToTaskIdMap[titleKey]) {
        return "task:" + titleToTaskIdMap[titleKey];
      }
      if (titleKey) return "tasktitle:" + titleKey;
      return "task_evt:" + String(ev.id != null ? ev.id : eventTimestamp(ev));
    }
    if (typ === "post_permanently_deleted") {
      return "post:" + (tid || String(ev.id != null ? ev.id : eventTimestamp(ev)));
    }
    if (typ === "policy_blocked") {
      return "policy:" + String(ev.id != null ? ev.id : eventTimestamp(ev));
    }
    if (typ === "" && knd) {
      return (
        "log:" +
        knd +
        ":" +
        String(ev.id != null ? ev.id : eventTimestamp(ev)) +
        ":" +
        String(ev.text != null ? ev.text : "").slice(0, 32)
      );
    }
    return "single:" + String(ev.id != null ? ev.id : eventTimestamp(ev));
  }

  function kayitlarTimelineGroupTitle(events) {
    if (!events || !events.length) return "—";
    var j;
    for (j = 0; j < events.length; j++) {
      var ev = events[j];
      if (ev && ev.type === "task_created" && ev.text != null && String(ev.text).trim() !== "") {
        return String(ev.text).trim();
      }
    }
    var last = events[events.length - 1];
    if (last && last.type === "policy_blocked" && last.text) {
      return String(last.text);
    }
    var lr = toLogRow(last);
    var raw = last && last.text != null ? String(last.text) : "";
    if (lr && lr.kind === "permanently_deleted") {
      var ext = extractPermanentDeleteLogTitle(raw);
      if (ext && !logEventTitleIsMissing(ext)) return ext;
    }
    if (raw && !logEventTitleIsMissing(raw)) {
      var oneLine = raw.replace(/\s+/g, " ").trim();
      return oneLine.length > 100 ? oneLine.slice(0, 97) + "…" : oneLine;
    }
    return formatLogEventListBody(lr ? lr.kind : "", raw) || "—";
  }

  function kayitlarTimelineGroupStatus(lastEv) {
    if (!lastEv) return { label: "Güncellendi", variant: "default" };
    var typ = lastEv.type != null ? String(lastEv.type) : "";
    var lr = toLogRow(lastEv);
    var lk = lr ? lr.kind : "";
    if (typ === "task_permanently_deleted" || lk === "permanently_deleted") {
      return { label: "Kalıcı silindi", variant: "permanently_deleted" };
    }
    if (typ === "post_permanently_deleted") {
      return { label: "Kalıcı silindi", variant: "permanently_deleted" };
    }
    if (typ === "task_deleted" || lk === "task_deleted") {
      return { label: "Çöpte", variant: "deleted" };
    }
    if (typ === "task_completed" || lk === "task_completed") {
      return { label: "Tamamlandı", variant: "completed" };
    }
    if (typ === "task_restored" || lk === "task_restored") {
      return { label: "Geri alındı", variant: "created" };
    }
    if (typ === "task_created" || lk === "task_created") {
      return { label: "Aktif", variant: "created" };
    }
    if (typ === "policy_blocked") {
      return { label: "Engellendi", variant: "default" };
    }
    if (lk === "trash") {
      return { label: "Çöpte", variant: "trash" };
    }
    if (lk === "görev") {
      return { label: "Güncellendi", variant: "completed" };
    }
    if (lk === "sandbox" || lk === "config" || lk === "identity" || lk === "keystore" || lk === "guard") {
      return { label: "Güncellendi", variant: "default" };
    }
    return { label: "Güncellendi", variant: "default" };
  }

  /** Kayıtlar detay zaman çizelgesi: sabit Türkçe adımlar (teknik kind/type kullanıcıya yansımaz). */
  function kayitlarTimelineStepLabel(ev) {
    if (!ev) return "güncellendi";
    var typ = ev.type != null ? String(ev.type) : "";
    if (typ === "task_created") return "oluşturuldu";
    if (typ === "task_completed") return "tamamlandı";
    if (typ === "task_restored") return "geri alındı";
    if (typ === "task_deleted") return "çöpe taşındı";
    if (typ === "task_permanently_deleted") return "kalıcı silindi";
    if (typ === "post_permanently_deleted") return "kalıcı silindi";
    if (typ === "policy_blocked") return "engellendi";
    var k = ev.kind != null ? String(ev.kind) : "";
    var lr = toLogRow(ev);
    var lk = lr ? lr.kind : k;
    if (lk === "task_created") return "oluşturuldu";
    if (lk === "task_completed") return "tamamlandı";
    if (lk === "task_restored") return "geri alındı";
    if (lk === "task_deleted") return "çöpe taşındı";
    if (lk === "permanently_deleted") return "kalıcı silindi";
    if (lk === "trash") return "çöpe taşındı";
    if (lk === "görev") return "güncellendi";
    if (lk === "sandbox" || lk === "config" || lk === "identity" || lk === "keystore" || lk === "guard") {
      return "güncellendi";
    }
    return "güncellendi";
  }

  /** Detay timeline’da gösterim: ilk harf büyük (tr-TR). */
  function kayitlarStepLabelTitleCase(lowerLabel) {
    var s = lowerLabel != null ? String(lowerLabel).trim() : "";
    if (!s) return "";
    try {
      return s.charAt(0).toLocaleUpperCase("tr-TR") + s.slice(1);
    } catch (_e) {
      return s.charAt(0).toUpperCase() + s.slice(1);
    }
  }

  /** Özet başlık: son durum (ör. TAMAMLANDI). */
  function kayitlarTimelineSummaryHeadline(statusLabel) {
    if (statusLabel == null || statusLabel === "") return "";
    try {
      return String(statusLabel).toLocaleUpperCase("tr-TR");
    } catch (_e) {
      return String(statusLabel).toUpperCase();
    }
  }

  /** Zaman çizelgesi alt satırı: yalnızca ek bağlam (ad, dosya); üstteki adım etiketi tekrarlanmaz. */
  function kayitlarTimelineStepDetailText(ev) {
    if (!ev) return "";
    var typ = ev.type != null ? String(ev.type) : "";
    var raw = ev.text != null ? String(ev.text).trim() : "";
    if (typ === "task_created" || typ === "task_completed" || typ === "task_deleted" || typ === "task_restored") {
      if (!raw || logEventTitleIsMissing(raw)) return "";
      return raw;
    }
    if (typ === "task_permanently_deleted" || typ === "post_permanently_deleted") {
      var ext = extractPermanentDeleteLogTitle(raw);
      if (ext && !logEventTitleIsMissing(ext)) return ext;
      return "";
    }
    if (typ === "policy_blocked") {
      return raw && !logEventTitleIsMissing(raw) ? raw : "";
    }
    var lr = toLogRow(ev);
    var lk = lr ? lr.kind : "";
    if (lk === "permanently_deleted") {
      var ex = extractPermanentDeleteLogTitle(raw);
      if (ex && !logEventTitleIsMissing(ex)) return ex;
      return "";
    }
    if (lk === "trash") {
      var tr = extractTrashLogTitle(raw);
      if (tr && !logEventTitleIsMissing(tr)) return tr;
      return "";
    }
    if (lk === "task_created" || lk === "task_completed" || lk === "task_deleted" || lk === "task_restored") {
      if (!raw || logEventTitleIsMissing(raw)) return "";
      return raw;
    }
    if (raw && !logEventTitleIsMissing(raw)) {
      var oneLine = raw.replace(/\s+/g, " ").trim();
      return oneLine.length > 120 ? oneLine.slice(0, 117) + "…" : oneLine;
    }
    return "";
  }

  function kayitlarStatusIconHtml(variant) {
    var v = variant != null ? String(variant) : "default";
    if (v === "permanently_deleted") {
      return '<span class="kayitlar-status-badge__icon" aria-hidden="true">\uD83D\uDDD1\uFE0F\u274C</span>';
    }
    if (v === "deleted" || v === "trash") {
      return '<span class="kayitlar-status-badge__icon" aria-hidden="true">\uD83D\uDDD1\uFE0F</span>';
    }
    if (v === "completed") {
      return '<span class="kayitlar-status-badge__icon kayitlar-status-badge__icon--symbol" aria-hidden="true">\u2713</span>';
    }
    if (v === "created") {
      return '<span class="kayitlar-status-badge__icon kayitlar-status-badge__icon--symbol" aria-hidden="true">\u25CF</span>';
    }
    return '<span class="kayitlar-status-badge__icon kayitlar-status-badge__icon--symbol" aria-hidden="true">\u25CB</span>';
  }

  /** Aynı olay id’si tekrar ledger’da görünürse tek satırda çift adım oluşmasın. */
  function dedupeKayitlarEventsById(events) {
    if (!events || !events.length) return events;
    var seen = {};
    var out = [];
    var i;
    for (i = 0; i < events.length; i++) {
      var e = events[i];
      if (!e) continue;
      var eid = e.id != null ? String(e.id) : "";
      if (eid) {
        if (seen[eid]) continue;
        seen[eid] = true;
      }
      out.push(e);
    }
    return out;
  }

  /**
   * tasktitle:* ile kalan kovalar, aynı başlıklı task:* kovasına taşınır (çift satır önleme).
   */
  function mergeKayitlarOrphanTitleBuckets(map, order) {
    var toRemove = [];
    var ri;
    for (ri = 0; ri < order.length; ri++) {
      var k = order[ri];
      if (k.indexOf("tasktitle:") !== 0) continue;
      var tk = k.slice("tasktitle:".length);
      var bucket = map[k];
      if (!bucket || !bucket.events.length) continue;
      var mergeInto = null;
      var oi;
      for (oi = 0; oi < order.length; oi++) {
        var ok = order[oi];
        if (ok === k || ok.indexOf("task:") !== 0) continue;
        var ob = map[ok];
        if (!ob || !ob.events.length) continue;
        var ej;
        for (ej = 0; ej < ob.events.length; ej++) {
          if (
            normalizeTaskCommandCompareKey(extractTitleForMotorEventGrouping(ob.events[ej])) === tk
          ) {
            mergeInto = ok;
            break;
          }
        }
        if (mergeInto) break;
      }
      if (mergeInto) {
        map[mergeInto].events = map[mergeInto].events.concat(bucket.events);
        delete map[k];
        toRemove.push(k);
      }
    }
    if (!toRemove.length) return order;
    return order.filter(function (x) {
      return toRemove.indexOf(x) === -1;
    });
  }

  /**
   * Kayıtlar sunum modeli: event dizisi değil, öğe (kayıt) listesi.
   * Her kayıt = { key, title, statusLabel, statusVariant, lastTs, events } — events yalnız detay timeline’da.
   */
  function buildKayitlarTimelineGroups(filteredEvents) {
    var titleToTaskIdMap = buildTitleToTaskIdFromLedger(filteredEvents);
    var map = {};
    var order = [];
    var i;
    for (i = 0; i < filteredEvents.length; i++) {
      var ev = filteredEvents[i];
      if (!ev) continue;
      if (!toLogRow(ev)) continue;
      var key = kayitlarTimelineGroupKey(ev, titleToTaskIdMap);
      if (!map[key]) {
        map[key] = { key: key, events: [] };
        order.push(key);
      }
      map[key].events.push(ev);
    }
    order = mergeKayitlarOrphanTitleBuckets(map, order);
    var groups = [];
    for (var oi = 0; oi < order.length; oi++) {
      var g = map[order[oi]];
      if (!g) continue;
      g.events.sort(compareKayitlarEventTsAsc);
      g.events = dedupeKayitlarEventsById(g.events);
      var lastEv = g.events[g.events.length - 1];
      g.title = kayitlarTimelineGroupTitle(g.events);
      var st = kayitlarTimelineGroupStatus(lastEv);
      g.statusLabel = st.label;
      g.statusVariant = st.variant;
      g.lastTs = eventTimestamp(lastEv);
      groups.push(g);
    }
    groups.sort(function (a, b) {
      var da = Date.parse(String(a.lastTs || ""));
      var db = Date.parse(String(b.lastTs || ""));
      if (isNaN(da)) da = 0;
      if (isNaN(db)) db = 0;
      return db - da;
    });
    return groups;
  }

  /** Kayıt grubu → gösterilecek kimlik (veri modeli değişmez; yalnız görünüm). */
  function kayitlarRecordDisplayId(g) {
    if (!g || g.key == null || String(g.key) === "") return "—";
    var k = String(g.key);
    if (k.indexOf("task:") === 0) return k.slice("task:".length);
    if (k.indexOf("post:") === 0) return k.slice("post:".length);
    if (k.indexOf("policy:") === 0) return k.slice("policy:".length);
    var evs = g.events || [];
    var ei;
    for (ei = 0; ei < evs.length; ei++) {
      var ev = evs[ei];
      if (ev && ev.taskId != null && String(ev.taskId).trim() !== "") return String(ev.taskId).trim();
    }
    for (ei = 0; ei < evs.length; ei++) {
      var e2 = evs[ei];
      if (e2 && e2.id != null && String(e2.id).trim() !== "") return String(e2.id).trim();
    }
    return k;
  }

  /**
   * Olay dizisinden meta zamanları (oluşturma = ilk olay, güncelleme = son olay;
   * tamamlanma / silinme = ilgili türlerin son eşlemesi).
   */
  function kayitlarRecordMetaFromEvents(events) {
    var out = {
      created: null,
      updated: null,
      completed: null,
      movedToTrash: null,
      permanentDeleted: null,
    };
    if (!events || !events.length) return out;
    out.created = eventTimestamp(events[0]);
    out.updated = eventTimestamp(events[events.length - 1]);
    var i;
    for (i = 0; i < events.length; i++) {
      var ev = events[i];
      if (!ev) continue;
      var typ = ev.type != null ? String(ev.type) : "";
      var lr = toLogRow(ev);
      var lk = lr ? lr.kind : "";
      var ts = eventTimestamp(ev);
      if (typ === "task_completed" || lk === "task_completed") {
        out.completed = ts;
      }
      if (typ === "task_deleted" || lk === "task_deleted") {
        out.movedToTrash = ts;
      }
      if (typ === "task_permanently_deleted" || typ === "post_permanently_deleted" || lk === "permanently_deleted") {
        out.permanentDeleted = ts;
      }
    }
    return out;
  }

  function wrapKayitlarDetailPanel(bodyInner) {
    return (
      '<div class="detail-panel kayitlar-timeline-detail">' +
      '<div class="detail-title">Detay</div>' +
      '<div class="detail-body kayitlar-timeline-detail-body">' +
      bodyInner +
      "</div></div>"
    );
  }

  function buildKayitlarTimelineDetailHtml(groups, selectedKey) {
    if (!selectedKey) {
      return wrapKayitlarDetailPanel(
        '<p class="text-muted-small kayitlar-detail-placeholder">' +
          escapeHtmlYanit(
            "Henüz seçim yok. Soldaki listeden bir kayda tıklayın; süreç zaman çizelgesi ve temel bilgiler burada görünür."
          ) +
          "</p>"
      );
    }
    var g = null;
    var gi;
    for (gi = 0; gi < groups.length; gi++) {
      if (groups[gi] && groups[gi].key === selectedKey) {
        g = groups[gi];
        break;
      }
    }
    if (!g) {
      return wrapKayitlarDetailPanel(
        '<p class="text-muted-small kayitlar-detail-placeholder">' +
          escapeHtmlYanit(
            "Bu seçim artık listede yok (ör. sekme değişti). Soldan geçerli bir kayıt seçin."
          ) +
          "</p>"
      );
    }
    var lastEv = g.events[g.events.length - 1];
    var st = kayitlarTimelineGroupStatus(lastEv);
    var summaryTimeUi = formatUiListTimestamp(eventTimestamp(lastEv));
    var summaryHead = kayitlarTimelineSummaryHeadline(st.label);
    var summaryClasses =
      "kayitlar-timeline-summary kayitlar-timeline-summary--" +
      String(st.variant || "default") +
      (st.variant === "created" ? " kayitlar-timeline-summary--pulse" : "");
    var summaryHtml =
      '<div class="' +
      summaryClasses +
      '">' +
      '<div class="kayitlar-timeline-summary-state">' +
      escapeHtmlYanit(summaryHead) +
      "</div>" +
      '<div class="kayitlar-timeline-summary-time">' +
      escapeHtmlYanit(summaryTimeUi) +
      "</div></div>";

    var lastIdx = g.events.length - 1;
    var ul = '<ul class="kayitlar-timeline-process">';
    var j;
    for (j = 0; j < g.events.length; j++) {
      var ev = g.events[j];
      var stepRaw = kayitlarTimelineStepLabel(ev);
      var stepDisp = kayitlarStepLabelTitleCase(stepRaw);
      var tsUi = formatUiListTimestamp(eventTimestamp(ev));
      var detailLine = kayitlarTimelineStepDetailText(ev);
      var stepClasses = "kayitlar-timeline-process-step";
      if (j === lastIdx) stepClasses += " kayitlar-timeline-process-step--latest";
      else stepClasses += " kayitlar-timeline-process-step--past";
      ul +=
        '<li class="' +
        stepClasses +
        '">' +
        '<div class="kayitlar-timeline-process-rail">' +
        '<span class="kayitlar-timeline-process-dot" aria-hidden="true">\u25CF</span></div>' +
        '<div class="kayitlar-timeline-process-body">' +
        '<div class="kayitlar-timeline-process-line">' +
        '<span class="kayitlar-timeline-process-label">' +
        escapeHtmlYanit(stepDisp) +
        "</span>" +
        '<span class="kayitlar-timeline-process-sep"> \u2014 </span>' +
        '<span class="kayitlar-timeline-process-time">' +
        escapeHtmlYanit(tsUi) +
        "</span></div>";
      if (detailLine) {
        ul +=
          '<div class="kayitlar-timeline-process-detail text-muted-small">' +
          escapeHtmlYanit(detailLine) +
          "</div>";
      }
      ul += "</div></li>";
    }
    ul += "</ul>";
    var meta = kayitlarRecordMetaFromEvents(g.events);
    var idDisp = kayitlarRecordDisplayId(g);
    var metaRows = [
      {
        label: "Kimlik",
        value: '<small class="task-detail-id-wrap"><code>' + escapeHtmlYanit(idDisp) + "</code></small>",
      },
      { label: "Oluşturulma", value: meta.created ? formatTime(meta.created) : "—" },
      { label: "Son güncelleme", value: meta.updated ? formatTime(meta.updated) : "—" },
    ];
    if (meta.completed) {
      metaRows.push({ label: "Tamamlanma", value: formatTime(meta.completed) });
    }
    if (meta.movedToTrash) {
      metaRows.push({ label: "Çöpe taşınma", value: formatTime(meta.movedToTrash) });
    }
    if (meta.permanentDeleted) {
      metaRows.push({ label: "Kalıcı silinme", value: formatTime(meta.permanentDeleted) });
    }
    var metaHtml =
      '<p class="kayitlar-detail-meta-heading">Temel bilgiler</p>' + buildDetailRows(metaRows);
    return wrapKayitlarDetailPanel(
      summaryHtml +
        '<div class="detail-title kayitlar-timeline-detail-record-title">' +
        escapeHtmlYanit(g.title) +
        "</div>" +
        '<div class="kayitlar-timeline-process-wrap kayitlar-timeline-process-wrap--secondary">' +
        ul +
        "</div>" +
        '<div class="kayitlar-detail-meta-block">' +
        metaHtml +
        "</div>"
    );
  }

  function KayitlarTimelineView(groups, selectedKey) {
    if (!groups || groups.length === 0) {
      return buildEmptyState("Henüz kayıt yok", "Bu sekme için gösterilecek satır yok.");
    }
    var listHtml = '<ul class="kayitlar-timeline-master list-selectable">';
    var i;
    for (i = 0; i < groups.length; i++) {
      var g = groups[i];
      var sel = selectedKey && g.key === selectedKey ? " selected" : "";
      var badgeClass = "kayitlar-status-badge kayitlar-status-badge--" + g.statusVariant;
      var lastTsUi = formatUiListTimestamp(g.lastTs);
      listHtml +=
        '<li class="kayitlar-timeline-row' +
        sel +
        '" data-kayitlar-timeline-key="' +
        escapeHtmlYanit(g.key) +
        '" role="button" tabindex="0">';
      listHtml +=
        '<span class="kayitlar-timeline-row-summary">' +
        '<span class="kayitlar-timeline-title">' +
        escapeHtmlYanit(g.title) +
        '</span><span class="kayitlar-timeline-row-trail">' +
        '<span class="' +
        badgeClass +
        '">' +
        kayitlarStatusIconHtml(g.statusVariant) +
        '<span class="kayitlar-status-badge__label">' +
        escapeHtmlYanit(g.statusLabel) +
        '</span></span><span class="kayitlar-timeline-date">' +
        escapeHtmlYanit(lastTsUi) +
        "</span></span></span>";
      listHtml += "</li>";
    }
    listHtml += "</ul>";
    var detailHtml = buildKayitlarTimelineDetailHtml(groups, selectedKey);
    return (
      '<div class="split-view kayitlar-timeline-split">' +
      '<div class="kayitlar-timeline-list-col">' +
      listHtml +
      "</div>" +
      '<div class="kayitlar-timeline-detail-col">' +
      detailHtml +
      "</div></div>"
    );
  }

  /** Ham birleşik olaylar → sekme süzgeci (Kayıtlar timeline; toLogRow + mevcut sekme kuralı). */
  function filterRawMergedEventsForKayitlar(merged, activeFilterId) {
    if (!activeFilterId || activeFilterId === "all") return merged.slice();
    return merged.filter(function (ev) {
      if (!ev) return false;
      var lr = toLogRow(ev);
      if (!lr) return false;
      return filterMergedLogEventsForKayitlar([lr], activeFilterId).length > 0;
    });
  }

  /** Sekme süzgeci: Görevler = task_* + görev kaynaklı kalıcı silme (permanently_deleted + metin). */
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
      if (kf === "trash" && e.kind === "permanently_deleted") return true;
      if (kf !== "görev") return false;
      if (e.kind === "task_created" || e.kind === "task_completed" || e.kind === "task_deleted") return true;
      if (e.kind === "permanently_deleted") {
        return String(e.text || "").indexOf("Görev kalıcı") !== -1;
      }
      return false;
    });
  }

  /** Kayıtlar: ham olaylar → sekme → kayitRecords (öğe bazlı sunum; events yalnız detayda). */
  function applyLogsViewFromMerged(data, mergedEvents, activeFilterId) {
    var af = activeFilterId || "all";
    var filteredRaw = filterRawMergedEventsForKayitlar(mergedEvents, af);
    var records = buildKayitlarTimelineGroups(filteredRaw);
    data.activeFilter = af;
    data.kayitRecords = records;
    data.logLineCount = records.length;
    data.events = [];
    return data;
  }

  function getLogsData() {
    var src = getLogsSourceData();
    var mergedEvents = getMergedPanelEventsList();
    var data;
    if ((src.type === "backend" || src.type === "fixture") && window.LumosFixtures && LC.normalizeLogs) {
      data = LC.normalizeLogs(LumosFixtures.mapLogsPayloadToPanelData(src.data), {});
    } else {
      var s = getEffectiveState();
      data = LC.normalizeLogs(LC.buildLogsStub(s), s);
    }
    var af = mockState.logFilter || data.activeFilter || "all";
    return applyPanelWorkModeSubtitle(applyLogsViewFromMerged(data, mergedEvents, af));
  }
  function getSystemStatusData() {
    var src = getSystemSourceData();
    var data;
    if ((src.type === "backend" || src.type === "fixture") && window.LumosFixtures && LC.normalizeSystem) {
      data = LC.normalizeSystem(LumosFixtures.mapSystemPayloadToPanelData(src.data), {});
    } else {
      data = LC.normalizeSystem(LC.buildSystemStub(src.data), src.data);
    }
    return applyPanelWorkModeSubtitle(data);
  }

  function getTopbarData() {
    var m = getEffectiveState();
    var badges = [];
    var modePres = getPanelWorkModePresentation();
    badges.push({ label: modePres.label, variant: modePres.variant });
    badges.push({
      label: getBadgeLabel("lock", m.keystoreState === "Kilitli" ? "LOCKED" : "UNLOCKED"),
      variant: getBadgeVariant(getBadgeLabel("lock", m.keystoreState === "Kilitli" ? "LOCKED" : "UNLOCKED")),
    });
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

  /** Silinenler: Çöp konumu kartı — POST /open-folder ile sistemde klasör açar. */
  function TrashLocationOpenMetricCard(title, displayValue, openPath) {
    var disp = displayValue != null ? String(displayValue) : "—";
    var op = openPath != null ? String(openPath).trim() : "";
    if (!op || op === "—" || disp === "—") {
      return MetricCard(title != null ? String(title) : "Çöp konumu", disp, null);
    }
    return (
      '<button type="button" class="metric-card metric-card--open-folder" data-lumos-open-folder="1" data-open-path="' +
      escapeHtmlYanit(op) +
      '" aria-label="Çöp klasörünü dosya yöneticisinde aç">' +
      '<div class="metric-title">' +
      escapeHtmlYanit(title != null ? String(title) : "Çöp konumu") +
      "</div>" +
      '<div class="metric-value">' +
      escapeHtmlYanit(disp) +
      "</div>" +
      '<p class="text-muted-small">Tıklayınca klasör açılır</p>' +
      "</button>"
    );
  }

  function SectionCard(title, bodyHtml) {
    return '<div class="section-card"><h2 class="section-title">' + title + "</h2><div class=\"section-body\">" + bodyHtml + "</div></div>";
  }

  /** Kayıtlar / Son Olaylar: kind → rozet sınıfı (yalnızca görünüm). */
  function logKayitEventBadgeVariant(kind) {
    var k = kind != null ? String(kind) : "";
    if (k === "task_created") return "created";
    if (k === "task_completed") return "completed";
    if (k === "task_deleted") return "deleted";
    if (k === "trash") return "trash";
    if (k === "permanently_deleted") return "permanently_deleted";
    return "default";
  }

  /** Kısa etiket: [created], [completed], … */
  function logKayitEventBadgeLabel(kind) {
    var k = kind != null ? String(kind) : "";
    if (k === "task_created") return "created";
    if (k === "task_completed") return "completed";
    if (k === "task_deleted") return "deleted";
    if (k === "trash") return "trash";
    if (k === "permanently_deleted") return "permanently_deleted";
    return k || "event";
  }

  function logEventTitleIsMissing(title) {
    var t = title != null ? String(title).trim() : "";
    return t === "" || t === "—" || t === "-" || t === "–";
  }

  function logEventFallbackLine(kind) {
    var k = kind != null ? String(kind).trim() : "";
    return "İşlem: " + (k || "event");
  }

  /** permanently_deleted: ham metinden başlık parçası (UI öncesi). */
  function extractPermanentDeleteLogTitle(raw) {
    var s = raw != null ? String(raw).trim() : "";
    if (!s) return "";
    var m;
    if ((m = /^Gönderi\s+kalıcı\s+silindi:\s*(.*)$/i.exec(s))) {
      return m[1].trim();
    }
    if ((m = /^Görev\s+kalıcı\s+silindi:\s*(.*)$/i.exec(s))) {
      return m[1].trim();
    }
    if (/^Gönderi\s+kalıcı\s+silindi$/i.test(s)) return "";
    if (/^Görev\s+kalıcı\s+silindi$/i.test(s)) return "";
    if ((m = /^Çöpteki\s+(\d+)\s+gönderi\s+kalıcı\s+silindi$/i.exec(s))) return m[1] + " gönderi";
    if (/^Çöpteki\s+gönderi\s+kalıcı\s+silindi$/i.test(s)) return "1 gönderi";
    if ((m = /^Kalıcı\s+silindi:\s*(.*)$/i.exec(s))) return m[1].trim();
    return s;
  }

  function extractTrashLogTitle(raw) {
    var s = raw != null ? String(raw).trim() : "";
    if (!s) return "";
    var m = /^Öğe\s+taşındı:\s*(.+)$/i.exec(s);
    if (m) return m[1].trim();
    return s;
  }

  /**
   * Kayıtlar / Son Olaylar: tek tip satır metni (yalnızca UI).
   */
  function formatLogEventListBody(kind, raw) {
    var k = kind != null ? String(kind) : "";
    var title;

    if (k === "task_created" || k === "task_completed" || k === "task_deleted") {
      title = raw != null ? String(raw).trim() : "";
      if (logEventTitleIsMissing(title)) return logEventFallbackLine(k);
      if (k === "task_created") return "Oluşturuldu: " + title;
      if (k === "task_completed") return "Tamamlandı: " + title;
      return "Çöpe taşındı: " + title;
    }

    if (k === "permanently_deleted") {
      title = extractPermanentDeleteLogTitle(raw);
      if (logEventTitleIsMissing(title)) return logEventFallbackLine("permanently_deleted");
      return "Kalıcı silindi: " + title;
    }

    if (k === "trash") {
      title = extractTrashLogTitle(raw);
      if (logEventTitleIsMissing(title)) return logEventFallbackLine("trash");
      return "Çöpe taşındı: " + title;
    }

    title = raw != null ? String(raw).trim() : "";
    if (logEventTitleIsMissing(title)) return logEventFallbackLine(k);
    return logEventFallbackLine(k) + ": " + title;
  }

  function EventList(events) {
    if (!events || events.length === 0) return '<ul class="event-list"><li>—</li></ul>';
    var html = '<ul class="event-list">';
    for (var i = 0; i < events.length; i++) {
      var e = events[i];
      var kind = e.kind != null ? String(e.kind) : "";
      var mod = logKayitEventBadgeVariant(kind);
      var shortLabel = logKayitEventBadgeLabel(kind);
      var iconHtml = "";
      if (mod === "permanently_deleted") {
        iconHtml = '<span class="log-event-badge__icon" aria-hidden="true">🗑️\uFE0F❌</span>';
      } else if (mod === "deleted") {
        iconHtml = '<span class="log-event-badge__icon" aria-hidden="true">⚠️</span>';
      } else if (mod === "trash") {
        iconHtml = '<span class="log-event-badge__icon" aria-hidden="true">🗑️\uFE0F</span>';
      }
      var bodyRaw = e.text != null ? String(e.text) : "";
      var bodyForList = formatLogEventListBody(kind, bodyRaw);
      var bodyClass = "log-event-body" + (mod === "permanently_deleted" ? " log-event-body--permanent_delete" : "");
      var tooltipText = String(bodyForList).replace(/\s+/g, " ").trim();
      var titleAttr = tooltipText !== "" ? ' title="' + escapeHtmlYanit(tooltipText) + '"' : "";
      html +=
        '<li class="log-event-row log-event-row--' +
        mod +
        '">' +
        '<span class="log-event-badge log-event-badge--' +
        mod +
        '">' +
        iconHtml +
        '<span class="log-event-badge__label">[' +
        escapeHtmlYanit(shortLabel) +
        "]</span></span>" +
        '<span class="event-time">' +
        escapeHtmlYanit(formatTime(e.ts)) +
        "</span>" +
        '<span class="' +
        bodyClass +
        '"' +
        titleAttr +
        ">" +
        escapeHtmlYanit(bodyForList) +
        "</span></li>";
    }
    return html + "</ul>";
  }

  /** Silinenler altı: yalnızca son kalıcı silinenler (salt okunur özet). */
  function humanPermanentDeleteLine(lr) {
    if (!lr) return "—";
    var raw = lr.text != null ? String(lr.text) : "";
    var title = extractPermanentDeleteLogTitle(raw);
    if (title && !logEventTitleIsMissing(title)) return title;
    var oneLine = raw.replace(/\s+/g, " ").trim();
    if (!oneLine) return "—";
    return oneLine.length > 100 ? oneLine.slice(0, 97) + "…" : oneLine;
  }

  function buildRecentPermanentDeletesSectionHtml() {
    var evs = getRecentPermanentDeleteMotorEvents(RECENT_PERMANENT_DELETES_LIMIT);
    var note = '<p class="text-muted-small trash-recent-permanent-note">Kayıtlar ekranında tüm geçmişe ulaşılır.</p>';
    if (evs.length === 0) {
      return buildSection(
        "Son kalıcı silinenler",
        note + '<p class="screen-placeholder">Henüz kayıt yok.</p>'
      );
    }
    var rows = "";
    var j;
    for (j = 0; j < evs.length; j++) {
      var lr = toLogRow(evs[j]);
      if (!lr) continue;
      var line = humanPermanentDeleteLine(lr);
      var tip = String(line).replace(/\s+/g, " ").trim();
      var titleAttr = tip !== "" ? ' title="' + escapeHtmlYanit(tip) + '"' : "";
      var tsUi = formatUiListTimestamp(lr.ts);
      rows +=
        '<li class="trash-recent-permanent-row">' +
        '<span class="trash-recent-permanent-stack">' +
        '<span class="trash-recent-permanent-name"' +
        titleAttr +
        ">" +
        escapeHtmlYanit(line) +
        "</span>" +
        '<span class="trash-recent-permanent-meta">Kalıcı silindi \u2022 ' +
        escapeHtmlYanit(tsUi) +
        "</span></span></li>";
    }
    return buildSection("Son kalıcı silinenler", note + '<ul class="trash-recent-permanent-list">' + rows + "</ul>");
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
    if (meta) {
      var wm = getPanelWorkModePresentation();
      meta.textContent = "Dal: " + data.branchName + " · " + wm.label;
    }
  }

  /** Veri kaynağı (tek satır); teknik endpoint listesi yok */
  function renderPostsApiBaseLine(F) {
    if (!F || !F.getBase) return "";
    return (
      '<p class="posts-api-base-line">' +
      '<span class="posts-api-base-label">Akış tabanı</span> ' +
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
      var feedHint = "";
      if (typeof window.LumosFeedApi !== "undefined" && window.LumosFeedApi.getBase) {
        feedHint = " · Akış bağlantısı ayarlı";
      }
      baseEl.textContent = "Çalışma alanı: " + data.basePath + feedHint;
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
      var dataSourceOpts =
        '<option value="demo"' +
        (useFixtureData ? '' : ' selected') +
        '>Yerel durum</option><option value="fixture"' +
        (useFixtureData ? ' selected' : '') +
        '>Sabit örnek</option>';
      actionsEl.innerHTML =
        '<div class="topbar-actions-dev">' +
        '<select id="demo-scenario-select" class="demo-scenario-select" aria-label="Örnek panel durumu" title="Örnek panel durumu">' +
        opts +
        "</select>" +
        '<select id="data-source-select" class="demo-scenario-select" aria-label="Veri kaynağı" title="Yerel durum veya sabit örnek veri">' +
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
    var modeLabel = g.mode === SOURCE_STATUS.ONLINE ? "Çevrimiçi" : "Çevrimdışı";
    var lockLabel = (g.lock || "").toUpperCase() === "UNLOCKED" ? "Açık" : "Kilitli";
    var consentLabel = g.consent ? "Açık" : "Kapalı";
    var durumHtml = "<p class=\"text-muted-small\"><strong>Mod:</strong> " + modeLabel + " · <strong>Kilit:</strong> " + lockLabel + " · <strong>Genel onay:</strong> " + consentLabel + "</p>";
    var engelHtml = (g.blocked_reason && g.blocked_reason.trim()) ? ("<p>" + g.blocked_reason + "</p>") : "<p class=\"text-muted-small\">Şu anda engel yok.</p>";
    var nextHtml = (g.next_step && g.next_step.trim()) ? ("<p>" + g.next_step + "</p>") : "<p class=\"text-muted-small\">Hazır.</p>";
    return SectionCard("Durum", durumHtml) + SectionCard("Engel", engelHtml) + SectionCard("Sonraki adım", nextHtml);
  }

  function buildLumosStatusCard() {
    var B = typeof LumosBackendBridge !== "undefined" ? LumosBackendBridge : {};
    var ls = B.readBackendLumosStatusState && B.readBackendLumosStatusState();
    var rs = typeof window !== "undefined" && window.__LUMOS_READ_STATE__ && window.__LUMOS_READ_STATE__.panel_meta;
    if (!ls) {
      return "<p class=\"text-muted-small\">Çekirdek durum köprüsü yok. <code>python panel/scripts/read_backend_state.py --write</code> çalıştırıp sayfayı yenileyin.</p>";
    }
    function esc(s) {
      if (s == null) return "";
      return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }
    var pf = (B.readBackendProductFeaturesState && B.readBackendProductFeaturesState()) || [];
    var apiFeat = null;
    for (var i = 0; i < pf.length; i++) {
      if (pf[i] && pf[i].key === "panel_api") { apiFeat = pf[i]; break; }
    }
    var apiLine = apiFeat ? (String(apiFeat.durum || "") + (apiFeat.aciklama ? (" — " + String(apiFeat.aciklama)) : "")) : "—";
    var modeTr = ls.online_mode === "online" ? "Çevrimiçi" : "Çevrimdışı";
    var coreTr = ls.core_active === true ? "Evet" : ls.core_active === false ? "Hayır" : "—";
    var sbTr = ls.sandbox_mode ? "Açık" : "Kapalı";
    var html = "";
    html += "<p><strong>API erişimi:</strong> " + esc(apiLine) + "</p>";
    html += "<p><strong>Çekirdek aktif:</strong> " + esc(coreTr) + " · <strong>Mod:</strong> " + esc(modeTr) + " · <strong>Sandbox:</strong> " + esc(sbTr) + " · <strong>Yazım:</strong> " + esc(ls.writing_base_dir) + "</p>";
    html += "<p class=\"text-muted-small\"><strong>Koruma (köprü):</strong> " + esc((window.__LUMOS_READ_STATE__ && window.__LUMOS_READ_STATE__.dashboard && window.__LUMOS_READ_STATE__.dashboard.guard_status) || "—") + "</p>";
    html += "<p class=\"text-muted-small\"><strong>Köprü zamanı:</strong> " + esc(ls.panel_bridge_built_at) + (ls.backend_live_at ? " · <strong>Backend canlı:</strong> " + esc(ls.backend_live_at) : "") + "</p>";
    if (rs && rs.server_time_utc) {
      html += "<p class=\"text-muted-small\"><strong>Sunucu zamanı (UTC):</strong> " + esc(rs.server_time_utc) + "</p>";
    }
    html += "<p class=\"text-muted-small\">" + esc(ls.state_inject_note) + "</p>";
    return html;
  }

  function buildProductFeaturesSection() {
    var B = typeof LumosBackendBridge !== "undefined" ? LumosBackendBridge : {};
    var items = B.readBackendProductFeaturesState && B.readBackendProductFeaturesState();
    if (!items || !items.length) return "<p class=\"text-muted-small\">Ürün özellik durumu henüz gelmedi.</p>";
    var html = '<div class="guidance-cards">';
    for (var i = 0; i < items.length; i++) {
      var f = items[i] || {};
      var ad = String(f.ad || f.key || "");
      var durum = typeof f.durum === "string" ? f.durum : "";
      var gor = typeof f.panelde_gorunuyor === "boolean" ? (f.panelde_gorunuyor ? "Evet" : "Hayır") : "—";
      var aciklama = typeof f.aciklama === "string" ? f.aciklama : "";
      var body =
        "<p><strong>Durum:</strong> " + ad + " · <strong>State:</strong> " + durum + " · <strong>Panel:</strong> " + gor + "</p>" +
        "<p class=\"text-muted-small\">" + aciklama + "</p>";
      html += SectionCard(ad, body);
    }
    html += "</div>";
    return html;
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
    var lumosStatusHtml = buildLumosStatusCard();
    var productFeaturesHtml = buildProductFeaturesSection();
    var sections =
      buildSection("Son Olaylar", EventList(data.sections[0].events)) +
      buildSection("Uyarılar ve notlar", warningsHtml) +
      buildSection("Canlı Sistem Durumu", lumosStatusHtml) +
      buildSection("Ürün Özellikleri", productFeaturesHtml) +
      buildSection("Durum ve rehber", guidanceHtml) +
      buildSection("Hızlı geçişler", '<p><a href="#feed" class="inline-link">Akış</a> (API) · <a href="#tasks" class="inline-link">Görevler</a> · <a href="#sandbox" class="inline-link">Korumalı Alan</a> · <a href="#config" class="inline-link">Yapılandırma</a> · <a href="#logs" class="inline-link">Kayıtlar</a></p><p class="text-muted-small">Hash ile sayfa yenilenmeden geçiş.</p>');
    return ViewHeader(data.title, data.subtitle) + '<div class="cards-grid">' + cards + "</div>" + sections;
  }

  function escapeHtmlYanit(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function inferTaskPanelActionFromCmd(cmd) {
    var c = String(cmd || "").trim().toLowerCase();
    if (/^görev\s+tamamla\b/.test(c) || /^gorev\s+tamamla\b/.test(c)) return "complete";
    if (/^görev\s+sil\b/.test(c) || /^gorev\s+sil\b/.test(c)) return "delete";
    if (/^görev\s+geri\s+al\b/.test(c) || /^gorev\s+geri\s+al\b/.test(c)) return "undo";
    if (/^görev\s+oluştur\b/.test(c) || /^gorev\s+olustur\b/.test(c)) return "create";
    return "";
  }

  function inferTaskPanelActionFromErrorText(s) {
    var t = String(s || "").toLowerCase();
    if (t.indexOf("görev tamamlama") !== -1 || t.indexOf("tamamlanacak görev") !== -1) return "complete";
    if (t.indexOf("görev silme") !== -1 || t.indexOf("silinecek görev") !== -1) return "delete";
    if (t.indexOf("geri alınacak") !== -1 || t.indexOf("silme iptal") !== -1) return "undo";
    if (t.indexOf("görev oluşturma") !== -1) return "create";
    return "";
  }

  /**
   * Görev Detay paneli flash — yalnızca gösterim (motor/chat ham metni aynı kalır).
   * Hata: [aksiyon] + (sebep); tek satır.
   */
  function formatTaskDetailPanelFlashText(raw, panelAction) {
    var s = String(raw || "")
      .replace(/\r\n/g, "\n")
      .trim();
    if (!s) return s;

    if (s.indexOf("Görev tamamlandı") === 0) {
      var m = s.match(/^Görev tamamlandı:\s*"([^"]*)"\s*\./);
      if (m) return "Tamamlandı: " + m[1] + ".";
      return "Tamamlandı.";
    }
    if (s.indexOf("Görev silindi") === 0) {
      var m2 = s.match(/^Görev silindi \(listeden kaldırıldı\):\s*"([^"]*)"\s*\./);
      if (m2) return "Silindi: " + m2[1] + ".";
      return "Silindi.";
    }
    if (s.indexOf("Siliniyor") === 0) return "Siliniyor…";
    if (s.indexOf("Silme iptal edildi") === 0) {
      var mu = s.match(/^Silme iptal edildi:\s*"([^"]*)"\s*\./);
      if (mu) return "Geri alındı: " + mu[1] + ".";
      return "Geri alındı.";
    }
    if (s.indexOf("Görev zaten tamamlanmış") === 0) return "Zaten tamamlanmış.";

    var act = panelAction || inferTaskPanelActionFromErrorText(s);
    if (!act) act = "complete";

    var sLow = s.toLowerCase();

    function policySebep() {
      if (sLow.indexOf("çevrimdışı") !== -1 || sLow.indexOf("offline") !== -1 || sLow.indexOf("önbellek") !== -1) {
        return "bağlantı";
      }
      if (sLow.indexOf("koruma") !== -1 || sLow.indexOf("korumalı") !== -1) return "koruma aktif";
      if (sLow.indexOf("onay") !== -1 || sLow.indexOf("consent") !== -1) return "onay gerekli";
      return "engelli";
    }

    function errComplete(sebep) {
      return "Görev tamamlanamadı (" + sebep + ")";
    }
    function errDelete(sebep) {
      return "Görev silinemedi (" + sebep + ")";
    }
    function errCreate(sebep) {
      return "Görev oluşturulamadı (" + sebep + ")";
    }
    function errUndo(sebep) {
      return "Geri alınamadı (" + sebep + ")";
    }
    function errPolicyBlock(sebep) {
      if (act === "complete") return "Tamamlama engellendi (" + sebep + ")";
      if (act === "delete") return errDelete(sebep);
      if (act === "undo") return errUndo(sebep);
      if (act === "create") return errCreate(sebep);
      return errComplete(sebep);
    }

    if (s.indexOf("Ne yapabilirsin:") !== -1 || s.indexOf("şu anda engellendi") !== -1) {
      return errPolicyBlock(policySebep());
    }

    if (s.indexOf(" engellendi.") !== -1) {
      return errPolicyBlock(policySebep());
    }

    if (s === "İşlem engellendi.") {
      return errPolicyBlock(policySebep());
    }

    if (
      (s.indexOf("API'ye ulaşılamıyor") !== -1 && s.indexOf("gönderilmedi") !== -1) ||
      (s.indexOf("Görev API") !== -1 && s.indexOf("ulaşılamıyor") !== -1)
    ) {
      if (act === "complete") return errComplete("bağlantı");
      if (act === "delete") return errDelete("bağlantı");
      if (act === "undo") return errUndo("bağlantı");
      return errCreate("bağlantı");
    }
    if (s.indexOf("Bağlantı modülü yüklenmedi") !== -1 || s.indexOf("Görev API bağlayıcısı yüklenmedi") !== -1) {
      if (act === "create") return errCreate("API kapalı");
      if (act === "complete") return errComplete("API kapalı");
      if (act === "undo") return errUndo("API kapalı");
      return errDelete("API kapalı");
    }
    if (s.indexOf("API adresi tanımlı değil") !== -1 || s.indexOf("LUMOS_PANEL_TASKS_API_BASE") !== -1) {
      if (act === "complete") return errComplete("yapılandırma eksik");
      if (act === "delete") return errDelete("yapılandırma eksik");
      if (act === "undo") return errUndo("yapılandırma eksik");
      return errCreate("yapılandırma eksik");
    }
    if (s.indexOf("Tamamlanacak görev bulunamadı") !== -1) {
      return errComplete("bulunamadı");
    }
    if (s.indexOf("Silinecek görev bulunamadı") !== -1) {
      return errDelete("bulunamadı");
    }
    if (s.indexOf("Geri alınacak silme bekleyen görev bulunamadı") !== -1) {
      return errUndo("bulunamadı");
    }
    if (s.indexOf("Görev komutu API üzerinde tanımsız") !== -1) {
      if (act === "complete") return errComplete("desteklenmiyor");
      if (act === "delete") return errDelete("desteklenmiyor");
      if (act === "undo") return errUndo("desteklenmiyor");
      return errCreate("desteklenmiyor");
    }

    if (
      s.indexOf("Bağlantı hatası") === 0 ||
      s.indexOf("Görev API veya ağ hatası") === 0 ||
      s === "İşlem tamamlanamadı." ||
      s.indexOf("İşlem tamamlanamadı") === 0
    ) {
      if (act === "complete") return errComplete("bağlantı");
      if (act === "delete") return errDelete("bağlantı");
      if (act === "undo") return errUndo("bağlantı");
      return errCreate("bağlantı");
    }

    if (/^http\s*\d/i.test(s) || sLow.indexOf("failed to fetch") !== -1 || sLow.indexOf("networkerror") !== -1) {
      if (act === "complete") return errComplete("bağlantı");
      if (act === "delete") return errDelete("bağlantı");
      if (act === "undo") return errUndo("bağlantı");
      return errCreate("bağlantı");
    }
    if (sLow.indexOf("abort") !== -1 && s.length < 80) {
      if (act === "complete") return errComplete("zaman aşımı");
      if (act === "delete") return errDelete("zaman aşımı");
      if (act === "undo") return errUndo("zaman aşımı");
      return errCreate("zaman aşımı");
    }

    if (s.length > 160) {
      if (act === "complete") return errComplete("bilinmeyen");
      if (act === "delete") return errDelete("bilinmeyen");
      if (act === "undo") return errUndo("bilinmeyen");
      return errCreate("bilinmeyen");
    }

    return s;
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
        var sel = taskIdEquals(data.selectedId, t.id) ? " selected" : "";
        var badge = buildBadge(t.status, getTaskStatusVariant(t.status));
        var tid = escapeHtmlYanit(t.id);
        var pdui = pendingDeleteUiFromRow(t);
        var isPendingRow = pdui.active;
        var pendingStrip = "";
        if (isPendingRow) {
          var undoGate = getTaskActionGate(data, "undo_pending");
          var btnDisList = taskDetailViewState.detailActionBusy || !undoGate.enabled ? " disabled" : "";
          var btnTitle = !undoGate.enabled && undoGate.reason ? (' title="' + escapeHtmlYanit(undoGate.reason) + '"') : "";
          pendingStrip =
            '<span class="task-list-pending-strip">' +
            '<span class="task-list-pending-msg">' +
            escapeHtmlYanit(TASK_PENDING_DELETE_UI_LABEL) +
            "</span>" +
            '<span class="task-list-pending-sec" aria-live="polite">' +
            String(pdui.secondsLeft) +
            " sn</span>" +
            '<button type="button" class="task-list-undo-btn" data-task-list-undo="1" data-task-ref="' +
            tid +
            '"' +
            btnDisList +
            btnTitle +
            ">Geri al</button>" +
            "</span>";
        }
        listItems +=
          '<li class="list-item' +
          sel +
          (isPendingRow ? " list-item--pending-delete" : "") +
          '" data-task-id="' +
          tid +
          '"><span class="task-list-row-main"><span class="task-list-badge">' +
          badge +
          '</span> <span class="task-list-title-text">' +
          escapeHtmlYanit(t.title) +
          "</span></span>" +
          pendingStrip +
          "</li>";
      });
      listBody += '<ul class="list-selectable" id="task-list">' + listItems + "</ul>";
    }
    var listSection = buildSection("Görev Listesi", listBody);

    var detailContent;
    if (!data.selectedTask) {
      detailContent = buildEmptyState("Görev seçin", "Soldaki listeden bir satıra tıklayın.");
    } else {
      var t = data.selectedTask;
      var st = String(t.status || "").toLowerCase();
      var createdDisp = t.createdAt ? formatTime(t.createdAt) : "—";
      var completedDisp = t.completedAt ? formatTime(t.completedAt) : "—";
      var updatedDisp = t.updated ? formatTime(t.updated) : "—";
      var refAttr = escapeHtmlYanit(t.id);
      var btnDis = taskDetailViewState.detailActionBusy ? " disabled" : "";
      var detailBtns = "";
      var pendingDeleteNote = "";
      if (st === "siliniyor") {
        var pduDetail = pendingDeleteUiFromRow(t);
        pendingDeleteNote =
          '<p class="text-muted-small task-pending-delete-hint" role="status">' +
          '<span class="task-pending-delete-hint__msg">' +
          escapeHtmlYanit(TASK_PENDING_DELETE_UI_LABEL) +
          "</span>" +
          ' <span class="task-pending-countdown" aria-live="polite">' +
          String(pduDetail.secondsLeft) +
          " sn kaldı</span>; tahmini kalıcı silinme <strong>" +
          escapeHtmlYanit(pduDetail.expireDisp) +
          "</strong>." +
          " İptal: listedeki veya buradaki <strong>Geri al</strong> (aynı komut)." +
          "</p>";
        detailBtns +=
          '<button type="button" class="task-detail-action-btn task-detail-action-btn--primary" data-task-detail-action="undo-pending" data-task-ref="' +
          refAttr +
          '"' +
          btnDis +
          ">Geri al</button>";
      } else {
        var canComplete = true;
        var canDelete = true;
        if (st === "aktif") {
          detailBtns +=
            '<button type="button" class="task-detail-action-btn task-detail-action-btn--primary" data-task-detail-action="complete" data-task-ref="' +
            refAttr +
            '"' +
            ((taskDetailViewState.detailActionBusy || !canComplete) ? " disabled" : "") +
            ">" +
            (canComplete ? "Tamamla" : "Tamamla (pasif)") +
            "</button>";
        }
        if (st === "aktif" || st === "tamamlandı" || st === "tamamlandi") {
          detailBtns +=
            '<button type="button" class="task-detail-action-btn task-detail-action-btn--secondary" data-task-detail-action="delete" data-task-ref="' +
            refAttr +
            '"' +
            ((taskDetailViewState.detailActionBusy || !canDelete) ? " disabled" : "") +
            ">Sil</button>";
        }
      }
      var detailActionsRow =
        detailBtns !== ""
          ? '<div class="task-detail-actions"' +
            (taskDetailViewState.detailActionBusy ? ' aria-busy="true"' : "") +
            ">" +
            detailBtns +
            "</div>"
          : "";
      var busyRow = "";
      if (taskDetailViewState.detailActionBusy) {
        busyRow =
          '<p class="task-detail-progress" aria-live="polite">' +
          '<span class="task-detail-progress-dot" aria-hidden="true"></span>' +
          "Uygulanıyor…" +
          "</p>";
      }
      var flashRow = "";
      if (taskDetailViewState.flash && taskDetailViewState.flash.text) {
        var fr = taskDetailViewState.flash;
        var fk =
          fr.kind === "error" ? "error" : fr.kind === "ok" ? "ok" : "info";
        var live = fr.kind === "error" ? "alert" : "status";
        flashRow =
          '<p class="task-detail-flash task-detail-flash--' +
          fk +
          '" role="' +
          live +
          '">' +
          escapeHtmlYanit(formatTaskDetailPanelFlashText(fr.text, fr.panelAction)) +
          "</p>";
      }
      var actionsHint = "";
      if (st === "siliniyor") {
        actionsHint = "";
      } else if (st === "aktif") {
        actionsHint = "Tamamla veya sil.";
      } else if (st === "tamamlandı" || st === "tamamlandi") {
        actionsHint = "Kalıcı olarak kaldırmak için sil.";
      } else {
        actionsHint = "";
      }
      var primaryBlock =
        detailBtns !== ""
          ? '<div class="task-detail-primary">' +
            '<p class="task-detail-actions-label">İşlemler</p>' +
            (pendingDeleteNote || "") +
            detailActionsRow +
            (actionsHint
              ? '<p class="text-muted-small task-detail-actions-hint">' + actionsHint + "</p>"
              : "") +
            "</div>"
          : "";
      var noActionsNote =
        detailBtns === ""
          ? '<p class="text-muted-small task-detail-no-actions">Bu görev için kullanılabilir işlem yok.</p>'
          : "";
      var metaRows;
      if (st === "siliniyor") {
        var pduMeta = pendingDeleteUiFromRow(t);
        metaRows = [
          {
            label: "Kimlik",
            value: '<small class="task-detail-id-wrap"><code>' + escapeHtmlYanit(t.id) + "</code></small>",
          },
          { label: "Oluşturulma", value: createdDisp },
          {
            label: "Kalan süre",
            value: String(pduMeta.secondsLeft) + " sn",
          },
          { label: "Kalıcı silinme (hedef)", value: pduMeta.expireDisp },
          {
            label: "Tamamlanma",
            value: completedDisp !== "—" ? completedDisp : "—",
          },
        ];
      } else {
        metaRows = [
          {
            label: "Kimlik",
            value: '<small class="task-detail-id-wrap"><code>' + escapeHtmlYanit(t.id) + "</code></small>",
          },
          { label: "Oluşturulma", value: createdDisp },
          { label: "Güncelleme", value: updatedDisp },
          { label: "Tamamlanma", value: st.indexOf("tamam") !== -1 ? completedDisp : "—" },
        ];
      }
      detailContent =
        busyRow +
        flashRow +
        "<p><strong>" + escapeHtmlYanit(t.title) + "</strong></p>" +
        "<p>Durum: " +
        buildBadge(t.status, getTaskStatusVariant(t.status)) +
        "</p>" +
        (t.summary ? ('<p class="text-muted-small">' + escapeHtmlYanit(t.summary) + "</p>") : "") +
        (t.result ? ('<p class="text-muted-small"><strong>Sonuç:</strong> ' + escapeHtmlYanit(t.result) + "</p>") : "") +
        primaryBlock +
        noActionsNote +
        '<p class="task-detail-meta-heading">Ayrıntılar</p>' +
        buildDetailRows(metaRows);
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
    taskTrashBusy: false,
  };

  /**
   * Geri yükle / kalıcı sil tek kaynak (panel_tasks_server).
   * Varsayılan: http://127.0.0.1:8766 — window.LUMOS_PANEL_TRASH_ACTION_API_BASE ile değiştirilebilir.
   */
  const API_BASE =
    typeof window !== "undefined" &&
    window.LUMOS_PANEL_TRASH_ACTION_API_BASE != null &&
    String(window.LUMOS_PANEL_TRASH_ACTION_API_BASE).trim() !== ""
      ? String(window.LUMOS_PANEL_TRASH_ACTION_API_BASE).replace(/\/$/, "")
      : "http://127.0.0.1:8766";

  /** lumos-read-state ile aynı HTTP kökü; aksi halde open-folder yanlış porta gider ve tarayıcı "Failed to fetch" verir. */
  function getLumosPanelOpenFolderUrl() {
    var live = resolveLumosLiveStateUrl();
    if (!live || typeof live !== "string") return "";
    var u = live.trim();
    var marker = "/lumos-read-state";
    var idx = u.indexOf(marker);
    var base = idx >= 0 ? u.slice(0, idx) : u;
    base = String(base).replace(/\/$/, "");
    if (!base) return "";
    return base + "/open-folder";
  }

  /** Disk çöpündeki görev: POST …/tasks/restore | POST …/tasks/delete-permanent. */
  function handleTrashTaskServerAction(action, taskId) {
    if (trashViewState.taskTrashBusy) return;
    var tid = resolveTrashActionTaskIdForRequest(taskId);
    if (!tid) return;
    if (typeof console !== "undefined" && console.log) {
      console.log("[LUMOS] trash POST body id:", tid);
    }
    var base = String(API_BASE).replace(/\/$/, "");
    var url =
      action === "restore" ? base + "/tasks/restore" : base + "/tasks/delete-permanent";
    var reqBody = { id: tid };
    trashViewState.taskTrashBusy = true;
    trashViewState.flash = { kind: "ok", source: "trash-task", text: "İşleniyor…" };
    refreshCurrentView();
    panelTasksTrashDirectPost(url, reqBody)
      .then(function (r) {
        return r.text().then(function (txt) {
          var j = null;
          try {
            j = txt && String(txt).trim() !== "" ? JSON.parse(txt) : null;
          } catch (_) {
            j = null;
          }
          return { ok: r.ok, status: r.status, j: j, rawPreview: txt != null ? String(txt).slice(0, 200) : "" };
        });
      })
      .then(function (x) {
        trashViewState.taskTrashBusy = false;
        var j = x.j && typeof x.j === "object" ? x.j : {};
        var code = j.error != null ? String(j.error) : "";
        var map = {
          missing_trash_file: "missing_trash_file: Çöp dosyası bulunamadı.",
          task_already_exists: "task_already_exists: Görev zaten listede.",
          empty_id: "empty_id: Geçersiz kimlik.",
          invalid_trash_file: "invalid_trash_file: Çöp dosyası okunamadı.",
          invalid_payload: "invalid_payload: Çöp kaydı geçersiz.",
          invalid_json: "invalid_json: İstek gövdesi geçersiz.",
        };
        if (!x.ok || !j.ok) {
          var errText;
          if (code === "not_found") {
            errText =
              action === "restore"
                ? "restore route yok — beklenen: POST " + API_BASE + "/tasks/restore"
                : "delete-permanent route yok — beklenen: POST " + API_BASE + "/tasks/delete-permanent";
          } else if (code && map[code]) {
            errText = map[code];
          } else if (code) {
            errText = code;
          } else if (x.status === 404) {
            errText =
              action === "restore"
                ? "restore route yok veya 404 — beklenen: POST " + API_BASE + "/tasks/restore"
                : "delete-permanent route yok veya 404 — beklenen: POST " + API_BASE + "/tasks/delete-permanent";
          } else if (x.status === 405) {
            errText = "HTTP 405: Yöntem bu yol için izinli değil (" + url + ").";
          } else if (x.status) {
            errText =
              "HTTP " +
              x.status +
              (x.rawPreview && x.rawPreview.indexOf("{") === -1 ? ": " + x.rawPreview : "") +
              (j && j.error ? " — " + String(j.error) : "");
          } else {
            errText = "İşlem başarısız (yanıt okunamadı).";
          }
          trashViewState.flash = {
            kind: "error",
            source: "trash-task",
            text: errText,
          };
        } else {
          trashViewState.flash = {
            kind: "ok",
            source: "trash-task",
            text: action === "restore" ? "Görev geri yüklendi." : "Çöpten kalıcı silindi.",
          };
          mockState.selectedTrashId = null;
        }
        return syncTasksDocumentFromApi().catch(function () {
          return null;
        });
      })
      .then(function () {
        refreshCurrentView();
        pollLumosReadState();
        return null;
      })
      .catch(function (err) {
        trashViewState.taskTrashBusy = false;
        var raw = (err && err.message) || String(err);
        if (typeof console !== "undefined" && console.warn) {
          console.warn("[LUMOS] trash-task fetch ağ hatası", { url: url, method: "POST", body: reqBody, error: raw });
        }
        var netFail =
          raw === "Failed to fetch" ||
          raw === "Load failed" ||
          raw === "NetworkError when attempting to fetch resource." ||
          (err && err.name === "AbortError");
        trashViewState.flash = {
          kind: "error",
          source: "trash-task",
          text: netFail ? "Sunucuya ulaşılamadı. (" + API_BASE + " ayakta mı?)" : raw,
        };
        refreshCurrentView();
        pollLumosReadState();
      });
  }

  function lumosOpenWorkspaceFolder(absPath) {
    var pathStr = absPath != null ? String(absPath).trim() : "";
    if (!pathStr || pathStr === "—") return;
    var url = getLumosPanelOpenFolderUrl();
    if (!url) {
      trashViewState.flash = {
        kind: "error",
        source: "open-folder",
        text: "Klasörü açmak için panel görev sunucusunu çalıştırın (örn. python3 panel/scripts/panel_tasks_server.py).",
      };
      if (getCurrentScreen().id === "trash") renderMain();
      return;
    }
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: pathStr }),
    })
      .then(function (r) {
        if (typeof console !== "undefined" && console.log) {
          console.log("[LUMOS] panel_tasks POST url:", url, "response status:", r.status);
        }
        return r.text().then(function (txt) {
          var j = null;
          try {
            j = txt && String(txt).trim() !== "" ? JSON.parse(txt) : null;
          } catch (_) {
            j = null;
          }
          return { ok: r.ok, status: r.status, j: j, raw: txt };
        });
      })
      .then(function (x) {
        var j = x.j && typeof x.j === "object" ? x.j : {};
        if (!x.ok || !j.ok) {
          var code = j.error != null ? String(j.error) : "";
          var map = {
            path_not_allowed: "Bu yol güvenlik nedeniyle açılamıyor.",
            not_a_directory: "Klasör bulunamadı.",
            empty_path: "Geçerli bir yol yok.",
            bad_path: "Geçersiz yol.",
            not_found: "open-folder uç noktası bulunamadı; panel sunucusunu güncelleyin.",
            http_404: "open-folder bulunamadı (404).",
          };
          var baseMsg = map[code] || (code ? code : "Klasör açılamadı.");
          if (!map[code] && x.status) baseMsg += " (HTTP " + x.status + ")";
          trashViewState.flash = {
            kind: "error",
            source: "open-folder",
            text: baseMsg,
          };
        } else {
          trashViewState.flash = { kind: "ok", source: "open-folder", text: "Çöp klasörü açıldı." };
        }
        if (getCurrentScreen().id === "trash") renderMain();
      })
      .catch(function (err) {
        var raw = (err && err.message) || String(err);
        if (typeof console !== "undefined" && console.warn) {
          console.warn("[LUMOS] open-folder fetch hatası (ağ/CORS/sunucu yok)", url, raw);
        }
        var friendly =
          raw === "Failed to fetch"
            ? "Çöp klasörü için sunucuya ulaşılamadı. lumos-read-state ile aynı adresin ayakta ve panel_tasks_server sürümünde /open-folder olduğundan emin olun."
            : "Sunucuya bağlanılamadı: " + raw;
        trashViewState.flash = { kind: "error", source: "open-folder", text: friendly };
        if (getCurrentScreen().id === "trash") renderMain();
      });
  }

  /** Görevler detay paneli: API beklerken buton kilidi; aksiyon sonrası görsel geri bildirim */
  var taskDetailViewState = {
    flash: null,
    detailActionBusy: false,
  };
  var taskDetailFlashTimer = null;
  var taskDetailFlashTicket = 0;
  /** Son detay komutu: complete | delete | create — flash [aksiyon](sebep) için */
  var taskDetailPanelLastCmdAction = "";

  function clearTaskDetailFlashTimer() {
    if (taskDetailFlashTimer) {
      clearTimeout(taskDetailFlashTimer);
      taskDetailFlashTimer = null;
    }
  }

  /** Başarı flash’ını bir süre sonra kaldır (detay sadeleşsin). */
  function scheduleTaskDetailOkFlashAutoClear() {
    clearTaskDetailFlashTimer();
    var ticket = ++taskDetailFlashTicket;
    taskDetailFlashTimer = setTimeout(function () {
      taskDetailFlashTimer = null;
      if (taskDetailFlashTicket !== ticket) return;
      if (taskDetailViewState.flash && taskDetailViewState.flash.kind === "ok") {
        taskDetailViewState.flash = null;
        if (getCurrentScreen().id === "tasks") refreshCurrentView();
      }
    }, 3200);
  }

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
    var emptiedTrashCount = (trashViewState.trashPosts || []).length;
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
        if (emptiedTrashCount > 0) {
          appendPanelEngineEvent({
            type: "post_permanently_deleted",
            taskId: "",
            text:
              emptiedTrashCount === 1
                ? "Çöpteki gönderi kalıcı silindi"
                : "Çöpteki " + emptiedTrashCount + " gönderi kalıcı silindi",
            ts: new Date().toISOString(),
          });
          persistTasksJsonDocument();
        }
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

  // ——— Ekran: Silinenler (köprü: window.__LUMOS_READ_STATE__.trash.trash_items → getTrashData) ———
  function renderTrash() {
    var data = getTrashData();
    var items = data.listItems || [];
    if (items.length > 0) {
      var sel = mockState.selectedTrashId != null ? String(mockState.selectedTrashId) : "";
      var found = false;
      var si;
      for (si = 0; si < items.length; si++) {
        var it0 = items[si];
        var k0 = trashListRowKey(it0);
        if (taskIdEquals(it0 && it0.id, sel) || taskIdEquals(k0, sel)) {
          found = true;
          break;
        }
      }
      if (!sel || !found) {
        mockState.selectedTrashId = items[0] ? trashListRowKey(items[0]) || items[0].id : null;
        data = getTrashData();
        items = data.listItems || [];
      }
    } else {
      mockState.selectedTrashId = null;
    }
    var recentPermanentHtml = buildRecentPermanentDeletesSectionHtml();
    var flashLine = "";
    if (trashViewState.flash && trashViewState.flash.text) {
      if (window.LumosFeedApi && trashViewState.flash.source !== "trash-task") {
        flashLine = trashFlashHtml(window.LumosFeedApi, { isLoading: false, postsLength: items.length });
      } else {
        var fk = trashViewState.flash.kind === "error" ? "error" : "ok";
        flashLine =
          '<p class="feed-action-flash feed-action-flash--' +
          fk +
          '" role="' +
          (fk === "error" ? "alert" : "status") +
          '">' +
          escapeHtmlYanit(trashViewState.flash.text) +
          "</p>";
      }
    }
    var metricsHtml = "";
    if (data.summaryMetrics && data.summaryMetrics.length) {
      var mcHtml = "";
      for (var mi = 0; mi < data.summaryMetrics.length; mi++) {
        var sm = data.summaryMetrics[mi];
        if (mi === 0 && sm && sm.title === "Çöp konumu") {
          mcHtml += TrashLocationOpenMetricCard(
            sm.title,
            sm.value,
            resolveTrashOpenPathForAction(data, sm.value)
          );
        } else {
          mcHtml += buildMetric({ title: sm.title, value: sm.value, note: sm.note || null });
        }
      }
      metricsHtml = '<div class="cards-grid">' + mcHtml + "</div>";
    }
    if (typeof console !== "undefined" && console.log) {
      console.log("renderTrash listItems", items);
    }
    var listPaneHtml;
    if (items.length === 0) {
      listPaneHtml = buildEmptyState(data.emptyListTitle || "Çöp listesi boş", data.emptyListDesc || "");
    } else {
      var listHtml = "";
      for (var li = 0; li < items.length; li++) {
        var it = items[li] || {};
        var iid = trashListRowKey(it) || (it.id != null ? String(it.id) : "");
        var sel =
          mockState.selectedTrashId != null ? (taskIdEquals(mockState.selectedTrashId, iid) ? " selected" : "") : "";
        var nm = it.name != null ? String(it.name) : "—";
        var mv = trashItemRowTimestampFormatted(it);
        listHtml +=
          '<li class="list-item' +
          sel +
          '" data-trash-id="' +
          escapeHtmlYanit(iid) +
          '"><span class="task-list-row-main"><span class="task-list-title-text">' +
          escapeHtmlYanit(nm) +
          '</span></span><span class="text-muted-small">' +
          escapeHtmlYanit(mv) +
          "</span></li>";
      }
      listPaneHtml = '<ul class="list-selectable" id="trash-list">' + listHtml + "</ul>";
    }
    var selectedItem = data.selectedItem;
    var detailBody;
    if (selectedItem && items.length) {
      var st = selectedItem.status != null ? String(selectedItem.status) : "—";
      var delAt = selectedItem.deletedAt != null && String(selectedItem.deletedAt) !== "—" ? String(selectedItem.deletedAt) : "";
      if (!delAt && selectedItem.movedAt) delAt = String(selectedItem.movedAt);
      if (!delAt) delAt = "—";
      detailBody = buildDetailRows([
        { label: "Ad", value: selectedItem.name != null ? String(selectedItem.name) : "—" },
        { label: "Durum", value: st },
        { label: "Silinme", value: delAt },
        { label: "Orijinal yol", value: selectedItem.originalPath != null ? String(selectedItem.originalPath) : "—" },
        { label: "Çöp yolu", value: selectedItem.trashPath != null ? String(selectedItem.trashPath) : "—" },
        { label: "Kapsam", value: selectedItem.scope != null ? String(selectedItem.scope) : "—" },
      ]);
      if (selectedItem.rawRecord && typeof selectedItem.rawRecord === "object") {
        detailBody +=
          '<pre class="trash-json-pre">' +
          escapeHtmlYanit(JSON.stringify(selectedItem.rawRecord, null, 2)) +
          "</pre>";
      }
    } else {
      detailBody = "<p class=\"screen-placeholder\">" + (data.emptyDetailPlaceholder || "Listeden bir öğe seçin.") + "</p>";
    }
    var detail = buildDetailPanel(data.detailTitle || "Detay", detailBody);
    var hasSel = !!(data.selectedItem && items.length);
    var tbBusy = trashViewState.taskTrashBusy === true;
    var btnDis = !hasSel || tbBusy ? " disabled" : "";
    var selForBtn = hasSel && data.selectedItem ? trashListRowKey(data.selectedItem) : "";
    var trashToolbar =
      '<div class="trash-task-toolbar" role="toolbar" aria-label="Çöp görev işlemleri">' +
      '<button type="button" class="task-detail-action-btn task-detail-action-btn--primary"' +
      (hasSel && !tbBusy ? ' data-trash-task-id="' + escapeHtmlYanit(selForBtn) + '"' : "") +
      ' data-trash-task-action="restore"' +
      btnDis +
      ">Geri yükle</button>" +
      '<button type="button" class="task-detail-action-btn task-detail-action-btn--secondary"' +
      (hasSel && !tbBusy ? ' data-trash-task-id="' + escapeHtmlYanit(selForBtn) + '"' : "") +
      ' data-trash-task-action="delete-permanent"' +
      btnDis +
      ">Kalıcı sil</button>" +
      '<span class="text-muted-small trash-task-toolbar-hint">İstek: ' +
      escapeHtmlYanit(API_BASE) +
      "/tasks/…</span>" +
      "</div>";
    var inboxBody =
      '<div class="split-view trash-inbox-split">' +
      '<div class="trash-inbox-list-col">' +
      trashToolbar +
      listPaneHtml +
      "</div>" +
      detail +
      "</div>";
    return (
      '<div class="trash-deletion-hub">' +
      ViewHeader(data.title || "Silinenler", data.subtitle || "") +
      flashLine +
      metricsHtml +
      buildSection("Silinen kayıtlar", inboxBody) +
      recentPermanentHtml +
      "</div>"
    );
  }

  // ——— Ekran: Kayıtlar (adapter + build) ———
  function renderLogs() {
    var data = getLogsData();
    var metaLine = "";
    if (data.logUpdatedText || data.logFileUpdated) {
      metaLine +=
        '<p class="text-muted-small">' +
        (data.logUpdatedText || "Son güncelleme: " + formatTime(data.logFileUpdated)) +
        "</p>";
    }
    var tabsHtml = data.filters.map(function (f) {
      var active = f.id === data.activeFilter ? " active" : "";
      return '<button type="button" class="log-tab' + active + '" data-log-filter="' + f.id + '">' + f.label + "</button>";
    }).join("");
    return (
      ViewHeader(data.title, data.subtitle) +
      (metaLine ? metaLine : "") +
      '<div class="log-tabs" id="log-tabs">' +
      tabsHtml +
      "</div>" +
      buildSection("Kayıtlar", KayitlarTimelineView(data.kayitRecords || [], mockState.selectedKayitlarTimelineKey))
    );
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

  /** Sohbet: bellek + tek kalıcı kaynak CHAT_PANEL_STORAGE_KEY (localStorage). Hash değişince sıfırlanmaz. */
  var chatViewState = {
    messages: [],
    /** Composer: polling/rerender innerHTML öncesi korunur (textarea yok edilmeden snapshot). */
    draft: "",
    /** Yeniden çizimden sonra log’u alta kaydır (kullanıcı yukarıda değilse). */
    stickToBottom: true,
    /** Bir sonraki render’da alta zorla (kullanıcı mesajı / kilit yanıtı). */
    userForcedScrollToBottom: false,
    /** renderChatMainInto sonunda textarea’ya focus (preventScroll ile). */
    focusComposerAfterRender: false,
    /** Unlock isteği devam ederken tekrar gönderimi engelle. */
    kilitAcUnlockInFlight: false,
  };

  var KILIT_AC_MSG_UNLOCK_OK = "Kilit açıldı";
  var KILIT_AC_MSG_UNLOCK_ERR = "Kilit açılamadı";

  function normalizeUnlockResult(out) {
    return out != null && typeof out === "object" && out.ok === true ? { ok: true } : { ok: false };
  }

  function applyUnlockChatAssistantMessage(result) {
    var r = result != null && typeof result === "object" ? result : { ok: false };
    if (r.ok === true) {
      chatViewState.messages.push({
        role: "assistant",
        text: KILIT_AC_MSG_UNLOCK_OK,
        depth: "simple",
      });
    } else {
      chatViewState.messages.push({
        role: "assistant",
        text: KILIT_AC_MSG_UNLOCK_ERR,
        depth: "simple",
      });
    }
    persistChatMessagesToStorage();
    refreshCurrentView();
  }

  function closeUnlockModal() {
    var root = document.getElementById("lumos-unlock-modal-root");
    if (root && root._lumosUnlockEsc) {
      document.removeEventListener("keydown", root._lumosUnlockEsc);
      root._lumosUnlockEsc = null;
    }
    if (root && root.parentNode) {
      root.parentNode.removeChild(root);
    }
  }

  function openUnlockModal() {
    if (chatViewState.kilitAcUnlockInFlight) {
      return;
    }
    closeUnlockModal();
    var root = document.createElement("div");
    root.id = "lumos-unlock-modal-root";
    root.className = "lumos-unlock-modal-root";
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-modal", "true");
    root.setAttribute("aria-labelledby", "lumos-unlock-title");
    root.innerHTML =
      '<div class="lumos-unlock-modal-backdrop" data-unlock-dismiss="1">' +
      '<div class="lumos-unlock-modal-panel" data-unlock-panel="1">' +
      '<h2 class="lumos-unlock-modal-title" id="lumos-unlock-title">Kilit aç</h2>' +
      '<label class="lumos-unlock-modal-label" for="unlock-pass">Şifre</label>' +
      '<input type="password" id="unlock-pass" class="lumos-unlock-modal-input" autocomplete="off" autocapitalize="off" spellcheck="false" />' +
      '<div class="lumos-unlock-modal-actions">' +
      '<button type="button" class="lumos-unlock-modal-btn lumos-unlock-modal-btn--primary" id="lumos-unlock-submit">Onayla</button>' +
      '<button type="button" class="lumos-unlock-modal-btn" id="lumos-unlock-cancel">İptal</button>' +
      "</div></div></div>";
    document.body.appendChild(root);

    root._lumosUnlockEsc = function (e) {
      if (e.key === "Escape") {
        closeUnlockModal();
      }
    };
    document.addEventListener("keydown", root._lumosUnlockEsc);

    function onBackdrop(e) {
      if (e.target && e.target.getAttribute && e.target.getAttribute("data-unlock-dismiss") === "1") {
        closeUnlockModal();
      }
    }
    root.addEventListener("click", onBackdrop);

    var panel = root.querySelector("[data-unlock-panel]");
    if (panel) {
      panel.addEventListener("click", function (ev) {
        ev.stopPropagation();
      });
    }

    document.getElementById("lumos-unlock-cancel").addEventListener("click", function () {
      closeUnlockModal();
    });

    document.getElementById("lumos-unlock-submit").addEventListener("click", function () {
      var inp = document.getElementById("unlock-pass");
      var v = inp && inp.value != null ? String(inp.value).trim() : "";
      runKilitAcUnlockFromUI(v);
    });

    var passEl = document.getElementById("unlock-pass");
    if (passEl) {
      passEl.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
          e.preventDefault();
          var v = passEl.value != null ? String(passEl.value).trim() : "";
          runKilitAcUnlockFromUI(v);
        }
      });
      try {
        passEl.focus({ preventScroll: true });
      } catch (_) {
        passEl.focus();
      }
    }
  }

  function runKilitAcUnlockFromUI(pass) {
    var p = pass != null ? String(pass).trim() : "";
    if (!p) {
      return;
    }
    closeUnlockModal();
    chatViewState.kilitAcUnlockInFlight = true;
    runKilitAcUnlockFromChat(p)
      .then(applyUnlockChatAssistantMessage)
      .catch(function () {
        applyUnlockChatAssistantMessage({ ok: false });
      })
      .finally(function () {
        chatViewState.kilitAcUnlockInFlight = false;
        chatViewState.focusComposerAfterRender = true;
        refreshCurrentView();
      });
  }

  /** Chat geçmişi — görev tasks.json hattından ayrı; tek anahtar, dağınık yazım yok. */
  var CHAT_PANEL_STORAGE_KEY = "lumos_panel_chat_messages_v1";
  /* Geçmişi sıfırlamak (test): localStorage.removeItem("lumos_panel_chat_messages_v1") veya DevTools → Application → Local Storage. */

  function normalizeChatMessageForStorage(m) {
    if (!m || typeof m !== "object") return null;
    var role = m.role === "user" || m.role === "assistant" ? m.role : null;
    if (!role) return null;
    var text = m.text != null ? String(m.text).trim() : "";
    var depth = m.depth != null && String(m.depth).trim() !== "" ? String(m.depth) : null;
    var blocks = m.blocks != null && typeof m.blocks === "object" ? m.blocks : null;
    if (role === "user") {
      if (!text) return null;
      return { role: "user", text: text };
    }
    var hasBlocks = blocks && Object.keys(blocks).length > 0;
    if (!text && !hasBlocks) return null;
    var o = { role: "assistant", text: text };
    if (depth) o.depth = depth;
    if (hasBlocks) o.blocks = blocks;
    return o;
  }

  function persistChatMessagesToStorage() {
    try {
      if (typeof localStorage === "undefined") return;
      var arr = chatViewState.messages || [];
      var out = [];
      for (var ci = 0; ci < arr.length; ci++) {
        var n = normalizeChatMessageForStorage(arr[ci]);
        if (n) out.push(n);
      }
      localStorage.setItem(CHAT_PANEL_STORAGE_KEY, JSON.stringify({ v: 1, messages: out }));
    } catch (_) {
      /* quota / private mode */
    }
  }

  function hydrateChatMessagesFromStorage() {
    try {
      if (typeof localStorage === "undefined") return;
      var raw = localStorage.getItem(CHAT_PANEL_STORAGE_KEY);
      if (!raw) return;
      var doc = JSON.parse(raw);
      if (!doc || doc.v !== 1 || !Array.isArray(doc.messages)) return;
      var list = [];
      for (var hi = 0; hi < doc.messages.length; hi++) {
        var n = normalizeChatMessageForStorage(doc.messages[hi]);
        if (n) list.push(n);
      }
      chatViewState.messages = list;
    } catch (_) {
      /* corrupt / yok */
    }
  }

  hydrateChatMessagesFromStorage();

  /** Chat intent eşlemesi: tr-TR küçük harf + boşluk normalize. */
  function normalizeChatIntentKey(s) {
    return normalizeTaskCommandWhitespace(s).toLocaleLowerCase("tr-TR");
  }

  function normalizeKilitAcCommandKey(s) {
    return normalizeChatIntentKey(String(s || ""))
      .replace(/[.?!…]+$/g, "")
      .trim();
  }

  /** «kilit aç» ve birleşik yazımlar — unlock; yalnızca «kilit» burada değil (normal sohbet). */
  function isKilitAcChatCommand(key) {
    var k = String(key || "").trim();
    if (!k) return false;
    if (/^(kilit\s+aç|kilit\s+ac|kilidi\s+aç|kilidi\s+ac)$/.test(k)) return true;
    if (/^(kilitaç|kilitac|kilidiac)$/.test(k)) return true;
    return false;
  }

  function onChatLogScroll() {
    var log = this;
    var threshold = 72;
    var dist = log.scrollHeight - log.scrollTop - log.clientHeight;
    chatViewState.stickToBottom = dist <= threshold;
  }

  function navigateChatToHashIfDifferent(hash) {
    try {
      var want = String(hash || "").trim();
      if (!want) return;
      var cur = ((window.location && window.location.hash) || "").split("?")[0].toLowerCase();
      if (cur !== want.toLowerCase()) {
        window.location.hash = want;
      }
    } catch (_) {
      /* ignore */
    }
  }

  function buildLiveSystemStatusChatLine() {
    var s = getEffectiveState();
    var g = s.guidance || {};
    var mode = g.mode != null ? String(g.mode) : "—";
    var lock = g.lock != null ? String(g.lock) : "—";
    var rs = typeof window !== "undefined" ? window.__LUMOS_READ_STATE__ : null;
    var fresh = rs && rs.panel_meta && rs.panel_meta.live_state_fresh === true;
    return (
      "Canlı durum özeti — mod: " +
      mode +
      ", kilit: " +
      lock +
      (fresh ? " (köprü güncel)." : " (köprü yüklemesiyle güncellenir).")
    );
  }

  /**
   * Tek ekran / kısayol komutları (görev motorundan önce).
   * @returns {{ text: string, depth?: string } | null}
   */
  function tryChatPanelNavigationIntent(trimmed) {
    var k = normalizeChatIntentKey(trimmed)
      .replace(/[.?!…]+$/g, "")
      .trim();
    if (!k) return null;
    if (/^(görevler|gorevler)$/.test(k)) {
      navigateChatToHashIfDifferent(SCREENS.tasks.hash);
      return {
        text: "Görevler ekranına geçtim; listeden görevleri görebilir veya detaydan işlem yapabilirsin.",
        depth: "simple",
      };
    }
    if (/^(durum|sistem|sistem durumu|system)$/.test(k)) {
      navigateChatToHashIfDifferent(SCREENS.system.hash);
      return { text: buildLiveSystemStatusChatLine(), depth: "simple" };
    }
    if (/^(anahtar\s+kasası|anahtar\s+kasasi|keystore)$/.test(k)) {
      navigateChatToHashIfDifferent(SCREENS.keystore.hash);
      return {
        text: "Anahtar Kasası ekranına geçtim; kilit ve hassas yazım kapsamını buradan yönetebilirsin.",
        depth: "simple",
      };
    }
    return null;
  }

  /**
   * Tek giriş noktası: görev oluştur | tamamla | sil (normalize edilmiş satır üzerinde).
   * @returns {{ verb: 'olustur', taskName: string } | { verb: 'tamamla'|'sil', ref: string } | null}
   */
  function parseGorevMotorCommand(raw) {
    var t = normalizeTaskCommandWhitespace(raw);
    if (!t) return null;
    var m = /^(?:görev|gorev)\s+(?:oluştur|olustur)(?=\s|:|$)/i.exec(t);
    if (m) {
      var taskName = normalizeTaskCommandWhitespace(
        t.slice(m[0].length).replace(/^\s*:?\s*/, "")
      );
      return { verb: "olustur", taskName: taskName };
    }
    m = /^(?:görev|gorev)\s+tamamla\b/i.exec(t);
    if (m) {
      var refDone = normalizeTaskCommandWhitespace(t.slice(m[0].length).replace(/^\s*:+\s*/, ""));
      return { verb: "tamamla", ref: refDone };
    }
    m = /^(?:görev|gorev)\s+sil(?=\s|:|$)/i.exec(t);
    if (m) {
      var refSil = normalizeTaskCommandWhitespace(t.slice(m[0].length).replace(/^\s*:+\s*/, ""));
      return { verb: "sil", ref: refSil };
    }
    m = /^(?:görev|gorev)\s+geri\s+al\b/i.exec(t);
    if (m) {
      var refUndo = normalizeTaskCommandWhitespace(t.slice(m[0].length).replace(/^\s*:+\s*/, ""));
      return { verb: "geri_al", ref: refUndo };
    }
    return null;
  }

  function mapParsedVerbToPolicyAction(verb) {
    if (verb === "olustur") return "create_task";
    if (verb === "tamamla") return "complete_task";
    if (verb === "sil") return "delete_task";
    if (verb === "geri_al") return "undo_pending_delete";
    return null;
  }

  function buildPanelPolicyContextPayload() {
    var s = getEffectiveState();
    var g = s.guidance || {};
    var modeStr = g.mode != null ? String(g.mode).toLowerCase() : "";
    var online = modeStr === SOURCE_STATUS.ONLINE || String(s.appMode || "").toLowerCase() === SOURCE_STATUS.ONLINE;
    if (!online && getPanelTasksPersistenceConfig().chatCommands === "api") {
      var apiB = getPanelTasksApiBaseResolved();
      if (apiB && String(apiB).trim() !== "") {
        online = true;
      }
    }
    var lockVal = g.lock != null ? String(g.lock) : "";
    var koruma = lockVal === "LOCKED";
    if (!koruma && s.keystoreState != null) {
      var ks = String(s.keystoreState).toLowerCase();
      if (ks.indexOf("kilit") !== -1) koruma = true;
    }
    return { online: online, korumaAktif: koruma, consent: !!g.consent };
  }

  function runPanelTaskPolicyOrNull(parsed) {
    var action = mapParsedVerbToPolicyAction(parsed.verb);
    if (!action) return null;
    var Engine = typeof LumosPolicyEngine !== "undefined" ? LumosPolicyEngine : null;
    if (!Engine || typeof Engine.checkPolicy !== "function") return null;
    var pr = Engine.checkPolicy(action, buildPanelPolicyContextPayload());
    if (pr.allow) return null;
    var tsIso = new Date().toISOString();
    var logSummary =
      Engine.formatPolicyBlockedShort && typeof Engine.formatPolicyBlockedShort === "function"
        ? Engine.formatPolicyBlockedShort(action, pr.reason)
        : Engine.buildPolicyBlockedMessage && typeof Engine.buildPolicyBlockedMessage === "function"
          ? Engine.buildPolicyBlockedMessage(action, pr.reason).split("\n")[0]
          : "İşlem engellendi.";
    var chatText =
      Engine.buildPolicyBlockedMessage && typeof Engine.buildPolicyBlockedMessage === "function"
        ? Engine.buildPolicyBlockedMessage(action, pr.reason)
        : Engine.formatPolicyBlockedChatDisplay && typeof Engine.formatPolicyBlockedChatDisplay === "function"
          ? Engine.formatPolicyBlockedChatDisplay(action, pr.reason)
          : logSummary;
    appendPanelEngineEvent({
      type: "policy_blocked",
      text:
        logSummary +
        " | ts=" +
        tsIso +
        " | actionCode=" +
        (Engine.toLogActionCode && typeof Engine.toLogActionCode === "function"
          ? Engine.toLogActionCode(action)
          : String(action || "")) +
        " | reasonCode=" +
        String(pr.reason || ""),
      ts: tsIso,
    });
    return { text: chatText, depth: "simple" };
  }

  /**
   * Görev motoru komutları: state + olay kuyruğu.
   * @returns {Promise<{ text: string, depth?: string, blocks?: object }>|{ text: string, depth?: string, blocks?: object } | null}
   */
  function tryHandleTaskEngineChatCommand(userText) {
    var parsed = parseGorevMotorCommand(userText);
    if (!parsed) return null;
    if (getPanelTasksPersistenceConfig().chatCommands === "api") {
      return tryHandleTaskEngineChatCommandViaApi(parsed);
    }
    var blocked = runPanelTaskPolicyOrNull(parsed);
    if (blocked) return blocked;
    if (parsed.verb === "olustur") {
      if (!parsed.taskName) {
        return { text: "Görev adı eksik. Örnek: görev oluştur alışveriş", depth: "simple" };
      }
      var task = LumosMinTaskEngine.createTask(parsed.taskName);
      if (!task) {
        return { text: "Görev adı eksik. Örnek: görev oluştur alışveriş", depth: "simple" };
      }
      appendPanelEngineEvent(createTaskCreatedEvent(task.id, task.title));
      finalizeTaskMutation();
      return { text: 'Görev oluşturuldu: "' + task.title + '".', depth: "simple" };
    }
    if (parsed.verb === "tamamla") {
      if (!parsed.ref) {
        return { text: "Görev adı eksik. Örnek: görev tamamla alışveriş", depth: "simple" };
      }
      var result = completeTask(parsed.ref);
      if (!result.ok) {
        if (result.reason === "empty") {
          return { text: "Görev adı eksik. Örnek: görev tamamla alışveriş", depth: "simple" };
        }
        if (result.reason === "already_done") {
          return { text: "Görev zaten tamamlanmış.", depth: "simple" };
        }
        return { text: "Tamamlanacak görev bulunamadı.", depth: "simple" };
      }
      appendPanelEngineEvent({
        type: "task_completed",
        taskId: result.task.id,
        text: String(result.task.title || "").trim(),
        ts: result.completedAt,
      });
      finalizeTaskMutation();
      return { text: 'Görev tamamlandı: "' + result.task.title + '".', depth: "simple" };
    }
    if (parsed.verb === "sil") {
      if (!parsed.ref) {
        return { text: "Görev adı eksik. Örnek: görev sil alışveriş", depth: "simple" };
      }
      if (!window.confirm('"' + parsed.ref + '" will be deleted. Do you confirm?')) {
        return { text: "Delete cancelled.", depth: "simple" };
      }
      var delResult = schedulePendingDeleteTask(parsed.ref);
      if (!delResult.ok) {
        if (delResult.reason === "empty") {
          return { text: "Görev adı eksik. Örnek: görev sil alışveriş", depth: "simple" };
        }
        return { text: "Silinecek görev bulunamadı.", depth: "simple" };
      }
      runPendingDeleteSweep();
      finalizeTaskMutation();
      var secLocal = pendingDeleteGraceSecondsRounded();
      return {
        text:
          TASK_PENDING_DELETE_UI_LABEL +
          " " +
          secLocal +
          " sn içinde kalıcı silinecek. İptal: listede veya detayda «Geri al» — \"" +
          delResult.task.title +
          '".',
        depth: "simple",
      };
    }
    if (parsed.verb === "geri_al") {
      if (!parsed.ref) {
        return { text: "Görev adı eksik. Örnek: görev geri al alışveriş", depth: "simple" };
      }
      var uResult = undoPendingDeleteTask(parsed.ref);
      if (!uResult.ok) {
        if (uResult.reason === "empty") {
          return { text: "Görev adı eksik. Örnek: görev geri al alışveriş", depth: "simple" };
        }
        return { text: "Geri alınacak silme bekleyen görev bulunamadı.", depth: "simple" };
      }
      clearPendingDeleteTickerIfIdle();
      finalizeTaskMutation();
      return { text: 'Silme iptal edildi: "' + uResult.task.title + '".', depth: "simple" };
    }
    return null;
  }

  /** Yanıt metnine göre flash türü: ok | info | error (buton → aksiyon → geri bildirim). */
  function taskDetailFlashKindFromReply(msg) {
    if (!msg || !String(msg).trim()) return "info";
    var s = String(msg);
    if (s.indexOf("Görev tamamlandı") === 0 || s.indexOf("Görev silindi") === 0) return "ok";
    if (s.indexOf("Siliniyor") === 0 || s.indexOf("Silme iptal edildi") === 0) return "ok";
    if (s.indexOf("Görev zaten tamamlanmış") === 0) return "info";
    return "error";
  }

  function applyTaskDetailFlashFromReplyText(txt) {
    if (!txt || !String(txt).trim()) {
      taskDetailViewState.flash = null;
      clearTaskDetailFlashTimer();
      return;
    }
    var kind = taskDetailFlashKindFromReply(txt);
    taskDetailViewState.flash = {
      kind: kind,
      text: String(txt),
      panelAction: taskDetailPanelLastCmdAction || undefined,
    };
    if (kind === "ok") scheduleTaskDetailOkFlashAutoClear();
    else clearTaskDetailFlashTimer();
  }

  /**
   * Detay paneli butonları → sohbetle aynı tryHandleTaskEngineChatCommand metin komutu.
   * @param {string} cmd örn. görev tamamla ref
   */
  function handleTaskDetailPanelCommand(cmd) {
    clearTaskDetailFlashTimer();
    taskDetailViewState.flash = null;
    taskDetailPanelLastCmdAction = inferTaskPanelActionFromCmd(cmd);
    var res = tryHandleTaskEngineChatCommand(cmd);
    if (res && typeof res.then === "function") {
      taskDetailViewState.detailActionBusy = true;
      refreshCurrentView();
      res
        .then(function (r) {
          taskDetailViewState.detailActionBusy = false;
          var txt = r && r.text != null ? String(r.text) : "";
          if (txt) applyTaskDetailFlashFromReplyText(txt);
          else {
            taskDetailViewState.flash = null;
            clearTaskDetailFlashTimer();
          }
          refreshCurrentView();
        })
        .catch(function (err) {
          taskDetailViewState.detailActionBusy = false;
          clearTaskDetailFlashTimer();
          taskDetailViewState.flash = {
            kind: "error",
            text: "İşlem tamamlanamadı.",
            panelAction: taskDetailPanelLastCmdAction || undefined,
          };
          refreshCurrentView();
        });
      return;
    }
    taskDetailViewState.detailActionBusy = false;
    if (res && res.text != null) applyTaskDetailFlashFromReplyText(String(res.text));
    else {
      taskDetailViewState.flash = null;
      clearTaskDetailFlashTimer();
    }
    refreshCurrentView();
  }

  function handleTaskDetailCompleteDirect(taskRef) {
    taskDetailViewState.detailActionBusy = true;
    taskDetailPanelLastCmdAction = "complete";
    clearTaskDetailFlashTimer();
    taskDetailViewState.flash = null;
    refreshCurrentView();
    fetchWithTimeout(
      TASKS_API_BASE + "/tasks/complete",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ref: String(taskRef || "") }),
      },
      PANEL_TASKS_FETCH_MS
    )
      .then(function (res) {
        if (res.status === 404) {
          return Promise.reject(new Error("Tamamlanacak görev bulunamadı."));
        }
        if (!res.ok && res.status !== 409) {
          return Promise.reject(new Error("İşlem tamamlanamadı."));
        }
        return refreshTasksDocumentFromApiStrict();
      })
      .then(function () {
        taskDetailViewState.detailActionBusy = false;
        taskDetailViewState.flash = { kind: "ok", text: "Görev tamamlandı.", panelAction: "complete" };
        scheduleTaskDetailOkFlashAutoClear();
        refreshCurrentView();
      })
      .catch(function (err) {
        taskDetailViewState.detailActionBusy = false;
        clearTaskDetailFlashTimer();
        taskDetailViewState.flash = {
          kind: "error",
          text: (err && err.message) || "İşlem tamamlanamadı.",
          panelAction: "complete",
        };
        refreshCurrentView();
      });
  }

  function handleTaskDetailDeleteDirect(taskId) {
    taskDetailViewState.detailActionBusy = true;
    taskDetailPanelLastCmdAction = "delete";
    clearTaskDetailFlashTimer();
    taskDetailViewState.flash = null;
    refreshCurrentView();
    fetchWithTimeout(
      TASKS_API_BASE + "/tasks/delete",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: String(taskId || "") }),
      },
      PANEL_TASKS_FETCH_MS
    )
      .then(function (res) {
        if (!res.ok) {
          return Promise.reject(new Error("İşlem tamamlanamadı."));
        }
        return refreshTasksDocumentFromApiStrict();
      })
      .then(function () {
        taskDetailViewState.detailActionBusy = false;
        taskDetailViewState.flash = { kind: "ok", text: "Görev silindi.", panelAction: "delete" };
        scheduleTaskDetailOkFlashAutoClear();
        refreshCurrentView();
        pollLumosReadState();
      })
      .catch(function (err) {
        taskDetailViewState.detailActionBusy = false;
        clearTaskDetailFlashTimer();
        taskDetailViewState.flash = {
          kind: "error",
          text: (err && err.message) || "İşlem tamamlanamadı.",
          panelAction: "delete",
        };
        refreshCurrentView();
      });
  }

  /**
   * @param {string} userText
   * @returns {Promise<{ text: string, depth?: string, blocks?: object }>|{ text: string, depth?: string, blocks?: object }}
   */
  function buildAssistantReply(userText) {
    var trimmed = String(userText || "").trim();
    if (!trimmed) {
      return { text: "Bir mesaj yazın.", depth: "simple" };
    }
    var nav = tryChatPanelNavigationIntent(trimmed);
    if (nav) return nav;
    var engineReply = tryHandleTaskEngineChatCommand(trimmed);
    if (engineReply) return engineReply;
    var keyTr = normalizeChatIntentKey(trimmed);
    var keyAscii = keyTr.replace(/ğ/g, "g").replace(/ü/g, "u").replace(/ş/g, "s").replace(/ı/g, "i").replace(/ö/g, "o").replace(/ç/g, "c");
    if (
      keyTr.indexOf("görev") !== -1 ||
      keyAscii.indexOf("gorev") !== -1
    ) {
      return {
        text: "Görevler ekranından listeyi görebilirsin. Yeni görev için: «görev oluştur başlık» (ör. görev oluştur alışveriş).",
        depth: "simple",
      };
    }
    if (keyTr.indexOf("kayıt") !== -1 || keyAscii.indexOf("kayit") !== -1) {
      return {
        text: "Kayıtlar ekranına geçip son çıktıyı inceleyebilirsin.",
        depth: "simple",
      };
    }
    if (keyTr.indexOf("akış") !== -1 || keyAscii.indexOf("akis") !== -1) {
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

    if (!text) {
      return;
    }
    var cmdKey = normalizeKilitAcCommandKey(text);
    var isUnlockCmd = isKilitAcChatCommand(cmdKey);

    if (isUnlockCmd) {
      if (chatViewState.kilitAcUnlockInFlight) {
        return;
      }
      ta.value = "";
      chatViewState.draft = "";
      chatViewState.userForcedScrollToBottom = true;
      chatViewState.focusComposerAfterRender = true;
      chatViewState.messages.push({ role: "user", text: text });
      persistChatMessagesToStorage();
      refreshCurrentView();
      openUnlockModal();
      return;
    }
    ta.value = "";
    chatViewState.draft = "";
    chatViewState.userForcedScrollToBottom = true;
    chatViewState.focusComposerAfterRender = true;
    chatViewState.messages.push({ role: "user", text: text });
    persistChatMessagesToStorage();
    refreshCurrentView();

    function pushAssistantAndRefresh(reply) {
      chatViewState.focusComposerAfterRender = true;
      var r = reply && typeof reply === "object" ? reply : { text: String(reply || ""), depth: "simple" };
      chatViewState.messages.push({
        role: "assistant",
        text: r.text != null ? String(r.text) : "",
        depth: r.depth,
        blocks: r.blocks,
      });
      persistChatMessagesToStorage();
      refreshCurrentView();
    }

    var replyOrPromise = buildAssistantReply(text);
    if (replyOrPromise && typeof replyOrPromise.then === "function") {
      replyOrPromise.then(pushAssistantAndRefresh).catch(function (err) {
        pushAssistantAndRefresh({
          text: "Bağlantı hatası; tekrar deneyin.",
          depth: "simple",
        });
      });
      return;
    }
    pushAssistantAndRefresh(replyOrPromise);
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

  /** Chat ana içeriği: önce mevcut yazıyı draft’a al, sonra HTML bas, sonra draft geri yükle. */
  function renderChatMainInto(mainEl) {
    if (!mainEl) return;
    var prev = document.getElementById("lumos-chat-input");
    if (prev) {
      chatViewState.draft = prev.value != null ? String(prev.value) : "";
    }
    var prevLog = mainEl.querySelector(".lumos-chat-log");
    var savedScroll = null;
    if (prevLog) {
      savedScroll = {
        scrollTop: prevLog.scrollTop,
        scrollHeight: prevLog.scrollHeight,
        clientHeight: prevLog.clientHeight,
      };
    }
    mainEl.innerHTML = renderChat();
    var next = document.getElementById("lumos-chat-input");
    if (next) {
      next.value = chatViewState.draft;
    }
    var logEl = mainEl.querySelector(".lumos-chat-log");
    if (logEl) {
      logEl.onscroll = onChatLogScroll;
    }
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        var log = mainEl.querySelector(".lumos-chat-log");
        if (!log) return;
        if (chatViewState.userForcedScrollToBottom || chatViewState.stickToBottom) {
          log.scrollTop = log.scrollHeight;
        } else if (savedScroll && savedScroll.scrollHeight > 0) {
          var oldBottom = savedScroll.scrollHeight - savedScroll.scrollTop - savedScroll.clientHeight;
          log.scrollTop = Math.max(0, log.scrollHeight - log.clientHeight - oldBottom);
        }
        chatViewState.userForcedScrollToBottom = false;
        if (chatViewState.focusComposerAfterRender) {
          var inp = document.getElementById("lumos-chat-input");
          if (inp) {
            try {
              if (typeof inp.focus === "function") {
                inp.focus({ preventScroll: true });
              } else {
                inp.focus();
              }
            } catch (e2) {
              inp.focus();
            }
            try {
              var len = inp.value.length;
              inp.setSelectionRange(len, len);
            } catch (e3) {
              /* ignore */
            }
          }
          chatViewState.focusComposerAfterRender = false;
        }
      });
    });
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

  /** Merkezi route → HTML (mockState her çağrıda render* içinden okunur; önbellek yok). */
  function renderRouteHtml() {
    var screen = getCurrentScreen();
    var fn = renderers[screen.id];
    return fn ? fn() : renderEmptyState("Geçersiz sayfa", "Menüden bir ekran seçin.");
  }

  function renderMain() {
    var main = document.getElementById("main-content");
    if (!main) return;
    var screen = getCurrentScreen();
    if (screen && screen.id === "chat") {
      renderChatMainInto(main);
      return;
    }
    main.innerHTML = renderRouteHtml();
  }

  /**
   * Aktif hash için doğrudan ilgili render* çalıştırır (tasks/logs/dashboard/chat açık adres).
   * Diğer rotalar: renderRouteHtml ile renderMain ile aynı zincir.
   */
  function refreshCurrentView() {
    var main = document.getElementById("main-content");
    if (!main) return;
    var h = (window.location.hash || DEFAULT_HASH).toLowerCase();
    if (h.length <= 1) h = DEFAULT_HASH.toLowerCase();
    if (h === "#tasks") {
      main.innerHTML = renderTasks();
      return;
    }
    if (h === "#logs") {
      main.innerHTML = renderLogs();
      return;
    }
    if (h === "#dashboard") {
      main.innerHTML = renderDashboard();
      return;
    }
    if (h === "#chat") {
      renderChatMainInto(main);
      return;
    }
    if (feedTabFromLocationHash()) {
      main.innerHTML = renderFeed();
      return;
    }
    main.innerHTML = renderRouteHtml();
  }

  /** Seçili görev, aktif filtrenin listesinde yoksa detay paneli için seçimi kaldır. */
  function syncTaskSelectionAfterMutation() {
    var selId = mockState.selectedTaskId;
    if (selId == null || selId === "") return;
    var fullList = getEngineTaskRowsForTasksScreen();
    var af = mockState.taskFilter || "all";
    var filtered = LC.filterTaskList ? LC.filterTaskList(fullList, af) : fullList;
    var visible = false;
    var i;
    for (i = 0; i < filtered.length; i++) {
      if (taskIdEquals(filtered[i].id, selId)) {
        visible = true;
        break;
      }
    }
    if (!visible) mockState.selectedTaskId = null;
  }

  /**
   * Görev motoru mutasyonu kapanışı: tek persist + seçim senkronu + aktif route ana içerik yenilemesi.
   */
  function finalizeTaskMutation() {
    persistTasksJsonDocument();
    syncTaskSelectionAfterMutation();
    refreshCurrentView();
  }

  function clearPendingDeleteTickerIfIdle() {
    if (engineHasPendingDeleteTasks()) return;
    if (pendingDeleteTickerId != null) {
      clearInterval(pendingDeleteTickerId);
      pendingDeleteTickerId = null;
    }
  }

  function refreshTasksViewIfPendingCountdownNeeded() {
    try {
      if ((window.location.hash || "").toLowerCase() !== "#tasks") return;
      if (engineHasPendingDeleteTasks()) refreshCurrentView();
    } catch (_) {
      /* ignore */
    }
  }

  function ensurePendingDeleteTicker() {
    if (pendingDeleteTickerId != null) return;
    pendingDeleteTickerId = setInterval(function () {
      tickPendingDeleteExpiry();
      refreshTasksViewIfPendingCountdownNeeded();
    }, 400);
  }

  function finalizeEngineTaskPermanentDelete(taskId) {
    var idStr = taskId != null ? String(taskId) : "";
    if (!idStr) return;
    var tasks = mockState.engineTasks || [];
    var task = null;
    var ti;
    for (ti = 0; ti < tasks.length; ti++) {
      var t = tasks[ti];
      if (t && String(t.id) === idStr && t.status === TASK_STATUS.PENDING_DELETE) {
        task = t;
        break;
      }
    }
    if (!task) return;

    var delBase = String(API_BASE).replace(/\/$/, "");
    var delUrl = delBase + "/tasks/delete-permanent";
    panelTasksTrashDirectPost(delUrl, { id: idStr })
      .then(function (r) {
        return r.text().then(function (txt) {
          var j = null;
          try {
            j = txt && String(txt).trim() ? JSON.parse(txt) : null;
          } catch (_) {
            j = null;
          }
          return { ok: r.ok, j: j && typeof j === "object" ? j : {} };
        });
      })
      .then(function (x) {
        if (!x.ok || !x.j.ok) return;
        return syncTasksDocumentFromApi().then(function () {
          clearPendingDeleteTickerIfIdle();
          refreshCurrentView();
        });
      })
      .catch(function () {});
  }

  function tickPendingDeleteExpiry() {
    var now = Date.now();
    var tasks = mockState.engineTasks || [];
    var ids = [];
    var i;
    for (i = 0; i < tasks.length; i++) {
      var t = tasks[i];
      if (!t || t.status !== TASK_STATUS.PENDING_DELETE) continue;
      var exp = t.expireAt != null ? Date.parse(String(t.expireAt)) : NaN;
      if (!isNaN(exp) && exp <= now) ids.push(String(t.id));
    }
    for (i = 0; i < ids.length; i++) {
      finalizeEngineTaskPermanentDelete(ids[i]);
    }
    clearPendingDeleteTickerIfIdle();
  }

  function runPendingDeleteSweep() {
    tickPendingDeleteExpiry();
    ensurePendingDeleteTicker();
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
    var trashTaskBtnEarly = t.closest && t.closest("[data-trash-task-action]");
    if (trashTaskBtnEarly && trashTaskBtnEarly.dataset && trashTaskBtnEarly.dataset.trashTaskAction) {
      if (!trashTaskBtnEarly.disabled) {
        e.preventDefault();
        e.stopPropagation();
        var ttidE = trashTaskBtnEarly.dataset.trashTaskId != null ? String(trashTaskBtnEarly.dataset.trashTaskId).trim() : "";
        if (ttidE) {
          var tactE = String(trashTaskBtnEarly.dataset.trashTaskAction);
          if (tactE === "restore" || tactE === "delete-permanent") {
            handleTrashTaskServerAction(tactE, ttidE);
          }
        }
      }
      return;
    }
    var listUndoBtn = t.closest && t.closest("[data-task-list-undo]");
    if (
      listUndoBtn &&
      listUndoBtn.dataset &&
      listUndoBtn.dataset.taskRef != null &&
      String(listUndoBtn.dataset.taskRef) !== ""
    ) {
      if (taskDetailViewState.detailActionBusy) return;
      e.preventDefault();
      e.stopPropagation();
      taskDetailPanelLastCmdAction = "undo";
      handleTaskDetailPanelCommand("görev geri al " + String(listUndoBtn.dataset.taskRef));
      return;
    }
    var detailActBtn = t.closest && t.closest("[data-task-detail-action]");
    if (
      detailActBtn &&
      detailActBtn.dataset &&
      detailActBtn.dataset.taskDetailAction &&
      detailActBtn.dataset.taskRef != null &&
      String(detailActBtn.dataset.taskRef) !== ""
    ) {
      if (taskDetailViewState.detailActionBusy) return;
      e.preventDefault();
      var dref = String(detailActBtn.dataset.taskRef);
      var dact = String(detailActBtn.dataset.taskDetailAction);
      if (dact === "complete") {
        handleTaskDetailCompleteDirect(dref);
        return;
      }
      if (dact === "delete") {
        if (!window.confirm('"' + dref + '" will be deleted. Do you confirm?')) return;
        handleTaskDetailDeleteDirect(dref);
        return;
      }
      var dcmd =
        dact === "undo-pending"
              ? "görev geri al " + dref
              : "";
      if (dcmd) handleTaskDetailPanelCommand(dcmd);
      return;
    }
    var taskRow =
      (t.closest && t.closest("[data-task-id]")) || closestByDataAttr(t, "taskId");
    if (taskRow && taskRow.dataset && taskRow.dataset.taskId) {
      clearTaskDetailFlashTimer();
      taskDetailViewState.flash = null;
      mockState.selectedTaskId = taskRow.dataset.taskId;
      renderMain();
      return;
    }
    if (t.dataset && t.dataset.taskFilter) {
      clearTaskDetailFlashTimer();
      taskDetailViewState.flash = null;
      mockState.taskFilter = t.dataset.taskFilter;
      syncTaskSelectionAfterMutation();
      renderMain();
      return;
    }
    var openTrashDirBtn = t.closest && t.closest("[data-lumos-open-folder]");
    if (
      openTrashDirBtn &&
      openTrashDirBtn.dataset &&
      openTrashDirBtn.dataset.openPath != null &&
      String(openTrashDirBtn.dataset.openPath).trim() !== ""
    ) {
      e.preventDefault();
      e.stopPropagation();
      lumosOpenWorkspaceFolder(String(openTrashDirBtn.dataset.openPath));
      return;
    }
    var trashListRow = t.closest && t.closest("[data-trash-id]");
    if (trashListRow && trashListRow.dataset && trashListRow.dataset.trashId != null && String(trashListRow.dataset.trashId) !== "") {
      mockState.selectedTrashId = trashListRow.dataset.trashId;
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
          if (trashAction === "permanent-delete") {
            var previewLine = "";
            var tposts = trashViewState.trashPosts || [];
            var pi;
            for (pi = 0; pi < tposts.length; pi++) {
              if (String(tposts[pi].id) === String(trashPostId)) {
                previewLine = trashPreviewText(tposts[pi].content || "");
                break;
              }
            }
            appendPanelEngineEvent({
              type: "post_permanently_deleted",
              taskId: String(trashPostId),
              text: previewLine ? "Gönderi kalıcı silindi: " + previewLine : "Gönderi kalıcı silindi",
              ts: new Date().toISOString(),
            });
            persistTasksJsonDocument();
          }
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
    var kayTl = t.closest && t.closest("[data-kayitlar-timeline-key]");
    if (kayTl && kayTl.dataset && kayTl.dataset.kayitlarTimelineKey != null && kayTl.dataset.kayitlarTimelineKey !== "") {
      mockState.selectedKayitlarTimelineKey = String(kayTl.dataset.kayitlarTimelineKey);
      renderMain();
      return;
    }
    if (t.dataset && t.dataset.logFilter) {
      mockState.logFilter = t.dataset.logFilter;
      mockState.selectedKayitlarTimelineKey = null;
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
      trashViewState.taskTrashBusy = false;
    }
    _lastRouteScreenId = cur.id;

    if (cur.id !== "tasks") {
      clearTaskDetailFlashTimer();
      taskDetailViewState.flash = null;
      taskDetailViewState.detailActionBusy = false;
    }

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
    setTaskSourceDomAttribute();
  }

  function onHashChange() {
    refresh();
    if (suppressNextTasksApiRevalidate) {
      suppressNextTasksApiRevalidate = false;
      return;
    }
    scheduleTasksApiRevalidate();
  }

  function onMainKeydown(e) {
    var t = e.target;
    if (!t || t.id !== "lumos-chat-input") return;
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      e.stopPropagation();
      submitChatFromComposer();
    }
  }

  function onMainInput(e) {
    var t = e.target;
    if (!t || t.id !== "lumos-chat-input") return;
    chatViewState.draft = t.value != null ? String(t.value) : "";
  }

  var mainEl = document.getElementById("main-content");
  if (mainEl) {
    mainEl.addEventListener("click", onMainClick);
    mainEl.addEventListener("keydown", onMainKeydown);
    mainEl.addEventListener("input", onMainInput);
  }

  /** İlk `location.hash` atamasının hashchange ile çift GET /tasks tetiklemesini engeller. */
  var suppressNextTasksApiRevalidate = false;

  function resolveLumosLiveStateUrl() {
    var w = typeof window !== "undefined" ? window : null;
    if (w && w.LUMOS_PANEL_LIVE_STATE_URL != null && String(w.LUMOS_PANEL_LIVE_STATE_URL).trim() !== "") {
      return String(w.LUMOS_PANEL_LIVE_STATE_URL).trim();
    }
    var base = getPanelTasksApiBaseResolved();
    if (!base || String(base).trim() === "") base = "http://127.0.0.1:8766";
    return String(base).replace(/\/$/, "") + "/lumos-read-state";
  }

  /** panel_tasks_server POST /lumos-consent; görev API tabanı ile aynı host. */
  function buildKilitAcConsentPostUrl() {
    var w = typeof window !== "undefined" ? window : null;
    if (!w || !w.location) return "";
    if (w.LUMOS_PANEL_TASKS_API_BASE === false) {
      return "";
    }
    var base = getPanelTasksApiBaseResolved();
    var baseTrim = base && String(base).trim() !== "" ? String(base).replace(/\/$/, "") : "";
    if (baseTrim) {
      try {
        var apiOrigin = new URL(baseTrim).origin;
        if (apiOrigin === w.location.origin) {
          return "/lumos-consent";
        }
        return new URL(baseTrim + "/lumos-consent").href;
      } catch (_) {
        return "";
      }
    }
    try {
      var proto = String(w.location.protocol || "");
      if (proto === "http:" || proto === "https:") {
        return "/lumos-consent";
      }
    } catch (_) {}
    try {
      return "http://127.0.0.1:8766/lumos-consent";
    } catch (_) {
      return "";
    }
  }

  /**
   * Gerçek host (fn var, _lumosStub değil) → unlock; aksi halde POST /lumos-consent.
   * Yalnızca { ok: true/false } döner; reject etmez (sonuç mesajı çağıran basar).
   */
  function runKilitAcUnlockFromChat(passphrase) {
    var w = typeof window !== "undefined" ? window : null;
    var fn = w && w.LUMOS_PANEL_KEYSTORE_UNLOCK;
    var pass = passphrase != null ? String(passphrase).trim() : "";

    function postConsentApi() {
      var postUrl;
      try {
        postUrl = buildKilitAcConsentPostUrl();
      } catch (_) {
        return Promise.resolve({ ok: false });
      }
      if (!postUrl || !pass) {
        return Promise.resolve({ ok: false });
      }
      return fetch(postUrl, {
        method: "POST",
        credentials: "omit",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ passphrase: pass }),
      })
        .then(function (r) {
          return r.text().then(function (txt) {
            var j = null;
            try {
              j = txt && String(txt).trim() ? JSON.parse(txt) : null;
            } catch (_) {
              j = null;
            }
            if (r.ok && j && j.ok === true) {
              try {
                pollLumosReadState();
              } catch (_) {}
              return { ok: true };
            }
            return { ok: false };
          });
        })
        .catch(function () {
          return { ok: false };
        });
    }

    var chain;
    try {
      if (typeof fn === "function" && fn._lumosStub !== true) {
        chain = Promise.resolve()
          .then(function () {
            return fn(pass);
          })
          .then(function (result) {
            if (result && typeof result === "object" && result.ok === false) {
              return { ok: false };
            }
            if (result && typeof result === "object" && result.ok === true) {
              try {
                pollLumosReadState();
              } catch (_) {}
              return { ok: true };
            }
            try {
              pollLumosReadState();
            } catch (_) {}
            return { ok: true };
          })
          .catch(function () {
            return { ok: false };
          });
      } else {
        chain = postConsentApi();
      }
    } catch (_) {
      chain = Promise.resolve({ ok: false });
    }
    return chain.then(normalizeUnlockResult).catch(function () {
      return { ok: false };
    });
  }

  function pollLumosReadState() {
    var url = resolveLumosLiveStateUrl();
    fetch(url, { method: "GET", credentials: "omit", cache: "no-store" })
      .then(function (r) {
        return r.ok ? r.json() : Promise.reject(new Error("http_" + r.status));
      })
      .then(function (data) {
        if (!data || typeof data !== "object") return;
        var trashResp = data.trash;
        var snapshot;
        try {
          snapshot = JSON.parse(JSON.stringify(data));
        } catch (_) {
          snapshot = data;
        }
        window.__LUMOS_READ_STATE__ = snapshot;
        if (trashResp != null && typeof trashResp === "object") {
          try {
            window.__LUMOS_READ_STATE__.trash = JSON.parse(JSON.stringify(trashResp));
          } catch (_) {
            window.__LUMOS_READ_STATE__.trash = trashResp;
          }
        }
        if (typeof console !== "undefined" && console.log) {
          console.log("RESPONSE.trash", data.trash);
          console.log("STATE.trash", window.__LUMOS_READ_STATE__ && window.__LUMOS_READ_STATE__.trash);
        }
        var pollHash = (window.location.hash || "").toLowerCase();
        if (pollHash !== "#chat") {
          refreshCurrentView();
        }
        renderSidebar();
        renderTopbar();
      })
      .catch(function () {
        // Panel state üretmez; hata durumunda mevcut backend state ekranda kalır.
      });
  }

  setTimeout(function () {
    pollLumosReadState();
  }, 0);

  hydrateTasksJsonPersistenceAsync(function () {
    window.addEventListener("hashchange", onHashChange);
    if (!window.location.hash) {
      suppressNextTasksApiRevalidate = true;
      window.location.hash = DEFAULT_HASH;
    } else {
      refresh();
    }
    setInterval(pollLumosReadState, 3000);
  });

})();
