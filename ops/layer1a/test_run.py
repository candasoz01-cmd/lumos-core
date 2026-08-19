from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

_RUNNER = Path(__file__).resolve().parent / "run.py"
_SPEC = importlib.util.spec_from_file_location("layer1a_run", _RUNNER)
assert _SPEC is not None and _SPEC.loader is not None
layer1a = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(layer1a)


NOW = datetime(2026, 8, 19, 8, 0, tzinfo=timezone.utc)
CHECKED_AT = "2026-08-19T08:00:00Z"

PASSING_BODIES = {
    "/": (200, "text/html", b"<!doctype html><title>Lumos</title>"),
    "/panel": (200, "text/html", b"<!doctype html><title>Lumos Panel</title>"),
    "/integrations": (200, "text/html", b"<!doctype html><title>Integrations</title>"),
    "/auth/readiness": (
        200,
        "application/json",
        json.dumps(
            {
                "ok": True,
                "live_login": True,
                "client_id_prefix": "48833665",
                "redirect_uri": "https://welockai.com/auth/google/callback",
                "has_client_secret": True,
                "has_dedicated_state_secret": True,
                "door": "lumos",
            }
        ).encode(),
    ),
    "/api/bridge/task": (
        503,
        "application/json",
        json.dumps({"ok": False, "error": "bridge_proxy_unconfigured"}).encode(),
    ),
}


def _fetch_from(table: dict[str, tuple[int, str, bytes]]):
    def fetch(url: str) -> tuple[int, str, bytes]:
        path = url.split("://", 1)[-1]
        path = path[path.find("/") :] if "/" in path else "/"
        if path not in table:
            raise AssertionError(f"unexpected url {url}")
        return table[path]

    return fetch


def _fetch_unknown(_url: str) -> tuple[int, str, bytes]:
    raise TimeoutError("simulated timeout")


def test_canon_is_exactly_five_get_checks() -> None:
    assert len(layer1a.CHECKS) == 5
    assert [item[0] for item in layer1a.CHECKS] == [
        "landing",
        "panel",
        "integrations",
        "auth_readiness",
        "bridge_fail_closed",
    ]
    assert all(item[0] and item[1].startswith("/") for item in layer1a.CHECKS)


def test_all_pass_writes_schema_and_overall_pass() -> None:
    report = layer1a.run_checks(
        base_url="https://welockai.com",
        fetch=_fetch_from(PASSING_BODIES),
        checked_at=CHECKED_AT,
        now=NOW,
    )
    assert report["schema"] == layer1a.SCHEMA
    assert report["overall"] == "pass"
    assert report["last_success_at"] == CHECKED_AT
    assert report["stale_after_seconds"] == layer1a.DEFAULT_STALE_AFTER_SECONDS
    assert report["base_url"] == "https://welockai.com"
    assert [item["id"] for item in report["checks"]] == [c[0] for c in layer1a.CHECKS]
    assert all(
        item["ok"] and item["result"] == "pass" and item["method"] == "GET"
        for item in report["checks"]
    )


def test_landing_non_200_fails_only_that_check() -> None:
    bodies = dict(PASSING_BODIES)
    bodies["/"] = (500, "text/plain", b"no")
    report = layer1a.run_checks(
        base_url="https://example.test",
        fetch=_fetch_from(bodies),
        last_success_at="2026-08-19T07:00:00Z",
        now=NOW,
        checked_at=CHECKED_AT,
    )
    by_id = {item["id"]: item for item in report["checks"]}
    assert report["overall"] == "fail"
    assert report["last_success_at"] == "2026-08-19T07:00:00Z"
    assert by_id["landing"]["ok"] is False
    assert by_id["landing"]["result"] == "fail"
    assert "500" in by_id["landing"]["detail"]
    assert by_id["panel"]["result"] == "pass"


def test_auth_readiness_rejects_secret_value() -> None:
    bodies = dict(PASSING_BODIES)
    bodies["/auth/readiness"] = (
        200,
        "application/json",
        json.dumps({"ok": True, "client_secret": "leak"}).encode(),
    )
    report = layer1a.run_checks(base_url="https://example.test", fetch=_fetch_from(bodies))
    readiness = next(item for item in report["checks"] if item["id"] == "auth_readiness")
    assert readiness["result"] == "fail"
    assert "secret" in readiness["detail"]


def test_bridge_200_is_fail_closed_violation() -> None:
    bodies = dict(PASSING_BODIES)
    bodies["/api/bridge/task"] = (200, "application/json", b'{"ok":true}')
    report = layer1a.run_checks(base_url="https://example.test", fetch=_fetch_from(bodies))
    bridge = next(item for item in report["checks"] if item["id"] == "bridge_fail_closed")
    assert bridge["result"] == "fail"
    assert "200" in bridge["detail"]


def test_bridge_401_unauthorized_passes() -> None:
    bodies = dict(PASSING_BODIES)
    bodies["/api/bridge/task"] = (
        401,
        "application/json",
        json.dumps({"ok": False, "error": "bridge_proxy_unauthorized"}).encode(),
    )
    report = layer1a.run_checks(base_url="https://example.test", fetch=_fetch_from(bodies))
    assert report["overall"] == "pass"


def test_timeout_is_unknown_not_fail() -> None:
    report = layer1a.run_checks(
        base_url="https://example.test",
        fetch=_fetch_unknown,
        now=NOW,
        checked_at=CHECKED_AT,
    )
    assert report["overall"] == "unknown"
    assert report["last_success_at"] is None
    assert all(item["result"] == "unknown" for item in report["checks"])
    assert all(item["ok"] is False for item in report["checks"])


def test_unknown_with_old_success_is_stale() -> None:
    report = layer1a.run_checks(
        base_url="https://example.test",
        fetch=_fetch_unknown,
        last_success_at="2026-08-19T06:00:00Z",
        now=NOW,
        checked_at=CHECKED_AT,
        stale_after_seconds=3600,
    )
    assert report["overall"] == "stale"
    assert report["last_success_at"] == "2026-08-19T06:00:00Z"


def test_unknown_with_recent_success_stays_unknown() -> None:
    report = layer1a.run_checks(
        base_url="https://example.test",
        fetch=_fetch_unknown,
        last_success_at="2026-08-19T07:30:00Z",
        now=NOW,
        checked_at=CHECKED_AT,
        stale_after_seconds=3600,
    )
    assert report["overall"] == "unknown"
    assert report["last_success_at"] == "2026-08-19T07:30:00Z"


def test_cli_persists_last_success_at_across_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "layer1a-result.json"
    state = tmp_path / "layer1a-state.json"
    monkeypatch.setattr(
        layer1a,
        "default_fetch",
        lambda url, timeout: _fetch_from(PASSING_BODIES)(url),
    )
    first = layer1a.main(
        [
            "--base-url",
            "https://welockai.com",
            "--output",
            str(output),
            "--state",
            str(state),
        ]
    )
    assert first == 0
    first_payload = json.loads(output.read_text(encoding="utf-8"))
    assert first_payload["overall"] == "pass"
    assert first_payload["last_success_at"]
    stored = json.loads(state.read_text(encoding="utf-8"))
    assert stored["schema"] == layer1a.STATE_SCHEMA
    assert stored["last_success_at"] == first_payload["last_success_at"]

    monkeypatch.setattr(layer1a, "default_fetch", lambda url, timeout: _fetch_unknown(url))
    second = layer1a.main(
        [
            "--base-url",
            "https://welockai.com",
            "--output",
            str(output),
            "--state",
            str(state),
            "--stale-after",
            "3600",
        ]
    )
    assert second == 1
    second_payload = json.loads(output.read_text(encoding="utf-8"))
    assert second_payload["overall"] in {"unknown", "stale"}
    assert second_payload["last_success_at"] == first_payload["last_success_at"]
    assert json.loads(state.read_text(encoding="utf-8"))["last_success_at"] == (
        first_payload["last_success_at"]
    )
