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

  // ——— Mock state helper'ları ———
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

  // ——— Ekran: Gösterge Paneli (ortak bileşenler) ———
  function renderDashboard() {
    var lastEv = mockState.recentEvents && mockState.recentEvents[0] ? mockState.recentEvents[0] : null;
    var sandboxValue = mockState.sandboxMode
      ? StatusBadge("KORUMALI ALAN") + " Açık"
      : "Kapalı";
    var sandboxNote = mockState.sandboxMode
      ? "Yazım sandbox dizinine yönlendiriliyor; canlıya overwrite yok."
      : "Yazım doğrudan çalışma alanına gidiyor.";
    var guardValue = StatusBadge(mockState.guardStatus) + " " + mockState.guardStatus;
    var guardNote = "Çekirdek state path'ler guard ile korunuyor; sözleşme hedefi dışına yazılmaz.";
    var writingNote = mockState.writingBaseDir === "canlı"
      ? "Tüm yazma işlemleri çalışma alanına gidiyor."
      : "Yazma işlemleri sandbox base'e yönlendiriliyor.";
    var activityValue = lastEv ? formatTime(lastEv.ts) : "—";
    var activityNote = lastEv ? (lastEv.text || "—") : "Henüz kayıt yok.";
    var cards = renderMetricCards([
      { title: "Korumalı Alan Durumu", value: sandboxValue, techNote: sandboxNote },
      { title: "Yazım Hedefi", value: mockState.writingBaseDir, techNote: writingNote },
      { title: "Koruma Durumu", value: guardValue, techNote: guardNote },
      { title: "Son Aktivite", value: activityValue, techNote: activityNote },
    ]);
    var warningsHtml = "";
    if (mockState.warnings && mockState.warnings.length > 0) {
      warningsHtml = "<ul class=\"event-list\">";
      for (var w = 0; w < mockState.warnings.length; w++) {
        warningsHtml += "<li>" + StatusBadge("UYARI", "badge-warning") + " " + mockState.warnings[w] + "</li>";
      }
      warningsHtml += "</ul>";
    } else {
      warningsHtml = "<p class=\"text-muted-small\">Aktif uyarı veya not yok.</p>";
    }
    var sections =
      renderSection("Son Olaylar", EventList(mockState.recentEvents)) +
      renderSection("Uyarılar / Notlar", warningsHtml) +
      renderSection("Hızlı Geçişler", '<p><a href="#tasks" class="inline-link">Görevler</a> · <a href="#sandbox" class="inline-link">Korumalı Alan</a> · <a href="#config" class="inline-link">Yapılandırma</a> · <a href="#logs" class="inline-link">Kayıtlar</a></p><p class="text-muted-small">Hash routing ile sayfa yenilenmeden geçiş.</p>');
    return ViewHeader("Gösterge Paneli", "Tek bakışta sistem durumu") + '<div class="cards-grid">' + cards + "</div>" + sections;
  }

  // ——— Ekran: Görevler (ViewHeader, SectionCard, DetailPanel, MetricCard, EmptyState) ———
  var TASK_FILTERS = [
    { id: "all", label: "Tümü" },
    { id: "active", label: "Aktif" },
    { id: "pending", label: "Bekleyen" },
    { id: "failed", label: "Başarısız" },
    { id: "blocked", label: "Engellenen" },
  ];

  function filterTaskList(list, filterId) {
    if (!list) return [];
    if (filterId === "all") return list;
    var statusMap = { active: "aktif", pending: "bekleyen", failed: "başarısız", blocked: "engellenen" };
    var status = statusMap[filterId];
    return status ? list.filter(function (t) { return t.status === status; }) : list;
  }

  function renderTasks() {
    var filter = mockState.taskFilter || "all";
    var filtered = filterTaskList(mockState.taskList, filter);
    var tabsHtml = TASK_FILTERS.map(function (f) {
      var active = f.id === filter ? " active" : "";
      return '<button type="button" class="log-tab task-filter-tab' + active + '" data-task-filter="' + f.id + '">' + f.label + "</button>";
    }).join("");
    var listBody = '<div class="task-filters" id="task-filters">' + tabsHtml + "</div>";
    if (filtered.length === 0) {
      listBody += renderEmptyState("Bu filtrede görev yok", "Farklı bir filtre seçin veya mock veriye yeni görev ekleyin.");
    } else {
      var listItems = "";
      filtered.forEach(function (t) {
        var sel = mockState.selectedTaskId === t.id ? " selected" : "";
        var badge = StatusBadge(t.status, getTaskStatusVariant(t.status));
        listItems += '<li class="list-item' + sel + '" data-task-id="' + t.id + '"><span class="task-list-badge">' + badge + "</span> " + t.title + "</li>";
      });
      listBody += '<ul class="list-selectable" id="task-list">' + listItems + "</ul>";
    }
    var listSection = renderSection("Görev Listesi", listBody);

    var selected = mockState.selectedTaskId
      ? mockState.taskList.filter(function (x) { return x.id === mockState.selectedTaskId; })[0]
      : null;
    var detailContent;
    if (!selected) {
      detailContent = EmptyState("Görev seçilmedi", "Listeden bir görev seçin; detay paneli güncellenecektir.");
    } else {
      var lastRunVal = selected.lastRun ? formatTime(selected.lastRun) : "—";
      var lastRunNote = selected.lastRun ? "Son çalıştırma zamanı (mock)." : "Henüz çalıştırılmadı.";
      var guardVal = selected.guardResult || "—";
      var guardNote = "Guard: izinli / reddedildi / engelli (profil veya hedef kapsamı).";
      var outVal = (selected.outputSummary || "—").slice(0, 120);
      if ((selected.outputSummary || "").length > 120) outVal += "…";
      var outNote = "Çıktı özeti; tam log kayıtlar ekranından görülebilir.";
      var metricRows = renderMetricCards([
        { title: "Son çalıştırma", value: lastRunVal, techNote: lastRunNote },
        { title: "Guard sonucu", value: guardVal, techNote: guardNote },
        { title: "Çıktı özeti", value: outVal, techNote: outNote },
      ]);
      detailContent =
        "<p><strong>" + selected.title + "</strong></p>" +
        "<p>Durum: " + StatusBadge(selected.status, getTaskStatusVariant(selected.status)) + " · Güncelleme: " + formatTime(selected.updated) + "</p>" +
        '<div class="detail-metrics">' + metricRows + "</div>";
    }
    var detail = DetailPanel("Görev Detayı", detailContent);

    var runNoteSection = renderSection("Çalıştırma Notu", "<p class=\"text-muted-small\">Seçilen görevin son çalıştırma ve guard sonucu yukarıdaki detay panelinde gösterilir. İlgili test ve doğrulama notu canlı entegrasyonda bu bölümde doldurulacaktır.</p>");

    return ViewHeader("Görevler", "Görev listesi, detay, son çalıştırma ve guard sonucu") + '<div class="split-view">' + listSection + detail + "</div>" + runNoteSection;
  }

  // ——— Ekran: Korumalı Alan (ortak bileşenler) ———
  function renderSandbox() {
    var sourceNote = "Öncelik: CLI → ENV → varsayılan. Şu an: " + (mockState.sandboxSource || "varsayılan") + ".";
    var sandboxBase = mockState.sandboxMode ? ".lumos/sandbox veya sözleşmeyle tanımlı base" : "— (korumalı alan kapalı)";
    var sandboxNote = mockState.sandboxMode ? "Korumalı alan açıkken tüm yazım bu dizine yönlendirilir." : "Korumalı alan açıldığında sözleşmedeki base kullanılır.";
    var dirValue = mockState.writingBaseDir;
    var dirNote = dirValue === "canlı" ? "Yazım doğrudan çalışma alanına gidiyor." : "Yazım sandbox base'e yönlendiriliyor.";
    var contractValue = mockState.sandboxMode ? StatusBadge("KORUMALI ALAN") + " Sözleşme tanımlı" : "Canlı mod; sandbox sözleşmesi devre dışı.";
    var contractNote = "Sandbox hedef dizini workspace sözleşmesiyle sabit; yeni çöp/sandbox alanı oluşturulmaz.";
    var topCards = renderMetricCards([
      { title: "Kaynak", value: mockState.sandboxSource || "varsayılan", techNote: sourceNote },
      { title: "Sandbox Base", value: sandboxBase, techNote: sandboxNote },
      { title: "Yazım Yönü (Writing Direction)", value: dirValue, techNote: dirNote },
      { title: "Sözleşme Durumu (Contract Status)", value: contractValue, techNote: contractNote },
    ]);
    var resolutionBody = "<p>Kaynak önceliği: <strong>CLI → ENV → varsayılan</strong>. Sistem kendi kafasına canlı hedef seçmez; yazma hedefi tek kaynaktan (canlı base veya sözleşmeyle tanımlı sandbox base) gelir.</p><p class=\"text-muted-small\">Resolution: single source of truth.</p>";
    var guardBody = "<p>Çekirdek state path'lere doğrudan overwrite yapılmaz. Yazma hedefi tek kaynaktan belirlenir. Canlı çekirdek ile sandbox hedefi ayrı tutulur.</p><p class=\"text-muted-small\">Core state: tasks, logs, trash, config, aliases.</p>";
    var diffBody = "<p><strong>Canlı:</strong> Doğrudan çalışma alanı (.lumos vb.).</p><p><strong>Sandbox:</strong> Tanımlı kopya alanı; deneme/geliştirme burada yapılır, canlıya overwrite yok.</p><p class=\"text-muted-small\">Sandbox aktifken çekirdek path'ler okuma için kullanılabilir; yazım yalnızca sandbox base'e.</p>";
    return (
      ViewHeader("Korumalı Alan", "Sandbox kararı ve yazım hedefi — tek bakışta nereye yazıldığı") +
      '<div class="cards-grid">' + topCards + "</div>" +
      renderSection("Çözümleme Mantığı", resolutionBody) +
      renderSection("Guard Kuralı", guardBody) +
      renderSection("Canlı çekirdek / sandbox hedef farkı", diffBody)
    );
  }

  // ——— Ekran: Yapılandırma (ortak bileşenler: ViewHeader, MetricCard, SectionCard) ———
  function renderConfig() {
    var cfg = mockState.configSnapshot || {};
    var summaryValue = (cfg.profil || "—") + " · " + (cfg.workspace_root || "—");
    var summaryNote = "config.json; profil ve workspace kökü.";
    var writeValue = cfg.writeStatus || "—";
    var writeNote = "Config yazımları merkezi sink/guard hattı üzerinden geçer; sözleşme hedefi dışına yazılmaz.";
    var lastActTs = cfg.lastActivity ? formatTime(cfg.lastActivity) : (mockState.recentEvents && mockState.recentEvents[2] ? formatTime(mockState.recentEvents[2].ts) : "—");
    var lastActText = cfg.lastActivityText || (mockState.recentEvents && mockState.recentEvents[2] ? mockState.recentEvents[2].text : "—");
    var lastActNote = lastActText;
    var topCards = renderMetricCards([
      { title: "Mevcut Yapılandırma Özeti", value: summaryValue, techNote: summaryNote },
      { title: "Yazım Durumu", value: writeValue, techNote: writeNote },
      { title: "Son Config Aktivitesi", value: lastActTs, techNote: lastActNote },
    ]);
    var sinkBody = "<p>Config yazımları <strong>merkezi sink/guard hattı</strong> üzerinden geçer. Çekirdek state path'ler (config, tasks, logs, trash, aliases) sözleşme ve guard ile korunur; hedef dışına yazım yapılmaz.</p><p class=\"text-muted-small\">Sink: tek giriş noktası; guard: hedef ve kapsam kontrolü.</p>";
    return (
      ViewHeader("Yapılandırma", "Config görünürlüğü — sink/guard hattı üzerinden yazım") +
      '<div class="cards-grid">' + topCards + "</div>" +
      renderSection("Sink / Guard hattı", sinkBody)
    );
  }

  // ——— Ekran: Kimlik (ortak bileşenler: ViewHeader, MetricCard, SectionCard) ———
  function renderIdentity() {
    var readyValue = mockState.identityState || "—";
    var readyNote = "Kimlik hattı sink/guard omurgasına bağlı; riskli işlemler panelden açılmaz.";
    var lastWriteValue = mockState.identityLastWrite ? formatTime(mockState.identityLastWrite) : "—";
    var lastWriteNote = "Son kimlik yazım/zamanı (mock).";
    var scopeValue = mockState.identityTargetScope || "—";
    var scopeNote = "Çekirdek kimlik alanı; yetki dışı değişiklik yapılmaz.";
    var guardValue = mockState.identityGuardResult || "—";
    var guardNote = "Guard sonucu: kimlik alanı korunuyor.";
    var topCards = renderMetricCards([
      { title: "Identity Ready", value: readyValue, techNote: readyNote },
      { title: "Son Yazım", value: lastWriteValue, techNote: lastWriteNote },
      { title: "Hedef Kapsam", value: scopeValue, techNote: scopeNote },
      { title: "Guard Sonucu", value: guardValue, techNote: guardNote },
    ]);
    var sinkBody = "<p>Bu hattın <strong>sink/guard omurgasına</strong> bağlı olduğu bu ekrandan görünür. Kimlik alanı çekirdek güvenlik kapsamında; riskli işlemler açılmaz, sadece durum ve kapsam görünürlüğü sağlanır.</p><p class=\"text-muted-small\">Identity sink: tek giriş; guard: kapsam ve yetki kontrolü.</p>";
    return (
      ViewHeader("Kimlik", "Identity durumu — sink/guard omurgasına bağlı görünürlük") +
      '<div class="cards-grid">' + topCards + "</div>" +
      renderSection("Sink / Guard bağlantısı", sinkBody)
    );
  }

  // ——— Ekran: Anahtar Kasası (ortak bileşenler: ViewHeader, MetricCard, SectionCard) ———
  function renderKeystore() {
    var readyValue = mockState.keystoreReady ? "Evet" : "Hayır (kilitli)";
    var readyNote = "Anahtar materyali ekranda açık gösterilmez; sadece durum ve akış görünürlüğü.";
    var encValue = mockState.keystoreState || "—";
    var encNote = "Passphrase ve anahtar içeriği gösterilmez.";
    var lastUpdValue = mockState.keystoreLastUpdate ? formatTime(mockState.keystoreLastUpdate) : "—";
    var lastUpdNote = "Son güncelleme zamanı (mock).";
    var writeScopeValue = mockState.keystoreWriteScope || "—";
    var writeScopeNote = "Kilit açılmadan hassas yazım yapılmaz.";
    var topCards = renderMetricCards([
      { title: "Hazır mı", value: readyValue, techNote: readyNote },
      { title: "Şifreli Durum", value: encValue, techNote: encNote },
      { title: "Son Güncelleme", value: lastUpdValue, techNote: lastUpdNote },
      { title: "Yazım Kapsamı", value: writeScopeValue, techNote: writeScopeNote },
    ]);
    var visibilityBody = "<p>Anahtar kasası ekranı <strong>durum ve akış görünürlüğü</strong> sağlar. Anahtar materyali (passphrase, key içeriği) açık gösterilmez; yalnızca hazır mı, şifreli durum, son güncelleme ve yazım kapsamı bilgisi gösterilir.</p><p class=\"text-muted-small\">Keystore sink: tek giriş; hassas veri panelde ifşa edilmez.</p>";
    return (
      ViewHeader("Anahtar Kasası", "Keystore durumu — durum ve akış görünürlüğü, anahtar ifşası yok") +
      '<div class="cards-grid">' + topCards + "</div>" +
      renderSection("Görünürlük ilkesi", visibilityBody)
    );
  }

  // ——— Ekran: Silinenler (ortak bileşenler: MetricCard, SectionCard, DetailPanel) ———
  function renderTrash() {
    var items = mockState.trashItems || [];
    var summary = renderMetricCards([
      { title: "Çöp Konumu", value: mockState.trashLocation },
      { title: "Son Taşıma", value: formatTime(mockState.trashLastMove) },
      { title: "Öğe Sayısı", value: String(items.length) },
      { title: "Kapsam", value: ".lumos/trash — aktif state kaynağı değildir" },
    ]);
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
    return ViewHeader("Silinenler", "Trash görünürlüğü") + '<div class="cards-grid">' + summary + "</div>" + '<div class="split-view">' + renderSection("Liste görünümü", listSection) + detail + "</div>";
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

  // ——— Ekran: Kayıtlar (ortak bileşenler: EventList, SectionCard) ———
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
    return ViewHeader("Kayıtlar", "Olay akışı görünürlüğü") + '<div class="log-tabs" id="log-tabs">' + tabsHtml + "</div>" + renderSection("Kayıt listesi", EventList(filtered));
  }

  // ——— Ekran: Sistem Durumu (ViewHeader, MetricCard, StatusBadge — hangi parça hazır / dikkat) ———
  function renderSystem() {
    var h = mockState.systemHealth || {};
    function healthCard(title, key) {
      var raw = h[key];
      if (!raw) return MetricCard(title, "—", "Veri yok.");
      var status = typeof raw === "string" ? raw : (raw.status || "—");
      var note = typeof raw === "string" ? "" : (raw.note || "");
      var value = StatusBadge(status, getHealthStatusVariant(status));
      return MetricCard(title, value, note);
    }
    var cards =
      healthCard("Workspace Contract", "workspace_contract") +
      healthCard("Task Engine", "task_engine") +
      healthCard("Sandbox Source", "sandbox_source") +
      healthCard("Trash Contract", "trash_contract") +
      healthCard("Config Sink", "config_sink") +
      healthCard("Identity Sink", "identity_sink") +
      healthCard("Keystore Sink", "keystore_sink") +
      healthCard("Genel Sağlık", "general");
    return ViewHeader("Sistem Durumu", "Hangi çekirdek parça hazır, hangisi dikkat istiyor — tek bakışta") + '<div class="cards-grid">' + cards + "</div>";
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
    main.innerHTML = fn ? fn() : renderEmptyState("Henüz veri yok", "Geçersiz sayfa. Kenar çubuğundan bir ekran seçin.");
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
