"""F3/F15: mobile approval MVP tests are in-process/integration, not live E2E.

On origin/main (9691c8a4) ``tests/test_mobile_approval_mvp_e2e.py`` was named
E2E but used ``BridgeHandler.__new__`` and a monkeypatched ``http_json``.
CI job ``test`` runs bare ``pytest`` (no live-server mobile job).
"""
from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_CI = _REPO / ".github" / "workflows" / "ci.yml"
_INPROCESS = _REPO / "tests" / "test_mobile_approval_mvp_inprocess.py"
_OLD_E2E = _REPO / "tests" / "test_mobile_approval_mvp_e2e.py"


def test_mobile_approval_mvp_file_is_named_inprocess_not_e2e() -> None:
    assert _INPROCESS.is_file()
    assert not _OLD_E2E.exists()
    src = _INPROCESS.read_text(encoding="utf-8")
    assert "in-process/integration" in src
    assert "Not a live-server or network E2E" in src
    assert "def test_mobile_approval_mvp_e2e_" not in src
    assert "def test_mobile_approval_mvp_inprocess_pc_open_url" in src


def test_mobile_approval_mvp_uses_inprocess_bridgehandler_not_live_server() -> None:
    src = _INPROCESS.read_text(encoding="utf-8")
    assert "BridgeHandler.__new__(BridgeHandler)" in src
    assert "no live server" in src
    assert "kando_bridge.mobile_approval_client.http_json" in src
    assert "HTTPServer" not in src
    assert "http.server" not in src
    assert "urlopen" not in src
    assert "socketserver" not in src


def test_ci_test_job_runs_pytest_without_live_mobile_e2e_job() -> None:
    """CI scope: this file is collected by pytest; there is no live-server job."""
    ci = _CI.read_text(encoding="utf-8")
    assert "run: pytest" in ci
    run_lines = [ln.strip() for ln in ci.splitlines() if ln.strip().startswith("run:")]
    assert not any("mobile" in ln.lower() and "live" in ln.lower() for ln in run_lines)
    assert "  test:" in ci
