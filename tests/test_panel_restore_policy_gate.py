"""ADR-012: POST /tasks/restore — CREATE_TASK policy gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from core.evidence_continuity import OPERATION_PANEL_TASK_RESTORE, title_preview_from  # noqa: E402
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


def _write_trash_task(tmp_path: Path, tid: str, title: str = "restore me") -> Path:
    trash_dir = tmp_path / "trash"
    trash_dir.mkdir(parents=True, exist_ok=True)
    path = trash_dir / f"{tid}.json"
    record = {
        "id": tid,
        "taskId": tid,
        "type": "task_deleted",
        "title": title,
        "payload": {"id": tid, "title": title, "status": "active"},
    }
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def _simulate_restore(
    *,
    monkeypatch,
    tmp_path: Path,
    tid: str,
) -> tuple[str, bool]:
    """_post_restore persist yolu — gate geçerse True."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    pts = _load_panel_tasks_server()
    gate = pts._task_action_gate(CREATE_TASK, log_on_block=True)
    if not gate["enabled"]:
        return "policy_blocked", False
    rid = pts._normalize_ws(tid)
    if not rid:
        return "empty_id", False
    tpath = pts._find_trash_json_for_task_id(rid)
    if tpath is None or not tpath.is_file():
        return "missing_trash", False
    record = json.loads(tpath.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        return "invalid_trash", False
    task = pts._task_from_trash_record(record)
    if not task or not str(task.get("id", "")).strip():
        return "invalid_payload", False
    doc = pts._read_doc()
    tasks = doc.setdefault("tasks", [])
    if not isinstance(tasks, list):
        tasks = []
        doc["tasks"] = tasks
    for existing in tasks:
        if isinstance(existing, dict) and str(existing.get("id", "")).strip() == rid:
            return "already_exists", False
    title = str(task.get("title", ""))
    now = pts._now_iso()
    tasks.append(task)
    ev = {
        "id": pts._new_event_id(),
        "type": "task_restored",
        "taskId": rid,
        "text": title,
        "ts": now,
    }
    doc.setdefault("events", []).append(ev)
    pts._write_doc(
        doc,
        evidence={
            "operation": OPERATION_PANEL_TASK_RESTORE,
            "mutation": "restore",
            "entity_id": rid,
            "route": "POST /tasks/restore",
            "title_preview": title_preview_from(title),
            "events_appended": 1,
        },
    )
    tpath.unlink()
    return "allowed", True


def test_restore_offline_blocked(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("LUMOS_MODE", raising=False)
    trash_path = _write_trash_task(tmp_path, "tsk_off")
    (tmp_path / "tasks.json").write_text('{"v":1,"tasks":[],"events":[]}', encoding="utf-8")
    status, restored = _simulate_restore(monkeypatch=monkeypatch, tmp_path=tmp_path, tid="tsk_off")
    assert status == "policy_blocked"
    assert restored is False
    assert trash_path.is_file()
    assert json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))["tasks"] == []


def test_restore_online_allowed(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "guvenli_yurut")
    monkeypatch.delenv("LUMOS_SESSION_UNLOCKED", raising=False)
    trash_path = _write_trash_task(tmp_path, "tsk_ok", title="geri")
    (tmp_path / "tasks.json").write_text('{"v":1,"tasks":[],"events":[]}', encoding="utf-8")
    status, restored = _simulate_restore(monkeypatch=monkeypatch, tmp_path=tmp_path, tid="tsk_ok")
    assert status == "allowed"
    assert restored is True
    assert not trash_path.is_file()
    doc = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))
    assert doc["tasks"][0]["id"] == "tsk_ok"
    assert doc["events"][-1]["type"] == "task_restored"


def test_restore_handler_uses_policy_gate() -> None:
    src = (_REPO_ROOT / "panel" / "scripts" / "panel_tasks_server.py").read_text(encoding="utf-8")
    block = src.split("def _post_restore")[1].split("\n    def ")[0]
    assert "_task_action_gate(CREATE_TASK" in block
    assert "action_disabled" in block
