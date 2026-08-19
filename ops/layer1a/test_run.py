from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_RUNNER = Path(__file__).resolve().parent / "run.py"
_SPEC = importlib.util.spec_from_file_location("layer1a_run", _RUNNER)
assert _SPEC is not None and _SPEC.loader is not None
layer1a = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(layer1a)


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
        checked_at="2026-08-19T08:00:00Z",
    )
    assert report["schema"] == layer1a.SCHEMA
    assert report["overall"] == "pass"
    assert report["base_url"] == "https://welockai.com"
    assert [item["id"] for item in report["checks"]] == [c[0] for c in layer1a.CHECKS]
    assert all(item["ok"] and item["method"] == "GET" for item in report["checks"])


def test_landing_non_200_fails_only_that_check() -> None:
    bodies = dict(PASSING_BODIES)
    bodies["/"] = (500, "text/plain", b"no")
    report = layer1a.run_checks(base_url="https://example.test", fetch=_fetch_from(bodies))
    by_id = {item["id"]: item for item in report["checks"]}
    assert report["overall"] == "fail"
    assert by_id["landing"]["ok"] is False
    assert "500" in by_id["landing"]["detail"]
    assert by_id["panel"]["ok"] is True


def test_auth_readiness_rejects_secret_value() -> None:
    bodies = dict(PASSING_BODIES)
    bodies["/auth/readiness"] = (
        200,
        "application/json",
        json.dumps({"ok": True, "client_secret": "leak"}).encode(),
    )
    report = layer1a.run_checks(base_url="https://example.test", fetch=_fetch_from(bodies))
    readiness = next(item for item in report["checks"] if item["id"] == "auth_readiness")
    assert readiness["ok"] is False
    assert "secret" in readiness["detail"]


def test_bridge_200_is_fail_closed_violation() -> None:
    bodies = dict(PASSING_BODIES)
    bodies["/api/bridge/task"] = (200, "application/json", b'{"ok":true}')
    report = layer1a.run_checks(base_url="https://example.test", fetch=_fetch_from(bodies))
    bridge = next(item for item in report["checks"] if item["id"] == "bridge_fail_closed")
    assert bridge["ok"] is False
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


def test_cli_writes_json_and_exit_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "layer1a-result.json"
    monkeypatch.setattr(
        layer1a,
        "default_fetch",
        lambda url, timeout: _fetch_from(PASSING_BODIES)(url),
    )
    code = layer1a.main(["--base-url", "https://welockai.com", "--output", str(output)])
    assert code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["overall"] == "pass"
    assert payload["schema"] == layer1a.SCHEMA
