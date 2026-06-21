"""PR-C3: POST /tasks — confirmation gate when LUMOS_CONFIRMATION_ENABLED."""

from __future__ import annotations

import json
import sys
from pathlib import Path

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


def _simulate_create(*, monkeypatch, tmp_path: Path, body: dict) -> bool:
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    pts = _load_panel_tasks_server()
    title = pts._normalize_ws(body.get("title", ""))
    if not title:
        return False
    scope = {"title": title}
    confirmation_id = str(body.get("confirmation_id") or "").strip()
    gate = pts._task_action_gate(
        CREATE_TASK,
        log_on_block=True,
        confirmation_id=confirmation_id,
        scope=scope,
    )
    if not gate["enabled"]:
        return False
    conf_err = pts._enforce_panel_mutation_confirmation(CREATE_TASK, body, scope)
    if conf_err is not None:
        return False
    doc = pts._read_doc()
    now = pts._now_iso()
    tid = pts._new_task_id()
    task = {
        "id": tid,
        "title": title,
        "status": "active",
        "createdAt": now,
        "completedAt": None,
    }
    doc.setdefault("tasks", []).append(task)
    pts._write_doc(
        doc,
        evidence={
            "operation": "panel_task_create",
            "mutation": "create",
            "entity_id": tid,
            "route": "POST /tasks",
            "events_appended": 0,
        },
    )
    return True


def test_create_confirmation_enabled_blocked(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "guvenli_yurut")
    allowed = _simulate_create(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        body={"title": "Yeni görev"},
    )
    assert allowed is False
    assert not (tmp_path / "tasks.json").is_file()


def test_create_confirmation_enabled_with_grant(tmp_path, monkeypatch) -> None:
    from policy.confirmation_policy import request_confirmation  # noqa: E402

    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "guvenli_yurut")
    title = "Onaylı görev"
    scope = {"title": title}
    pending = request_confirmation("create_task", scope, base_dir=tmp_path)
    allowed = _simulate_create(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        body={"title": title, "confirmation_id": pending.confirmation_id},
    )
    assert allowed is True
    doc = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))
    assert any(t.get("title") == title for t in doc.get("tasks", []))
