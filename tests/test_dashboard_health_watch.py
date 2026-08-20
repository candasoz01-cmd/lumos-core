"""Controlled observe-shift: report-if-needed, no credentials, no Fix."""

from __future__ import annotations

import io
import json
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

import pytest

from dashboard_health.bridge_llm import CARD_ID
from dashboard_health.watch import (
    default_fetch,
    load_previous,
    main,
    run_shift,
    should_report,
    write_json,
)

_REPO = Path(__file__).resolve().parents[1]
_WORKFLOW = _REPO / ".github/workflows/bridge-llm-observe.yml"
_WATCH = _REPO / "src/dashboard_health/watch.py"

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


def test_first_inconclusive_502_is_quiet_change_from_healthy_reports() -> None:
    first = run_shift(
        url="https://welockai.com/api/bridge/health",
        now=_NOW,
        fetch=_fetch_factory(502, {"error": "bad_gateway"}),
    )
    assert first["card"]["state"] == "unknown"
    assert first["card"]["reason_code"] == "probe_inconclusive"
    assert first["report"] is False
    healthy = run_shift(
        url="https://welockai.com/api/bridge/health",
        now=_NOW,
        fetch=_fetch_factory(200, {"status": "ok"}),
    )
    changed = run_shift(
        url="https://welockai.com/api/bridge/health",
        now=_NOW,
        previous=healthy,
        fetch=_fetch_factory(502, {"error": "bad_gateway"}),
    )
    assert changed["report"] is True


def test_evidence_state_file_roundtrip(tmp_path: Path) -> None:
    first = run_shift(
        url="https://welockai.com/api/bridge/health",
        now=_NOW,
        fetch=_fetch_factory(200, {"status": "ok"}),
    )
    state = tmp_path / "bridge-llm-observe-state.json"
    evidence = tmp_path / "bridge-llm-observe-result.json"
    write_json(str(state), first)
    write_json(str(evidence), first)
    loaded = load_previous(str(state))
    assert loaded is not None
    assert loaded["card"]["state"] == "healthy"
    second = run_shift(
        url="https://welockai.com/api/bridge/health",
        now=_NOW,
        previous=loaded,
        fetch=_fetch_factory(200, {"status": "ok"}),
    )
    assert second["report"] is False
    write_json(str(state), second)
    again = json.loads(state.read_text(encoding="utf-8"))
    assert again["card"]["state"] == "healthy"


def test_cli_empty_url_exits_zero_without_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LUMOS_BRIDGE_HEALTH_URL", raising=False)
    evidence = tmp_path / "bridge-llm-observe-result.json"
    state = tmp_path / "bridge-llm-observe-state.json"
    rc = main(
        [
            "--url",
            "",
            "--output",
            str(evidence),
            "--state",
            str(state),
        ]
    )
    assert rc == 0
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["card"]["state"] == "unknown"
    assert payload["card"]["reason_code"] == "not_checked"
    assert payload["card"]["checked_at"] is None
    assert payload["probed"] is False
    assert payload["report"] is False
    assert payload["boundary"]["fix"] is False
    assert payload["boundary"]["credentials_chased"] is False


def test_cli_failed_card_keeps_job_green(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_urlopen(request, timeout=None):  # noqa: ANN001
        raise urllib.error.HTTPError(
            request.full_url,
            500,
            "Internal Server Error",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"boom"}'),
        )

    monkeypatch.setattr("dashboard_health.watch.urllib.request.urlopen", fake_urlopen)
    evidence = tmp_path / "out.json"
    state = tmp_path / "state.json"
    rc = main(
        [
            "--url",
            "https://welockai.com/api/bridge/health",
            "--output",
            str(evidence),
            "--state",
            str(state),
        ]
    )
    assert rc == 0
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["card"]["state"] == "failed"
    assert payload["report"] is True
    assert payload["probed"] is True


def test_default_fetch_sends_only_accept_and_user_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout=None):  # noqa: ANN001
        captured["headers"] = {k.lower(): v for k, v in request.header_items()}
        captured["timeout"] = timeout
        raise urllib.error.URLError("unit-test: no network")

    monkeypatch.setattr("dashboard_health.watch.urllib.request.urlopen", fake_urlopen)
    status, body = default_fetch("https://welockai.com/api/bridge/health", 1.5)
    assert status is None
    assert body is None
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers.get("accept") == "application/json"
    assert headers.get("user-agent") == "lumos-bridge-llm-observe/1.0"
    assert "cookie" not in headers
    assert "authorization" not in headers
    assert set(headers) == {"accept", "user-agent"}


def test_workflow_is_thirty_minute_secretless_watch() -> None:
    text = _WORKFLOW.read_text(encoding="utf-8")
    watch = _WATCH.read_text(encoding="utf-8")
    assert 'cron: "*/30 * * * *"' in text
    assert "workflow_dispatch:" in text
    assert "contents: read" in text
    assert "LUMOS_BRIDGE_HEALTH_URL: https://welockai.com/api/bridge/health" in text
    assert "python3 -m dashboard_health.watch" in text
    assert "--output bridge-llm-observe-result.json" in text
    assert "--state bridge-llm-observe-state.json" in text
    assert "actions/cache/restore@v4" in text
    assert "actions/cache/save@v4" in text
    assert "actions/upload-artifact@v4" in text
    assert "${{ secrets." not in text
    assert "secrets." not in text
    assert "GITHUB_TOKEN" not in text
    assert "GITHUB_TOKEN" not in watch
    assert "Cookie" not in watch
    assert "Authorization" not in watch
    assert "credentials_chased" in watch
    assert "Not Fix" in text
    assert "no remediations applied" in text
