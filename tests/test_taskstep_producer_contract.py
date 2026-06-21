"""PR-W1-02: TaskStep producer envanteri + karakterizasyon (test-only).

Sabitleme: planner/registry/store yollarında dört helper metadata alanının
(step_kind, action_key, action_tag, policy_action) mevcut doluluk envanteri;
serialize roundtrip; permanent_delete engine istisna snapshot.
Davranış değişikliği yok.
"""
from __future__ import annotations

import json
import tempfile
from collections.abc import Callable

import pytest

from task_engine.diagnostics import BLOCK_SECURITY_NEVER_AUTO
from task_engine.engine import TaskEngine, TaskStep, TaskStore
from task_engine.planner import plan as planner_plan
from task_engine.profiles import (
    PROFILE_GUVENLI_YURUT,
    PROFILE_RAPOR,
    STEP_TYPE_ANALYZE,
    STEP_TYPE_PLAN,
    STEP_TYPE_READ,
    STEP_TYPE_SAFE_LOCAL,
    get_security_never_auto_member,
)
from task_engine.engine import TaskRecord

# Envanter: üretim yolu → beklenen metadata doluluk sözleşmesi (karakterizasyon).
# action_tag / policy_action TaskStep'te ayrı alan değil; yalnızca helper API'de.
PRODUCER_INVENTORY: tuple[tuple[str, Callable[[], list[TaskStep]], dict[str, bool]], ...] = (
    (
        "planner.generic",
        lambda: planner_plan("genel görev açıklaması"),
        {"step_kind": True, "action_key": False, "action_tag": False, "policy_action": False},
    ),
    (
        "planner.notes",
        lambda: planner_plan("not kontrol ve kısa özet"),
        {"step_kind": True, "action_key": False, "action_tag": False, "policy_action": False},
    ),
    (
        "planner.patch",
        lambda: planner_plan("patch: src/foo.py"),
        {"step_kind": True, "action_key": False, "action_tag": False, "policy_action": False},
    ),
)


def _metadata_from_step(step: TaskStep) -> dict[str, str | None]:
    """TaskStep alanları + helper API için mevcut taşınabilir metadata."""
    return {
        "step_kind": step.kind or None,
        "action_key": step.action_key or None,
        "action_tag": None,
        "policy_action": None,
    }


def _field_populated(meta: dict[str, str | None], field: str) -> bool:
    return bool(meta.get(field))


@pytest.mark.parametrize("path_id,producer,expected", PRODUCER_INVENTORY)
def test_producer_metadata_inventory(
    path_id: str,
    producer: Callable[[], list[TaskStep]],
    expected: dict[str, bool],
) -> None:
    """Her üretim yolunda dört metadata alanının beklenen doluluk envanteri."""
    steps = producer()
    assert steps, f"{path_id}: boş adım listesi"
    for step in steps:
        meta = _metadata_from_step(step)
        for field, should_be_set in expected.items():
            assert _field_populated(meta, field) is should_be_set, (
                f"{path_id} step={step.title!r} field={field} "
                f"expected={should_be_set} meta={meta}"
            )


def test_task_store_create_uses_planner_inventory() -> None:
    """TaskStore.create → planner yolu; action_key boş kalır."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        task = store.create("Özet", "not kontrol", PROFILE_RAPOR)
        assert len(task.steps) >= 1
        for step in task.steps:
            assert step.kind in (
                STEP_TYPE_READ,
                STEP_TYPE_ANALYZE,
                STEP_TYPE_PLAN,
                STEP_TYPE_SAFE_LOCAL,
            )
            assert step.action_key == ""


def test_create_from_steps_preserves_caller_metadata() -> None:
    """TaskStore.create_from_steps — çağıranın action_key değerini taşır."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        steps = [
            TaskStep(
                "Tagged",
                kind=STEP_TYPE_ANALYZE,
                action_key="external_write",
            )
        ]
        task = store.create_from_steps("T", "desc", steps, PROFILE_RAPOR)
        assert task.steps[0].action_key == "external_write"
        assert task.steps[0].kind == STEP_TYPE_ANALYZE


def test_taskstep_action_key_serialize_roundtrip() -> None:
    """TaskStep.to_dict/from_dict ve TaskRecord persist action_key kaybı yok."""
    step = TaskStep(
        "Kalıcı etiket",
        kind=STEP_TYPE_ANALYZE,
        action_key="permanent_delete",
    )
    restored = TaskStep.from_dict(step.to_dict())
    assert restored.action_key == "permanent_delete"
    assert restored.kind == STEP_TYPE_ANALYZE

    record = TaskRecord(
        task_id=1,
        title="T",
        description="D",
        created_at="2026-06-21T00:00:00",
        steps=[step],
    )
    payload = json.dumps(record.to_dict())
    loaded = TaskRecord.from_dict(json.loads(payload))
    assert loaded.steps[0].action_key == "permanent_delete"

    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create_from_steps("T", "D", [step], PROFILE_RAPOR)
        t2 = store.get(t.task_id)
        assert t2 is not None
        assert t2.steps[0].action_key == "permanent_delete"


def test_helper_reads_taskstep_fields_only() -> None:
    """Engine branch yalnızca step.kind + step.action_key ile helper çağırır."""
    step = TaskStep("x", kind=STEP_TYPE_SAFE_LOCAL, action_key="critical_system_config")
    member = get_security_never_auto_member(
        step_kind=step.kind,
        action_key=step.action_key,
        include_permanent_delete=False,
    )
    assert member == "critical_system_config"


def test_permanent_delete_engine_exception_snapshot() -> None:
    """#463 istisna: action_key=permanent_delete engine branch tarafından durdurulmaz."""
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
        assert t2 is not None
        assert t2.block_reason != BLOCK_SECURITY_NEVER_AUTO


def test_engine_never_auto_branch_regression_inventory() -> None:
    """Dar engine branch (#463): üç üye kind veya action_key ile durdurulur."""
    members = ("external_write", "irreversible_user_op", "critical_system_config")
    for member in members:
        with tempfile.TemporaryDirectory() as d:
            store = TaskStore(d)
            t = store.create("Asla", "desc", PROFILE_GUVENLI_YURUT)
            t.steps = [
                TaskStep(
                    "Risk",
                    kind=STEP_TYPE_SAFE_LOCAL,
                    action_key=member,
                )
            ]
            store.update(t)
            engine = TaskEngine(store, PROFILE_GUVENLI_YURUT, general_approval=True)
            ok, _ = engine.run_task(t.task_id)
            assert ok is False, member
            t2 = store.get(t.task_id)
            assert t2 is not None
            assert t2.block_reason == BLOCK_SECURITY_NEVER_AUTO
