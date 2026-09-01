"""ADR-031: lumos_gate_execute opt-in task execution grant."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from kando_runtime.lumos_gate import execute_approved_pending_record, lumos_gate_execute
from policy.task_execution_grant import (
    CLASSIFICATION_UNCLASSIFIED,
    ENV_ENABLED,
    GRANTS_DIR,
    KIND_CAPABILITY_DEVIATION,
    REASON_MISMATCH,
    REASON_MISSING,
    REASON_USED,
    ExecutionBinding,
    issue_task_execution_grant,
)


@pytest.fixture(autouse=True)
def _clear_grant_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_ENABLED, raising=False)


@pytest.fixture(autouse=True)
def _pin_substep_validator(monkeypatch: pytest.MonkeyPatch) -> None:
    """These tests assert grant semantics, so no live model gets a vote here."""

    def _allow(
        step: dict,
        parent: dict,
        *,
        fallback_marker_key: str = "llm_substep_validation",
    ) -> dict:
        return {"ok": True, "reason": "", "risk_hint": "low"}

    monkeypatch.setattr("kando_runtime.lumos_gate.validate_substep_with_llm", _allow)


def _ctx() -> object:
    return type(
        "Ctx",
        (),
        {
            "policy_ok": True,
            "reasoning_summary": "",
            "execution_mode": "plan",
            "generated_content": None,
            "verification_summary": "",
        },
    )()


def _binding(**overrides: str) -> ExecutionBinding:
    data = {
        "subject_id": "user:alice",
        "task_id": "task-file-1",
        "action_key": "patch",
        "resource": "notes/readme.md",
        "permission": "write",
    }
    data.update(overrides)
    return ExecutionBinding(**data)


def _bundle(tmp_path: Path, **overrides: object) -> dict:
    bundle: dict = {
        "_kind": "run",
        "plan": {
            "steps": [
                {
                    "type": "patch",
                    "file": "notes/readme.md",
                    "content": "summarize notes\n",
                }
            ]
        },
        "ctx": _ctx(),
        "norm": {"target_rel": "notes/readme.md"},
        "reasoning": {"source": "test"},
        "risk": "low",
        "mode": "direct_patch",
        "payload": "TARGET: notes/readme.md\nsummarize notes\n",
        "approval_granted": True,
        "repo_root": tmp_path,
        "audit": None,
        "replay_mode": False,
        "subject_id": "user:alice",
        "task_id": "task-file-1",
        "task_execution_action_key": "patch",
        "task_execution_permission": "write",
    }
    bundle.update(overrides)
    return bundle


def test_lumos_gate_execute_without_token_when_grant_disabled(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def _run_direct(instr: str) -> dict:
        calls.append(instr)
        return {"execution_result": "patch_applied", "detail": ""}

    def _start_agent(_goal: str, _auto: bool) -> str:
        return "job-disabled"

    lumos_gate_execute(
        _bundle(tmp_path),
        run_direct=_run_direct,
        start_agent=_start_agent,
        run_agent_auto=None,
    )
    assert calls, "env off: execute without token must still run"


def test_lumos_gate_execute_matching_minted_grant_when_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_ENABLED, "true")
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    issued = issue_task_execution_grant(_binding(), base_dir=lumos)
    calls: list[str] = []

    def _run_direct(instr: str) -> dict:
        calls.append(instr)
        return {"execution_result": "patch_applied", "detail": ""}

    def _start_agent(_goal: str, _auto: bool) -> str:
        return "job-grant"

    lumos_gate_execute(
        _bundle(tmp_path, task_execution_grant_token=issued.token),
        run_direct=_run_direct,
        start_agent=_start_agent,
        run_agent_auto=None,
    )
    assert calls, "matching grant must reach execute_plan"
    stored = json.loads(
        (lumos / GRANTS_DIR / f"{issued.grant_id}.json").read_text(encoding="utf-8")
    )
    assert stored.get("consumed") is True


def test_lumos_gate_execute_missing_token_denied_not_attacker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_ENABLED, "true")
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    issue_task_execution_grant(_binding(), base_dir=lumos)
    calls: list[str] = []

    def _run_direct(instr: str) -> dict:
        calls.append(instr)
        return {"execution_result": "patch_applied", "detail": ""}

    def _start_agent(_goal: str, _auto: bool) -> str:
        return "job-missing"

    out = lumos_gate_execute(
        _bundle(tmp_path),
        run_direct=_run_direct,
        start_agent=_start_agent,
        run_agent_auto=None,
    )
    assert calls == []
    assert out["blocked"] is True
    assert out["execution_result"] == "task_execution_grant_denied"
    assert out["reason"] == REASON_MISSING
    assert out["classification"] == CLASSIFICATION_UNCLASSIFIED
    assert "attacker" not in json.dumps(out).lower()


def test_lumos_gate_execute_file_read_grant_cannot_send_mail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_ENABLED, "true")
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    issued = issue_task_execution_grant(_binding(), base_dir=lumos)
    calls: list[str] = []

    def _run_direct(instr: str) -> dict:
        calls.append(instr)
        return {"execution_result": "patch_applied", "detail": ""}

    def _start_agent(_goal: str, _auto: bool) -> str:
        return "job-mismatch"

    out = lumos_gate_execute(
        _bundle(
            tmp_path,
            task_execution_action_key="mail_send",
            task_execution_permission="send",
            task_execution_grant_token=issued.token,
        ),
        run_direct=_run_direct,
        start_agent=_start_agent,
        run_agent_auto=None,
    )
    assert calls == []
    assert out["blocked"] is True
    assert out["reason"] == REASON_MISMATCH
    assert out["classification"] == CLASSIFICATION_UNCLASSIFIED
    stored = json.loads(
        (lumos / GRANTS_DIR / f"{issued.grant_id}.json").read_text(encoding="utf-8")
    )
    assert stored.get("consumed") is False


def test_lumos_gate_execute_file_read_grant_cannot_run_patch_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_ENABLED, "true")
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    issued = issue_task_execution_grant(
        _binding(action_key="file_read", permission="read"), base_dir=lumos
    )
    calls: list[str] = []

    def _run_direct(instr: str) -> dict:
        calls.append(instr)
        return {"execution_result": "patch_applied", "detail": ""}

    def _start_agent(_goal: str, _auto: bool) -> str:
        return "job-deviation"

    out = lumos_gate_execute(
        _bundle(
            tmp_path,
            task_execution_action_key="file_read",
            task_execution_permission="read",
            task_execution_grant_token=issued.token,
        ),
        run_direct=_run_direct,
        start_agent=_start_agent,
        run_agent_auto=None,
    )
    assert calls == []
    assert out["blocked"] is True
    assert out["reason"] == REASON_MISMATCH
    assert out["event_kind"] == KIND_CAPABILITY_DEVIATION
    stored = json.loads(
        (lumos / GRANTS_DIR / f"{issued.grant_id}.json").read_text(encoding="utf-8")
    )
    assert stored.get("consumed") is False


def test_lumos_gate_execute_matching_patch_grant_allows_patch_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_ENABLED, "true")
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    issued = issue_task_execution_grant(_binding(), base_dir=lumos)
    calls: list[str] = []

    def _run_direct(instr: str) -> dict:
        calls.append(instr)
        return {"execution_result": "patch_applied", "detail": ""}

    def _start_agent(_goal: str, _auto: bool) -> str:
        return "job-patch"

    lumos_gate_execute(
        _bundle(tmp_path, task_execution_grant_token=issued.token),
        run_direct=_run_direct,
        start_agent=_start_agent,
        run_agent_auto=None,
    )
    assert calls, "plan action matching grant must reach execute_plan"


def test_lumos_gate_execute_agent_plan_with_file_target_rel_consumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_ENABLED, "true")
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    issued = issue_task_execution_grant(
        _binding(
            action_key="agent",
            permission="execute",
            resource="summarize the notes",
        ),
        base_dir=lumos,
    )
    jobs: list[str] = []

    def _run_direct(instr: str) -> dict:
        raise AssertionError(f"patch executor must not run: {instr}")

    def _start_agent(goal: str, _auto: bool) -> str:
        jobs.append(goal)
        return "job-agent"

    out = lumos_gate_execute(
        _bundle(
            tmp_path,
            plan={"steps": [{"type": "agent", "goal": "summarize the notes"}]},
            mode="agent",
            task_execution_action_key="agent",
            task_execution_permission="execute",
            task_execution_grant_token=issued.token,
        ),
        run_direct=_run_direct,
        start_agent=_start_agent,
        run_agent_auto=None,
    )
    assert jobs == ["summarize the notes"]
    assert out.get("blocked") is not True
    stored = json.loads(
        (lumos / GRANTS_DIR / f"{issued.grant_id}.json").read_text(encoding="utf-8")
    )
    assert stored.get("consumed") is True


def test_execute_approved_pending_agent_plan_with_file_target_rel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_ENABLED, "true")
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    issued = issue_task_execution_grant(
        _binding(
            action_key="agent",
            permission="execute",
            resource="summarize the notes",
        ),
        base_dir=lumos,
    )
    jobs: list[str] = []

    def _run_direct(instr: str) -> dict:
        raise AssertionError(f"patch executor must not run: {instr}")

    def _start_agent(goal: str, _auto: bool) -> str:
        jobs.append(goal)
        return "job-approve-agent"

    out = execute_approved_pending_record(
        _pending_record(
            tmp_path,
            mode="agent",
            execution_plan={"steps": [{"type": "agent", "goal": "summarize the notes"}]},
            task_execution_action_key="agent",
            task_execution_permission="execute",
            task_execution_grant_token=issued.token,
        ),
        run_direct=_run_direct,
        start_agent=_start_agent,
        repo_root=tmp_path,
    )
    assert jobs == ["summarize the notes"]
    assert out.get("blocked") is not True
    stored = json.loads(
        (lumos / GRANTS_DIR / f"{issued.grant_id}.json").read_text(encoding="utf-8")
    )
    assert stored.get("consumed") is True


def test_lumos_gate_execute_denies_changed_agent_goal_despite_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_ENABLED, "true")
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    issued = issue_task_execution_grant(
        _binding(
            action_key="agent",
            permission="execute",
            resource="summarize the notes",
        ),
        base_dir=lumos,
    )
    jobs: list[str] = []

    def _run_direct(instr: str) -> dict:
        raise AssertionError(f"patch executor must not run: {instr}")

    def _start_agent(goal: str, _auto: bool) -> str:
        jobs.append(goal)
        return "job-mutated"

    out = lumos_gate_execute(
        _bundle(
            tmp_path,
            plan={
                "steps": [
                    {
                        "type": "agent",
                        "file": "summarize the notes",
                        "goal": "mail_send inbox",
                    }
                ]
            },
            mode="agent",
            task_execution_action_key="agent",
            task_execution_permission="execute",
            task_execution_grant_token=issued.token,
        ),
        run_direct=_run_direct,
        start_agent=_start_agent,
        run_agent_auto=None,
    )
    assert jobs == []
    assert out["blocked"] is True
    assert out["reason"] == REASON_MISMATCH
    assert out["event_kind"] == KIND_CAPABILITY_DEVIATION
    stored = json.loads(
        (lumos / GRANTS_DIR / f"{issued.grant_id}.json").read_text(encoding="utf-8")
    )
    assert stored.get("consumed") is False


def _pending_record(tmp_path: Path, **overrides: object) -> dict:
    record: dict = {
        "schema_version": "lumos.pending_approval.v1",
        "policy_ok": True,
        "final_decision": "await_user_approval",
        "risk_level": "high",
        "execution_mode": "pending_approval",
        "mode": "direct_patch",
        "original_payload": "TARGET: notes/readme.md\nsummarize notes\n",
        "execution_plan": {
            "steps": [
                {
                    "type": "patch",
                    "file": "notes/readme.md",
                    "content": "summarize notes\n",
                }
            ]
        },
        "reasoning_snapshot": {"source": "test"},
        "normalized_task": {"target_rel": "notes/readme.md"},
        "subject_id": "user:alice",
        "task_id": "task-file-1",
        "task_execution_action_key": "patch",
        "task_execution_permission": "write",
    }
    record.update(overrides)
    return record


def test_execute_approved_pending_without_grant_when_disabled(tmp_path: Path) -> None:
    calls: list[str] = []

    def _run_direct(instr: str) -> dict:
        calls.append(instr)
        return {"execution_result": "patch_applied", "detail": ""}

    def _start_agent(_goal: str, _auto: bool) -> str:
        return "job-approve-off"

    execute_approved_pending_record(
        _pending_record(tmp_path),
        run_direct=_run_direct,
        start_agent=_start_agent,
        repo_root=tmp_path,
    )
    assert calls, "flag off: approve-resume must still execute"


def test_execute_approved_pending_missing_grant_denied_when_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_ENABLED, "true")
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    issue_task_execution_grant(_binding(), base_dir=lumos)
    calls: list[str] = []

    def _run_direct(instr: str) -> dict:
        calls.append(instr)
        return {"execution_result": "patch_applied", "detail": ""}

    def _start_agent(_goal: str, _auto: bool) -> str:
        return "job-approve-missing"

    out = execute_approved_pending_record(
        _pending_record(tmp_path),
        run_direct=_run_direct,
        start_agent=_start_agent,
        repo_root=tmp_path,
    )
    assert calls == []
    assert out["blocked"] is True
    assert out["reason"] == REASON_MISSING


def test_execute_approved_pending_file_read_grant_cannot_run_patch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_ENABLED, "true")
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    issued = issue_task_execution_grant(
        _binding(action_key="file_read", permission="read"), base_dir=lumos
    )
    calls: list[str] = []

    def _run_direct(instr: str) -> dict:
        calls.append(instr)
        return {"execution_result": "patch_applied", "detail": ""}

    def _start_agent(_goal: str, _auto: bool) -> str:
        return "job-approve-mismatch"

    out = execute_approved_pending_record(
        _pending_record(
            tmp_path,
            task_execution_action_key="file_read",
            task_execution_permission="read",
            task_execution_grant_token=issued.token,
        ),
        run_direct=_run_direct,
        start_agent=_start_agent,
        repo_root=tmp_path,
    )
    assert calls == []
    assert out["blocked"] is True
    assert out["reason"] == REASON_MISMATCH
    assert out["event_kind"] == KIND_CAPABILITY_DEVIATION
    stored = json.loads(
        (lumos / GRANTS_DIR / f"{issued.grant_id}.json").read_text(encoding="utf-8")
    )
    assert stored.get("consumed") is False


def test_high_risk_approve_matching_grant_consumes_once_replay_denied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_ENABLED, "true")
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    issued = issue_task_execution_grant(_binding(), base_dir=lumos)
    calls: list[str] = []

    def _run_direct(instr: str) -> dict:
        calls.append(instr)
        return {"execution_result": "patch_applied", "detail": ""}

    def _start_agent(_goal: str, _auto: bool) -> str:
        return "job-approve-ok"

    pending_out = lumos_gate_execute(
        _bundle(
            tmp_path,
            risk="high",
            approval_granted=False,
            task_execution_grant_token=issued.token,
        ),
        run_direct=_run_direct,
        start_agent=_start_agent,
        run_agent_auto=None,
    )
    assert calls == []
    pending = pending_out["pending_approval_record"]
    assert pending["task_execution_grant_token"] == issued.token
    stored = json.loads(
        (lumos / GRANTS_DIR / f"{issued.grant_id}.json").read_text(encoding="utf-8")
    )
    assert stored.get("consumed") is False

    first = execute_approved_pending_record(
        pending,
        run_direct=_run_direct,
        start_agent=_start_agent,
        repo_root=tmp_path,
    )
    assert calls, "matching grant must consume then execute"
    assert first.get("blocked") is not True
    stored = json.loads(
        (lumos / GRANTS_DIR / f"{issued.grant_id}.json").read_text(encoding="utf-8")
    )
    assert stored.get("consumed") is True

    replay = execute_approved_pending_record(
        pending,
        run_direct=_run_direct,
        start_agent=_start_agent,
        repo_root=tmp_path,
    )
    assert len(calls) == 1
    assert replay["blocked"] is True
    assert replay["reason"] == REASON_USED
