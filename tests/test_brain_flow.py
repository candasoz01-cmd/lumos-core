"""Brain flow tests: user request → plan → task execution → verification → observation → response."""
import tempfile

from core.brain import (
    parse_request_to_goal,
    build_response,
    run as brain_run,
    BrainResult,
)
from task_engine import TaskStore, TaskEngine, PROFILE_GUVENLI_YURUT, PROFILE_RAPOR
from task_engine.engine import TaskRecord, TaskStep
from task_engine.observation import ObservationEngine
from task_engine.planner import plan as planner_plan_import


def test_user_request_to_plan():
    """User request is parsed to goal; Planner produces steps from goal."""
    goal = parse_request_to_goal("  not sistemini kontrol et  ")
    assert goal == "not sistemini kontrol et"
    steps = planner_plan_import(goal)
    assert len(steps) >= 1
    assert all(hasattr(s, "title") and hasattr(s, "kind") for s in steps)

    goal2 = parse_request_to_goal("")
    assert goal2 == ""
    steps2 = planner_plan_import("genel analiz")
    assert len(steps2) >= 1


def test_plan_to_task_execution():
    """Planned steps → create_from_steps → run_task executes and updates task."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        steps = planner_plan_import("not sistemini kontrol et ve özet ver")
        task = store.create_from_steps(
            title="Kontrol",
            description="not sistemini kontrol et ve özet ver",
            steps=steps,
            permission_profile=PROFILE_GUVENLI_YURUT,
        )
        assert task.task_id >= 1
        assert len(task.steps) == len(steps)
        engine = TaskEngine(store, PROFILE_GUVENLI_YURUT, True, base_dir=d)
        ok, _ = engine.run_task(task.task_id)
        assert ok is True
        task2 = store.get(task.task_id)
        assert task2 is not None
        assert task2.status in ("tamamlandi", "kismi", "dogrulanamadi", "simulasyon")


def test_task_execution_to_verification():
    """After run_task, task has verification counts and final status."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        steps = planner_plan_import("görevi analiz et")
        task = store.create_from_steps(
            title="Analiz",
            description="görevi analiz et",
            steps=steps,
            permission_profile=PROFILE_GUVENLI_YURUT,
        )
        engine = TaskEngine(store, PROFILE_GUVENLI_YURUT, True, base_dir=d)
        engine.run_task(task.task_id)
        task_after = store.get(task.task_id)
        assert task_after is not None
        assert hasattr(task_after, "verified_count")
        assert hasattr(task_after, "unverified_count")
        assert hasattr(task_after, "simulation_count")
        assert task_after.status in (
            "tamamlandi",
            "kismi",
            "dogrulanamadi",
            "simulasyon",
            "hata",
            "durdu",
        )


def test_verification_to_observation():
    """With observation_engine, run_task records events (task_created, action_executed, step_verified/step_failed)."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        obs = ObservationEngine()
        steps = planner_plan_import("kısa özet hazırla")
        task = store.create_from_steps(
            title="Özet",
            description="kısa özet hazırla",
            steps=steps,
            permission_profile=PROFILE_RAPOR,
        )
        engine = TaskEngine(
            store, PROFILE_RAPOR, True, base_dir=d, observation_engine=obs
        )
        engine.run_task(task.task_id)
        events = obs.get_recent_events(limit=20)
        task_events = [e for e in events if e.task_id == task.task_id]
        assert len(task_events) >= 1
        types = {e.event_type for e in task_events}
        assert "task_created" in types or "action_executed" in types or "step_verified" in types or "step_failed" in types


def test_final_response_summary_built_correctly():
    """build_response and full brain.run() produce summary with goal, task id, status, counts, reason/observation."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        obs = ObservationEngine()
        result = brain_run(
            "not sistemini kontrol et",
            store,
            d,
            PROFILE_GUVENLI_YURUT,
            True,
            observation_engine=obs,
        )
        assert isinstance(result, BrainResult)
        assert result.goal == "not sistemini kontrol et"
        assert result.task_id >= 1
        assert result.task_status in (
            "tamamlandi",
            "kismi",
            "dogrulanamadi",
            "simulasyon",
            "hata",
            "durdu",
        )
        assert result.verified_count >= 0
        assert result.unverified_count >= 0
        assert result.simulation_count >= 0
        assert "Hedef:" in result.human_readable_summary or "not" in result.human_readable_summary
        assert "Görev:" in result.human_readable_summary or str(result.task_id) in result.human_readable_summary
        assert "Durum:" in result.human_readable_summary

        task = store.get(result.task_id)
        assert task is not None
        summary2 = build_response(result.goal, task, obs.get_recent_events(limit=10))
        assert "Durum:" in summary2
        assert str(result.task_id) in summary2 or "Görev:" in summary2


def test_brain_empty_request():
    """Empty request returns a safe BrainResult with no task created."""
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        result = brain_run("", store, d, PROFILE_GUVENLI_YURUT, True)
    assert result.success is False
    assert result.task_id == 0
    assert "boş" in result.human_readable_summary.lower() or "Hedef boş" in result.message
