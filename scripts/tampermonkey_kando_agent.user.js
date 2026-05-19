// ==UserScript==
// @name        Lumos Kando Agent (localhost bridge)
// @namespace   https://github.com/candasoz01-cmd/lumos-core
// @version     1.0.0
// @description ChatGPT / web: serbest metni POST /agent-run ile gönderir; raporu sayfaya yazar. GM_xmlhttpRequest ile mixed-content/CORS aşılır.
// @author      lumos-core
// @match       *://chatgpt.com/*
// @match       *://chat.openai.com/*
// @match       *://127.0.0.1/*
// @match       *://localhost/*
// @grant       GM_xmlhttpRequest
// @grant       GM_setValue
// @grant       GM_getValue
// @connect     127.0.0.1
// @connect     localhost
// @run-at      document-idle
// ==/UserScript==
//
// GERÇEKÇİLİK: Ağ/git/kimlik/merge hataları her zaman yazılımla "sıfırlanamaz".
// Bu script yeniden deneme + yedek agent-last ile başarı ORANINI maksimize eder.
//
(function () {
  "use strict";

  var BASE = GM_getValue("kando_bridge_base", "http://127.0.0.1:8765");
  var TOKEN = GM_getValue("kando_token", ""); // KANDO_BRIDGE_SECRET ile aynı
  /** Repo göreli yol; selected_target boşken file: satırı için kullanılır */
  var FILE_PATH = GM_getValue("kando_file_path", "");
  /** Öncelikli hedef dosya; boşsa FILE_PATH */
  var SELECTED_TARGET = GM_getValue("kando_selected_target", "");
  var POLL_MS = 600;
  var MAX_WAIT_MS = 600000;
  var REQ_RETRIES = 4;
  var REQ_RETRY_DELAY_MS = 800;
  var TASK_BASE = "http://127.0.0.1:8766";
  var TASK_TITLE_MAX = 120;

  function sleep(ms) {
    return new Promise(function (r) {
      setTimeout(r, ms);
    });
  }

  function gmRequest(method, url, body) {
    return new Promise(function (resolve, reject) {
      var headers = {};
      if (body != null) headers["Content-Type"] = "application/json; charset=utf-8";
      if (TOKEN) headers["X-Kando-Token"] = TOKEN;
      var attempt = 0;
      function run() {
        GM_xmlhttpRequest({
          method: method,
          url: url,
          data: body,
          headers: headers,
          timeout: 180000,
          onload: function (r) {
            resolve({ status: r.status, text: r.responseText || "" });
          },
          onerror: function () {
            attempt++;
            if (attempt < REQ_RETRIES) {
              sleep(REQ_RETRY_DELAY_MS * attempt).then(run);
            } else {
              reject(new Error("ağ: " + url));
            }
          },
          ontimeout: function () {
            attempt++;
            if (attempt < REQ_RETRIES) {
              sleep(REQ_RETRY_DELAY_MS * attempt).then(run);
            } else {
              reject(new Error("zaman aşımı: " + url));
            }
          },
        });
      }
      run();
    });
  }

  function parseJsonSafe(t) {
    try {
      return JSON.parse(t);
    } catch (e) {
      return null;
    }
  }

  /** "file: ... | task: ..." → "file: ...\ntask: ..." (köprü / patch_scope ile uyumlu) */
  function normalizePipeToNewline(s) {
    var g = String(s || "").trim();
    if (!g) return g;
    var m = g.match(/^\s*file:\s*(.+?)\s*\|\s*task:\s*([\s\S]+)\s*$/i);
    if (m) {
      return "file: " + m[1].trim() + "\n" + "task: " + m[2].trim();
    }
    return g;
  }

  function resolveTargetPath() {
    var st = String(SELECTED_TARGET || "").trim();
    if (st) return st;
    return String(FILE_PATH || "").trim();
  }

  /** file: / task: newline sözleşmesi; hedef: selected_target || filePath */
  function buildAgentGoalString(composerText) {
    var raw = normalizePipeToNewline(String(composerText || "").trim());
    if (!raw) return raw;
    var target = resolveTargetPath();
    var hasFileLine = /^file:\s*/im.test(raw);
    if (target) {
      if (hasFileLine) {
        return raw.replace(/^(\s*)file:\s*.*$/m, "$1file: " + target);
      }
      return "file: " + target + "\n" + "task: " + raw;
    }
    return raw;
  }

  async function fetchAgentLast() {
    var lastUrl = BASE.replace(/\/$/, "") + "/agent-last";
    var rl = await gmRequest("GET", lastUrl, null);
    if (rl.status !== 200) return null;
    return parseJsonSafe(rl.text);
  }

  /** Serbest metin → agent; job bitene kadar poll; başarısızlıkta agent-last dene */
  async function runAgent(goal) {
    var g = buildAgentGoalString(String(goal || "").trim());
    if (!g) throw new Error("boş goal");

    var runUrl = BASE.replace(/\/$/, "") + "/agent-run";
    var r0 = await gmRequest(
      "POST",
      runUrl,
      JSON.stringify({ goal: g })
    );
    if (r0.status < 200 || r0.status >= 300) {
      throw new Error("agent-run HTTP " + r0.status + " " + r0.text.slice(0, 400));
    }
    var started = parseJsonSafe(r0.text) || {};
    var jobId = started.job_id;
    if (!jobId) throw new Error("job_id yok: " + r0.text.slice(0, 300));

    var statusUrl = BASE.replace(/\/$/, "") + "/agent-status?id=" + encodeURIComponent(jobId);
    var t0 = Date.now();
    while (Date.now() - t0 < MAX_WAIT_MS) {
      var rs = await gmRequest("GET", statusUrl, null);
      if (rs.status === 200) {
        var doc = parseJsonSafe(rs.text);
        if (doc && (doc.phase === "done" || doc.status === "completed" || doc.status === "failed")) {
          if (doc.final_report) return doc.final_report;
          return doc;
        }
      }
      await sleep(POLL_MS);
    }

    var last = await fetchAgentLast();
    if (last) {
      last._note = "agent-status zaman aşımı; agent-last yedek okundu";
      return last;
    }
    throw new Error("agent zaman aşımı ve agent-last okunamadı");
  }

  function formatReport(rep) {
    if (!rep || typeof rep !== "object") return String(rep);
    var lines = [
      "### Kando agent raporu",
      "",
      "- **durum:** " + (rep.status || "—"),
      "- **hedef:** `" + (rep.selected_target || "—") + "`",
      "- **görev:** " + (rep.task || "—"),
      "- **dosyalar:** " + JSON.stringify(rep.changed_files || []),
      "- **verify:** " + JSON.stringify(rep.verify || {}),
      "- **commit:** " + JSON.stringify(rep.commit || {}),
      "- **push:** " + JSON.stringify(rep.push || {}),
      "- **sonraki:** " + (rep.next_focus || "—"),
      "- **hatalar:** " + JSON.stringify(rep.errors || []),
    ];
    if (rep._note) lines.push("- **not:** " + rep._note);
    return lines.join("\n");
  }

  function sendToTaskServer(title) {
    var t = String(title || "").trim().slice(0, TASK_TITLE_MAX);
    if (!t) return;
    try {
      GM_xmlhttpRequest({
        method: "POST",
        url: TASK_BASE + "/tasks",
        data: JSON.stringify({ title: t }),
        headers: { "Content-Type": "application/json; charset=utf-8" },
        timeout: 5000,
        onload: function () {},
        onerror: function () {},
        ontimeout: function () {},
      });
    } catch (_) {}
  }

  function findComposer() {
    return (
      document.querySelector("textarea[data-id='root']") ||
      document.querySelector("#prompt-textarea") ||
      document.querySelector("textarea[placeholder*='Message']") ||
      document.querySelector("div[contenteditable='true'][role='textbox']")
    );
  }

  function setComposerText(el, text) {
    if (!el) return;
    if (el.tagName === "TEXTAREA" || el.tagName === "INPUT") {
      el.focus();
      el.value = text;
      el.dispatchEvent(new Event("input", { bubbles: true }));
    } else {
      el.focus();
      el.innerText = text;
      el.dispatchEvent(new Event("input", { bubbles: true }));
    }
  }

  /** Sayfadaki metin kutusundaki metni agent’a gönderir, cevabı kutuya yazar (otomatik göndermez) */
  window.__KANDO_AGENT_RUN__ = async function () {
    var el = findComposer();
    var goal = "";
    if (el && (el.value != null || el.innerText != null)) {
      goal = (el.value || el.innerText || "").trim();
    }
    if (!goal) goal = window.prompt("Kando goal (serbest metin):", "");
    if (!goal) return;
    sendToTaskServer(goal);

    var rep;
    var errMsg = "";
    try {
      rep = await runAgent(goal);
    } catch (e) {
      errMsg = String(e && e.message ? e.message : e);
      try {
        var yedek = await fetchAgentLast();
        if (yedek) {
          yedek._note = "İstisna sonrası agent-last yedek: " + errMsg.slice(0, 500);
          rep = yedek;
        }
      } catch (_) {}
      if (!rep) {
        rep = {
          status: "failed",
          errors: [errMsg],
          task: goal,
          selected_target: "",
        };
      }
    }
    var md = formatReport(rep);
    setComposerText(findComposer(), md);
    return rep;
  };

  /* Küçük yüzen: tıkla → composer’daki metni çalıştır */
  var bar = document.createElement("div");
  bar.style.cssText =
    "position:fixed;bottom:12px;right:12px;z-index:2147483647;font:12px system-ui;padding:8px 10px;background:#111;color:#eee;border-radius:8px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.4);max-width:280px;";
  bar.textContent = "Kando agent";
  bar.title = "Composer’daki metni /agent-run ile gönderir; raporu yazar. Köprü: " + BASE;
  bar.addEventListener("click", function () {
    window.__KANDO_AGENT_RUN__().catch(function (e) {
      alert("Kando: " + (e && e.message ? e.message : e));
    });
  });
  document.documentElement.appendChild(bar);
})();
