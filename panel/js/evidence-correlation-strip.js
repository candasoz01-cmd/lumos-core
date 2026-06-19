/**
 * EC2-06 / EC2-08 — read-only evidence correlation strip (legacy + shared).
 * Journal read-only; istemci yazmaz. Astro panel.astro ile gruplama parity.
 */
(function (global) {
  "use strict";

  var EVIDENCE_BRIDGE_PAIR_MAX_MS = 60000;

  function parseEvidenceTsMs(ts) {
    var d = Date.parse(String(ts || ""));
    return Number.isNaN(d) ? 0 : d;
  }

  function evidenceTitlePreviewPrefixMatch(a, b) {
    var x = String(a || "").trim();
    var y = String(b || "").trim();
    if (!x || !y) return false;
    var px = x.slice(0, 20);
    var py = y.slice(0, 20);
    return x.startsWith(py) || y.startsWith(px) || px === py;
  }

  function evidenceSourceLabel(source) {
    var s = String(source || "");
    if (s === "panel_tasks_server") return "Panel";
    if (s === "kando_bridge") return "Köprü";
    if (s === "guard_audit") return "Koruma";
    if (s === "action_policy") return "Koruma";
    if (s === "task_engine") return "Motor";
    return s || "Kaynak";
  }

  function buildEvidenceUiGroup(primary, kind, label) {
    var ev = primary && typeof primary === "object" ? primary : {};
    var entityRef =
      ev.entity_ref && typeof ev.entity_ref === "object" ? ev.entity_ref : null;
    var entityId = entityRef && entityRef.id ? String(entityRef.id).trim() : "";
    var titlePreview =
      ev.payload_summary &&
      ev.payload_summary.title_preview != null &&
      String(ev.payload_summary.title_preview).trim()
        ? String(ev.payload_summary.title_preview).trim()
        : "";
    var continueKind = null;
    var canContinue = false;
    if (entityId) {
      continueKind = "task";
      canContinue = true;
    } else if (titlePreview && kind !== "guard") {
      continueKind = "chat";
      canContinue = true;
    } else if (kind === "guard") {
      continueKind = "info";
      canContinue = false;
    }
    return {
      ts: ev.ts != null ? String(ev.ts) : "",
      kind: kind,
      label: label,
      primaryEvent: ev,
      entityRefId: entityId || null,
      titlePreview: titlePreview || null,
      canContinue: canContinue,
      continueKind: continueKind,
    };
  }

  function groupEvidenceEventsForUi(events) {
    var list = Array.isArray(events) ? events.slice() : [];
    list.sort(function (a, b) {
      return parseEvidenceTsMs(b && b.ts) - parseEvidenceTsMs(a && a.ts);
    });
    var used = Object.create(null);
    var groups = [];
    var i;
    var j;

    function markUsed(idx) {
      used[String(idx)] = true;
    }
    function isUsed(idx) {
      return !!used[String(idx)];
    }

    for (i = 0; i < list.length; i++) {
      if (isUsed(i)) continue;
      var ev = list[i];
      if (!ev || typeof ev !== "object") {
        markUsed(i);
        continue;
      }
      var op = String(ev.operation || "");
      var phase = String(ev.phase || "");
      var source = String(ev.source || "");

      if (op === "bridge.task.post" && phase === "result") {
        var matchedAfter = null;
        for (j = i + 1; j < list.length; j++) {
          if (isUsed(j)) continue;
          var cand = list[j];
          if (!cand || String(cand.operation || "") !== "bridge.task.post") continue;
          if (String(cand.phase || "") !== "after") continue;
          var dt = Math.abs(parseEvidenceTsMs(ev.ts) - parseEvidenceTsMs(cand.ts));
          if (dt > EVIDENCE_BRIDGE_PAIR_MAX_MS) continue;
          var tp1 =
            ev.payload_summary && ev.payload_summary.title_preview != null
              ? String(ev.payload_summary.title_preview)
              : "";
          var tp2 =
            cand.payload_summary && cand.payload_summary.title_preview != null
              ? String(cand.payload_summary.title_preview)
              : "";
          if (tp1 && tp2 && !evidenceTitlePreviewPrefixMatch(tp1, tp2)) continue;
          matchedAfter = cand;
          markUsed(j);
          break;
        }
        var outcome = String(ev.outcome || "ok");
        var preview =
          ev.payload_summary && ev.payload_summary.title_preview != null
            ? String(ev.payload_summary.title_preview).trim()
            : "";
        var bridgeLabel =
          "Köprü: " +
          outcome +
          (preview ? " · " + preview : matchedAfter ? " · iletim" : "");
        groups.push(buildEvidenceUiGroup(ev, "bridge", bridgeLabel));
        markUsed(i);
        continue;
      }

      if (source === "panel_tasks_server" && phase === "after") {
        var mutation = ev.mutation != null ? String(ev.mutation) : "işlem";
        var panelOutcome = String(ev.outcome || "ok");
        groups.push(
          buildEvidenceUiGroup(ev, "panel", "Görev: " + mutation + " · " + panelOutcome),
        );
        markUsed(i);
        continue;
      }

      if (op === "guard.decision" || op === "policy.blocked") {
        var code =
          ev.error && ev.error.code != null
            ? String(ev.error.code)
            : ev.payload_summary && ev.payload_summary.reason_code != null
              ? String(ev.payload_summary.reason_code)
              : "koruma";
        groups.push(buildEvidenceUiGroup(ev, "guard", "Koruma: " + code));
        markUsed(i);
        continue;
      }

      if (source === "task_engine") {
        groups.push(
          buildEvidenceUiGroup(ev, "engine", "Motor · " + String(ev.outcome || "ok")),
        );
        markUsed(i);
        continue;
      }

      if (phase === "before") {
        markUsed(i);
        continue;
      }

      groups.push(
        buildEvidenceUiGroup(
          ev,
          "other",
          evidenceSourceLabel(source) + " · " + String(ev.outcome || "ok"),
        ),
      );
      markUsed(i);
    }

    groups.sort(function (a, b) {
      return parseEvidenceTsMs(b.ts) - parseEvidenceTsMs(a.ts);
    });
    return groups;
  }

  function pickLatestEvidenceGroup(groups) {
    if (!Array.isArray(groups) || !groups.length) return null;
    return groups[0];
  }

  function fetchEvidenceRecent(apiBase) {
    var base = String(apiBase || "").replace(/\/$/, "");
    if (!base) return Promise.resolve(null);
    return fetch(base + "/evidence/recent", {
      headers: { Accept: "application/json" },
    })
      .then(function (r) {
        if (!r.ok) return null;
        return r.json();
      })
      .then(function (data) {
        if (!data || !Array.isArray(data.events)) return null;
        return data;
      })
      .catch(function () {
        return null;
      });
  }

  function buildLegacyEvidenceStripHtml() {
    return (
      '<div class="legacy-primary-surface-note" role="note">' +
      '<p class="text-muted-small">Birincil üretim yüzeyi: Astro <code>/panel</code>. ' +
      "Bu legacy panel E2E/statik kapıdır; EC2-02 kuyruk yalnız Astro'da.</p>" +
      "</div>" +
      '<div id="legacy-evidence-strip" class="legacy-evidence-strip" hidden>' +
      '<p id="legacy-evidence-summary" class="legacy-evidence-summary"></p>' +
      '<button type="button" id="legacy-evidence-continue" class="legacy-evidence-continue-btn" hidden>' +
      "Buradan devam" +
      "</button>" +
      "</div>" +
      '<p id="legacy-evidence-empty" class="legacy-evidence-empty text-muted-small" role="status" hidden>' +
      "Henüz sunucu kanıtı yok" +
      "</p>"
    );
  }

  function refreshLegacyEvidenceStrip(opts) {
    opts = opts || {};
    var stripEl = opts.stripEl || document.getElementById("legacy-evidence-strip");
    var summaryEl = opts.summaryEl || document.getElementById("legacy-evidence-summary");
    var continueBtn = opts.continueBtn || document.getElementById("legacy-evidence-continue");
    var emptyEl = opts.emptyEl || document.getElementById("legacy-evidence-empty");
    if (!stripEl || !summaryEl || !continueBtn || !emptyEl) {
      return Promise.resolve(null);
    }

    return fetchEvidenceRecent(opts.apiBase).then(function (data) {
      if (!data) {
        if (typeof opts.onGroupChange === "function") opts.onGroupChange(null);
        stripEl.hidden = true;
        emptyEl.hidden = false;
        emptyEl.textContent = "Henüz sunucu kanıtı yok";
        continueBtn.hidden = true;
        return null;
      }

      var groups = groupEvidenceEventsForUi(data.events);
      var latest = pickLatestEvidenceGroup(groups);
      if (!latest) {
        if (typeof opts.onGroupChange === "function") opts.onGroupChange(null);
        stripEl.hidden = true;
        emptyEl.hidden = false;
        emptyEl.textContent = "Henüz sunucu kanıtı yok";
        continueBtn.hidden = true;
        return null;
      }

      if (typeof opts.onGroupChange === "function") opts.onGroupChange(latest);
      emptyEl.hidden = true;
      stripEl.hidden = false;
      summaryEl.textContent = "Son işlem kanıtı: " + latest.label;
      continueBtn.hidden = !latest.canContinue;
      return latest;
    });
  }

  global.LumosEvidenceCorrelationStrip = {
    EVIDENCE_BRIDGE_PAIR_MAX_MS: EVIDENCE_BRIDGE_PAIR_MAX_MS,
    parseEvidenceTsMs: parseEvidenceTsMs,
    evidenceTitlePreviewPrefixMatch: evidenceTitlePreviewPrefixMatch,
    evidenceSourceLabel: evidenceSourceLabel,
    buildEvidenceUiGroup: buildEvidenceUiGroup,
    groupEvidenceEventsForUi: groupEvidenceEventsForUi,
    pickLatestEvidenceGroup: pickLatestEvidenceGroup,
    fetchEvidenceRecent: fetchEvidenceRecent,
    buildLegacyEvidenceStripHtml: buildLegacyEvidenceStripHtml,
    refreshLegacyEvidenceStrip: refreshLegacyEvidenceStrip,
  };
})(typeof window !== "undefined" ? window : this);
