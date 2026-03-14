/**
 * Lumos Panel v1 — Backend-benzeri payload fixture'ları ve panel contract'a mapper'lar.
 * Veri sözleşmesi: panel/js/contracts.js CONTRACTS tek kaynaktır; mapper çıktıları bu şemaya uyar.
 * Eksik alanlar normalizer'da (ve isteğe bağlı applyContractFallbacks) güvenli varsayılana çekilir.
 */
(function (global) {
  "use strict";

  var LC = typeof LumosContracts !== "undefined" ? LumosContracts : {};
  function applyFallback(screenKey, data) {
    if (data && LC.applyContractFallbacks) LC.applyContractFallbacks(screenKey, data);
    return data;
  }
  var formatTime = LC.formatTime || function (s) {
    if (!s || s === "—") return "—";
    try {
      var d = new Date(s);
      return isNaN(d.getTime()) ? s : d.toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" });
    } catch (_) { return s; }
  };
  var TASK_FILTERS = LC.TASK_FILTERS || [
    { id: "all", label: "Tümü" }, { id: "active", label: "Aktif" }, { id: "pending", label: "Bekleyen" },
    { id: "completed", label: "Tamamlandı" }, { id: "failed", label: "Başarısız" }, { id: "blocked", label: "Engellenen" },
  ];
  var LOG_FILTERS = LC.LOG_FILTERS || [
    { id: "all", label: "Tümü", kind: null }, { id: "tasks", label: "Görevler", kind: "görev" },
    { id: "sandbox", label: "Korumalı Alan", kind: "sandbox" }, { id: "config", label: "Yapılandırma", kind: "config" },
    { id: "trash", label: "Silinenler", kind: "trash" }, { id: "identity", label: "Kimlik", kind: "identity" },
    { id: "keystore", label: "Anahtar Kasası", kind: "keystore" }, { id: "guard", label: "Koruma", kind: "guard" },
  ];
  var EMPTY_DESC = LC.EMPTY_DESC_DEFAULT || "Mock veri; canlı entegrasyon sonraki aşamada açılacak.";

  function arr(x) { return Array.isArray(x) ? x : []; }
  function str(x) { return x != null && x !== "" ? String(x) : "—"; }
  function metric(title, value, note, valueBadge) {
    var m = { title: str(title), value: str(value), note: str(note) };
    if (valueBadge && (valueBadge.label || valueBadge.variant)) m.valueBadge = { label: valueBadge.label || "", variant: valueBadge.variant || "" };
    return m;
  }

  // ——— Backend-benzeri payload fixture'ları (snake_case / farklı yapı) ———
  var PAYLOAD_FIXTURES = {
    dashboard: {
      sandbox_mode: false,
      writing_base_dir: "canlı",
      guard_status: "KORUMA AKTİF",
      recent_events: [
        { id: "e1", kind: "görev", text: "Görev t2 güncellendi", ts: "2025-03-14T10:05:00" },
        { id: "e2", kind: "sandbox", text: "Korumalı alan kapalı", ts: "2025-03-14T09:00:00" },
      ],
      warnings: ["Fixture veri; canlı bağlantı yok."],
    },
    sandbox: {
      sandbox_mode: true,
      sandbox_source: "CLI",
      writing_base_dir: "sandbox",
    },
    config: {
      config_snapshot: {
        profil: "guvenli_yurut",
        workspace_root: ".lumos",
        write_status: "Yazım uygun",
        last_activity: "2025-03-14T08:55:00",
        last_activity_text: "config okundu",
      },
    },
    identity: {
      identity_state: "mevcut değil",
      identity_last_write: "2025-03-14T08:00:00",
      identity_target_scope: "çekirdek kimlik alanı",
      identity_guard_result: "Korunuyor",
    },
    keystore: {
      keystore_ready: false,
      keystore_state: "Kilitli",
      keystore_last_update: "2025-03-14T07:55:00",
      keystore_write_scope: "Kilit açılmadan hassas yazım yapılmaz",
    },
    trash: {
      trash_location: ".lumos/trash",
      trash_last_move: "2025-03-12T14:00:00",
      trash_scope_fallback_note: "original_path ve scope dosya sisteminden okunamadı; meta yoksa — gösterilir.",
      trash_items: [
        { id: "tr1", name: "eski_tasks_backup.json", original_path: ".lumos/tasks_backup.json", trash_path: ".lumos/trash/eski_tasks_backup.json", moved_at: "2025-03-12T14:00:00", scope: "tasks" },
        { id: "tr2", name: "notlar_eski.md", original_path: ".lumos/notlar_eski.md", trash_path: ".lumos/trash/notlar_eski.md", moved_at: "2025-03-11T11:00:00", scope: "notes" },
      ],
    },
    logs: {
      log_items: [
        { id: "L1", kind: "görev", text: "Görev t2 güncellendi", ts: "2025-03-14T10:05:00" },
        { id: "L2", kind: "sandbox", text: "Korumalı alan kapalı", ts: "2025-03-14T09:00:00" },
        { id: "L3", kind: "config", text: "config okundu", ts: "2025-03-14T08:55:00" },
      ],
      log_filter: "all",
      log_file_updated: "2025-03-14T10:05:00",
      log_updated_text: "Son güncelleme: 14.03.2025 10:05",
      log_location: ".lumos/logs/log.txt",
    },
    tasks: {
      task_list: [
        { id: "t1", title: "Panel iskeleti genişlet", status: "aktif", updated: "2025-03-14T10:00:00", last_run: "2025-03-14T10:05:00", guard_result: "İzinli", output_summary: "Panel bileşenleri güncellendi." },
        { id: "t2", title: "Mock state birleştir", status: "bekleyen", updated: "2025-03-14T09:30:00", last_run: null, guard_result: "—", output_summary: "—" },
        { id: "t3", title: "README güncelle", status: "tamamlandı", updated: "2025-03-13T16:00:00", last_run: "2025-03-13T16:00:00", guard_result: "İzinli", output_summary: "README güncellendi." },
      ],
      task_filter: "all",
      selected_task_id: null,
      list_updated: "2025-03-14T10:00:00",
      list_updated_text: "Son güncelleme: 14.03.2025 10:00",
      tasks_file_path: null,
    },
    system: {
      system_health: {
        workspace_contract: { status: "ok", note: "Sözleşme yüklü; çekirdek path'ler tanımlı." },
        task_engine: { status: "ok", note: "Görev motoru çalışıyor." },
        sandbox_source: { status: "ok", note: "Sandbox kaynağı çözümlendi." },
        trash_contract: { status: "ok", note: "Trash konumu sözleşmeyle sabit." },
        config_sink: { status: "ok", note: "Config sink yazım hattı hazır." },
        identity_sink: { status: "uyarı", note: "Kimlik mevcut değil." },
        keystore_sink: { status: "uyarı", note: "Keystore kilitli." },
        general: { status: "ok", note: "Çekirdek parçalar operasyonel; 2 uyarı." },
      },
    },
  };

  // ——— Mapper'lar: backend-benzeri payload → panel contract şekli (güvenli fallback) ———

  function mapDashboardPayloadToPanelData(payload) {
    if (!payload) return applyFallback("dashboard", { title: "Gösterge Paneli", subtitle: "Sistem durumu özeti", metrics: [], sections: [{ title: "Son Olaylar", events: [] }, { title: "Uyarılar ve notlar", warnings: [] }, { title: "Hızlı geçişler", links: true }] });
    var ev = arr(payload.recent_events);
    var lastEv = ev[0] || null;
    var sandboxBadge = payload.sandbox_mode ? { label: "KORUMALI ALAN", variant: "badge-sandbox" } : null;
    return applyFallback("dashboard", {
      title: "Gösterge Paneli",
      subtitle: "Sistem durumu özeti",
      metrics: [
        metric("Korumalı Alan Durumu", payload.sandbox_mode ? " Açık" : "Kapalı", payload.sandbox_mode ? "Yazım sandbox dizinine yönlendiriliyor." : "Yazım doğrudan çalışma alanına gidiyor.", sandboxBadge),
        metric("Yazım Hedefi", payload.writing_base_dir, payload.writing_base_dir === "canlı" ? "Tüm yazma işlemleri çalışma alanına gidiyor." : "Yazma işlemleri sandbox base'e yönlendiriliyor.", null),
        metric("Koruma Durumu", null, "Çekirdek state path'ler guard ile korunuyor.", { label: str(payload.guard_status), variant: "badge-guard" }),
        metric("Son Aktivite", lastEv ? formatTime(lastEv.ts) : "—", lastEv ? str(lastEv.text) : "Henüz kayıt yok.", null),
      ],
      sections: [
        { title: "Son Olaylar", events: ev, warnings: undefined, links: false },
        { title: "Uyarılar ve notlar", events: undefined, warnings: arr(payload.warnings), links: false },
        { title: "Hızlı geçişler", events: undefined, warnings: undefined, links: true },
      ],
    });
  }

  function mapSandboxPayloadToPanelData(payload) {
    if (!payload) return applyFallback("sandbox", { title: "Korumalı Alan", subtitle: "Yazım hedefi ve sandbox durumu", metrics: [], sections: [] });
    var badge = payload.sandbox_mode ? { label: "KORUMALI ALAN", variant: "badge-sandbox" } : null;
    return applyFallback("sandbox", {
      title: "Korumalı Alan",
      subtitle: "Yazım hedefi ve sandbox durumu",
      metrics: [
        metric("Kaynak", payload.sandbox_source, "Öncelik: CLI → ENV → varsayılan.", null),
        metric("Sandbox Base", payload.sandbox_mode ? ".lumos/sandbox veya sözleşmeyle tanımlı base" : "— (korumalı alan kapalı)", payload.sandbox_mode ? "Tüm yazım bu dizine yönlendirilir." : "Korumalı alan açıldığında sözleşmedeki base kullanılır.", null),
        metric("Yazım Yönü", payload.writing_base_dir, payload.writing_base_dir === "canlı" ? "Yazım doğrudan çalışma alanına gidiyor." : "Yazım sandbox base'e yönlendiriliyor.", null),
        metric("Sözleşme Durumu", payload.sandbox_mode ? " Sözleşme tanımlı" : "Canlı mod; sandbox sözleşmesi devre dışı.", "Sandbox hedef dizini workspace sözleşmesiyle sabit.", badge),
      ],
      sections: [
        { title: "Çözümleme Mantığı", body: "<p>Kaynak önceliği: <strong>CLI → ENV → varsayılan</strong>. Yazma hedefi tek kaynaktan gelir.</p>" },
        { title: "Guard Kuralı", body: "<p>Çekirdek state path'lere doğrudan overwrite yapılmaz. Core state: tasks, logs, trash, config, aliases.</p>" },
        { title: "Canlı çekirdek / sandbox hedef farkı", body: "<p><strong>Canlı:</strong> Doğrudan çalışma alanı.</p><p><strong>Sandbox:</strong> Tanımlı kopya alanı; canlıya overwrite yok.</p>" },
      ],
    });
  }

  function mapConfigPayloadToPanelData(payload) {
    if (!payload) return applyFallback("config", { title: "Yapılandırma", subtitle: "Config özeti ve yazım durumu", metrics: [], sections: [] });
    var cfg = payload.config_snapshot || {};
    var writeBadge = (cfg.write_status || "").indexOf("Uyarı") !== -1 ? { label: "UYARI", variant: "badge-warning" } : null;
    return applyFallback("config", {
      title: "Yapılandırma",
      subtitle: "Config özeti ve yazım durumu",
      metrics: [
        metric("Mevcut Yapılandırma Özeti", (cfg.profil || "—") + " · " + (cfg.workspace_root || "—"), "config.json; profil ve workspace kökü.", null),
        metric("Yazım Durumu", cfg.write_status, "Config yazımları merkezi sink/guard hattı üzerinden geçer.", writeBadge),
        metric("Son Config Aktivitesi", cfg.last_activity ? formatTime(cfg.last_activity) : "—", cfg.last_activity_text || "—", null),
      ],
      sections: [{ title: "Sink / Guard hattı", body: "<p>Config yazımları <strong>merkezi sink/guard hattı</strong> üzerinden geçer. Çekirdek state path'ler sözleşme ve guard ile korunur.</p>" }],
    });
  }

  function mapIdentityPayloadToPanelData(payload) {
    if (!payload) return applyFallback("identity", { title: "Kimlik", subtitle: "Kimlik durumu ve kapsam", metrics: [], sections: [] });
    return applyFallback("identity", {
      title: "Kimlik",
      subtitle: "Kimlik durumu ve kapsam",
      metrics: [
        metric("Kimlik hazır mı", payload.identity_state, "Kimlik hattı sink/guard omurgasına bağlı.", null),
        metric("Son Yazım", payload.identity_last_write ? formatTime(payload.identity_last_write) : "—", "Son kimlik yazım/zamanı.", null),
        metric("Hedef Kapsam", payload.identity_target_scope, "Çekirdek kimlik alanı; yetki dışı değişiklik yapılmaz.", null),
        metric("Guard Sonucu", payload.identity_guard_result, "Guard sonucu: kimlik alanı korunuyor.", null),
      ],
      sections: [{ title: "Sink / Guard bağlantısı", body: "<p>Kimlik alanı çekirdek güvenlik kapsamında; sadece durum ve kapsam görünürlüğü sağlanır.</p>" }],
    });
  }

  function mapKeystorePayloadToPanelData(payload) {
    if (!payload) return applyFallback("keystore", { title: "Anahtar Kasası", subtitle: "Durum görünürlüğü; anahtar ifşası yok", metrics: [], sections: [] });
    return applyFallback("keystore", {
      title: "Anahtar Kasası",
      subtitle: "Durum görünürlüğü; anahtar ifşası yok",
      metrics: [
        metric("Hazır mı", payload.keystore_ready ? "Evet" : "Hayır (kilitli)", "Anahtar materyali ekranda açık gösterilmez.", null),
        metric("Şifreli Durum", payload.keystore_state, "Passphrase ve anahtar içeriği gösterilmez.", null),
        metric("Son Güncelleme", payload.keystore_last_update ? formatTime(payload.keystore_last_update) : "—", "Son güncelleme zamanı.", null),
        metric("Yazım Kapsamı", payload.keystore_write_scope, "Kilit açılmadan hassas yazım yapılmaz.", null),
      ],
      sections: [{ title: "Görünürlük ilkesi", body: "<p>Anahtar kasası ekranı <strong>durum ve akış görünürlüğü</strong> sağlar. Hassas veri panelde ifşa edilmez.</p>" }],
    });
  }

  function mapTrashPayloadToPanelData(payload) {
    if (!payload) return applyFallback("trash", { title: "Silinenler", subtitle: "Çöp konumu ve liste", summaryMetrics: [], listItems: [], selectedId: null, selectedItem: null, detailTitle: "Seçilen öğe", emptyListTitle: "Çöp listesi boş", emptyListDesc: "Silinen öğe yok. " + EMPTY_DESC, emptyDetailPlaceholder: "Listeden bir öğe seçin.", trashItemCount: 0, trashDirExists: false });
    var items = arr(payload.trash_items).map(function (t) {
      return { id: t.id, name: t.name || t.id, originalPath: t.original_path || "—", trashPath: t.trash_path || "—", movedAt: t.moved_at || "—", scope: t.scope || "—" };
    });
    var trashItemCount = payload.trash_item_count != null ? payload.trash_item_count : items.length;
    var trashDirExists = payload.trash_dir_exists === true;
    var trashScopeFallbackNote = payload.trash_scope_fallback_note != null ? str(payload.trash_scope_fallback_note) : "";
    return applyFallback("trash", {
      title: "Silinenler",
      subtitle: "Çöp konumu ve liste",
      summaryMetrics: [
        { title: "Çöp Konumu", value: str(payload.trash_location) },
        { title: "Son Taşıma", value: formatTime(payload.trash_last_move) },
        { title: "Öğe Sayısı", value: String(trashItemCount) },
        { title: "Kapsam", value: ".lumos/trash — aktif state kaynağı değildir" },
      ],
      listItems: items,
      selectedId: null,
      selectedItem: null,
      detailTitle: "Seçilen öğe",
      emptyListTitle: "Çöp listesi boş",
      emptyListDesc: "Silinen öğe yok. " + EMPTY_DESC,
      emptyDetailPlaceholder: "Listeden bir öğe seçin.",
      trashItemCount: trashItemCount,
      trashDirExists: trashDirExists,
      trashScopeFallbackNote: trashScopeFallbackNote,
    });
  }

  function mapLogsPayloadToPanelData(payload) {
    if (!payload) return applyFallback("logs", { title: "Kayıtlar", subtitle: "Olay akışı", filters: LOG_FILTERS, activeFilter: "all", events: [], logFileUpdated: null, logUpdatedText: null, logLocation: null, sectionTitle: "Kayıt listesi", logLineCount: 0, logFileExists: false });
    var events = arr(payload.log_items).map(function (e) { return { id: e.id, kind: e.kind, text: e.text, ts: e.ts }; });
    var logLineCount = payload.log_line_count != null ? payload.log_line_count : events.length;
    var logFileExists = payload.log_file_exists === true;
    return applyFallback("logs", {
      title: "Kayıtlar",
      subtitle: "Olay akışı",
      filters: LOG_FILTERS,
      activeFilter: payload.log_filter || "all",
      events: events,
      logFileUpdated: payload.log_file_updated || null,
      logUpdatedText: payload.log_updated_text || null,
      logLocation: payload.log_location || null,
      sectionTitle: "Kayıt listesi",
      logLineCount: logLineCount,
      logFileExists: logFileExists,
    });
  }

  function mapTasksPayloadToPanelData(payload) {
    if (!payload) return applyFallback("tasks", { title: "Görevler", subtitle: "Liste, detay ve guard sonucu", filters: TASK_FILTERS, activeFilter: "all", listItems: [], selectedId: null, selectedTask: null, listUpdated: null, listUpdatedText: null, tasksFilePath: null, emptyListTitle: "Bu filtrede görev yok", emptyListDesc: EMPTY_DESC, detailTitle: "Görev Detayı", runNoteTitle: "Çalıştırma notu", runNoteBody: "Son çalıştırma ve guard sonucu yukarıdaki detayda." });
    var list = arr(payload.task_list).map(function (t) {
      return { id: t.id, title: t.title, status: t.status, updated: t.updated, lastRun: t.last_run != null ? t.last_run : null, guardResult: t.guard_result || "—", outputSummary: t.output_summary || "—" };
    });
    var selId = payload.selected_task_id || null;
    var sel = selId ? list.filter(function (x) { return x.id === selId; }) : [];
    var selected = sel[0] || null;
    var filter = payload.task_filter || "all";
    var statusForFilter = { all: null, active: "aktif", pending: "bekleyen", completed: "tamamlandı", failed: "başarısız", blocked: "engellenen" }[filter];
    var filtered = !statusForFilter ? list : list.filter(function (t) { return t.status === statusForFilter; });
    var listUpdated = payload.list_updated || null;
    var listUpdatedText = payload.list_updated_text || null;
    var tasksFilePath = payload.tasks_file_path || null;
    var taskCount = payload.task_count != null ? payload.task_count : list.length;
    var tasksFileExists = payload.tasks_file_exists === true;
    return applyFallback("tasks", {
      title: "Görevler",
      subtitle: "Liste, detay ve guard sonucu",
      filters: TASK_FILTERS,
      activeFilter: filter,
      listItems: filtered,
      selectedId: selId,
      selectedTask: selected,
      listUpdated: listUpdated,
      listUpdatedText: listUpdatedText,
      tasksFilePath: tasksFilePath,
      taskCount: taskCount,
      tasksFileExists: tasksFileExists,
      emptyListTitle: "Bu filtrede görev yok",
      emptyListDesc: "Farklı filtre seçin. " + EMPTY_DESC,
      detailTitle: "Görev Detayı",
      runNoteTitle: "Çalıştırma notu",
      runNoteBody: "Son çalıştırma ve guard sonucu yukarıdaki detayda.",
    });
  }

  /** System: Phase 2 ilk gerçek backend okuma hedefi; key sırası read_backend_state.py SYSTEM_HEALTH_KEYS ile uyumlu. system_paths / system_summary varsa ek kartlar. */
  function mapSystemPayloadToPanelData(payload) {
    if (!payload) return applyFallback("system", { title: "Sistem Durumu", subtitle: "Çekirdek parçaların durumu", healthCards: [] });
    var h = payload.system_health || {};
    var keys = [
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
    for (var i = 0; i < keys.length; i++) {
      var raw = h[keys[i].key];
      var status = !raw ? "—" : (typeof raw === "string" ? raw : str(raw.status));
      var note = !raw ? "Veri yok." : (typeof raw === "string" ? "" : str(raw.note));
      healthCards.push({ title: keys[i].title, status: status, note: note });
    }
    var paths = payload.system_paths;
    if (paths && typeof paths === "object") {
      var pathParts = [];
      if (paths.writing_base != null && paths.writing_base !== "") pathParts.push("Yazım: " + paths.writing_base);
      if (paths.trash != null && paths.trash !== "") pathParts.push("Trash: " + paths.trash);
      if (paths.sandbox_base != null && paths.sandbox_base !== "") pathParts.push("Sandbox: " + paths.sandbox_base);
      if (paths.config != null && paths.config !== "") pathParts.push("Config: " + paths.config);
      if (paths.logs != null && paths.logs !== "") pathParts.push("Logs: " + paths.logs);
      if (paths.tasks != null && paths.tasks !== "") pathParts.push("Görevler: " + paths.tasks);
      var pathNote = pathParts.length ? pathParts.join("\n") : "Veri yok.";
      healthCards.push({ title: "Çalışma yolları", status: pathParts.length ? "ok" : "—", note: pathNote });
    }
    var summary = payload.system_summary;
    if (summary && typeof summary === "object") {
      var cfg = summary.config_exists ? "var" : "yok";
      var tr = (summary.trash_item_count != null ? summary.trash_item_count : 0) + " öğe";
      var log = (summary.log_line_count != null ? summary.log_line_count : 0) + " satır";
      var task = (summary.task_count != null ? summary.task_count : 0) + " kayıt";
      var sumNote = "Config: " + cfg + ". Trash: " + tr + ". Log: " + log + ". Görevler: " + task + ".";
      healthCards.push({ title: "Çekirdek dosya özeti", status: "ok", note: sumNote });
    }
    return applyFallback("system", { title: "Sistem Durumu", subtitle: "Çekirdek parçaların durumu", healthCards: healthCards });
  }

  global.LumosFixtures = {
    payloads: PAYLOAD_FIXTURES,
    mapDashboardPayloadToPanelData: mapDashboardPayloadToPanelData,
    mapSandboxPayloadToPanelData: mapSandboxPayloadToPanelData,
    mapConfigPayloadToPanelData: mapConfigPayloadToPanelData,
    mapIdentityPayloadToPanelData: mapIdentityPayloadToPanelData,
    mapKeystorePayloadToPanelData: mapKeystorePayloadToPanelData,
    mapTrashPayloadToPanelData: mapTrashPayloadToPanelData,
    mapLogsPayloadToPanelData: mapLogsPayloadToPanelData,
    mapTasksPayloadToPanelData: mapTasksPayloadToPanelData,
    mapSystemPayloadToPanelData: mapSystemPayloadToPanelData,
  };
})(typeof window !== "undefined" ? window : this);
