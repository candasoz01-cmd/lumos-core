"""ADR-031: lumos_gate_execute opt-in task execution grant."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from kando_runtime.lumos_gate import lumos_gate_execute
from policy.task_execution_grant import (
    CLASSIFICATION_UNCLASSIFIED,
    ENV_ENABLED,
    GRANTS_DIR,
    REASON_MISMATCH,
    REASON_MISSING,
    ExecutionBinding,
    issue_task_execution_grant,
)


@pytest.fixture(autouse=True)
def _clear_grant_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_ENABLED, raising=False)


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
        "action_key": "file_read",
        "resource": "notes/readme.md",
        "permission": "read",
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
        "approval_granted": False,
        "repo_root": tmp_path,
        "audit": None,
        "replay_mode": False,
        "subject_id": "user:alice",
        "task_id": "task-file-1",
        "task_execution_action_key": "file_read",
        "task_execution_permission": "read",
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
    (tmp_path / ".lumos").mkdir()
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
            task_id="task-mail-1",
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
