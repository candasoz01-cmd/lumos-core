"""Controlled observe-shift: report-if-needed, no credentials, no Fix."""

from __future__ import annotations

from datetime import datetime, timezone

from dashboard_health.bridge_llm import CARD_ID
from dashboard_health.watch import run_shift, should_report

_NOW = datetime(2026, 8, 20, 10, 24, tzinfo=timezone.utc)


def _fetch_factory(status, body):
    def fetch(url: str, timeout: float):
        assert url.startswith("https://")
        assert timeout > 0
        return status, body

    return fetch


def test_empty_url_is_not_checked_not_a_probe() -> None:
    out = run_shift(url="", now=_NOW, fetch=_fetch_factory(200, {"status": "ok"}))
    assert out["probed"] is False
    assert out["report"] is False
    assert out["card"]["id"] == CARD_ID
    assert out["card"]["state"] == "unknown"
    assert out["card"]["reason_code"] == "not_checked"
    assert out["card"]["checked_at"] is None
    assert out["boundary"]["fix"] is False
    assert out["boundary"]["credentials_chased"] is False


def test_401_is_unknown_completed_check_without_credentials() -> None:
    out = run_shift(
        url="https://welockai.com/api/bridge/health",
        now=_NOW,
        fetch=_fetch_factory(401, {"error": "unauthorized"}),
    )
    assert out["probed"] is True
    assert out["card"]["state"] == "unknown"
    assert out["card"]["reason_code"] == "unauthorized"
    assert out["card"]["checked_at"] == "2026-08-20T10:24:00Z"
    assert out["report"] is False


def test_controlled_500_reports_failed_without_fix() -> None:
    out = run_shift(
        url="https://welockai.com/api/bridge/health",
        now=_NOW,
        fetch=_fetch_factory(500, {"error": "boom"}),
    )
    assert out["card"]["state"] == "failed"
    assert out["report"] is True
    assert out["boundary"]["remediate"] is False
    assert out["boundary"]["other_cards"] is False


def test_healthy_is_quiet_until_state_changes() -> None:
    first = run_shift(
        url="https://welockai.com/api/bridge/health",
        now=_NOW,
        fetch=_fetch_factory(200, {"status": "ok"}),
    )
    assert first["card"]["state"] == "healthy"
    assert first["report"] is False
    second = run_shift(
        url="https://welockai.com/api/bridge/health",
        now=_NOW,
        previous=first,
        fetch=_fetch_factory(200, {"status": "ok"}),
    )
    assert second["report"] is False
    changed = run_shift(
        url="https://welockai.com/api/bridge/health",
        now=_NOW,
        previous=first,
        fetch=_fetch_factory(503, {"status": "unconfigured"}),
    )
    assert changed["card"]["state"] == "not_configured"
    assert changed["report"] is True


def test_network_miss_is_unknown_not_healthy() -> None:
    out = run_shift(
        url="https://welockai.com/api/bridge/health",
        now=_NOW,
        fetch=lambda url, timeout: (None, None),
    )
    assert out["card"]["state"] == "unknown"
    assert out["card"]["checked_at"] is None
    assert out["card"]["reason_code"] == "probe_unreachable"


def test_should_report_ignores_first_unknown() -> None:
    card = {"state": "unknown", "reason_code": "not_checked"}
    assert should_report(card, None) is False
    assert should_report({"state": "failed", "reason_code": "probe_rejected"}, None) is True
