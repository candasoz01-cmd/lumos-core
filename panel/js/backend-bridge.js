/**
 * Lumos Panel v1 — Backend bridge (Phase 1).
 * Gerçek veri okuma giriş noktaları. Bugün no-op; yarın fetch/API buradan bağlanacak.
 * Sadece Dashboard, Sandbox, System ekranları için.
 */
(function (global) {
  "use strict";

  function readBackendDashboardState() {
    // Gerçek entegrasyonda: API'den dashboard ham verisi (backend payload şeklinde) dönecek.
    return null;
  }

  function readBackendSandboxState() {
    // Gerçek entegrasyonda: API/workspace_contract'tan sandbox durumu.
    return null;
  }

  function readBackendSystemState() {
    // Gerçek entegrasyonda: API/startup_health benzeri sistem durumu.
    return null;
  }

  global.LumosBackendBridge = {
    readBackendDashboardState: readBackendDashboardState,
    readBackendSandboxState: readBackendSandboxState,
    readBackendSystemState: readBackendSystemState,
  };
})(typeof window !== "undefined" ? window : this);
