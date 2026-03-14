/**
 * Lumos Panel v1 — Backend bridge (Phase 1).
 * Read-only source bridge: okunabilir kaynak varsa (window.__LUMOS_READ_STATE__) döner;
 * yoksa null → panel fixture/demo fallback kullanır.
 * Dashboard, Sandbox, System, Config, Identity, Keystore ekranları.
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

  global.LumosBackendBridge = {
    readBackendDashboardState: readBackendDashboardState,
    readBackendSandboxState: readBackendSandboxState,
    readBackendSystemState: readBackendSystemState,
    readBackendConfigState: readBackendConfigState,
    readBackendIdentityState: readBackendIdentityState,
    readBackendKeystoreState: readBackendKeystoreState,
  };
})(typeof window !== "undefined" ? window : this);
