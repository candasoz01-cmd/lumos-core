/**
 * Lumos Panel v1 — Backend bridge (Phase 1).
 * Read-only: okunabilir kaynak varsa (window.__LUMOS_READ_STATE__) backend şeklini (snake_case) döner;
 * yoksa null → panel fixture/demo fallback kullanır.
 * Bridge çıktısı panel veri şekline fixtures.js map*PayloadToPanelData ile dönüştürülür (contract: js/contracts.js).
 * Kaynak: panel/scripts/read_backend_state.py.
 */
(function (global) {
  "use strict";

  function getReadState() {
    try {
      var s = global.__LUMOS_READ_STATE__;
      return s && typeof s === "object" ? s : null;
    } catch (_) {
      return null;
    }
  }

  function readBackendDashboardState() {
    var state = getReadState();
    if (!state || !state.dashboard || typeof state.dashboard.sandbox_mode === "undefined") return null;
    return state.dashboard;
  }

  function readBackendSandboxState() {
    var state = getReadState();
    if (!state || !state.sandbox || typeof state.sandbox.sandbox_mode === "undefined") return null;
    return state.sandbox;
  }

  /** Phase 2 ilk gerçek backend okuma hedefi: System ekranı. system_health sırası read_backend_state.py SYSTEM_HEALTH_KEYS ile uyumlu. */
  function readBackendSystemState() {
    var state = getReadState();
    if (!state || !state.system || !state.system.system_health) return null;
    return state.system;
  }

  function readBackendConfigState() {
    var state = getReadState();
    if (!state || !state.config || !state.config.config_snapshot) return null;
    return state.config;
  }

  function readBackendIdentityState() {
    var state = getReadState();
    if (!state || !state.identity || typeof state.identity.identity_guard_result === "undefined") return null;
    return state.identity;
  }

  function readBackendKeystoreState() {
    var state = getReadState();
    if (!state || !state.keystore || typeof state.keystore.keystore_ready === "undefined") return null;
    return state.keystore;
  }

  function readBackendTasksState() {
    var state = getReadState();
    if (!state || !state.tasks || !Array.isArray(state.tasks.task_list)) return null;
    return state.tasks;
  }

  function readBackendTrashState() {
    var state = getReadState();
    if (!state || !state.trash || !Array.isArray(state.trash.trash_items)) return null;
    return state.trash;
  }

  function readBackendLogsState() {
    var state = getReadState();
    if (!state || !state.logs || !Array.isArray(state.logs.log_items)) return null;
    return state.logs;
  }

  global.LumosBackendBridge = {
    readBackendDashboardState: readBackendDashboardState,
    readBackendSandboxState: readBackendSandboxState,
    readBackendSystemState: readBackendSystemState,
    readBackendConfigState: readBackendConfigState,
    readBackendIdentityState: readBackendIdentityState,
    readBackendKeystoreState: readBackendKeystoreState,
    readBackendTasksState: readBackendTasksState,
    readBackendTrashState: readBackendTrashState,
    readBackendLogsState: readBackendLogsState,
  };
})(typeof window !== "undefined" ? window : this);
