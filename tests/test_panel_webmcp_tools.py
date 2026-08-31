"""WebMCP dilimi (2026-08-25 sonrası) — panel tool kaydı ve onay kapısı sözleşmesi.

Bu testler kaynak sözleşmesini korur:
  * tool'lar gerçekten `document.modelContext.registerTool()` ile kaydedilir,
  * her dış etkili tool panelin insan onay kapısından geçer,
  * onay kapısını atlayan bir kısayol eklenmemiştir.

Çalışan uçtan uca doğrulama ayrıca: `npm run e2e:webmcp --prefix ui`.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PANEL_PAGE = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"
_PANEL_COMPONENTS = _REPO_ROOT / "ui" / "src" / "components" / "panel"
_WEBMCP_TOOLS = _PANEL_COMPONENTS / "WebMcpTools.astro"
_PANEL_RUNTIME = _PANEL_COMPONENTS / "PanelRuntime.astro"
_E2E = _REPO_ROOT / "ui" / "e2e" / "webmcp-panel-tools.mjs"

TOOL_NAMES = ("lumos-list-tasks", "lumos-propose-task", "lumos-complete-task")
WRITE_TOOL_BRIDGE_CALLS = ("b.proposeTask(", "b.completeTask(")


def _tools_src() -> str:
    return _WEBMCP_TOOLS.read_text(encoding="utf-8")


def _runtime_src() -> str:
    return _PANEL_RUNTIME.read_text(encoding="utf-8")


def test_webmcp_component_is_mounted_on_panel_page() -> None:
    page = _PANEL_PAGE.read_text(encoding="utf-8")
    assert 'import WebMcpTools from "../components/panel/WebMcpTools.astro";' in page
    assert "<WebMcpTools />" in page


def test_tools_are_registered_through_model_context() -> None:
    src = _tools_src()
    assert "modelContext" in src
    assert "registerTool" in src
    # Spec yüzeyi document.modelContext; navigator/window yalnızca yedek yoklama.
    assert "typeof document !== \"undefined\" ? document : null" in src
    for name in TOOL_NAMES:
        assert f'name: "{name}"' in src, name


def test_every_tool_declares_description_and_input_schema() -> None:
    src = _tools_src()
    assert src.count("description:") >= len(TOOL_NAMES)
    assert src.count("inputSchema:") >= len(TOOL_NAMES)
    assert src.count("execute(") >= len(TOOL_NAMES)


def test_write_tools_delegate_to_panel_bridge_only() -> None:
    """Tool'lar kendi başına yazmaz; panel köprüsünü çağırır."""
    src = _tools_src()
    for call in WRITE_TOOL_BRIDGE_CALLS:
        assert call in src, call
    # Tool bileşeni doğrudan görev REST'ine veya localStorage'a yazmamalı.
    assert "localStorage.setItem" not in src
    assert "fetch(" not in src


def test_bridge_write_paths_go_through_human_confirmation_gate() -> None:
    src = _runtime_src()
    assert "panelWebMcpHumanGate" in src
    # Her iki yazma yolu da kapıyı çağırır.
    assert src.count("await panelWebMcpHumanGate(") == 2
    # Kapı: sunucu onayı açıksa confirmation akışı, kapalıysa yerel modal.
    gate_start = src.index("async function panelWebMcpHumanGate(")
    gate_body = src[gate_start : gate_start + 1200]
    assert "isPanelConfirmationEnabled()" in gate_body
    assert "panelEnsureMutationConfirmation(" in gate_body
    assert "showPanelConfirmationModal(" in gate_body


def test_rejected_gate_never_writes() -> None:
    src = _runtime_src()
    # Onay alınmadan dönülür; mutasyon çağrısı kapının arkasında kalır.
    assert src.count('reason: gate.busy ? "confirmation_busy" : "user_rejected",') == 2
    propose_start = src.index("async function panelWebMcpProposeTask(")
    propose_body = src[propose_start : src.index("async function panelWebMcpCompleteTask(")]
    assert propose_body.index("panelWebMcpHumanGate(") < propose_body.index(
        "persistPanelGorevCreateViaApi("
    )


def test_read_tool_has_no_confirmation_dependency() -> None:
    src = _runtime_src()
    list_start = src.index("function panelWebMcpListTasks(")
    list_body = src[list_start : list_start + 400]
    assert "panelWebMcpHumanGate" not in list_body
    assert "tasksApiPost" not in list_body


def test_confirmation_modal_ignores_stale_close_event() -> None:
    """Ardışık onaylarda önceki `close` olayı yeni diyaloğu iptal etmemeli."""
    src = _runtime_src()
    close_start = src.index("function onClose() {")
    close_body = src[close_start : close_start + 700]
    assert "if (dlg.open) return;" in close_body


def test_e2e_scenario_exists_and_covers_rejection() -> None:
    assert _E2E.is_file()
    e2e = _E2E.read_text(encoding="utf-8")
    assert "lumos-confirm-cancel" in e2e
    assert "lumos-confirm-approve" in e2e
    assert "onay kapısı atlanmış" in e2e
    assert "WEBMCP_PANEL_E2E_RESULT" in e2e
