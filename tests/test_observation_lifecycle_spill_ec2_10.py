"""EC2-10: ObservationEngine disk spill — O1–O6."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from task_engine.observation import (  # noqa: E402
    EVENT_STEP_VERIFIED,
    EVENT_TASK_CREATED,
    ObservationEngine,
    ObservationLifecycleSpill,
    make_event,
)
from task_engine.observation.lifecycle_spill import (  # noqa: E402
    OBSERVATION_LIFECYCLE_SCHEMA,
    observation_lifecycle_path,
    read_recent_observation_lifecycle,
)
from task_engine import TaskEngine, TaskStore  # noqa: E402
from task_engine.profiles import PROFILE_GUVENLI_YURUT  # noqa: E402


def test_o1_spill_record_schema() -> None:
    ev = make_event(1, EVENT_TASK_CREATED, payload={"title": "t"})
    from task_engine.observation.lifecycle_spill import observation_event_to_spill_record

    rec = observation_event_to_spill_record(ev)
    assert rec["schema"] == OBSERVATION_LIFECYCLE_SCHEMA
    assert rec["task_id"] == 1
    assert rec["event_type"] == EVENT_TASK_CREATED


def test_o2_spill_append_and_read(tmp_path: Path) -> None:
    spill = ObservationLifecycleSpill(tmp_path)
    engine = ObservationEngine(lifecycle_spill=spill)
    engine.record_event(make_event(2, EVENT_STEP_VERIFIED, step_id=0))
    path = observation_lifecycle_path(tmp_path)
    assert path.is_file()
    rows = read_recent_observation_lifecycle(tmp_path, limit=10)
    assert len(rows) == 1
    assert rows[0]["event_type"] == EVENT_STEP_VERIFIED


def test_o3_task_engine_auto_wire_spill(tmp_path: Path) -> None:
    store = TaskStore(tmp_path / "tasks" / "tasks.json")
    obs = ObservationEngine()
    engine = TaskEngine(
        store,
        PROFILE_GUVENLI_YURUT,
        True,
        base_dir=tmp_path,
        observation_engine=obs,
    )
    assert engine._observation_engine is not None
    assert engine._observation_engine.lifecycle_spill is not None


def test_o4_no_spill_without_base_dir(tmp_path: Path) -> None:
    obs = ObservationEngine()
    store = TaskStore(tmp_path / "tasks" / "tasks.json")
    engine = TaskEngine(store, PROFILE_GUVENLI_YURUT, True, observation_engine=obs)
    assert engine._observation_engine.lifecycle_spill is None


def test_o5_memory_unchanged_without_spill() -> None:
    engine = ObservationEngine()
    engine.record_event(make_event(3, EVENT_TASK_CREATED))
    assert len(engine.memory) == 1


def test_o6_read_empty_when_no_file(tmp_path: Path) -> None:
    assert read_recent_observation_lifecycle(tmp_path) == []
