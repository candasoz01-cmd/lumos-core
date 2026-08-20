"""dashboard-health-v1 mapper for the bridge.llm observe slice.

Keep in lockstep with ui/src/lib/dashboard-health/bridge-llm.js.
Observation only — does not hand the domain to Lumos.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

CARD_ID = "bridge.llm"
TTL_SECONDS = 120  # provisional default; not an SLO
STATES = frozenset({"not_configured", "unknown", "healthy", "failed", "stale"})


def unprobed_card() -> dict[str, Any]:
    return {
        "id": CARD_ID,
        "state": "unknown",
        "checked_at": None,
        "ttl_seconds": TTL_SECONDS,
        "last_known": None,
        "reason_code": "not_checked",
        "evidence": "GET /api/bridge/health not_called",
    }


def card_from_http(
    http_status: int | None,
    body: dict[str, Any] | None,
    *,
    fetched_at: datetime,
) -> dict[str, Any]:
    """Map a probe. http_status None = network/timeout (not a completed check)."""
    stamp = _iso(fetched_at)
    if http_status is None:
        return _card("unknown", None, "probe_unreachable", "GET /api/bridge/health unreachable")
    if http_status == 401:
        return _card("unknown", stamp, "unauthorized", "GET /api/bridge/health → 401")
    status_field = ""
    if isinstance(body, dict):
        status_field = str(body.get("status") or "").strip().lower()
    if http_status == 503 and status_field == "unconfigured":
        return _card(
            "not_configured",
            stamp,
            "unconfigured",
            "GET /api/bridge/health → 503 unconfigured",
        )
    if http_status == 200 and status_field == "ok":
        return _card("healthy", stamp, None, "GET /api/bridge/health → 200")
    if http_status >= 500:
        return _card("failed", stamp, "probe_rejected", f"GET /api/bridge/health → {http_status}")
    return _card(
        "unknown",
        stamp,
        "unmapped_value",
        f"GET /api/bridge/health → {http_status} unmapped",
    )


def apply_freshness(card: dict[str, Any], now: datetime) -> dict[str, Any]:
    out = dict(card)
    checked = out.get("checked_at")
    state = out.get("state")
    if state in ("healthy", "failed", "stale") and not checked:
        return unprobed_card()
    if state in ("healthy", "failed") and checked:
        age = (now - _parse(checked)).total_seconds()
        ttl = int(out.get("ttl_seconds") or TTL_SECONDS)
        if age > ttl:
            out["last_known"] = state
            out["state"] = "stale"
            out["reason_code"] = "freshness_expired"
            return out
    if out.get("state") != "stale":
        out["last_known"] = None
    return out


def pill_modifier(state: str) -> str:
    return {
        "not_configured": "off",
        "unknown": "unknown",
        "healthy": "ready",
        "failed": "failed",
        "stale": "stale",
    }.get(state, "unknown")


def _card(state: str, checked_at: str | None, reason: str | None, evidence: str) -> dict[str, Any]:
    if state not in STATES:
        state = "unknown"
        reason = "unmapped_value"
    if state in ("healthy", "failed", "stale") and not checked_at:
        state = "unknown"
        reason = "not_checked"
    return {
        "id": CARD_ID,
        "state": state,
        "checked_at": checked_at,
        "ttl_seconds": TTL_SECONDS,
        "last_known": None,
        "reason_code": reason,
        "evidence": evidence,
    }


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
