/**
 * Lumos Panel v1 — Backend bridge (Phase 1).
 * Read-only source bridge: okunabilir kaynak varsa (window.__LUMOS_READ_STATE__) döner;
 * yoksa null → panel fixture/demo fallback kullanır.
 * Sadece Dashboard, Sandbox, System ekranları.
 * Kaynak: panel/scripts/read_backend_state.py (workspace_contract + consent_ok).
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

  function readBackendSystemState() {
    var state = getReadState();
    if (!state || !state.system || !state.system.system_health) return null;
    return state.system;
  }

  global.LumosBackendBridge = {
    readBackendDashboardState: readBackendDashboardState,
    readBackendSandboxState: readBackendSandboxState,
    readBackendSystemState: readBackendSystemState,
  };
})(typeof window !== "undefined" ? window : this);
