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
GENERATED_AT = "2026-08-19T08:00:01Z"
OLD_SUCCESS = "2026-08-19T06:00:00Z"
RECENT_SUCCESS = "2026-08-19T07:30:00Z"

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
        401,
        "application/json",
        json.dumps({"ok": False, "error": "bridge_proxy_unauthorized"}).encode(),
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


def _report(**kwargs):
    defaults = {
        "base_url": "https://example.test",
        "checked_at": CHECKED_AT,
        "generated_at": GENERATED_AT,
        "now": NOW,
        "run_attempt": 2,
    }
    defaults.update(kwargs)
    return layer1a.run_checks(**defaults)


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


def test_all_pass_writes_schema_generated_at_and_per_check_success() -> None:
    report = _report(base_url="https://welockai.com", fetch=_fetch_from(PASSING_BODIES))
    assert report["schema"] == layer1a.SCHEMA
    assert report["overall"] == "pass"
    assert report["generated_at"] == GENERATED_AT
    assert report["run_attempt"] == 2
    assert report["stale_after_seconds"] == layer1a.DEFAULT_STALE_AFTER_SECONDS
    assert report["base_url"] == "https://welockai.com"
    assert isinstance(report["last_success_at"], dict)
    assert report["last_success_at"] == {item[0]: CHECKED_AT for item in layer1a.CHECKS}
    assert [item["id"] for item in report["checks"]] == [c[0] for c in layer1a.CHECKS]
    assert all(
        item["ok"]
        and item["result"] == "pass"
        and item["method"] == "GET"
        and item["last_success_at"] == CHECKED_AT
        and item["age_seconds"] == 1
        for item in report["checks"]
    )


def test_landing_503_is_fail_bridge_exception_is_not_global() -> None:
    bodies = dict(PASSING_BODIES)
    bodies["/"] = (503, "text/plain", b"unavailable")
    report = _report(fetch=_fetch_from(bodies))
    landing = next(item for item in report["checks"] if item["id"] == "landing")
    assert landing["result"] == "fail"
    assert report["overall"] == "fail"


def test_landing_non_200_fails_only_that_check() -> None:
    bodies = dict(PASSING_BODIES)
    bodies["/"] = (500, "text/plain", b"no")
    prior = {check_id: RECENT_SUCCESS for check_id in layer1a.CHECK_IDS}
    report = _report(fetch=_fetch_from(bodies), last_success_at=prior)
    by_id = {item["id"]: item for item in report["checks"]}
    assert report["overall"] == "fail"
    assert by_id["landing"]["ok"] is False
    assert by_id["landing"]["result"] == "fail"
    assert by_id["landing"]["last_success_at"] == RECENT_SUCCESS
    assert by_id["landing"]["age_seconds"] == 1801
    assert "500" in by_id["landing"]["detail"]
    assert by_id["panel"]["result"] == "pass"
    assert by_id["panel"]["last_success_at"] == CHECKED_AT
    assert by_id["panel"]["age_seconds"] == 1
    assert report["last_success_at"]["landing"] == RECENT_SUCCESS
    assert report["last_success_at"]["panel"] == CHECKED_AT


def test_auth_readiness_rejects_secret_value() -> None:
    bodies = dict(PASSING_BODIES)
    bodies["/auth/readiness"] = (
        200,
        "application/json",
        json.dumps({"ok": True, "client_secret": "leak"}).encode(),
    )
    report = _report(fetch=_fetch_from(bodies))
    readiness = next(item for item in report["checks"] if item["id"] == "auth_readiness")
    assert readiness["result"] == "fail"
    assert "secret" in readiness["detail"]


def test_bridge_200_is_fail_closed_violation() -> None:
    bodies = dict(PASSING_BODIES)
    bodies["/api/bridge/task"] = (200, "application/json", b'{"ok":true}')
    report = _report(fetch=_fetch_from(bodies))
    bridge = next(item for item in report["checks"] if item["id"] == "bridge_fail_closed")
    assert bridge["result"] == "fail"
    assert "200" in bridge["detail"]


def test_bridge_401_unauthorized_passes() -> None:
    report = _report(fetch=_fetch_from(PASSING_BODIES))
    bridge = next(item for item in report["checks"] if item["id"] == "bridge_fail_closed")
    assert bridge["result"] == "pass"
    assert report["overall"] == "pass"


def test_bridge_503_is_unknown_not_pass() -> None:
    result, detail = layer1a._bridge_fail_closed(
        503,
        "application/json",
        json.dumps({"ok": False, "error": "bridge_proxy_unconfigured"}).encode(),
    )
    assert result == "unknown"
    assert result != "pass"
    assert "503" in (detail or "")

    bodies = dict(PASSING_BODIES)
    bodies["/api/bridge/task"] = (
        503,
        "application/json",
        json.dumps({"ok": False, "error": "bridge_proxy_unconfigured"}).encode(),
    )
    report = _report(fetch=_fetch_from(bodies))
    bridge = next(item for item in report["checks"] if item["id"] == "bridge_fail_closed")
    assert bridge["result"] == "unknown"
    assert report["overall"] == "unknown"


def test_timeout_is_unknown_not_fail() -> None:
    report = _report(fetch=_fetch_unknown)
    assert report["overall"] == "unknown"
    assert report["last_success_at"] == {}
    assert all(item["result"] == "unknown" for item in report["checks"])
    assert all(item["ok"] is False for item in report["checks"])
    assert all(item["last_success_at"] is None for item in report["checks"])
    assert all(item["age_seconds"] is None for item in report["checks"])


def test_stale_uses_the_unknown_check_timestamp_not_a_global_value() -> None:
    prior = {check_id: RECENT_SUCCESS for check_id in layer1a.CHECK_IDS}
    prior["bridge_fail_closed"] = OLD_SUCCESS
    bodies = dict(PASSING_BODIES)
    bodies["/api/bridge/task"] = (
        503,
        "application/json",
        json.dumps({"ok": False, "error": "bridge_proxy_unconfigured"}).encode(),
    )
    report = _report(fetch=_fetch_from(bodies), last_success_at=prior)
    by_id = {item["id"]: item for item in report["checks"]}
    assert by_id["bridge_fail_closed"]["result"] == "unknown"
    assert by_id["bridge_fail_closed"]["last_success_at"] == OLD_SUCCESS
    assert by_id["bridge_fail_closed"]["age_seconds"] == 7201
    assert by_id["landing"]["last_success_at"] == CHECKED_AT
    assert by_id["landing"]["age_seconds"] == 1
    assert report["overall"] == "stale"
    assert isinstance(report["last_success_at"], dict)
    assert report["last_success_at"]["bridge_fail_closed"] == OLD_SUCCESS


def test_unknown_with_recent_per_check_success_stays_unknown() -> None:
    prior = {check_id: RECENT_SUCCESS for check_id in layer1a.CHECK_IDS}
    report = _report(fetch=_fetch_unknown, last_success_at=prior)
    assert report["overall"] == "unknown"
    assert report["last_success_at"] == prior
    assert all(item["last_success_at"] == RECENT_SUCCESS for item in report["checks"])
    assert all(item["age_seconds"] == 1801 for item in report["checks"])


def test_global_string_last_success_at_is_not_applied_to_checks() -> None:
    report = _report(fetch=_fetch_unknown, last_success_at=OLD_SUCCESS)  # type: ignore[arg-type]
    assert report["overall"] == "unknown"
    assert report["last_success_at"] == {}
    assert all(item["last_success_at"] is None for item in report["checks"])
    assert all(item["age_seconds"] is None for item in report["checks"])


def test_cli_persists_per_check_last_success_at(
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
            "--run-attempt",
            "3",
        ]
    )
    assert first == 0
    first_payload = json.loads(output.read_text(encoding="utf-8"))
    assert first_payload["overall"] == "pass"
    assert first_payload["generated_at"]
    assert first_payload["run_attempt"] == 3
    assert isinstance(first_payload["last_success_at"], dict)
    stored = json.loads(state.read_text(encoding="utf-8"))
    assert stored["schema"] == layer1a.STATE_SCHEMA
    assert set(stored) == {"schema", "last_success_at"}
    assert "age_seconds" not in stored
    assert "age_seconds" not in json.dumps(stored)
    assert stored["last_success_at"] == first_payload["last_success_at"]
    assert set(stored["last_success_at"]) == set(layer1a.CHECK_IDS)
    assert all("age_seconds" in item for item in first_payload["checks"])

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
    assert all(
        item["last_success_at"] == first_payload["last_success_at"][item["id"]]
        for item in second_payload["checks"]
    )
    second_state = json.loads(state.read_text(encoding="utf-8"))
    assert set(second_state) == {"schema", "last_success_at"}
    assert "age_seconds" not in json.dumps(second_state)
    assert all(item["age_seconds"] is not None for item in second_payload["checks"])


def test_age_seconds_is_derived_and_omitted_from_state(tmp_path: Path) -> None:
    assert layer1a.age_seconds_between(GENERATED_AT, CHECKED_AT) == 1
    assert layer1a.age_seconds_between(GENERATED_AT, None) is None
    poisoned = tmp_path / "layer1a-state.json"
    poisoned.write_text(
        json.dumps(
            {
                "schema": layer1a.STATE_SCHEMA,
                "last_success_at": {"landing": OLD_SUCCESS},
                "age_seconds": 999,
            }
        ),
        encoding="utf-8",
    )
    loaded = layer1a.load_state(str(poisoned))
    assert loaded == {"landing": OLD_SUCCESS}
    layer1a.save_state(str(poisoned), {"landing": OLD_SUCCESS, "age_seconds": "999"})  # type: ignore[dict-item]
    stored = json.loads(poisoned.read_text(encoding="utf-8"))
    assert set(stored) == {"schema", "last_success_at"}
    assert stored["last_success_at"] == {"landing": OLD_SUCCESS}

