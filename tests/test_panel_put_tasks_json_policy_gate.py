"""ADR-012: PUT /tasks.json — check_policy gate (SECURITY_NEVER_AUTO enforcement map)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from core.evidence_continuity import OPERATION_PANEL_TASK_PUT  # noqa: E402
from policy.action_policy import CREATE_TASK  # noqa: E402

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


def _simulate_put_doc(*, monkeypatch, tmp_path: Path, body: dict) -> bool:
    """do_PUT persist yolu — gate + confirmation geçerse True, redde False."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    pts = _load_panel_tasks_server()
    scope = {"route": "PUT /tasks.json"}
    confirmation_id = str(body.get("confirmation_id") or "").strip()
    gate = pts._task_action_gate(
        CREATE_TASK,
        log_on_block=True,
        full_doc_replace=True,
        confirmation_id=confirmation_id,
        scope=scope,
    )
    if not gate["enabled"]:
        return False
    conf_err = pts._enforce_panel_mutation_confirmation(
        CREATE_TASK,
        body,
        scope,
        full_doc_replace=True,
    )
    if conf_err is not None:
        return False
    doc = pts._empty_doc()
    doc["v"] = 1
    if isinstance(body.get("tasks"), list):
        doc["tasks"] = body["tasks"]
    if isinstance(body.get("events"), list):
        doc["events"] = body["events"]
    pts._write_doc(
        doc,
        evidence={
            "operation": OPERATION_PANEL_TASK_PUT,
            "mutation": "update",
            "route": "PUT /tasks.json",
            "events_appended": 0,
        },
    )
    return True


def test_put_tasks_json_offline_blocked(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("LUMOS_MODE", raising=False)
    tasks_file = tmp_path / "tasks.json"
    tasks_file.write_text(
        '{"v":1,"tasks":[{"id":"tsk_1","title":"keep"}],"events":[]}',
        encoding="utf-8",
    )
    allowed = _simulate_put_doc(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        body={"tasks": [{"id": "tsk_2", "title": "new"}], "events": []},
    )
    assert allowed is False
    assert "keep" in tasks_file.read_text(encoding="utf-8")


def test_put_tasks_json_online_allowed(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "kisitli_otonom")
    monkeypatch.setenv("LUMOS_GENERAL_APPROVAL", "true")
    monkeypatch.delenv("LUMOS_SESSION_UNLOCKED", raising=False)
    allowed = _simulate_put_doc(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        body={"tasks": [{"id": "tsk_new", "title": "allowed"}], "events": []},
    )
    assert allowed is True
    saved = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))
    assert saved["tasks"][0]["id"] == "tsk_new"


def test_put_tasks_json_guvenli_yurut_profile_blocked(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "guvenli_yurut")
    tasks_file = tmp_path / "tasks.json"
    tasks_file.write_text(
        '{"v":1,"tasks":[{"id":"tsk_1","title":"keep"}],"events":[]}',
        encoding="utf-8",
    )
    allowed = _simulate_put_doc(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        body={"tasks": [{"id": "tsk_2", "title": "new"}], "events": []},
    )
    assert allowed is False
    assert "keep" in tasks_file.read_text(encoding="utf-8")


def test_put_handler_uses_policy_gate() -> None:
    src = (_REPO_ROOT / "panel" / "scripts" / "panel_tasks_server.py").read_text(encoding="utf-8")
    assert "def do_PUT" in src
    put_block = src.split("def do_PUT")[1].split("\n    def do_POST")[0]
    assert "_task_action_gate(" in put_block
    assert "CREATE_TASK" in put_block
    assert "full_doc_replace=True" in put_block
    assert "action_disabled" in put_block
    assert "_enforce_panel_mutation_confirmation" in put_block


def test_put_tasks_json_confirmation_enabled_blocked(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "kisitli_otonom")
    monkeypatch.setenv("LUMOS_GENERAL_APPROVAL", "true")
    tasks_file = tmp_path / "tasks.json"
    tasks_file.write_text(
        '{"v":1,"tasks":[{"id":"tsk_1","title":"keep"}],"events":[]}',
        encoding="utf-8",
    )
    allowed = _simulate_put_doc(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        body={"tasks": [{"id": "tsk_2", "title": "new"}], "events": []},
    )
    assert allowed is False
    assert "keep" in tasks_file.read_text(encoding="utf-8")


def test_put_tasks_json_confirmation_enabled_with_grant(tmp_path, monkeypatch) -> None:
    from policy.confirmation_policy import request_confirmation  # noqa: E402

    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "kisitli_otonom")
    monkeypatch.setenv("LUMOS_GENERAL_APPROVAL", "true")
    scope = {"route": "PUT /tasks.json"}
    pending = request_confirmation("write_local", scope, base_dir=tmp_path)
    allowed = _simulate_put_doc(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        body={
            "tasks": [{"id": "tsk_new", "title": "confirmed"}],
            "events": [],
            "confirmation_id": pending.confirmation_id,
        },
    )
    assert allowed is True
    saved = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))
    assert saved["tasks"][0]["id"] == "tsk_new"
