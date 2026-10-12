"""Central claim lock / task write controller."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lumos_board.claim_cli import main as claim_cli_main
from lumos_board.task_claim import ClaimError, TaskClaimStore
from lumos_board.write_gate import assert_write


NOW = datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self) -> None:
        self.value = NOW

    def __call__(self) -> datetime:
        return self.value


def _store(tmp_path: Path) -> TaskClaimStore:
    return TaskClaimStore(tmp_path / "board", clock=Clock())


def _claim(store: TaskClaimStore, *, task: str, owner: str, scope: str):
    return store.claim(
        task_id=task,
        repo="lumos-core",
        branch=f"cursor/{task.lower()}",
        worktree=f"/worktrees/{task.lower()}",
        owner=owner,
        scopes=[scope],
    )


def test_owner_may_write_inside_active_claim(tmp_path: Path) -> None:
    store = _store(tmp_path)
    acquired = _claim(store, task="KA-LOCK", owner="agent-a", scope="src/lumos_board")
    assert acquired.accepted
    held = assert_write(
        store,
        task_id="KA-LOCK",
        owner="agent-a",
        repo="lumos-core",
        scopes=["src/lumos_board/task_claim.py"],
    )
    assert held.claim_id == acquired.claim.claim_id


def test_second_agent_cannot_write_same_task(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _claim(store, task="KA-LOCK", owner="agent-a", scope="src/lumos_board")
    with pytest.raises(ClaimError, match="DUPLICATE_TASK"):
        assert_write(
            store,
            task_id="KA-LOCK",
            owner="agent-b",
            repo="lumos-core",
            scopes=["src/lumos_board/write_gate.py"],
        )


def test_overlapping_scope_foreign_owner_is_conflict(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _claim(store, task="KA-ONE", owner="agent-a", scope="src/lumos_board")
    with pytest.raises(ClaimError, match="SCOPE_CONFLICT"):
        assert_write(
            store,
            task_id="KA-TWO",
            owner="agent-b",
            repo="lumos-core",
            scopes=["src/lumos_board/task_claim.py"],
        )


def test_write_without_claim_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ClaimError, match="WRITE_WITHOUT_CLAIM"):
        assert_write(
            store,
            task_id="KA-LOCK",
            owner="agent-a",
            repo="lumos-core",
            scopes=["src/lumos_board/task_claim.py"],
        )


def test_queued_waiter_cannot_write(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = _claim(store, task="KA-LOCK", owner="agent-a", scope="src/lumos_board")
    assert first.accepted
    queued = store.claim(
        task_id="KA-LOCK",
        repo="lumos-core",
        branch="cursor/waiter",
        worktree="/worktrees/waiter",
        owner="agent-b",
        scopes=["src/lumos_board"],
        queue_on_conflict=True,
    )
    assert queued.accepted is False
    with pytest.raises(ClaimError, match="DUPLICATE_TASK"):
        assert_write(
            store,
            task_id="KA-LOCK",
            owner="agent-b",
            repo="lumos-core",
            scopes=["src/lumos_board/task_claim.py"],
        )


def test_write_outside_claimed_scope_is_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _claim(store, task="KA-LOCK", owner="agent-a", scope="src/lumos_board")
    with pytest.raises(ClaimError, match="SCOPE_OUTSIDE_CLAIM"):
        assert_write(
            store,
            task_id="KA-LOCK",
            owner="agent-a",
            repo="lumos-core",
            scopes=["src/kando/agent_runner.py"],
        )


def test_cli_assert_write_conflict_exit_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    store_dir = tmp_path / "board"
    rc = claim_cli_main(
        [
            "--store",
            str(store_dir),
            "claim",
            "--task",
            "KA-LOCK",
            "--repo",
            "lumos-core",
            "--branch",
            "cursor/a",
            "--worktree",
            "/wt/a",
            "--owner",
            "agent-a",
            "--scope",
            "src/lumos_board",
        ]
    )
    assert rc == 0
    rc2 = claim_cli_main(
        [
            "--store",
            str(store_dir),
            "assert-write",
            "--task",
            "KA-LOCK",
            "--owner",
            "agent-b",
            "--repo",
            "lumos-core",
            "--scope",
            "src/lumos_board/write_gate.py",
        ]
    )
    assert rc2 == 2
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["error"] == "DUPLICATE_TASK"


def test_agent_pipeline_blocks_without_claim(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from kando import agent_runner

    monkeypatch.setenv("LUMOS_WRITE_GATE", "1")
    monkeypatch.delenv("LUMOS_TASK_ID", raising=False)
    monkeypatch.delenv("LUMOS_CLAIM_OWNER", raising=False)
    monkeypatch.setattr(
        agent_runner, "select_target_and_task", lambda *_a, **_k: ("src/core/x.py", "t", {})
    )
    monkeypatch.setattr(agent_runner, "_allowed_agent_target", lambda _rel: True)
    report = agent_runner.run_agent_pipeline(
        "görev", human_approved=True, repo_root=tmp_path
    )
    assert report["status"] == "failed"
    assert any("WRITE_WITHOUT_CLAIM" in err for err in report["errors"])


def test_agent_pipeline_lock_allows_claim_owner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from kando import agent_runner

    store_dir = tmp_path / "board"
    rc = claim_cli_main(
        [
            "--store",
            str(store_dir),
            "claim",
            "--task",
            "KA-LOCK",
            "--repo",
            "lumos-core",
            "--branch",
            "cursor/a",
            "--worktree",
            str(tmp_path),
            "--owner",
            "agent-a",
            "--scope",
            "src/core",
        ]
    )
    assert rc == 0
    monkeypatch.setenv("LUMOS_WRITE_GATE", "1")
    monkeypatch.setenv("LUMOS_TASK_ID", "KA-LOCK")
    monkeypatch.setenv("LUMOS_CLAIM_OWNER", "agent-a")
    monkeypatch.setenv("LUMOS_BOARD_DIR", str(store_dir))
    monkeypatch.setattr(
        agent_runner, "select_target_and_task", lambda *_a, **_k: ("src/core/x.py", "t", {})
    )
    monkeypatch.setattr(agent_runner, "_allowed_agent_target", lambda _rel: True)
    monkeypatch.setattr(
        agent_runner,
        "_run_executor_goal",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("should stop after lock in this test")),
    )
    # Owner is allowed through the lock; executor is the next phase.
    report = agent_runner.run_agent_pipeline(
        "görev", human_approved=True, repo_root=tmp_path
    )
    assert report["status"] == "failed"
    assert any("executor" in err for err in report["errors"])
