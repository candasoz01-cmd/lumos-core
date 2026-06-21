"""P2: TaskEngine SECURITY_NEVER_AUTO branch (permanent_delete excluded)."""
from __future__ import annotations

import tempfile

from task_engine.diagnostics import BLOCK_SECURITY_NEVER_AUTO
from task_engine.engine import TaskEngine, TaskStep, TaskStore
from task_engine.observation import EVENT_POLICY_BLOCKED, ObservationEngine, ObservationMemory
from task_engine.profiles import (
    PROFILE_GUVENLI_YURUT,
    PROFILE_KISITLI_OTONOM,
    STEP_TYPE_ANALYZE,
    STEP_TYPE_SAFE_LOCAL,
    STEP_TYPE_WRITE_LOCAL,
    get_security_never_auto_member,
    is_security_never_auto,
)

_ENGINE_MEMBERS = ("external_write", "irreversible_user_op", "critical_system_config")


def test_is_security_never_auto_helper_matches_members() -> None:
    for member in _ENGINE_MEMBERS:
        assert is_security_never_auto(step_kind=member) is True
        assert is_security_never_auto(action_key=member) is True
    assert is_security_never_auto(step_kind="permanent_delete") is True
    assert is_security_never_auto(
        step_kind="permanent_delete", include_permanent_delete=False
    ) is False
    assert is_security_never_auto(step_kind="analyze") is False


def test_get_security_never_auto_member_engine_scope_excludes_permanent_delete() -> None:
    assert get_security_never_auto_member(
        action_key="permanent_delete", include_permanent_delete=False
    ) is None
    assert get_security_never_auto_member(
        action_key="external_write", include_permanent_delete=False
    ) == "external_write"


def test_engine_blocks_never_auto_tagged_safe_local_step() -> None:
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create("Dış yaz", "desc", PROFILE_GUVENLI_YURUT)
        t.steps = [
            TaskStep(
                "Dış servise yaz",
                kind=STEP_TYPE_SAFE_LOCAL,
                action_key="external_write",
            )
        ]
        store.update(t)
        engine = TaskEngine(store, PROFILE_GUVENLI_YURUT, general_approval=True)
        ok, msg = engine.run_task(t.task_id)
        assert ok is False
        t2 = store.get(t.task_id)
        assert t2.status == "durdu"
        assert t2.block_reason == BLOCK_SECURITY_NEVER_AUTO
        assert "external_write" in (t2.error_summary or "")


def test_engine_blocks_never_auto_kind_even_with_approval() -> None:
    for member in _ENGINE_MEMBERS:
        with tempfile.TemporaryDirectory() as d:
            store = TaskStore(d)
            t = store.create("Asla", "desc", PROFILE_KISITLI_OTONOM)
            t.steps = [TaskStep("Riskli", kind=member)]
            store.update(t)
            engine = TaskEngine(store, PROFILE_KISITLI_OTONOM, general_approval=True)
            ok, _ = engine.run_task(t.task_id)
            assert ok is False, member
            t2 = store.get(t.task_id)
            assert t2.block_reason == BLOCK_SECURITY_NEVER_AUTO


def test_engine_blocks_write_local_with_irreversible_tag() -> None:
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create("Geri dönüşsüz", "desc", PROFILE_KISITLI_OTONOM)
        t.steps = [
            TaskStep(
                "Geri dönüşsüz iş",
                kind=STEP_TYPE_WRITE_LOCAL,
                action_key="irreversible_user_op",
            )
        ]
        store.update(t)
        engine = TaskEngine(store, PROFILE_KISITLI_OTONOM, general_approval=True)
        ok, _ = engine.run_task(t.task_id)
        assert ok is False
        t2 = store.get(t.task_id)
        assert t2.block_reason == BLOCK_SECURITY_NEVER_AUTO


def test_engine_permanent_delete_tag_not_blocked_by_never_auto_branch() -> None:
    """permanent_delete excluded from engine branch; profile may still allow analyze."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create("Kalıcı", "desc", PROFILE_GUVENLI_YURUT)
        t.steps = [
            TaskStep(
                "Kalıcı silme etiketi",
                kind=STEP_TYPE_ANALYZE,
                action_key="permanent_delete",
            )
        ]
        store.update(t)
        engine = TaskEngine(store, PROFILE_GUVENLI_YURUT, general_approval=True)
        ok, _ = engine.run_task(t.task_id)
        assert ok is True
        t2 = store.get(t.task_id)
        assert t2.block_reason != BLOCK_SECURITY_NEVER_AUTO


def test_never_auto_block_emits_policy_blocked_event() -> None:
    mem = ObservationMemory(maxlen=20)
    obs = ObservationEngine(memory=mem)
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create("Engel", "desc", PROFILE_GUVENLI_YURUT)
        t.steps = [
            TaskStep(
                "Config",
                kind=STEP_TYPE_SAFE_LOCAL,
                action_key="critical_system_config",
            )
        ]
        store.update(t)
        engine = TaskEngine(
            store, PROFILE_GUVENLI_YURUT, True, base_dir=d, observation_engine=obs
        )
        ok, _ = engine.run_task(t.task_id)
        assert ok is False
    blocked = [e for e in obs.get_recent_events(limit=10) if e.event_type == EVENT_POLICY_BLOCKED]
    assert len(blocked) >= 1
    assert blocked[0].payload.get("reason") == BLOCK_SECURITY_NEVER_AUTO
