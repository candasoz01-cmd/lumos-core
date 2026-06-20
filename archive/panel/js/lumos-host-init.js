/**
 * window.LUMOS_PANEL_KEYSTORE_UNLOCK — host köprüsü sözleşmesi
 *
 * BU REPO İÇİNDE gerçek (native) implementasyon YOK. Gerçek kilidi açan kod:
 *   src/core/lumos_runtime.py → unlock_with_passphrase (passphrase → FileKeyStore → lock_state.unlock)
 * Bu yalnızca CLI / Python sürecinde çalışır; panel statik JS bunu doğrudan çağıramaz.
 *
 * GEÇİCİ TEST: aşağıdaki mock (_lumosStub yok → host dalı). Üretimde host inject eder.
 * Sohbet: «kilit aç» → openUnlockModal (#unlock-pass); sonuç yalnızca chat’te (Kilit açıldı / açılamadı).
 */
(function (global) {
  "use strict";
  if (typeof global.LUMOS_PANEL_KEYSTORE_UNLOCK === "function") {
    return;
  }
  global.LUMOS_PANEL_KEYSTORE_UNLOCK = async function (pass) {
    if (pass === "1770") {
      return { ok: true };
    }
    return { ok: false };
  };
})(typeof window !== "undefined" ? window : this);
