/**
 * Lumos Panel v1 — Tek veri sözleşmesi dosyası (Contract & Stub katmanı).
 *
 * Panel veri sözleşmesi: Tüm ekranların beklenen veri alanları bu dosyada CONTRACTS ile tanımlıdır.
 * - Bridge (backend-bridge.js): backend şeklini (snake_case) döner.
 * - Fixture mapper'ları (fixtures.js): backend/fixture payload → panel şekline çevirir.
 * - Adapter (app.js): getXxxData() → normalizer bu sözleşmeye göre eksik alanları güvenli varsayılana çeker.
 * Bu dosyada fetch/API yok; sadece şema, stub ve normalizer.
 */
(function (global) {
  "use strict";

  var EMPTY_DESC_DEFAULT = "Mock veri; canlı entegrasyon sonraki aşamada açılacak.";

  // ——— Panel veri sözleşmesi: ekran bazlı beklenen alanlar (tek kaynak) ———
  // Dashboard: title, subtitle, metrics[], sections[{ title, events?, warnings?, links? }]
  // Sandbox:   title, subtitle, metrics[], sections[{ title, body }]
  // System:    title, subtitle, healthCards[{ title, status, note }]
  // Config:    title, subtitle, metrics[], sections[{ title, body }]
  // Identity:  title, subtitle, metrics[], sections[{ title, body }]
  // Keystore:  title, subtitle, metrics[], sections[{ title, body }]
  // Tasks:     title, subtitle, filters[], activeFilter, listItems[{ id, title, status, updated, lastRun, guardResult, outputSummary }], selectedId, selectedTask, emptyListTitle, emptyListDesc, detailTitle, runNoteTitle, runNoteBody
  // Trash:     title, subtitle, summaryMetrics[], listItems[{ id, name, originalPath, trashPath, movedAt, scope }], selectedId, selectedItem, detailTitle, emptyListTitle, emptyListDesc, emptyDetailPlaceholder
  // Logs:      title, subtitle, filters[], activeFilter, events[{ id, kind, text, ts }], sectionTitle

  /**
   * CONTRACTS — Ekran bazlı beklenen veri şemaları (varsayılan değerler).
   * Eksik gelen alanlar applyContractFallbacks ve normalizer ile güvenli varsayılana çekilir.
   */
  var CONTRACTS = {
    dashboard: {
      title: "",
      subtitle: "",
      metrics: [],
      sections: [{ title: "", events: [], warnings: [], links: false }],
    },
    tasks: {
      title: "",
      subtitle: "",
      filters: [],
      activeFilter: "",
      listItems: [],
      selectedId: null,
      selectedTask: null,
      listUpdated: null,
      emptyListTitle: "",
      emptyListDesc: "",
      detailTitle: "",
      runNoteTitle: "",
      runNoteBody: "",
    },
    sandbox: {
      title: "",
      subtitle: "",
      metrics: [],
      sections: [{ title: "", body: "" }],
    },
    config: {
      title: "",
      subtitle: "",
      metrics: [],
      sections: [{ title: "", body: "" }],
    },
    identity: {
      title: "",
      subtitle: "",
      metrics: [],
      sections: [{ title: "", body: "" }],
    },
    keystore: {
      title: "",
      subtitle: "",
      metrics: [],
      sections: [{ title: "", body: "" }],
    },
    trash: {
      title: "",
      subtitle: "",
      summaryMetrics: [],
      listItems: [],
      selectedId: null,
      selectedItem: null,
      detailTitle: "",
      emptyListTitle: "",
      emptyListDesc: "",
      emptyDetailPlaceholder: "",
    },
    logs: {
      title: "",
      subtitle: "",
      filters: [],
      activeFilter: "",
      events: [],
      logFileUpdated: null,
      logLocation: null,
      sectionTitle: "",
    },
    system: {
      title: "",
      subtitle: "",
      healthCards: [{ title: "", status: "", note: "" }],
    },
  };

  var TASK_FILTERS = [
    { id: "all", label: "Tümü" },
    { id: "active", label: "Aktif" },
    { id: "pending", label: "Bekleyen" },
    { id: "completed", label: "Tamamlandı" },
    { id: "failed", label: "Başarısız" },
    { id: "blocked", label: "Engellenen" },
  ];

  var LOG_FILTERS = [
    { id: "all", label: "Tümü", kind: null },
    { id: "tasks", label: "Görevler", kind: "görev" },
    { id: "sandbox", label: "Korumalı Alan", kind: "sandbox" },
    { id: "config", label: "Yapılandırma", kind: "config" },
    { id: "trash", label: "Silinenler", kind: "trash" },
    { id: "identity", label: "Kimlik", kind: "identity" },
    { id: "keystore", label: "Anahtar Kasası", kind: "keystore" },
    { id: "guard", label: "Koruma", kind: "guard" },
  ];

  /** CONTRACTS anahtarları (ekran adları). */
  var SCREEN_KEYS = ["dashboard", "tasks", "sandbox", "config", "identity", "keystore", "trash", "logs", "system"];

  /**
   * Eksik üst-seviye alanları CONTRACTS[screenKey] varsayılanlarıyla doldurur.
   * Bridge/fixture mapper çıktısı normalizer'a gelmeden önce veya normalizer içinde tek noktadan fallback.
   */
  function applyContractFallbacks(screenKey, data) {
    if (!data || typeof data !== "object") return data;
    var def = CONTRACTS[screenKey];
    if (!def) return data;
    var key;
    for (key in def) {
      if (Object.prototype.hasOwnProperty.call(def, key) && data[key] === undefined) {
        data[key] = Array.isArray(def[key]) ? def[key].slice() : (typeof def[key] === "object" && def[key] !== null ? JSON.parse(JSON.stringify(def[key])) : def[key]);
      }
    }
    return data;
  }

  function formatTime(s) {
    if (!s || s === "—") return "—";
    try {
      var d = new Date(s);
      return isNaN(d.getTime()) ? s : d.toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" });
    } catch (_) {
      return s;
    }
  }

  function filterTaskList(list, filterId) {
    if (!list) return [];
    if (filterId === "all") return list;
    var statusMap = { active: "aktif", pending: "bekleyen", completed: "tamamlandı", failed: "başarısız", blocked: "engellenen" };
    var status = statusMap[filterId];
    return status ? list.filter(function (t) { return t.status === status; }) : list;
  }

  // ——— Stub üreticileri (state → contract şeklinde veri) ———

  function buildDashboardStub(state) {
    var lastEv = state.recentEvents && state.recentEvents[0] ? state.recentEvents[0] : null;
    var sandboxBadge = state.sandboxMode ? { label: "KORUMALI ALAN", variant: "badge-sandbox" } : null;
    return {
      title: "Gösterge Paneli",
      subtitle: "Sistem durumu özeti",
      metrics: [
        { title: "Korumalı Alan Durumu", value: state.sandboxMode ? " Açık" : "Kapalı", valueBadge: sandboxBadge, note: state.sandboxMode ? "Yazım sandbox dizinine yönlendiriliyor; canlıya overwrite yok." : "Yazım doğrudan çalışma alanına gidiyor." },
        { title: "Yazım Hedefi", value: state.writingBaseDir, note: state.writingBaseDir === "canlı" ? "Tüm yazma işlemleri çalışma alanına gidiyor." : "Yazma işlemleri sandbox base'e yönlendiriliyor." },
        { title: "Koruma Durumu", valueBadge: { label: state.guardStatus, variant: "badge-guard" }, note: "Çekirdek state path'ler guard ile korunuyor; sözleşme hedefi dışına yazılmaz." },
        { title: "Son Aktivite", value: lastEv ? formatTime(lastEv.ts) : "—", note: lastEv ? (lastEv.text || "—") : "Henüz kayıt yok." },
      ],
      sections: [
        { title: "Son Olaylar", events: state.recentEvents },
        { title: "Uyarılar ve notlar", warnings: state.warnings },
        { title: "Hızlı geçişler", links: true },
      ],
    };
  }

  function buildTasksStub(state) {
    var filter = state.taskFilter || "all";
    var list = state.taskList || [];
    var filtered = filterTaskList(list, filter);
    var selected = state.selectedTaskId ? list.filter(function (x) { return x.id === state.selectedTaskId; })[0] : null;
    return {
      title: "Görevler",
      subtitle: "Liste, detay ve guard sonucu",
      filters: TASK_FILTERS,
      activeFilter: filter,
      listItems: filtered,
      selectedId: state.selectedTaskId,
      selectedTask: selected,
      listUpdated: state.listUpdated || null,
      emptyListTitle: "Bu filtrede görev yok",
      emptyListDesc: "Farklı filtre seçin. " + EMPTY_DESC_DEFAULT,
      detailTitle: "Görev Detayı",
      runNoteTitle: "Çalıştırma notu",
      runNoteBody: "Son çalıştırma ve guard sonucu yukarıdaki detayda. Canlı entegrasyonda test notu burada doldurulacak.",
    };
  }

  function buildSandboxStub(state) {
    var contractBadge = state.sandboxMode ? { label: "KORUMALI ALAN", variant: "badge-sandbox" } : null;
    return {
      title: "Korumalı Alan",
      subtitle: "Yazım hedefi ve sandbox durumu",
      metrics: [
        { title: "Kaynak", value: state.sandboxSource || "varsayılan", note: "Öncelik: CLI → ENV → varsayılan. Şu an: " + (state.sandboxSource || "varsayılan") + "." },
        { title: "Sandbox Base", value: state.sandboxMode ? ".lumos/sandbox veya sözleşmeyle tanımlı base" : "— (korumalı alan kapalı)", note: state.sandboxMode ? "Korumalı alan açıkken tüm yazım bu dizine yönlendirilir." : "Korumalı alan açıldığında sözleşmedeki base kullanılır." },
        { title: "Yazım Yönü", value: state.writingBaseDir, note: state.writingBaseDir === "canlı" ? "Yazım doğrudan çalışma alanına gidiyor." : "Yazım sandbox base'e yönlendiriliyor." },
        { title: "Sözleşme Durumu", value: state.sandboxMode ? " Sözleşme tanımlı" : "Canlı mod; sandbox sözleşmesi devre dışı.", valueBadge: contractBadge, note: "Sandbox hedef dizini workspace sözleşmesiyle sabit; yeni çöp/sandbox alanı oluşturulmaz." },
      ],
      sections: [
        { title: "Çözümleme Mantığı", body: "<p>Kaynak önceliği: <strong>CLI → ENV → varsayılan</strong>. Sistem kendi kafasına canlı hedef seçmez; yazma hedefi tek kaynaktan (canlı base veya sözleşmeyle tanımlı sandbox base) gelir.</p><p class=\"text-muted-small\">Resolution: single source of truth.</p>" },
        { title: "Guard Kuralı", body: "<p>Çekirdek state path'lere doğrudan overwrite yapılmaz. Yazma hedefi tek kaynaktan belirlenir. Canlı çekirdek ile sandbox hedefi ayrı tutulur.</p><p class=\"text-muted-small\">Core state: tasks, logs, trash, config, aliases.</p>" },
        { title: "Canlı çekirdek / sandbox hedef farkı", body: "<p><strong>Canlı:</strong> Doğrudan çalışma alanı (.lumos vb.).</p><p><strong>Sandbox:</strong> Tanımlı kopya alanı; deneme/geliştirme burada yapılır, canlıya overwrite yok.</p><p class=\"text-muted-small\">Sandbox aktifken çekirdek path'ler okuma için kullanılabilir; yazım yalnızca sandbox base'e.</p>" },
      ],
    };
  }

  function buildConfigStub(state) {
    var cfg = state.configSnapshot || {};
    var lastEv = state.recentEvents && state.recentEvents[2] ? state.recentEvents[2] : null;
    var writeStatusBadge = (cfg.writeStatus || "").indexOf("Uyarı") !== -1 ? { label: "UYARI", variant: "badge-warning" } : null;
    return {
      title: "Yapılandırma",
      subtitle: "Config özeti ve yazım durumu",
      metrics: [
        { title: "Mevcut Yapılandırma Özeti", value: (cfg.profil || "—") + " · " + (cfg.workspace_root || "—"), note: "config.json; profil ve workspace kökü." },
        { title: "Yazım Durumu", value: cfg.writeStatus || "—", valueBadge: writeStatusBadge, note: "Config yazımları merkezi sink/guard hattı üzerinden geçer; sözleşme hedefi dışına yazılmaz." },
        { title: "Son Config Aktivitesi", value: cfg.lastActivity ? formatTime(cfg.lastActivity) : (lastEv ? formatTime(lastEv.ts) : "—"), note: cfg.lastActivityText || (lastEv ? lastEv.text : "—") },
      ],
      sections: [
        { title: "Sink / Guard hattı", body: "<p>Config yazımları <strong>merkezi sink/guard hattı</strong> üzerinden geçer. Çekirdek state path'ler (config, tasks, logs, trash, aliases) sözleşme ve guard ile korunur; hedef dışına yazım yapılmaz.</p><p class=\"text-muted-small\">Sink: tek giriş noktası; guard: hedef ve kapsam kontrolü.</p>" },
      ],
    };
  }

  function buildIdentityStub(state) {
    return {
      title: "Kimlik",
      subtitle: "Kimlik durumu ve kapsam",
      metrics: [
        { title: "Kimlik hazır mı", value: state.identityState || "—", note: "Kimlik hattı sink/guard omurgasına bağlı; riskli işlemler panelden açılmaz." },
        { title: "Son Yazım", value: state.identityLastWrite ? formatTime(state.identityLastWrite) : "—", note: "Son kimlik yazım/zamanı (mock)." },
        { title: "Hedef Kapsam", value: state.identityTargetScope || "—", note: "Çekirdek kimlik alanı; yetki dışı değişiklik yapılmaz." },
        { title: "Guard Sonucu", value: state.identityGuardResult || "—", note: "Guard sonucu: kimlik alanı korunuyor." },
      ],
      sections: [
        { title: "Sink / Guard bağlantısı", body: "<p>Bu hattın <strong>sink/guard omurgasına</strong> bağlı olduğu bu ekrandan görünür. Kimlik alanı çekirdek güvenlik kapsamında; riskli işlemler açılmaz, sadece durum ve kapsam görünürlüğü sağlanır.</p><p class=\"text-muted-small\">Identity sink: tek giriş; guard: kapsam ve yetki kontrolü.</p>" },
      ],
    };
  }

  function buildKeystoreStub(state) {
    return {
      title: "Anahtar Kasası",
      subtitle: "Durum görünürlüğü; anahtar ifşası yok",
      metrics: [
        { title: "Hazır mı", value: state.keystoreReady ? "Evet" : "Hayır (kilitli)", note: "Anahtar materyali ekranda açık gösterilmez; sadece durum ve akış görünürlüğü." },
        { title: "Şifreli Durum", value: state.keystoreState || "—", note: "Passphrase ve anahtar içeriği gösterilmez." },
        { title: "Son Güncelleme", value: state.keystoreLastUpdate ? formatTime(state.keystoreLastUpdate) : "—", note: "Son güncelleme zamanı (mock)." },
        { title: "Yazım Kapsamı", value: state.keystoreWriteScope || "—", note: "Kilit açılmadan hassas yazım yapılmaz." },
      ],
      sections: [
        { title: "Görünürlük ilkesi", body: "<p>Anahtar kasası ekranı <strong>durum ve akış görünürlüğü</strong> sağlar. Anahtar materyali (passphrase, key içeriği) açık gösterilmez; yalnızca hazır mı, şifreli durum, son güncelleme ve yazım kapsamı bilgisi gösterilir.</p><p class=\"text-muted-small\">Keystore sink: tek giriş; hassas veri panelde ifşa edilmez.</p>" },
      ],
    };
  }

  function buildTrashStub(state) {
    var items = state.trashItems || [];
    var selected = state.selectedTrashId ? items.filter(function (x) { return x.id === state.selectedTrashId; })[0] : null;
    return {
      title: "Silinenler",
      subtitle: "Çöp konumu ve liste",
      summaryMetrics: [
        { title: "Çöp Konumu", value: state.trashLocation },
        { title: "Son Taşıma", value: formatTime(state.trashLastMove) },
        { title: "Öğe Sayısı", value: String(items.length) },
        { title: "Kapsam", value: ".lumos/trash — aktif state kaynağı değildir" },
      ],
      listItems: items,
      selectedId: state.selectedTrashId,
      selectedItem: selected,
      detailTitle: "Seçilen öğe",
      emptyListTitle: "Çöp listesi boş",
      emptyListDesc: "Silinen öğe yok. " + EMPTY_DESC_DEFAULT,
      emptyDetailPlaceholder: "Listeden bir öğe seçin.",
    };
  }

  function buildLogsStub(state) {
    var filter = state.logFilter || "all";
    var list = state.logItems || [];
    var kindForFilter = null;
    for (var fi = 0; fi < LOG_FILTERS.length; fi++) {
      if (LOG_FILTERS[fi].id === filter) { kindForFilter = LOG_FILTERS[fi].kind; break; }
    }
    var filtered = filter === "all" || !kindForFilter ? list : list.filter(function (e) { return e.kind === kindForFilter; });
    return {
      title: "Kayıtlar",
      subtitle: "Olay akışı",
      filters: LOG_FILTERS,
      activeFilter: filter,
      events: filtered,
      logFileUpdated: state.logFileUpdated || null,
      logLocation: state.logLocation || null,
      sectionTitle: "Kayıt listesi",
    };
  }

  /** System: Phase 2 ilk gerçek backend okuma hedefi. healthKeys sırası read_backend_state.py SYSTEM_HEALTH_KEYS ile uyumlu tutulur. */
  function buildSystemStub(state) {
    var h = state.systemHealth || {};
    var healthKeys = [
      { key: "workspace_contract", title: "Workspace Sözleşmesi" },
      { key: "task_engine", title: "Görev Motoru" },
      { key: "sandbox_source", title: "Sandbox Kaynağı" },
      { key: "trash_contract", title: "Trash Sözleşmesi" },
      { key: "config_sink", title: "Config Sink" },
      { key: "identity_sink", title: "Identity Sink" },
      { key: "keystore_sink", title: "Keystore Sink" },
      { key: "general", title: "Genel Sağlık" },
    ];
    var healthCards = [];
    for (var i = 0; i < healthKeys.length; i++) {
      var raw = h[healthKeys[i].key];
      var status = !raw ? "—" : (typeof raw === "string" ? raw : (raw.status || "—"));
      var note = !raw ? "Veri yok." : (typeof raw === "string" ? "" : (raw.note || ""));
      healthCards.push({ title: healthKeys[i].title, status: status, note: note });
    }
    return { title: "Sistem Durumu", subtitle: "Çekirdek parçaların durumu", healthCards: healthCards };
  }

  // ——— Hafif doğrulama / normalizer (eksik alan → güvenli varsayılan; EmptyState için detail boşsa hazır) ———

  function normalizeDashboard(data, stateForFallback) {
    if (!data) return buildDashboardStub(stateForFallback || {});
    applyContractFallbacks("dashboard", data);
    data.metrics = Array.isArray(data.metrics) ? data.metrics : [];
    data.sections = Array.isArray(data.sections) ? data.sections : [];
    if (!data.sections[0]) data.sections[0] = { title: "Son Olaylar", events: [] };
    if (!data.sections[1]) data.sections[1] = { title: "Uyarılar ve notlar", warnings: [] };
    if (data.sections[1] && !Array.isArray(data.sections[1].warnings)) data.sections[1].warnings = [];
    return data;
  }

  function normalizeTasks(data, stateForFallback) {
    if (!data) return buildTasksStub(stateForFallback || {});
    applyContractFallbacks("tasks", data);
    data.filters = Array.isArray(data.filters) ? data.filters : TASK_FILTERS;
    data.listItems = Array.isArray(data.listItems) ? data.listItems : [];
    data.selectedTask = data.selectedTask != null ? data.selectedTask : null;
    data.listUpdated = data.listUpdated != null ? data.listUpdated : null;
    if (!data.emptyListTitle) data.emptyListTitle = "Bu filtrede görev yok";
    if (!data.emptyListDesc) data.emptyListDesc = EMPTY_DESC_DEFAULT;
    return data;
  }

  function normalizeSandbox(data, stateForFallback) {
    if (!data) return buildSandboxStub(stateForFallback || {});
    applyContractFallbacks("sandbox", data);
    data.metrics = Array.isArray(data.metrics) ? data.metrics : [];
    data.sections = Array.isArray(data.sections) ? data.sections : [];
    return data;
  }

  function normalizeConfig(data, stateForFallback) {
    if (!data) return buildConfigStub(stateForFallback || {});
    applyContractFallbacks("config", data);
    data.metrics = Array.isArray(data.metrics) ? data.metrics : [];
    data.sections = Array.isArray(data.sections) ? data.sections : [];
    return data;
  }

  function normalizeIdentity(data, stateForFallback) {
    if (!data) return buildIdentityStub(stateForFallback || {});
    applyContractFallbacks("identity", data);
    data.metrics = Array.isArray(data.metrics) ? data.metrics : [];
    data.sections = Array.isArray(data.sections) ? data.sections : [];
    return data;
  }

  function normalizeKeystore(data, stateForFallback) {
    if (!data) return buildKeystoreStub(stateForFallback || {});
    applyContractFallbacks("keystore", data);
    data.metrics = Array.isArray(data.metrics) ? data.metrics : [];
    data.sections = Array.isArray(data.sections) ? data.sections : [];
    return data;
  }

  function normalizeTrash(data, stateForFallback) {
    if (!data) return buildTrashStub(stateForFallback || {});
    applyContractFallbacks("trash", data);
    data.summaryMetrics = Array.isArray(data.summaryMetrics) ? data.summaryMetrics : [];
    data.listItems = Array.isArray(data.listItems) ? data.listItems : [];
    data.selectedItem = data.selectedItem != null ? data.selectedItem : null;
    if (!data.emptyDetailPlaceholder) data.emptyDetailPlaceholder = "Listeden bir öğe seçin.";
    return data;
  }

  function normalizeLogs(data, stateForFallback) {
    if (!data) return buildLogsStub(stateForFallback || {});
    applyContractFallbacks("logs", data);
    data.filters = Array.isArray(data.filters) ? data.filters : LOG_FILTERS;
    data.events = Array.isArray(data.events) ? data.events : [];
    data.logFileUpdated = data.logFileUpdated != null ? data.logFileUpdated : null;
    data.logLocation = data.logLocation != null ? data.logLocation : null;
    return data;
  }

  function normalizeSystem(data, stateForFallback) {
    if (!data) return buildSystemStub(stateForFallback || {});
    applyContractFallbacks("system", data);
    data.healthCards = Array.isArray(data.healthCards) ? data.healthCards : [];
    return data;
  }

  var LumosContracts = {
    CONTRACTS: CONTRACTS,
    PANEL_DATA_SCHEMA: CONTRACTS,
    SCREEN_KEYS: SCREEN_KEYS,
    applyContractFallbacks: applyContractFallbacks,
    EMPTY_DESC_DEFAULT: EMPTY_DESC_DEFAULT,
    TASK_FILTERS: TASK_FILTERS,
    LOG_FILTERS: LOG_FILTERS,
    formatTime: formatTime,
    filterTaskList: filterTaskList,
    buildDashboardStub: buildDashboardStub,
    buildTasksStub: buildTasksStub,
    buildSandboxStub: buildSandboxStub,
    buildConfigStub: buildConfigStub,
    buildIdentityStub: buildIdentityStub,
    buildKeystoreStub: buildKeystoreStub,
    buildTrashStub: buildTrashStub,
    buildLogsStub: buildLogsStub,
    buildSystemStub: buildSystemStub,
    normalizeDashboard: normalizeDashboard,
    normalizeTasks: normalizeTasks,
    normalizeSandbox: normalizeSandbox,
    normalizeConfig: normalizeConfig,
    normalizeIdentity: normalizeIdentity,
    normalizeKeystore: normalizeKeystore,
    normalizeTrash: normalizeTrash,
    normalizeLogs: normalizeLogs,
    normalizeSystem: normalizeSystem,
  };

  global.LumosContracts = LumosContracts;
})(typeof window !== "undefined" ? window : this);
