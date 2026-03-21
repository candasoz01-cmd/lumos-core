/**
 * Minimal policy gate for panel chat → görev motoru (hardcoded rules).
 * Mirrors src/policy/action_policy.py intent.
 */
(function (global) {
  "use strict";

  function normalizePolicyValue(v) {
    return v != null ? String(v).toLowerCase().trim() : "";
  }

  /** @param {string} action motor (create_task) veya kayıt kind (task_created) */
  function toPolicyCheckAction(action) {
    var a = normalizePolicyValue(action);
    if (a === "task_created") return "create_task";
    if (a === "task_completed") return "complete_task";
    if (a === "task_deleted") return "delete_task";
    return a;
  }

  /**
   * Politika eylemi → Kayıtlar / EventList kind ile aynı task_* kodu.
   * @param {string} action
   * @returns {string}
   */
  function toLogActionCode(action) {
    var a = normalizePolicyValue(action);
    if (a === "task_created" || a === "create_task") return "task_created";
    if (a === "task_completed" || a === "complete_task") return "task_completed";
    if (a === "task_deleted" || a === "delete_task") return "task_deleted";
    return action != null ? String(action).trim() : "";
  }

  /**
   * @param {string} action create_task | task_created | … (access_identity | access_keystore)
   * @param {{ online?: boolean, korumaAktif?: boolean, consent?: boolean }} context
   * @returns {{ allow: boolean, reason: string }}
   */
  function checkPolicy(action, context) {
    var pa = toPolicyCheckAction(action);
    var c = context || {};
    var online = !!c.online;
    var koruma = !!c.korumaAktif;
    var consent = !!c.consent;
    if (!online) {
      if (pa === "create_task" || pa === "complete_task" || pa === "delete_task") {
        return { allow: false, reason: "offline_mode" };
      }
    }
    if (koruma && pa === "delete_task") {
      return { allow: false, reason: "koruma_aktif_delete" };
    }
    if (!consent && (pa === "access_identity" || pa === "access_keystore")) {
      return { allow: false, reason: "consent_required" };
    }
    return { allow: true, reason: "" };
  }

  function capitalizeFirst(text) {
    if (!text) return "";
    return text.charAt(0).toUpperCase() + text.slice(1);
  }

  /**
   * Policy reason -> kullanıcı dili
   * Eski ve yeni reason kodlarını birlikte destekler.
   * @param {string} reason
   * @returns {string}
   */
  function mapPolicyReason(reason) {
    var r = normalizePolicyValue(reason);

    if (r === "offline" || r === "offline_mode") {
      return "sistem çevrimdışı";
    }

    if (
      r === "protection" ||
      r === "koruma_aktif" ||
      r === "koruma_aktif_delete"
    ) {
      return "koruma aktif";
    }

    if (r === "consent" || r === "consent_required") {
      return "kullanıcı onayı gerekiyor";
    }

    return "sebep bilinmiyor";
  }

  /**
   * Policy action -> kullanıcı dili
   * Kayıt kind (task_*) ile motor kodları (create_task) aynı eşlemede.
   * @param {string} action
   * @returns {string}
   */
  function mapPolicyAction(action) {
    var a = normalizePolicyValue(action);

    if (a === "task_created" || a === "create_task") {
      return "görev oluşturma";
    }

    if (a === "task_completed" || a === "complete_task") {
      return "görev tamamlama";
    }

    if (a === "task_deleted" || a === "delete_task") {
      return "görev silme";
    }

    if (a === "access_identity") {
      return "kimlik alanına erişim";
    }

    if (a === "access_keystore") {
      return "anahtar kasasına erişim";
    }

    return "işlem";
  }

  /**
   * Reason bazlı kısa yönlendirme
   * @param {string} reason
   * @returns {string}
   */
  function mapPolicySuggestion(reason) {
    var r = normalizePolicyValue(reason);

    if (r === "offline" || r === "offline_mode") {
      return "API bağlantısını kontrol et.";
    }

    if (
      r === "protection" ||
      r === "koruma_aktif" ||
      r === "koruma_aktif_delete"
    ) {
      return "Bu alan korumalı. İzinli yöntemle devam et.";
    }

    if (r === "consent" || r === "consent_required") {
      return "Önce kullanıcı onayı ver.";
    }

    return "";
  }

  /**
   * Kısa bildirim metni
   * Toast / badge / dar alanlar için
   * @param {string} action
   * @param {string} reason
   * @returns {string}
   */
  function formatPolicyBlockedShort(action, reason) {
    var actionText = capitalizeFirst(mapPolicyAction(action));
    var reasonText = capitalizeFirst(mapPolicyReason(reason));
    return actionText + " engellendi. " + reasonText + ".";
  }

  /**
   * Uzun bildirim metni
   * Detay paneli / modal / log detayı için
   * @param {string} action
   * @param {string} reason
   * @returns {string}
   */
  function formatPolicyBlockedDetail(action, reason) {
    var actionText = capitalizeFirst(mapPolicyAction(action));
    var reasonText = mapPolicyReason(reason);
    var suggestion = mapPolicySuggestion(reason);

    var text = actionText + " şu anda engellendi.\n";
    text += "Neden: " + reasonText + ".";

    if (suggestion) {
      text += "\nNe yapabilirsin: " + suggestion;
    }

    return text;
  }

  /**
   * Geriye dönük uyum için:
   * Eski kod formatPolicyBlockedMessage(...) çağırıyorsa bozulmasın.
   * @param {string} action
   * @param {string} reason
   * @returns {string}
   */
  function formatPolicyBlockedMessage(action, reason) {
    return formatPolicyBlockedDetail(action, reason);
  }

  function buildPolicyBlockedMessage(action, reason) {
    return formatPolicyBlockedDetail(action, reason);
  }

  /** @deprecated use buildPolicyBlockedMessage */
  function formatPolicyBlockedChatDisplay(action, reason) {
    return buildPolicyBlockedMessage(action, reason);
  }

  /** @deprecated */
  function userMessage(reason) {
    return formatPolicyBlockedMessage("unknown_action", reason);
  }

  global.LumosPolicyEngine = {
    checkPolicy: checkPolicy,
    toLogActionCode: toLogActionCode,
    userMessage: userMessage,
    normalizePolicyValue: normalizePolicyValue,
    mapPolicyReason: mapPolicyReason,
    mapPolicyAction: mapPolicyAction,
    mapPolicySuggestion: mapPolicySuggestion,
    formatPolicyBlockedShort: formatPolicyBlockedShort,
    formatPolicyBlockedDetail: formatPolicyBlockedDetail,
    buildPolicyBlockedMessage: buildPolicyBlockedMessage,
    formatPolicyBlockedMessage: formatPolicyBlockedMessage,
    formatPolicyBlockedChatDisplay: formatPolicyBlockedChatDisplay,
  };
})(typeof window !== "undefined" ? window : globalThis);
