/**
 * Lumos Panel v1 — operatör paneli.
 * Veri adapter katmanı: ekranlar normalize veri ile beslenir; kaynak şu an mockState (backend yok).
 * Ortak bileşenler, hash routing. Gerçek API entegrasyonu sonraki aşamada adapter üzerinden eklenecek.
 */

(function () {
  "use strict";

  var DEFAULT_HASH = "#dashboard";

  var SCREENS = {
    dashboard: { id: "dashboard", label: "Gösterge Paneli", hash: "#dashboard" },
    tasks: { id: "tasks", label: "Görevler", hash: "#tasks" },
    sandbox: { id: "sandbox", label: "Korumalı Alan", hash: "#sandbox" },
    config: { id: "config", label: "Yapılandırma", hash: "#config" },
    identity: { id: "identity", label: "Kimlik", hash: "#identity" },
    keystore: { id: "keystore", label: "Anahtar Kasası", hash: "#keystore" },
    trash: { id: "trash", label: "Silinenler", hash: "#trash" },
    logs: { id: "logs", label: "Kayıtlar", hash: "#logs" },
    system: { id: "system", label: "Sistem Durumu", hash: "#system" },
  };

  var EMPTY_DESC_DEFAULT = "Mock veri; canlı entegrasyon sonraki aşamada açılacak.";
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
    selectedTaskId: null,
    selectedTrashId: null,
    logFilter: "all",
  };

  // ——— Yardımcılar ———
  function formatTime(s) {
    if (!s || s === "—") return "—";
    try {
      var d = new Date(s);
      return isNaN(d.getTime()) ? s : d.toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" });
    } catch (_) {
      return s;
    }
  }

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

  // ——— Veri adapter (tek kaynak: mockState; normalize çıktı) ———
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

  function filterTaskList(list, filterId) {
    if (!list) return [];
    if (filterId === "all") return list;
    var statusMap = { active: "aktif", pending: "bekleyen", completed: "tamamlandı", failed: "başarısız", blocked: "engellenen" };
    var status = statusMap[filterId];
    return status ? list.filter(function (t) { return t.status === status; }) : list;
  }

  function getDashboardData() {
    var lastEv = mockState.recentEvents && mockState.recentEvents[0] ? mockState.recentEvents[0] : null;
    var sandboxBadge = mockState.sandboxMode ? { label: "KORUMALI ALAN", variant: "badge-sandbox" } : null;
    return {
      title: "Gösterge Paneli",
      subtitle: "Sistem durumu özeti",
      metrics: [
        { title: "Korumalı Alan Durumu", value: mockState.sandboxMode ? " Açık" : "Kapalı", valueBadge: sandboxBadge, note: mockState.sandboxMode ? "Yazım sandbox dizinine yönlendiriliyor; canlıya overwrite yok." : "Yazım doğrudan çalışma alanına gidiyor." },
        { title: "Yazım Hedefi", value: mockState.writingBaseDir, note: mockState.writingBaseDir === "canlı" ? "Tüm yazma işlemleri çalışma alanına gidiyor." : "Yazma işlemleri sandbox base'e yönlendiriliyor." },
        { title: "Koruma Durumu", valueBadge: { label: mockState.guardStatus, variant: "badge-guard" }, note: "Çekirdek state path'ler guard ile korunuyor; sözleşme hedefi dışına yazılmaz." },
        { title: "Son Aktivite", value: lastEv ? formatTime(lastEv.ts) : "—", note: lastEv ? (lastEv.text || "—") : "Henüz kayıt yok." },
      ],
      sections: [
        { title: "Son Olaylar", events: mockState.recentEvents },
        { title: "Uyarılar ve notlar", warnings: mockState.warnings },
        { title: "Hızlı geçişler", links: true },
      ],
    };
  }

  function getTasksData() {
    var filter = mockState.taskFilter || "all";
    var list = mockState.taskList || [];
    var filtered = filterTaskList(list, filter);
    var selected = mockState.selectedTaskId ? list.filter(function (x) { return x.id === mockState.selectedTaskId; })[0] : null;
    return {
      title: "Görevler",
      subtitle: "Liste, detay ve guard sonucu",
      filters: TASK_FILTERS,
      activeFilter: filter,
      listItems: filtered,
      selectedId: mockState.selectedTaskId,
      selectedTask: selected,
      emptyListTitle: "Bu filtrede görev yok",
      emptyListDesc: "Farklı filtre seçin. " + EMPTY_DESC_DEFAULT,
      detailTitle: "Görev Detayı",
      runNoteTitle: "Çalıştırma notu",
      runNoteBody: "Son çalıştırma ve guard sonucu yukarıdaki detayda. Canlı entegrasyonda test notu burada doldurulacak.",
    };
  }

  function getSandboxData() {
    var m = mockState;
    var contractBadge = m.sandboxMode ? { label: "KORUMALI ALAN", variant: "badge-sandbox" } : null;
    return {
      title: "Korumalı Alan",
      subtitle: "Yazım hedefi ve sandbox durumu",
      metrics: [
        { title: "Kaynak", value: m.sandboxSource || "varsayılan", note: "Öncelik: CLI → ENV → varsayılan. Şu an: " + (m.sandboxSource || "varsayılan") + "." },
        { title: "Sandbox Base", value: m.sandboxMode ? ".lumos/sandbox veya sözleşmeyle tanımlı base" : "— (korumalı alan kapalı)", note: m.sandboxMode ? "Korumalı alan açıkken tüm yazım bu dizine yönlendirilir." : "Korumalı alan açıldığında sözleşmedeki base kullanılır." },
        { title: "Yazım Yönü", value: m.writingBaseDir, note: m.writingBaseDir === "canlı" ? "Yazım doğrudan çalışma alanına gidiyor." : "Yazım sandbox base'e yönlendiriliyor." },
        { title: "Sözleşme Durumu", value: m.sandboxMode ? " Sözleşme tanımlı" : "Canlı mod; sandbox sözleşmesi devre dışı.", valueBadge: contractBadge, note: "Sandbox hedef dizini workspace sözleşmesiyle sabit; yeni çöp/sandbox alanı oluşturulmaz." },
      ],
      sections: [
        { title: "Çözümleme Mantığı", body: "<p>Kaynak önceliği: <strong>CLI → ENV → varsayılan</strong>. Sistem kendi kafasına canlı hedef seçmez; yazma hedefi tek kaynaktan (canlı base veya sözleşmeyle tanımlı sandbox base) gelir.</p><p class=\"text-muted-small\">Resolution: single source of truth.</p>" },
        { title: "Guard Kuralı", body: "<p>Çekirdek state path'lere doğrudan overwrite yapılmaz. Yazma hedefi tek kaynaktan belirlenir. Canlı çekirdek ile sandbox hedefi ayrı tutulur.</p><p class=\"text-muted-small\">Core state: tasks, logs, trash, config, aliases.</p>" },
        { title: "Canlı çekirdek / sandbox hedef farkı", body: "<p><strong>Canlı:</strong> Doğrudan çalışma alanı (.lumos vb.).</p><p><strong>Sandbox:</strong> Tanımlı kopya alanı; deneme/geliştirme burada yapılır, canlıya overwrite yok.</p><p class=\"text-muted-small\">Sandbox aktifken çekirdek path'ler okuma için kullanılabilir; yazım yalnızca sandbox base'e.</p>" },
      ],
    };
  }

  function getConfigData() {
    var cfg = mockState.configSnapshot || {};
    var lastEv = mockState.recentEvents && mockState.recentEvents[2] ? mockState.recentEvents[2] : null;
    return {
      title: "Yapılandırma",
      subtitle: "Config özeti ve yazım durumu",
      metrics: [
        { title: "Mevcut Yapılandırma Özeti", value: (cfg.profil || "—") + " · " + (cfg.workspace_root || "—"), note: "config.json; profil ve workspace kökü." },
        { title: "Yazım Durumu", value: cfg.writeStatus || "—", note: "Config yazımları merkezi sink/guard hattı üzerinden geçer; sözleşme hedefi dışına yazılmaz." },
        { title: "Son Config Aktivitesi", value: cfg.lastActivity ? formatTime(cfg.lastActivity) : (lastEv ? formatTime(lastEv.ts) : "—"), note: cfg.lastActivityText || (lastEv ? lastEv.text : "—") },
      ],
      sections: [
        { title: "Sink / Guard hattı", body: "<p>Config yazımları <strong>merkezi sink/guard hattı</strong> üzerinden geçer. Çekirdek state path'ler (config, tasks, logs, trash, aliases) sözleşme ve guard ile korunur; hedef dışına yazım yapılmaz.</p><p class=\"text-muted-small\">Sink: tek giriş noktası; guard: hedef ve kapsam kontrolü.</p>" },
      ],
    };
  }

  function getIdentityData() {
    var m = mockState;
    return {
      title: "Kimlik",
      subtitle: "Kimlik durumu ve kapsam",
      metrics: [
        { title: "Kimlik hazır mı", value: m.identityState || "—", note: "Kimlik hattı sink/guard omurgasına bağlı; riskli işlemler panelden açılmaz." },
        { title: "Son Yazım", value: m.identityLastWrite ? formatTime(m.identityLastWrite) : "—", note: "Son kimlik yazım/zamanı (mock)." },
        { title: "Hedef Kapsam", value: m.identityTargetScope || "—", note: "Çekirdek kimlik alanı; yetki dışı değişiklik yapılmaz." },
        { title: "Guard Sonucu", value: m.identityGuardResult || "—", note: "Guard sonucu: kimlik alanı korunuyor." },
      ],
      sections: [
        { title: "Sink / Guard bağlantısı", body: "<p>Bu hattın <strong>sink/guard omurgasına</strong> bağlı olduğu bu ekrandan görünür. Kimlik alanı çekirdek güvenlik kapsamında; riskli işlemler açılmaz, sadece durum ve kapsam görünürlüğü sağlanır.</p><p class=\"text-muted-small\">Identity sink: tek giriş; guard: kapsam ve yetki kontrolü.</p>" },
      ],
    };
  }

  function getKeystoreData() {
    var m = mockState;
    return {
      title: "Anahtar Kasası",
      subtitle: "Durum görünürlüğü; anahtar ifşası yok",
      metrics: [
        { title: "Hazır mı", value: m.keystoreReady ? "Evet" : "Hayır (kilitli)", note: "Anahtar materyali ekranda açık gösterilmez; sadece durum ve akış görünürlüğü." },
        { title: "Şifreli Durum", value: m.keystoreState || "—", note: "Passphrase ve anahtar içeriği gösterilmez." },
        { title: "Son Güncelleme", value: m.keystoreLastUpdate ? formatTime(m.keystoreLastUpdate) : "—", note: "Son güncelleme zamanı (mock)." },
        { title: "Yazım Kapsamı", value: m.keystoreWriteScope || "—", note: "Kilit açılmadan hassas yazım yapılmaz." },
      ],
      sections: [
        { title: "Görünürlük ilkesi", body: "<p>Anahtar kasası ekranı <strong>durum ve akış görünürlüğü</strong> sağlar. Anahtar materyali (passphrase, key içeriği) açık gösterilmez; yalnızca hazır mı, şifreli durum, son güncelleme ve yazım kapsamı bilgisi gösterilir.</p><p class=\"text-muted-small\">Keystore sink: tek giriş; hassas veri panelde ifşa edilmez.</p>" },
      ],
    };
  }

  function getTrashData() {
    var items = mockState.trashItems || [];
    var selected = mockState.selectedTrashId ? items.filter(function (x) { return x.id === mockState.selectedTrashId; })[0] : null;
    return {
      title: "Silinenler",
      subtitle: "Çöp konumu ve liste",
      summaryMetrics: [
        { title: "Çöp Konumu", value: mockState.trashLocation },
        { title: "Son Taşıma", value: formatTime(mockState.trashLastMove) },
        { title: "Öğe Sayısı", value: String(items.length) },
        { title: "Kapsam", value: ".lumos/trash — aktif state kaynağı değildir" },
      ],
      listItems: items,
      selectedId: mockState.selectedTrashId,
      selectedItem: selected,
      detailTitle: "Seçilen öğe",
      emptyListTitle: "Çöp listesi boş",
      emptyListDesc: "Silinen öğe yok. " + EMPTY_DESC_DEFAULT,
      emptyDetailPlaceholder: "Listeden bir öğe seçin.",
    };
  }

  function getLogsData() {
    var filter = mockState.logFilter || "all";
    var list = mockState.logItems || [];
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
      sectionTitle: "Kayıt listesi",
    };
  }

  function getSystemStatusData() {
    var h = mockState.systemHealth || {};
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

  function getTopbarData() {
    var badges = [
      { label: getBadgeLabel("mode", mockState.appMode), variant: getBadgeVariant(getBadgeLabel("mode", mockState.appMode)) },
      { label: getBadgeLabel("lock", mockState.keystoreState === "Kilitli" ? "LOCKED" : "UNLOCKED"), variant: getBadgeVariant(getBadgeLabel("lock", mockState.keystoreState === "Kilitli" ? "LOCKED" : "UNLOCKED")) },
    ];
    if (mockState.sandboxMode) badges.push({ label: "KORUMALI ALAN", variant: "badge-sandbox" });
    return { basePath: mockState.basePath || "—", badges: badges };
  }

  function getSidebarData() {
    return { workspaceName: mockState.workspaceName || "—", branchName: mockState.branchName || "—" };
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

  // ——— Topbar (adapter verisi) ———
  function renderTopbar() {
    var screen = getCurrentScreen();
    var titleEl = document.getElementById("topbar-pagetitle");
    if (titleEl) titleEl.textContent = screen.label || "—";
    var data = getTopbarData();
    var baseEl = document.getElementById("topbar-base-label");
    if (baseEl) baseEl.textContent = "Temel: " + data.basePath;
    var wrap = document.getElementById("topbar-badges");
    if (wrap) {
      var html = "";
      for (var i = 0; i < data.badges.length; i++) html += buildBadge(data.badges[i].label, data.badges[i].variant);
      wrap.innerHTML = html;
    }
  }

  // ——— Routing ———
  function getCurrentScreen() {
    var hash = (window.location.hash || DEFAULT_HASH).toLowerCase();
    if (hash.length <= 1) return SCREENS.dashboard;
    var id = hash.slice(1);
    if (SCREENS[id]) return SCREENS[id];
    return { id: "_empty", label: "", hash: hash };
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
    var sections =
      buildSection("Son Olaylar", EventList(data.sections[0].events)) +
      buildSection("Uyarılar ve notlar", warningsHtml) +
      buildSection("Hızlı geçişler", '<p><a href="#tasks" class="inline-link">Görevler</a> · <a href="#sandbox" class="inline-link">Korumalı Alan</a> · <a href="#config" class="inline-link">Yapılandırma</a> · <a href="#logs" class="inline-link">Kayıtlar</a></p><p class="text-muted-small">Hash ile sayfa yenilenmeden geçiş.</p>');
    return ViewHeader(data.title, data.subtitle) + '<div class="cards-grid">' + cards + "</div>" + sections;
  }

  // ——— Ekran: Görevler (adapter + build) ———
  function renderTasks() {
    var data = getTasksData();
    var tabsHtml = data.filters.map(function (f) {
      var active = f.id === data.activeFilter ? " active" : "";
      return '<button type="button" class="log-tab task-filter-tab' + active + '" data-task-filter="' + f.id + '">' + f.label + "</button>";
    }).join("");
    var listBody = '<div class="task-filters" id="task-filters">' + tabsHtml + "</div>";
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

  // ——— Ekran: Silinenler (adapter + build) ———
  function renderTrash() {
    var data = getTrashData();
    var summary = buildMetricCards(data.summaryMetrics);
    var listSection;
    if (data.listItems.length === 0) {
      listSection = buildSection("Liste", buildEmptyState(data.emptyListTitle, data.emptyListDesc));
    } else {
      var listHtml = "";
      data.listItems.forEach(function (item) {
        var sel = data.selectedId === item.id ? " selected" : "";
        listHtml += '<li class="list-item' + sel + '" data-trash-id="' + item.id + '">' + (item.name || item.id) + " — " + formatTime(item.movedAt) + "</li>";
      });
      listSection = buildSection("Liste", '<ul class="list-selectable" id="trash-list">' + listHtml + "</ul>");
    }
    var detailBody = data.selectedItem
      ? buildDetailRows([
          { label: "Ad", value: data.selectedItem.name },
          { label: "Orijinal yol", value: data.selectedItem.originalPath },
          { label: "Çöp yolu", value: data.selectedItem.trashPath },
          { label: "Taşınma", value: formatTime(data.selectedItem.movedAt) },
          { label: "Kapsam", value: data.selectedItem.scope },
        ])
      : "<p class=\"screen-placeholder\">" + data.emptyDetailPlaceholder + "</p>";
    var detail = buildDetailPanel(data.detailTitle, detailBody);
    return ViewHeader(data.title, data.subtitle) + '<div class="cards-grid">' + summary + "</div>" + '<div class="split-view">' + listSection + detail + "</div>";
  }

  // ——— Ekran: Kayıtlar (adapter + build) ———
  function renderLogs() {
    var data = getLogsData();
    var tabsHtml = data.filters.map(function (f) {
      var active = f.id === data.activeFilter ? " active" : "";
      return '<button type="button" class="log-tab' + active + '" data-log-filter="' + f.id + '">' + f.label + "</button>";
    }).join("");
    return ViewHeader(data.title, data.subtitle) + '<div class="log-tabs" id="log-tabs">' + tabsHtml + "</div>" + buildSection(data.sectionTitle, EventList(data.events));
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

  var renderers = {
    dashboard: renderDashboard,
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
    var t = e.target;
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
    if (t.dataset && t.dataset.logFilter) {
      mockState.logFilter = t.dataset.logFilter;
      renderMain();
    }
  }

  function refresh() {
    renderSidebar();
    renderTopbar();
    renderMain();
  }

  function onHashChange() {
    refresh();
  }

  var mainEl = document.getElementById("main-content");
  if (mainEl) mainEl.addEventListener("click", onMainClick);

  window.addEventListener("hashchange", onHashChange);
  if (!window.location.hash) {
    window.location.hash = DEFAULT_HASH;
  } else {
    refresh();
  }
})();
