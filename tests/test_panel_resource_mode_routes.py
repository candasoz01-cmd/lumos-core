"""Panel ORAA routes — GET /resource-mode/propose, POST /resource-mode/apply."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from integrations.resource_mode_advisor import (
    CONNECTS_PER_DAY_ACTIVE,
    ResourceLayer,
    record_event,
    resource_modes_path,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _load_panel_tasks_server():
    panel_scripts = _REPO_ROOT / "panel" / "scripts"
    if str(panel_scripts) not in sys.path:
        sys.path.insert(0, str(panel_scripts))
    import panel_tasks_server as pts  # noqa: E402

    return pts


@pytest.fixture
def tmp_lumos_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base = tmp_path / ".lumos"
    base.mkdir()
    monkeypatch.setenv("LUMOS_BASE_DIR", str(base))
    return base


def test_panel_server_resource_mode_route_wiring() -> None:
    src = (_REPO_ROOT / "panel" / "scripts" / "panel_tasks_server.py").read_text(encoding="utf-8")
    assert "/resource-mode/propose" in src
    assert "/resource-mode/apply" in src
    assert "build_resource_mode_propose_response" in src
    assert "build_resource_mode_apply_response" in src
    assert "propose_mode_change" in src
    assert "apply_mode_change" in src


def test_build_resource_mode_propose_response_shape(tmp_lumos_base: Path) -> None:
    pts = _load_panel_tasks_server()
    payload = pts.build_resource_mode_propose_response("quantum")
    assert payload["ok"] is True
    proposal = payload["proposal"]
    assert proposal["layer"] == "quantum"
    assert proposal["never_auto"] is True
    assert proposal["requires_approval"] is True
    assert payload["show_card"] == (proposal.get("current_mode") != proposal.get("proposed_mode"))


def test_build_resource_mode_propose_show_card_when_modes_differ(tmp_lumos_base: Path) -> None:
    for _ in range(CONNECTS_PER_DAY_ACTIVE):
        record_event(ResourceLayer.QUANTUM, "connect", base_dir=tmp_lumos_base)
    pts = _load_panel_tasks_server()
    payload = pts.build_resource_mode_propose_response("quantum")
    assert payload["show_card"] is True
    assert payload["proposal"]["proposed_mode"] == "active"


def test_build_resource_mode_apply_requires_explicit_approval(tmp_lumos_base: Path) -> None:
    pts = _load_panel_tasks_server()
    denied = pts.build_resource_mode_apply_response(
        {"layer": "quantum", "mode": "active", "user_approved": False},
    )
    assert denied["ok"] is False
    assert denied["error"] == "approval_required"
    assert not resource_modes_path(tmp_lumos_base).is_file()

    approved = pts.build_resource_mode_apply_response(
        {"layer": "quantum", "mode": "active", "user_approved": True},
    )
    assert approved["ok"] is True
    assert approved["user_approved"] is True
    assert resource_modes_path(tmp_lumos_base).is_file()


def test_build_resource_mode_apply_invalid_layer(tmp_lumos_base: Path) -> None:
    pts = _load_panel_tasks_server()
    with pytest.raises(ValueError):
        pts.build_resource_mode_apply_response(
            {"layer": "not_a_layer", "mode": "active", "user_approved": True},
        )


def test_panel_astro_resource_mode_wiring() -> None:
    text = (_REPO_ROOT / "ui" / "src" / "pages" / "panel.astro").read_text(encoding="utf-8")
    assert "/resource-mode/propose" in text
    assert "/resource-mode/apply" in text
    assert "refreshResourceModeAdvisorPanel" in text
    assert 'id="panel-resource-mode-advisor"' in text
    assert "applyResourceModeDecision" in text
