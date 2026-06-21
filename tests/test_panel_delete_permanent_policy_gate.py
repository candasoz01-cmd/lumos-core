"""ADR-012: POST /tasks/delete-permanent — DELETE_TASK gate + may_perform_permanent_delete."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from policy.action_policy import DELETE_TASK  # noqa: E402

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


def _simulate_delete_permanent(
    *,
    monkeypatch,
    tmp_path: Path,
    tid: str,
    confirm: bool | str | None = False,
) -> tuple[str, bool]:
    """
    _post_delete_permanent persist yolu — gate + confirm geçerse True.
    Dönüş: (durum, trash_silindi) — durum: allowed | policy_blocked | confirm_blocked
    """
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    pts = _load_panel_tasks_server()
    gate = pts._task_action_gate(DELETE_TASK, log_on_block=True)
    if not gate["enabled"]:
        return "policy_blocked", False
    body: dict = {"id": tid}
    if confirm is not None:
        body["confirm"] = confirm
    user_initiated = pts._body_confirm_user_initiated(body)
    from core.workspace_contract import may_perform_permanent_delete  # noqa: E402

    if not may_perform_permanent_delete(user_initiated):
        return "confirm_blocked", False
    tpath = pts._find_trash_json_for_task_id(tid)
    if tpath is None or not tpath.is_file():
        return "allowed", False
    tpath.unlink()
    doc = pts._read_doc()
    now = pts._now_iso()
    ev = {
        "id": pts._new_event_id(),
        "type": "task_permanently_deleted",
        "taskId": tid,
        "text": tid,
        "ts": now,
    }
    doc.setdefault("events", []).append(ev)
    pts._write_doc(doc, evidence={"skip": True})
    return "allowed", True


def _write_trash_task(tmp_path: Path, tid: str, title: str = "trash item") -> Path:
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


def test_delete_permanent_offline_blocked(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("LUMOS_MODE", raising=False)
    trash_path = _write_trash_task(tmp_path, "tsk_off")
    status, deleted = _simulate_delete_permanent(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        tid="tsk_off",
        confirm=True,
    )
    assert status == "policy_blocked"
    assert deleted is False
    assert trash_path.is_file()


def test_delete_permanent_koruma_blocked(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.delenv("LUMOS_SESSION_UNLOCKED", raising=False)
    trash_path = _write_trash_task(tmp_path, "tsk_koruma")
    status, deleted = _simulate_delete_permanent(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        tid="tsk_koruma",
        confirm=True,
    )
    assert status == "policy_blocked"
    assert deleted is False
    assert trash_path.is_file()


def test_delete_permanent_confirm_required(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_SESSION_UNLOCKED", "true")
    trash_path = _write_trash_task(tmp_path, "tsk_noconfirm")
    status, deleted = _simulate_delete_permanent(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        tid="tsk_noconfirm",
        confirm=False,
    )
    assert status == "confirm_blocked"
    assert deleted is False
    assert trash_path.is_file()


def test_delete_permanent_success(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_SESSION_UNLOCKED", "true")
    trash_path = _write_trash_task(tmp_path, "tsk_ok", title="sil")
    status, deleted = _simulate_delete_permanent(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        tid="tsk_ok",
        confirm=True,
    )
    assert status == "allowed"
    assert deleted is True
    assert not trash_path.is_file()
    doc = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))
    assert doc["events"][-1]["type"] == "task_permanently_deleted"
    assert doc["events"][-1]["taskId"] == "tsk_ok"


def test_delete_permanent_handler_uses_gates() -> None:
    src = (_REPO_ROOT / "panel" / "scripts" / "panel_tasks_server.py").read_text(encoding="utf-8")
    block = src.split("def _post_delete_permanent")[1].split("\n    def ")[0]
    assert "_task_action_gate(DELETE_TASK" in block
    assert "may_perform_permanent_delete" in block
    assert "confirm_required" in block
    assert "_body_confirm_user_initiated" in block
