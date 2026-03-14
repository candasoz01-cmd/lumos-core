/**
 * Lumos Panel v1 — operatör paneli iskeleti.
 * Mock state, hash routing; backend entegrasyonu yok.
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

  // ——— Merkezi mock state ———
  var mockState = {
    mode: "offline",
    sandbox_mode: false,
    sandbox_source: "varsayılan",
    writing_base_dir: "canlı",
    guard_status: "KORUMA AKTİF",
    workspace_name: "lumos-core",
    branch_name: "kando/main",
    dev_mode: "DEV",
    base_path: ".lumos",
    task_list: [
      { id: "t1", title: "Panel iskeleti genişlet", status: "devam", updated: "2025-03-14T10:00:00" },
      { id: "t2", title: "Mock state birleştir", status: "bekliyor", updated: "2025-03-14T09:30:00" },
      { id: "t3", title: "README güncelle", status: "tamamlandı", updated: "2025-03-13T16:00:00" },
    ],
    recent_events: [
      { id: "e1", kind: "görev", text: "Görev t2 güncellendi", ts: "2025-03-14T10:05:00" },
      { id: "e2", kind: "sandbox", text: "Korumalı alan kapalı", ts: "2025-03-14T09:00:00" },
      { id: "e3", kind: "config", text: "config okundu", ts: "2025-03-14T08:55:00" },
    ],
    warnings: ["Mock veri; canlı bağlantı yok."],
    trash_items: [
      { id: "tr1", name: "eski_tasks_backup.json", moved_at: "2025-03-12T14:00:00" },
    ],
    trash_location: ".lumos/trash",
    trash_last_move: "2025-03-12T14:00:00",
    config_snapshot: { profil: "guvenli_yurut", workspace_root: ".lumos" },
    config_write_ok: true,
    identity_state: "mevcut değil",
    identity_last_write: "—",
    keystore_state: "Kilitli",
    keystore_last_update: "—",
    system_health: {
      workspace_contract: "ok",
      task_engine: "ok",
      sandbox_source: "ok",
      trash_contract: "ok",
      config_sink: "ok",
      identity_sink: "ok",
      keystore_sink: "ok",
    },
    selected_task_id: null,
    selected_trash_id: null,
    log_filter: "all",
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

  function getBadgeVariant(key) {
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
    return v[key] || "badge-mode";
  }

  function getBadgeLabel(key, value) {
    if (key === "mode") return value === "online" ? "CANLI" : "Çevrimdışı";
    if (key === "lock") return value === "LOCKED" ? "KORUMA AKTİF" : "Açık";
    if (key === "sandbox") return "KORUMALI ALAN";
    return value;
  }

  // ——— Ortak bileşenler (factory) ———
  function ViewHeader(title, subtitle) {
    var sub = subtitle ? '<p class="view-subtitle">' + subtitle + "</p>" : "";
    return '<div class="view-header"><h1>' + title + "</h1>" + sub + "</div>";
  }

  function EmptyState(title, desc) {
    title = title || "Henüz veri yok";
    desc = desc || "Bu bölüm panel iskeletine bağlıdır; canlı entegrasyon sonraki aşamada açılacaktır.";
    return (
      '<div class="empty-state">' +
      '<p class="empty-title">' + title + "</p>" +
      '<p class="empty-desc">' + desc + "</p>" +
      "</div>"
    );
  }

  function StatusBadge(label, variant) {
    var cls = "badge " + (variant || getBadgeVariant(label));
    return '<span class="' + cls + '">' + label + "</span>";
  }

  function MetricCard(title, value, techNote) {
    var note = techNote ? '<p class="text-muted-small">' + techNote + "</p>" : "";
    return (
      '<div class="metric-card">' +
      '<div class="metric-title">' + title + "</div>" +
      '<div class="metric-value">' + value + "</div>" +
      note +
      "</div>"
    );
  }

  function SectionCard(title, bodyHtml) {
    return (
      '<div class="section-card">' +
      '<h2 class="section-title">' + title + "</h2>" +
      '<div class="section-body">' + bodyHtml + "</div>" +
      "</div>"
    );
  }

  function EventList(events) {
    if (!events || events.length === 0) return '<ul class="event-list"><li>—</li></ul>';
    var html = '<ul class="event-list">';
    for (var i = 0; i < events.length; i++) {
      var e = events[i];
      html +=
        "<li><span class=\"event-time\">" +
        formatTime(e.ts) +
        "</span> [" +
        e.kind +
        "] " +
        e.text +
        "</li>";
    }
    return html + "</ul>";
  }

  function DetailPanel(title, bodyHtml) {
    return (
      '<div class="detail-panel">' +
      '<div class="detail-title">' + title + "</div>" +
      '<div class="detail-body">' + bodyHtml + "</div>" +
      "</div>"
    );
  }

  // ——— Routing & UI güncelleme ———
  function getCurrentScreen() {
    var hash = (window.location.hash || DEFAULT_HASH).toLowerCase();
    if (hash.length <= 1) return SCREENS.dashboard;
    var id = hash.slice(1);
    if (SCREENS[id]) return SCREENS[id];
    return { id: "_empty", label: "", hash: hash };
  }

  function renderNav() {
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
  }

  function setTopbar() {
    var screen = getCurrentScreen();
    var titleEl = document.getElementById("topbar-pagetitle");
    if (titleEl) titleEl.textContent = screen.label || "—";
    var baseEl = document.getElementById("topbar-base-label");
    if (baseEl) baseEl.textContent = "Temel: " + (mockState.base_path || "—");
    var wrap = document.getElementById("topbar-badges");
    if (wrap) {
      var badges = [];
      badges.push(StatusBadge(getBadgeLabel("mode", mockState.mode)));
      badges.push(StatusBadge(getBadgeLabel("lock", mockState.keystore_state === "Kilitli" ? "LOCKED" : "UNLOCKED")));
      if (mockState.sandbox_mode) badges.push(StatusBadge("KORUMALI ALAN"));
      wrap.innerHTML = badges.join("");
    }
    var ws = document.getElementById("sidebar-workspace");
    if (ws) ws.textContent = "Çalışma Alanı: " + (mockState.workspace_name || "—");
    var meta = document.getElementById("sidebar-meta");
    if (meta) meta.textContent = "Dal: " + (mockState.branch_name || "—") + " · Mod: " + (mockState.dev_mode || "—");
  }

  // ——— Ekran renderları ———
  function renderDashboard() {
    var cards =
      MetricCard("Korumalı Alan Durumu", mockState.sandbox_mode ? "Açık" : "Kapalı") +
      MetricCard("Yazım Hedefi", mockState.writing_base_dir) +
      MetricCard("Koruma Durumu", mockState.guard_status) +
      MetricCard("Son Aktivite", formatTime(mockState.recent_events[0] ? mockState.recent_events[0].ts : "—"));
    var sections =
      SectionCard("Son Olaylar", EventList(mockState.recent_events)) +
      SectionCard("Uyarılar / Notlar", "<p>" + (mockState.warnings && mockState.warnings[0] ? mockState.warnings[0] : "—") + "</p>") +
      SectionCard("Hızlı Geçişler", '<p class="screen-placeholder">Görevler, Korumalı Alan, Kayıtlar için kısayollar (mock).</p>');
    return ViewHeader("Gösterge Paneli", "Tek bakışta sistem durumu") + '<div class="cards-grid">' + cards + "</div>" + sections;
  }

  function renderTasks() {
    var listHtml = "";
    mockState.task_list.forEach(function (t) {
      var sel = mockState.selected_task_id === t.id ? " selected" : "";
      listHtml += '<li class="list-item' + sel + '" data-task-id="' + t.id + '">' + t.title + " — " + t.status + "</li>";
    });
    var listSection = '<ul class="list-selectable" id="task-list">' + listHtml + "</ul>";
    var detail = mockState.selected_task_id
      ? (function () {
          var t = mockState.task_list.filter(function (x) {
            return x.id === mockState.selected_task_id;
          })[0];
          return t
            ? DetailPanel("Görev Detayı", "<p><strong>" + t.title + "</strong></p><p>Durum: " + t.status + "</p><p>Güncelleme: " + formatTime(t.updated) + "</p>")
            : DetailPanel("Görev Detayı", "<p>Seçili görev yok.</p>");
        })()
      : DetailPanel("Görev Detayı", "<p class=\"screen-placeholder\">Listeden bir görev seçin.</p>");
    return (
      ViewHeader("Görevler", "Görev motoru görünürlüğü") +
      SectionCard("Görev Listesi", listSection) +
      detail +
      SectionCard("Çalıştırma Notu", '<p class="screen-placeholder">İlgili test ve doğrulama notu burada gösterilir.</p>') +
      SectionCard("Filtre", '<p class="screen-placeholder">Durum, etiket, tarih filtreleri (mock).</p>')
    );
  }

  function renderSandbox() {
    var body =
      "<p><strong>Kaynak:</strong> " +
      (mockState.sandbox_source || "—") +
      " (CLI / ENV / varsayılan)</p>" +
      "<p><strong>Sandbox Base:</strong> " +
      (mockState.sandbox_mode ? "sandbox/" : "—") +
      "</p>" +
      "<p><strong>Yazım Yönü (Writing Direction):</strong> " +
      mockState.writing_base_dir +
      "</p>" +
      "<p><strong>Sözleşme Durumu (Contract Status):</strong> Tanımlı</p>" +
      "<p><strong>Çözümleme Mantığı:</strong> Kaynak önceliği CLI → ENV → varsayılan</p>" +
      "<p><strong>Guard Kuralı:</strong> Çekirdek state path’lere doğrudan yazılmaz.</p>";
    return (
      ViewHeader("Korumalı Alan", "Sandbox kaynağı ve yönlendirme görünürlüğü") +
      SectionCard("Kaynak (CLI / ENV / varsayılan)", "<p>" + mockState.sandbox_source + "</p>") +
      SectionCard("Sandbox Base", "<p>" + (mockState.sandbox_mode ? "sandbox/" : "Kapalı") + "</p>") +
      SectionCard("Writing Direction", "<p>" + mockState.writing_base_dir + "</p>") +
      SectionCard("Contract Status", "<p>Tanımlı</p><p class=\"text-muted-small\">Sandbox hedef dizini sözleşmesi</p>") +
      SectionCard("Çözümleme Mantığı", "<p>CLI → ENV → varsayılan</p>") +
      SectionCard("Guard Kuralı", "<p>Çekirdek state alanlarına doğrudan overwrite yapılmaz.</p>")
    );
  }

  function renderConfig() {
    var cfg = mockState.config_snapshot || {};
    var summary = "<p>Profil: " + (cfg.profil || "—") + "</p><p>Kök: " + (cfg.workspace_root || "—") + "</p>";
    return (
      ViewHeader("Yapılandırma", "Config görünürlüğü") +
      SectionCard("Mevcut Yapılandırma Özeti", summary + '<p class="text-muted-small">config.json</p>') +
      SectionCard("Yazım Durumu", "<p>" + (mockState.config_write_ok ? "Yazım uygun" : "Salt okunur") + "</p>") +
      SectionCard("Son Config Aktivitesi", "<p>" + formatTime(mockState.recent_events[2] ? mockState.recent_events[2].ts : "—") + " — config okundu</p>")
    );
  }

  function renderIdentity() {
    return (
      ViewHeader("Kimlik", "Identity durumu") +
      SectionCard("Identity Ready", "<p>" + mockState.identity_state + "</p>") +
      SectionCard("Son Yazım", "<p>" + mockState.identity_last_write + "</p>") +
      SectionCard("Hedef Kapsam", "<p class=\"screen-placeholder\">Kimlik yazım kapsamı (mock).</p>") +
      SectionCard("Guard Sonucu", "<p>Çekirdek güvenlik alanı; yetkisiz değişiklik yapılmaz.</p>")
    );
  }

  function renderKeystore() {
    return (
      ViewHeader("Anahtar Kasası", "Keystore durumu") +
      SectionCard("Hazır mı", "<p>" + (mockState.keystore_state === "Kilitli" ? "Hayır (kilitli)" : "Evet") + "</p>") +
      SectionCard("Şifreli Durum", "<p>" + mockState.keystore_state + "</p><p class=\"text-muted-small\">Passphrase gösterilmez.</p>") +
      SectionCard("Son Güncelleme", "<p>" + mockState.keystore_last_update + "</p>") +
      SectionCard("Yazım Kapsamı", "<p class=\"screen-placeholder\">Kilit açılmadan hassas yazım yapılmaz.</p>")
    );
  }

  function renderTrash() {
    var listHtml = "";
    (mockState.trash_items || []).forEach(function (item) {
      var sel = mockState.selected_trash_id === item.id ? " selected" : "";
      listHtml += '<li class="list-item' + sel + '" data-trash-id="' + item.id + '">' + item.name + " — " + formatTime(item.moved_at) + "</li>";
    });
    if (!listHtml) listHtml = "<li class=\"screen-placeholder\">Öğe yok</li>";
    var listSection = '<ul class="list-selectable" id="trash-list">' + listHtml + "</ul>";
    var detail = mockState.selected_trash_id
      ? (function () {
          var t = (mockState.trash_items || []).filter(function (x) {
            return x.id === mockState.selected_trash_id;
          })[0];
          return t ? DetailPanel("Seçilen öğe", "<p><strong>" + t.name + "</strong></p><p>Taşınma: " + formatTime(t.moved_at) + "</p>") : DetailPanel("Seçilen öğe", "<p>—</p>");
        })()
      : DetailPanel("Seçilen öğe", "<p class=\"screen-placeholder\">Listeden bir öğe seçin.</p>");
    return (
      ViewHeader("Silinenler", "Trash görünürlüğü") +
      SectionCard("Trash Location", "<p>" + mockState.trash_location + "</p>") +
      SectionCard("Son Taşıma", "<p>" + formatTime(mockState.trash_last_move) + "</p>") +
      MetricCard("Öğe Sayısı", String((mockState.trash_items || []).length)) +
      SectionCard("Scope", "<p>.lumos/trash — aktif state kaynağı değildir.</p>") +
      '<div class="split-view">' +
      SectionCard("Liste görünümü", listSection) +
      detail +
      "</div>"
    );
  }

  var LOG_FILTERS = [
    { id: "all", label: "Tümü" },
    { id: "tasks", label: "Görevler" },
    { id: "sandbox", label: "Korumalı Alan" },
    { id: "config", label: "Yapılandırma" },
    { id: "trash", label: "Silinenler" },
    { id: "identity", label: "Kimlik" },
    { id: "keystore", label: "Anahtar Kasası" },
    { id: "guard", label: "Koruma" },
  ];

  function renderLogs() {
    var filter = mockState.log_filter || "all";
    var events = mockState.recent_events || [];
    var filtered =
      filter === "all" ? events : events.filter(function (e) { return e.kind === filter; });
    var tabsHtml = LOG_FILTERS.map(function (f) {
      var active = f.id === filter ? " active" : "";
      return '<button type="button" class="log-tab' + active + '" data-log-filter="' + f.id + '">' + f.label + "</button>";
    }).join("");
    return (
      ViewHeader("Kayıtlar", "Olay akışı görünürlüğü") +
      '<div class="log-tabs" id="log-tabs">' + tabsHtml + "</div>" +
      SectionCard("Kayıt listesi", EventList(filtered))
    );
  }

  function renderSystem() {
    var h = mockState.system_health || {};
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
      mockState.selected_task_id = t.dataset.taskId;
      renderMain();
      return;
    }
    if (t.dataset && t.dataset.trashId) {
      mockState.selected_trash_id = t.dataset.trashId;
      renderMain();
      return;
    }
    if (t.dataset && t.dataset.logFilter) {
      mockState.log_filter = t.dataset.logFilter;
      renderMain();
    }
  }

  function refresh() {
    renderNav();
    setTopbar();
    renderMain();
  }

  function onHashChange() {
    refresh();
  }

  var main = document.getElementById("main-content");
  if (main) main.addEventListener("click", onMainClick);

  window.addEventListener("hashchange", onHashChange);
  if (!window.location.hash) {
    window.location.hash = DEFAULT_HASH;
  } else {
    refresh();
  }
})();
