/**
 * dashboard-health-v1 mapper for bridge.llm.
 * Lockstep with src/dashboard_health/bridge_llm.py.
 * unmeasured must not render healthy.
 */
export const CARD_ID = "bridge.llm";
export const TTL_SECONDS = 120;

export function unprobedCard() {
  return {
    id: CARD_ID,
    state: "unknown",
    checked_at: null,
    ttl_seconds: TTL_SECONDS,
    last_known: null,
    reason_code: "not_checked",
    evidence: "GET /api/bridge/health not_called",
  };
}

export function cardFromHttp(httpStatus, body, fetchedAt) {
  const stamp = iso(fetchedAt);
  if (httpStatus == null) {
    return card("unknown", null, "probe_unreachable", "GET /api/bridge/health unreachable");
  }
  if (httpStatus === 401) {
    return card("unknown", stamp, "unauthorized", "GET /api/bridge/health → 401");
  }
  const statusField = body && typeof body === "object" ? String(body.status || "").trim().toLowerCase() : "";
  if (httpStatus === 503 && statusField === "unconfigured") {
    return card("not_configured", stamp, "unconfigured", "GET /api/bridge/health → 503 unconfigured");
  }
  if (httpStatus === 200 && statusField === "ok") {
    return card("healthy", stamp, null, "GET /api/bridge/health → 200");
  }
  if (httpStatus >= 500) {
    return card("failed", stamp, "probe_rejected", `GET /api/bridge/health → ${httpStatus}`);
  }
  return card("unknown", stamp, "unmapped_value", `GET /api/bridge/health → ${httpStatus} unmapped`);
}

export function applyFreshness(input, now) {
  const out = { ...input };
  const checked = out.checked_at;
  const state = out.state;
  if ((state === "healthy" || state === "failed" || state === "stale") && !checked) {
    return unprobedCard();
  }
  if ((state === "healthy" || state === "failed") && checked) {
    const age = (now.getTime() - Date.parse(checked)) / 1000;
    const ttl = Number(out.ttl_seconds || TTL_SECONDS);
    if (age > ttl) {
      out.last_known = state;
      out.state = "stale";
      out.reason_code = "freshness_expired";
      return out;
    }
  }
  if (out.state !== "stale") out.last_known = null;
  return out;
}

export function pillModifier(state) {
  return (
    {
      not_configured: "off",
      unknown: "unknown",
      healthy: "ready",
      failed: "failed",
      stale: "stale",
    }[state] || "unknown"
  );
}

function card(state, checkedAt, reason, evidence) {
  if ((state === "healthy" || state === "failed" || state === "stale") && !checkedAt) {
    state = "unknown";
    reason = "not_checked";
  }
  return {
    id: CARD_ID,
    state,
    checked_at: checkedAt,
    ttl_seconds: TTL_SECONDS,
    last_known: null,
    reason_code: reason,
    evidence,
  };
}

function iso(date) {
  return date.toISOString().replace(/\.\d{3}Z$/, "Z");
}
