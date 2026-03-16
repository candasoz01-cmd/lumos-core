from __future__ import annotations

from pathlib import Path


from core.change_plan import ChangePlan, validate_plan
from core.change_sensitivity import ChangeSensitivity
from core.patch_model import PatchFingerprint, PatchMetadata, PatchProposal
from core.plan_registry import (
    clear_plans,
    mark_applied,
    mark_executing,
    mark_ready,
    mark_validated,
    register_plan,
    mark_failed,
)


def _make_patch(tmp_path: Path, rel: str, original: str, proposed: str) -> PatchProposal:
    target = tmp_path / "src" / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(original, encoding="utf-8")
    meta = PatchMetadata(
        reason="test-plan",
        caller="test_change_plan",
        source="test",
        user_initiated=True,
        requires_review=False,
        protected_target=False,
    )
    fp = PatchFingerprint.from_text(original)
    return PatchProposal(
        id=rel,
        target_path=target,
        operation="replace_file",
        original_fingerprint=fp,
        original_text=original,
        proposed_text=proposed,
        metadata=meta,
        diff_text=None,
    )


def test_plan_creation_and_sensitivity(tmp_path: Path):
    p1 = _make_patch(tmp_path, "core/workspace_contract.py", "a", "b")
    p2 = _make_patch(tmp_path, "tools/run_classify.py", "x", "y")

    plan = ChangePlan.new("Update core and tools", [p1, p2])

    assert plan.goal_description == "Update core and tools"
    assert plan.patch_count == 2
    assert len(plan.target_paths) == 2
    # core/ → CRITICAL, tools/ → NORMAL; plan hassasiyeti en yüksek olan
    assert plan.estimated_sensitivity == ChangeSensitivity.CRITICAL


def test_plan_validation_with_duplicate_path(tmp_path: Path):
    p1 = _make_patch(tmp_path, "core/workspace_contract.py", "a", "b")
    # Aynı target_path ile ikinci patch
    p2 = PatchProposal(
        id="dup",
        target_path=p1.target_path,
        operation=p1.operation,
        original_fingerprint=p1.original_fingerprint,
        original_text=p1.original_text,
        proposed_text="c",
        metadata=p1.metadata,
        diff_text=None,
    )
    plan = ChangePlan.new("duplicate", [p1, p2])

    res = validate_plan(plan)
    assert res.ok is False
    assert any("duplicate_patch_for_path" in e for e in res.errors)


def test_plan_registry_lifecycle(tmp_path: Path):
    clear_plans()
    p1 = _make_patch(tmp_path, "core/workspace_contract.py", "a", "b")
    plan = ChangePlan.new("lifecycle", [p1])

    rec = register_plan(plan)
    assert rec.state == "PLAN_CREATED"
    assert rec.plan.plan_id == plan.plan_id

    rec = mark_validated(plan.plan_id)
    assert rec is not None and rec.state == "PLAN_VALIDATED"

    rec = mark_ready(plan.plan_id)
    assert rec is not None and rec.state == "PLAN_READY"

    rec = mark_executing(plan.plan_id)
    assert rec is not None and rec.state == "PLAN_EXECUTING"
    assert rec.executed_at is not None

    rec = mark_applied(plan.plan_id)
    assert rec is not None and rec.state == "PLAN_APPLIED"


def test_plan_failed_with_failed_patches(tmp_path: Path):
    clear_plans()
    p1 = _make_patch(tmp_path, "core/workspace_contract.py", "a", "b")
    p2 = _make_patch(tmp_path, "engine/model_client.py", "x", "y")
    plan = ChangePlan.new("partial-failure", [p1, p2])

    rec = register_plan(plan)
    assert rec.state == "PLAN_CREATED"

    failed_ids = [p2.id]
    rec = mark_failed(plan.plan_id, failed_ids)
    assert rec is not None
    assert rec.state == "PLAN_FAILED"
    assert rec.failed_patches == failed_ids

