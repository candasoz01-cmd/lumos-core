/**
 * Tek tuş agent akışı: POST /agent-run → job_id → /agent-status poll → final rapor.
 * Eski POST /task (legacy) bu dosyada kullanılmaz.
 */
"use strict";

var KANDO_AGENT_BASE =
  (typeof process !== "undefined" &&
    process.env &&
    process.env.KANDO_BRIDGE_URL &&
    process.env.KANDO_BRIDGE_URL.replace(/\/task\/?$/, "")) ||
  "http://127.0.0.1:8765";

function agentRunUrl() {
  return KANDO_AGENT_BASE.replace(/\/$/, "") + "/agent-run";
}
function agentStatusUrl(jobId) {
  return KANDO_AGENT_BASE.replace(/\/$/, "") + "/agent-status?id=" + encodeURIComponent(jobId);
}
function agentLastUrl() {
  return KANDO_AGENT_BASE.replace(/\/$/, "") + "/agent-last";
}

/**
 * @param {string} goal kullanıcı niyeti (serbest metin)
 * @param {{ url?: string, token?: string, pollMs?: number, maxWaitMs?: number }} [options]
 */
async function runAgentAndWaitReport(goal, options) {
  var base =
    (options && options.url) ||
    KANDO_AGENT_BASE.replace(/\/$/, "");
  var runUrl = base + "/agent-run";
  var statusBase = base + "/agent-status?id=";
  var lastUrl = base + "/agent-last";
  var headers = { "Content-Type": "application/json; charset=utf-8" };
  if (options && options.token) {
    headers["X-Kando-Token"] = options.token;
  }
  var pollMs = (options && options.pollMs) || 500;
  var maxWaitMs = (options && options.maxWaitMs) || 300000;

  var res = await fetch(runUrl, {
    method: "POST",
    headers: headers,
    body: JSON.stringify({
      goal: String(goal || "").trim(),
      auto_approve_safe: true,
    }),
  });
  if (!res.ok) {
    var errText = await res.text();
    throw new Error("agent-run failed: " + res.status + " " + errText);
  }
  var started = await res.json();
  var jobId = started.job_id;
  if (!jobId) throw new Error("agent-run: job_id yok");

  var t0 = Date.now();
  while (Date.now() - t0 < maxWaitMs) {
    var st = await fetch(statusBase + encodeURIComponent(jobId), {
      headers: options && options.token ? { "X-Kando-Token": options.token } : {},
    });
    if (st.ok) {
      var doc = await st.json();
      if (doc.phase === "done" || doc.status === "completed" || doc.status === "failed") {
        return doc.final_report || doc;
      }
    }
    await new Promise(function (r) {
      setTimeout(r, pollMs);
    });
  }

  var last = await fetch(lastUrl, {
    headers: options && options.token ? { "X-Kando-Token": options.token } : {},
  });
  if (last.ok) {
    return await last.json();
  }
  throw new Error("agent zaman aşımı ve agent-last okunamadı");
}

/**
 * Chat kutusuna yaz + isteğe bağlı otomatik gönder (ör. input.dispatchEvent).
 * @param {string} text
 * @param {{ chatInput?: HTMLElement, sendButton?: HTMLElement }} [hooks]
 */
function writeReportToChat(text, hooks) {
  var el =
    hooks && hooks.chatInput
      ? hooks.chatInput
      : typeof document !== "undefined"
        ? document.querySelector(
            'textarea[placeholder*="message"], textarea[data-testid="composer-input"], #chat-input'
          )
        : null;
  if (el) {
    el.value = (el.value ? el.value + "\n\n" : "") + text;
    el.dispatchEvent(new Event("input", { bubbles: true }));
  }
  var btn =
    hooks && hooks.sendButton
      ? hooks.sendButton
      : typeof document !== "undefined"
        ? document.querySelector('button[data-testid="send"], button[aria-label*="Send"]')
        : null;
  if (btn) btn.click();
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    runAgentAndWaitReport,
    writeReportToChat,
    agentRunUrl,
    agentStatusUrl,
    agentLastUrl,
  };
}
