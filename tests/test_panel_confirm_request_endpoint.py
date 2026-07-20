"""PR-C5: POST /lumos-confirm/request — CU7 preview + confirmation_id."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from tests.test_panel_component_split import read_panel_source

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


def test_panel_mutation_confirmation_spec_create() -> None:
    pts = _load_panel_tasks_server()
    spec = pts._panel_mutation_confirmation_spec("/tasks", {"title": "Deneme"})
    assert spec is not None
    action_key, scope, preview = spec
    assert action_key == "create_task"
    assert scope == {"title": "Deneme"}
    assert preview["what"] == "create_task"
    assert preview["where"] == "Deneme"
    assert preview["effect"] == "local_task_create"


def test_panel_mutation_confirmation_spec_complete() -> None:
    pts = _load_panel_tasks_server()
    spec = pts._panel_mutation_confirmation_spec("/tasks/complete", {"ref": "tsk_1"})
    assert spec is not None
    action_key, scope, preview = spec
    assert action_key == "complete_task"
    assert scope == {"ref": "tsk_1"}
    assert preview["effect"] == "local_task_complete"


def test_lumos_confirm_request_disabled(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("LUMOS_CONFIRMATION_ENABLED", raising=False)
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    pts = _load_panel_tasks_server()
    assert not pts.is_confirmation_enabled()


def test_lumos_confirm_request_creates_grant(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    pts = _load_panel_tasks_server()
    action_key, scope, preview = pts._panel_mutation_confirmation_spec(
        "/tasks",
        {"title": "Onaylı"},
    )
    assert action_key == "create_task"
    pending = pts.request_confirmation(action_key, scope, preview, base_dir=tmp_path)
    assert pending.confirmation_id
    assert pending.preview == preview
    grant_path = tmp_path / "pending_confirmations" / f"{pending.confirmation_id}.json"
    assert grant_path.is_file()
    grant = json.loads(grant_path.read_text(encoding="utf-8"))
    assert grant["preview"]["what"] == "create_task"
    assert grant["preview"]["where"] == "Onaylı"
    assert grant["preview"]["effect"] == "local_task_create"


def test_lumos_confirm_request_handler_wiring() -> None:
    src = (_REPO_ROOT / "panel" / "scripts" / "panel_tasks_server.py").read_text(encoding="utf-8")
    assert '"/lumos-confirm/request"' in src
    assert "_post_lumos_confirm_request" in src
    assert "request_confirmation" in src
    assert "confirmation_enabled" in src


def test_panel_astro_confirmation_wiring() -> None:
    text = read_panel_source()
    for token in (
        "lumos-confirm-dialog",
        "panelEnsureMutationConfirmation",
        "requestPanelConfirmation",
        "isPanelConfirmationEnabled",
        "confirmation_required",
        "confirmation_expired",
        "scope_mismatch",
        "/lumos-confirm/request",
    ):
        assert token in text, f"missing panel.astro token: {token}"
