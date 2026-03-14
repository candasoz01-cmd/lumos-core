/**
 * Lumos Panel v1 — operatör paneli.
 * Ortak bileşenler, merkezi mock state, hash routing. Backend entegrasyonu yok.
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

  var EMPTY_FALLBACK =
    '<div class="empty-state">' +
    '<p class="empty-title">Henüz veri yok</p>' +
    '<p class="empty-desc">Bu bölüm panel iskeletine bağlıdır; canlı entegrasyon sonraki aşamada açılacaktır.</p>' +
    "</div>";

  // ——— Merkezi mock state (tek kaynak) ———
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
    configSnapshot: { profil: "guvenli_yurut", workspace_root: ".lumos" },
    identityState: "mevcut değil",
    keystoreState: "Kilitli",
    systemHealth: {
      workspace_contract: "ok",
      task_engine: "ok",
      sandbox_source: "ok",
      trash_contract: "ok",
      config_sink: "ok",
      identity_sink: "ok",
      keystore_sink: "ok",
    },
    taskList: [
      { id: "t1", title: "Panel iskeleti genişlet", status: "devam", updated: "2025-03-14T10:00:00" },
      { id: "t2", title: "Mock state birleştir", status: "bekliyor", updated: "2025-03-14T09:30:00" },
      { id: "t3", title: "README güncelle", status: "tamamlandı", updated: "2025-03-13T16:00:00" },
    ],
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

  // ——— Ortak bileşenler (tekrar kullanılabilir) ———
  function ViewHeader(title, subtitle) {
    var sub = subtitle ? '<p class="view-subtitle">' + subtitle + "</p>" : "";
    return '<div class="view-header"><h1>' + title + "</h1>" + sub + "</div>";
  }

  function EmptyState(title, desc) {
    title = title || "Henüz veri yok";
    desc = desc || "Bu bölüm panel iskeletine bağlıdır; canlı entegrasyon sonraki aşamada açılacaktır.";
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

  // ——— Sidebar (sol menü) ———
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
    var ws = document.getElementById("sidebar-workspace");
    if (ws) ws.textContent = "Çalışma Alanı: " + (mockState.workspaceName || "—");
    var meta = document.getElementById("sidebar-meta");
    if (meta) meta.textContent = "Dal: " + (mockState.branchName || "—") + " · Mod: DEV";
  }

  // ——— Topbar (üst bar) ———
  function renderTopbar() {
    var screen = getCurrentScreen();
    var titleEl = document.getElementById("topbar-pagetitle");
    if (titleEl) titleEl.textContent = screen.label || "—";
    var baseEl = document.getElementById("topbar-base-label");
    if (baseEl) baseEl.textContent = "Temel: " + (mockState.basePath || "—");
    var wrap = document.getElementById("topbar-badges");
    if (wrap) {
      var badges = [];
      badges.push(StatusBadge(getBadgeLabel("mode", mockState.appMode)));
      badges.push(StatusBadge(getBadgeLabel("lock", mockState.keystoreState === "Kilitli" ? "LOCKED" : "UNLOCKED")));
      if (mockState.sandboxMode) badges.push(StatusBadge("KORUMALI ALAN"));
      wrap.innerHTML = badges.join("");
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

  // ——— Ekran: Gösterge Paneli ———
  function renderDashboard() {
    var cards =
      MetricCard("Korumalı Alan Durumu", mockState.sandboxMode ? "Açık" : "Kapalı") +
      MetricCard("Yazım Hedefi", mockState.writingBaseDir) +
      MetricCard("Koruma Durumu", mockState.guardStatus) +
      MetricCard("Son Aktivite", formatTime(mockState.recentEvents[0] ? mockState.recentEvents[0].ts : "—"));
    var sections =
      SectionCard("Son Olaylar", EventList(mockState.recentEvents)) +
      SectionCard("Uyarılar / Notlar", "<p>" + (mockState.warnings && mockState.warnings[0] ? mockState.warnings[0] : "—") + "</p>") +
      SectionCard("Hızlı Geçişler", '<p><a href="#tasks" class="inline-link">Görevler</a> · <a href="#sandbox" class="inline-link">Korumalı Alan</a> · <a href="#logs" class="inline-link">Kayıtlar</a></p><p class="text-muted-small">Hash linkleri (mock)</p>');
    return ViewHeader("Gösterge Paneli", "Tek bakışta sistem durumu") + '<div class="cards-grid">' + cards + "</div>" + sections;
  }

  // ——— Ekran: Görevler ———
  function renderTasks() {
    var listHtml = "";
    mockState.taskList.forEach(function (t) {
      var sel = mockState.selectedTaskId === t.id ? " selected" : "";
      listHtml += '<li class="list-item' + sel + '" data-task-id="' + t.id + '">' + t.title + " — " + t.status + "</li>";
    });
    var listSection = '<ul class="list-selectable" id="task-list">' + listHtml + "</ul>";
    var detail = mockState.selectedTaskId
      ? (function () {
          var t = mockState.taskList.filter(function (x) { return x.id === mockState.selectedTaskId; })[0];
          return t ? DetailPanel("Görev Detayı", "<p><strong>" + t.title + "</strong></p><p>Durum: " + t.status + "</p><p>Güncelleme: " + formatTime(t.updated) + "</p>") : DetailPanel("Görev Detayı", "<p>Seçili görev yok.</p>");
        })()
      : DetailPanel("Görev Detayı", "<p class=\"screen-placeholder\">Listeden bir görev seçin.</p>");
    return ViewHeader("Görevler", "Görev motoru görünürlüğü") + SectionCard("Görev Listesi", listSection) + detail + SectionCard("Çalıştırma Notu", '<p class="screen-placeholder">İlgili test ve doğrulama notu burada gösterilir.</p>') + SectionCard("Filtre", '<p class="screen-placeholder">Durum, etiket, tarih filtreleri (mock).</p>');
  }

  // ——— Ekran: Korumalı Alan ———
  function renderSandbox() {
    var sandboxBase = mockState.sandboxMode ? "sandbox/" : "—";
    return (
      ViewHeader("Korumalı Alan", "Sandbox kaynağı ve yönlendirme görünürlüğü") +
      SectionCard("Kaynak", "<p>CLI / ENV / varsayılan</p><p><strong>Şu an:</strong> " + (mockState.sandboxSource || "—") + "</p>") +
      SectionCard("Sandbox Base", "<p>" + sandboxBase + "</p><p class=\"text-muted-small\">Korumalı alan açıkken yazım hedefi</p>") +
      SectionCard("Yazım Yönü (Writing Direction)", "<p>" + mockState.writingBaseDir + "</p>") +
      SectionCard("Sözleşme Durumu (Contract Status)", "<p>Tanımlı</p><p class=\"text-muted-small\">Sandbox hedef dizini sözleşmesi</p>") +
      SectionCard("Çözümleme Mantığı", "<p>Kaynak önceliği: CLI → ENV → varsayılan. Sistem kendi kafasına canlı hedef seçmez.</p>") +
      SectionCard("Guard Kuralı", "<p>Çekirdek state path’lere doğrudan overwrite yapılmaz. Yazma hedefi tek kaynaktan (canlı base veya sözleşmeyle tanımlı sandbox base).</p>") +
      SectionCard("Canlı çekirdek / sandbox hedef dizin farkı", "<p>Canlı: doğrudan çalışma alanı. Sandbox: tanımlı kopya alanı; deneme/geliştirme burada yapılır, canlıya overwrite yok.</p><p class=\"text-muted-small\">Core state paths read-only when sandbox active.</p>")
    );
  }

  // ——— Ekran: Yapılandırma ———
  function renderConfig() {
    var cfg = mockState.configSnapshot || {};
    var summary = "<p>Profil: " + (cfg.profil || "—") + "</p><p>Kök: " + (cfg.workspace_root || "—") + "</p>";
    return ViewHeader("Yapılandırma", "Config görünürlüğü") + SectionCard("Mevcut Yapılandırma Özeti", summary + '<p class="text-muted-small">config.json</p>') + SectionCard("Yazım Durumu", "<p>Yazım uygun</p>") + SectionCard("Son Config Aktivitesi", "<p>" + formatTime(mockState.recentEvents[2] ? mockState.recentEvents[2].ts : "—") + " — config okundu</p>");
  }

  // ——— Ekran: Kimlik ———
  function renderIdentity() {
    return ViewHeader("Kimlik", "Identity durumu") + SectionCard("Identity Ready", "<p>" + mockState.identityState + "</p>") + SectionCard("Son Yazım", "<p>—</p>") + SectionCard("Hedef Kapsam", "<p class=\"screen-placeholder\">Kimlik yazım kapsamı (mock).</p>") + SectionCard("Guard Sonucu", "<p>Çekirdek güvenlik alanı; yetkisiz değişiklik yapılmaz.</p>");
  }

  // ——— Ekran: Anahtar Kasası ———
  function renderKeystore() {
    return ViewHeader("Anahtar Kasası", "Keystore durumu") + SectionCard("Hazır mı", "<p>" + (mockState.keystoreState === "Kilitli" ? "Hayır (kilitli)" : "Evet") + "</p>") + SectionCard("Şifreli Durum", "<p>" + mockState.keystoreState + "</p><p class=\"text-muted-small\">Passphrase gösterilmez.</p>") + SectionCard("Son Güncelleme", "<p>—</p>") + SectionCard("Yazım Kapsamı", "<p class=\"screen-placeholder\">Kilit açılmadan hassas yazım yapılmaz.</p>");
  }

  // ——— Ekran: Silinenler ———
  function renderTrash() {
    var items = mockState.trashItems || [];
    var summary =
      MetricCard("Trash Location", mockState.trashLocation) +
      MetricCard("Son Taşıma (Last Move)", formatTime(mockState.trashLastMove)) +
      MetricCard("Öğe Sayısı (Item Count)", String(items.length)) +
      MetricCard("Scope", ".lumos/trash — aktif state kaynağı değildir");
    var listHtml = "";
    items.forEach(function (item) {
      var sel = mockState.selectedTrashId === item.id ? " selected" : "";
      listHtml += '<li class="list-item' + sel + '" data-trash-id="' + item.id + '">' + (item.name || item.id) + " — " + formatTime(item.movedAt) + "</li>";
    });
    if (!listHtml) listHtml = "<li class=\"screen-placeholder\">Öğe yok</li>";
    var listSection = '<ul class="list-selectable" id="trash-list">' + listHtml + "</ul>";
    var selected = items.filter(function (x) { return x.id === mockState.selectedTrashId; })[0];
    var detailBody = selected
      ? "<p><strong>Name:</strong> " + (selected.name || "—") + "</p>" +
        "<p><strong>Original Path:</strong> " + (selected.originalPath || "—") + "</p>" +
        "<p><strong>Trash Path:</strong> " + (selected.trashPath || "—") + "</p>" +
        "<p><strong>Moved At:</strong> " + formatTime(selected.movedAt) + "</p>" +
        "<p><strong>Scope:</strong> " + (selected.scope || "—") + "</p>"
      : "<p class=\"screen-placeholder\">Listeden bir öğe seçin.</p>";
    var detail = DetailPanel("Seçilen öğe detayı", detailBody);
    return ViewHeader("Silinenler", "Trash görünürlüğü") + '<div class="cards-grid">' + summary + "</div>" + '<div class="split-view">' + SectionCard("Liste görünümü", listSection) + detail + "</div>";
  }

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

  // ——— Ekran: Kayıtlar ———
  function renderLogs() {
    var filter = mockState.logFilter || "all";
    var list = mockState.logItems || [];
    var kindForFilter = null;
    for (var fi = 0; fi < LOG_FILTERS.length; fi++) {
      if (LOG_FILTERS[fi].id === filter) { kindForFilter = LOG_FILTERS[fi].kind; break; }
    }
    var filtered = filter === "all" || !kindForFilter ? list : list.filter(function (e) { return e.kind === kindForFilter; });
    var tabsHtml = LOG_FILTERS.map(function (f) {
      var active = f.id === filter ? " active" : "";
      return '<button type="button" class="log-tab' + active + '" data-log-filter="' + f.id + '">' + f.label + "</button>";
    }).join("");
    return ViewHeader("Kayıtlar", "Olay akışı görünürlüğü") + '<div class="log-tabs" id="log-tabs">' + tabsHtml + "</div>" + SectionCard("Kayıt listesi", EventList(filtered));
  }

  // ——— Ekran: Sistem Durumu ———
  function renderSystem() {
    var h = mockState.systemHealth || {};
    var cards =
      MetricCard("Workspace Contract", h.workspace_contract || "—") +
      MetricCard("Task Engine", h.task_engine || "—") +
      MetricCard("Sandbox Source", h.sandbox_source || "—") +
      MetricCard("Trash Contract", h.trash_contract || "—") +
      MetricCard("Config Sink", h.config_sink || "—") +
      MetricCard("Identity Sink", h.identity_sink || "—") +
      MetricCard("Keystore Sink", h.keystore_sink || "—") +
      MetricCard("Genel Sağlık", "ok");
    return ViewHeader("Sistem Durumu", "Çekirdek teknik sağlık görünümü") + '<div class="cards-grid">' + cards + "</div>";
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
    main.innerHTML = fn ? fn() : EmptyState("Henüz veri yok", "Geçersiz sayfa. Kenar çubuğundan bir ekran seçin.");
  }

  // ——— Etkileşimler (delegation) ———
  function onMainClick(e) {
    var t = e.target;
    if (t.dataset && t.dataset.taskId) {
      mockState.selectedTaskId = t.dataset.taskId;
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
