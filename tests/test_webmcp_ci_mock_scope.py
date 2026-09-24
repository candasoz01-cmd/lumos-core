"""F2: CI WebMCP e2e is mock/simulated; it must not read as native Chrome WebMCP.

On origin/main (9691c8a4) ``ui-smoke`` ran ``npm run e2e:webmcp`` which injects
``document.modelContext`` and serves mock ``POST /lumos-confirm/request``.
``e2e:webmcp:native`` is not in CI and defaults to macOS Google Chrome.
"""
from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_CI = _REPO / ".github" / "workflows" / "ci.yml"
_HARNESS = _REPO / "ui" / "e2e" / "webmcp-panel-tools.mjs"
_NATIVE = _REPO / "ui" / "e2e" / "webmcp-native-verify.mjs"
_UI_PKG = _REPO / "ui" / "package.json"
_ROOT_PKG = _REPO / "package.json"


def _ci_run_lines() -> list[str]:
    lines: list[str] = []
    for raw in _CI.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped.startswith("run:"):
            lines.append(stripped)
    return lines


def test_ci_runs_webmcp_mock_script_not_native() -> None:
    runs = _ci_run_lines()
    assert any("npm run e2e:webmcp:mock" in line for line in runs)
    assert not any("e2e:webmcp:native" in line for line in runs)
    assert "run: npm run e2e:webmcp" not in runs
    ci = _CI.read_text(encoding="utf-8")
    assert "not native Chrome" in ci


def test_ci_webmcp_harness_is_mock_confirm_and_injected_model_context() -> None:
    harness = _HARNESS.read_text(encoding="utf-8")
    assert "function startConfirmMockServer" in harness
    assert 'url === "/lumos-confirm/request"' in harness
    assert 'Object.defineProperty(document, "modelContext"' in harness
    assert "addInitScript(AGENT_HARNESS)" in harness
    assert "WEBMCP_PANEL_MOCK_E2E_RESULT" in harness
    assert "WEBMCP_NATIVE_RESULT" not in harness
    assert "not native Chrome WebMCP" in harness
    assert "mock POST /lumos-confirm/request" in harness


def test_npm_scripts_expose_mock_name() -> None:
    ui = json.loads(_UI_PKG.read_text(encoding="utf-8"))
    root = json.loads(_ROOT_PKG.read_text(encoding="utf-8"))
    assert ui["scripts"]["e2e:webmcp:mock"] == "node e2e/webmcp-panel-tools.mjs"
    assert ui["scripts"]["e2e:webmcp"] == "node e2e/webmcp-panel-tools.mjs"
    assert ui["scripts"]["e2e:webmcp:native"] == "node e2e/webmcp-native-verify.mjs"
    assert "e2e:webmcp:mock" in root["scripts"]
    assert "e2e:webmcp:mock --prefix ui" in root["scripts"]["e2e:webmcp"]


def test_native_script_stays_out_of_linux_ci_and_needs_macos_chrome() -> None:
    """Linux CI cannot honestly run native WebMCP; do not add a fake native job."""
    native = _NATIVE.read_text(encoding="utf-8")
    assert "/Applications/Google Chrome.app" in native
    assert "addInitScript(" not in native
    assert 'Object.defineProperty(document, "modelContext"' not in native
    assert "WEBMCP_NATIVE_RESULT" in native
    ci = _CI.read_text(encoding="utf-8")
    assert "npm run e2e:webmcp:native" not in ci
