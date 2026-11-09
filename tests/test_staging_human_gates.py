"""Staging runtime forces human confirmation and the task-execution grant."""
from __future__ import annotations

from pathlib import Path

import pytest

from policy.confirmation_policy import (
    REASON_CONFIRMATION_REQUIRED,
    check_confirmation,
    is_confirmation_enabled,
)
from policy.task_execution_grant import (
    REASON_MISSING,
    ExecutionBinding,
    accept_execution_task,
    is_task_execution_grant_enabled,
    require_task_execution_grant,
)


def _binding() -> ExecutionBinding:
    return ExecutionBinding(
        subject_id="user:X",
        agent_id="agent:kando",
        session_id="session:s1",
        task_id="G-staging",
        action_key="file_read",
        resource="notes/fileA.md",
        permission="read",
    )


@pytest.fixture(autouse=True)
def _clear_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LUMOS_RUNTIME_ENV", raising=False)
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    monkeypatch.delenv("LUMOS_CONFIRMATION_ENABLED", raising=False)
    monkeypatch.delenv("LUMOS_TASK_EXECUTION_GRANT_ENABLED", raising=False)


def test_local_default_leaves_both_gates_off() -> None:
    assert is_confirmation_enabled() is False
    assert is_task_execution_grant_enabled() is False


def test_explicit_false_stays_off_outside_staging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "false")
    monkeypatch.setenv("LUMOS_TASK_EXECUTION_GRANT_ENABLED", "0")
    assert is_confirmation_enabled() is False
    assert is_task_execution_grant_enabled() is False


@pytest.mark.parametrize("runtime", ["staging", "stage"])
def test_runtime_env_forces_both_gates(
    monkeypatch: pytest.MonkeyPatch,
    runtime: str,
) -> None:
    monkeypatch.setenv("LUMOS_RUNTIME_ENV", runtime)
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "false")
    monkeypatch.setenv("LUMOS_TASK_EXECUTION_GRANT_ENABLED", "false")
    assert is_confirmation_enabled() is True
    assert is_task_execution_grant_enabled() is True


def test_vercel_preview_forces_both_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "0")
    monkeypatch.setenv("LUMOS_TASK_EXECUTION_GRANT_ENABLED", "no")
    assert is_confirmation_enabled() is True
    assert is_task_execution_grant_enabled() is True


def test_staging_confirmation_without_id_denies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_RUNTIME_ENV", "staging")
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "false")
    result = check_confirmation("delete_permanent", {"id": "1"}, {})
    assert result.allowed is False
    assert result.reason == REASON_CONFIRMATION_REQUIRED


def test_staging_task_grant_without_token_denies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LUMOS_RUNTIME_ENV", "staging")
    monkeypatch.setenv("LUMOS_TASK_EXECUTION_GRANT_ENABLED", "false")
    binding = _binding()
    accept_execution_task(binding, base_dir=tmp_path)
    result = require_task_execution_grant("", binding, base_dir=tmp_path)
    assert result.allowed is False
    assert result.reason == REASON_MISSING
