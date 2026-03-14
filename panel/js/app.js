/**
 * Lumos Panel v1 — iskelet; mock state, hash routing, placeholder ekranlar.
 * Gerçek API entegrasyonu yok.
 */

(function () {
  "use strict";

  // ——— Ekran haritası (Panel v1) ———
  var SCREENS = {
    dashboard: { id: "dashboard", label: "Dashboard", hash: "#dashboard" },
    tasks: { id: "tasks", label: "Görevler", hash: "#tasks" },
    sandbox: { id: "sandbox", label: "Sandbox durumu", hash: "#sandbox" },
    identity: { id: "identity", label: "Identity / Keystore", hash: "#identity" },
    config: { id: "config", label: "Config", hash: "#config" },
    trash: { id: "trash", label: "Trash / Silinenler", hash: "#trash" },
    logs: { id: "logs", label: "Logs / Activity", hash: "#logs" },
  };

  var DEFAULT_HASH = "#dashboard";

  // ——— Mock state (gerçek backend yok) ———
  var mockState = {
    mode: "offline",
    lock_status: "LOCKED",
    sandbox_active: false,
    tasks_count: 3,
    trash_count: 0,
    last_activity: "",
  };

  function getCurrentScreen() {
    var hash = (window.location.hash || DEFAULT_HASH).toLowerCase();
    if (hash.length <= 1) return SCREENS.dashboard;
    var id = hash.slice(1);
    return SCREENS[id] || SCREENS.dashboard;
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

  function setTopbarStatus() {
    var el = document.getElementById("topbar-status");
    if (!el) return;
    el.textContent =
      "Mock: " +
      mockState.mode +
      " | " +
      mockState.lock_status +
      (mockState.sandbox_active ? " | Sandbox açık" : "");
  }

  // ——— Placeholder bileşenler (her ekran için kısa içerik) ———
  function renderDashboard() {
    return (
      '<h1>Dashboard</h1>' +
      '<p class="screen-placeholder">Özet bilgi alanı (mock).</p>' +
      "<ul>" +
      "<li>Mod: " +
      mockState.mode +
      "</li>" +
      "<li>Kilit: " +
      mockState.lock_status +
      "</li>" +
      "<li>Görev sayısı: " +
      mockState.tasks_count +
      "</li>" +
      "<li>Sandbox: " +
      (mockState.sandbox_active ? "Açık" : "Kapalı") +
      "</li>" +
      "</ul>"
    );
  }

  function renderTasks() {
    return (
      '<h1>Görevler</h1>' +
      '<p class="screen-placeholder">Görev listesi (mock).</p>' +
      "<ul><li>Örnek görev 1</li><li>Örnek görev 2</li><li>Örnek görev 3</li></ul>"
    );
  }

  function renderSandbox() {
    return (
      '<h1>Sandbox durumu</h1>' +
      '<p class="screen-placeholder">Sandbox açık/kapalı ve yazım hedefi (mock).</p>' +
      "<ul><li>Aktif: " +
      (mockState.sandbox_active ? "Evet" : "Hayır") +
      "</li><li>Yazım hedefi: " +
      (mockState.sandbox_active ? "sandbox/" : "canlı base") +
      "</li></ul>"
    );
  }

  function renderIdentity() {
    return (
      '<h1>Identity / Keystore</h1>' +
      '<p class="screen-placeholder">Kimlik ve keystore durumu (mock). Gerçek veri gösterilmez.</p>' +
      "<ul><li>Kimlik: mevcut değil (mock)</li><li>Keystore: kilitli (mock)</li></ul>"
    );
  }

  function renderConfig() {
    return (
      '<h1>Config</h1>' +
      '<p class="screen-placeholder">Ayarlar (mock).</p>' +
      "<ul><li>config.json placeholder</li><li>presence.json placeholder</li></ul>"
    );
  }

  function renderTrash() {
    return (
      '<h1>Trash / Silinenler</h1>' +
      '<p class="screen-placeholder">.lumos/trash içeriği (mock).</p>' +
      "<ul><li>Öğe sayısı: " + mockState.trash_count + "</li></ul>"
    );
  }

  function renderLogs() {
    return (
      '<h1>Logs / Activity</h1>' +
      '<p class="screen-placeholder">Son aktivite / log önizleme (mock).</p>' +
      "<ul><li>Son kayıt: " +
      (mockState.last_activity || "—") +
      "</li></ul>"
    );
  }

  var renderers = {
    dashboard: renderDashboard,
    tasks: renderTasks,
    sandbox: renderSandbox,
    identity: renderIdentity,
    config: renderConfig,
    trash: renderTrash,
    logs: renderLogs,
  };

  function renderMain() {
    var main = document.getElementById("main-content");
    if (!main) return;
    var screen = getCurrentScreen();
    var fn = renderers[screen.id];
    main.innerHTML = fn ? fn() : renderDashboard();
  }

  function refresh() {
    renderNav();
    setTopbarStatus();
    renderMain();
  }

  function onHashChange() {
    refresh();
  }

  window.addEventListener("hashchange", onHashChange);
  if (!window.location.hash) {
    window.location.hash = DEFAULT_HASH;
  } else {
    refresh();
  }
})();
