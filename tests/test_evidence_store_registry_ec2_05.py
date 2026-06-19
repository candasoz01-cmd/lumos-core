"""EC2-05 — task store registry and dual-store read-only health (R1–R8)."""
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.evidence_continuity import (  # noqa: E402
    PANEL_TASKS_STORE_REL_PATH,
    STORE_PANEL_TASKS,
    STORE_TASK_ENGINE,
    TASK_ENGINE_STORE_REL_PATH,
    resolve_task_store_path,
    task_store_rel_path,
    validate_evidence_record,
)
from core.panel_bridge_state import build_panel_read_state  # noqa: E402


def test_r1_task_store_rel_path_panel_tasks():
    assert task_store_rel_path(STORE_PANEL_TASKS) == PANEL_TASKS_STORE_REL_PATH == "tasks.json"


def test_r2_task_store_rel_path_task_engine():
    assert task_store_rel_path(STORE_TASK_ENGINE) == TASK_ENGINE_STORE_REL_PATH == "tasks/tasks.json"


def test_r3_task_store_rel_path_unknown():
    assert task_store_rel_path("bridge_outbox") is None
    assert task_store_rel_path("unknown") is None


def test_r4_resolve_task_store_path(tmp_path):
    p = resolve_task_store_path(tmp_path, STORE_TASK_ENGINE)
    assert p == tmp_path / "tasks" / "tasks.json"


def test_r5_panel_store_only_health(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    (tmp_path / "tasks.json").write_text(json.dumps({"tasks": []}), encoding="utf-8")
    state = build_panel_read_state(repo_root=_REPO_ROOT)
    summary = state["system"]["system_summary"]
    paths = state["system"]["system_paths"]
    health = state["system"]["system_health"]["task_engine"]
    assert summary["panel_tasks_store_ok"] is True
    assert summary["task_engine_store_ok"] is False
    assert paths.get("panel_tasks") is not None
    assert paths.get("task_engine_tasks") is not None
    assert not (tmp_path / "tasks" / "tasks.json").is_file()
    assert health["status"] == "uyarı"


def test_r6_engine_store_only_health(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    engine_dir = tmp_path / "tasks"
    engine_dir.mkdir()
    (engine_dir / "tasks.json").write_text(
        json.dumps({"tasks": [], "next_id": 1}), encoding="utf-8"
    )
    state = build_panel_read_state(repo_root=_REPO_ROOT)
    summary = state["system"]["system_summary"]
    health = state["system"]["system_health"]["task_engine"]
    assert summary["panel_tasks_store_ok"] is False
    assert summary["task_engine_store_ok"] is True
    assert summary["task_count"] == 0
    assert health["status"] == "uyarı"


def test_r7_both_stores_present(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    (tmp_path / "tasks.json").write_text(
        json.dumps({"tasks": [{"task_id": "p1", "title": "Panel"}]}), encoding="utf-8"
    )
    engine_dir = tmp_path / "tasks"
    engine_dir.mkdir()
    (engine_dir / "tasks.json").write_text(
        json.dumps({"tasks": [{"id": 1, "title": "Engine"}], "next_id": 2}),
        encoding="utf-8",
    )
    state = build_panel_read_state(repo_root=_REPO_ROOT)
    summary = state["system"]["system_summary"]
    paths = state["system"]["system_paths"]
    health = state["system"]["system_health"]["task_engine"]
    assert summary["panel_tasks_store_ok"] is True
    assert summary["task_engine_store_ok"] is True
    assert paths["panel_tasks"] != paths["task_engine_tasks"]
    assert health["status"] == "ok"
    assert "ayrı path" in health["note"]


def test_r8_evidence_validator_regression():
    """EC2-14 frozenset — store enums unchanged."""
    from core.evidence_continuity import build_evidence_record, generate_correlation_id
    from core.evidence_continuity import (
        OPERATION_ENGINE_TASK_MUTATION,
        OUTCOME_OK,
        PHASE_AFTER,
        SOURCE_TASK_ENGINE,
    )

    rec = build_evidence_record(
        correlation_id=generate_correlation_id(),
        source=SOURCE_TASK_ENGINE,
        store=STORE_TASK_ENGINE,
        operation=OPERATION_ENGINE_TASK_MUTATION,
        phase=PHASE_AFTER,
        outcome=OUTCOME_OK,
        mutation="create",
        entity_id="tsk_1",
    )
    assert validate_evidence_record(rec) == []
