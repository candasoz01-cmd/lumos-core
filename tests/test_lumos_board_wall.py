"""ADR-025: Agent Wall salt-okunur görünürlük — komut yüzeyi yok."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lumos_board.claim_cli import main as claim_cli_main
from lumos_board.task_claim import ClaimStatus, TaskClaimStore
from lumos_board.wall import WallState, format_wall_table, read_wall_projection

NOW = datetime(2026, 8, 17, 18, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self) -> None:
        self.value = NOW

    def __call__(self) -> datetime:
        return self.value


def _claim(store: TaskClaimStore, *, task: str, owner: str, scope: str, **kwargs: object):
    return store.claim(
        task_id=task,
        repo="lumos-core",
        branch=f"codex/{task.lower()}-{owner}",
        worktree=f"/worktrees/{task.lower()}-{owner}",
        owner=owner,
        scopes=[scope],
        **kwargs,
    )


def _write_status(
    directory: Path,
    job_id: str,
    *,
    agent_id: str,
    owner: str,
    status: str,
    updated_at: str = "2026-08-17T17:59:00+00:00",
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "agent_id": agent_id,
        "job_id": job_id,
        "status": status,
        "owner": owner,
        "started_at": "2026-08-17T17:00:00+00:00",
        "updated_at": updated_at,
        "evidence_ref": f"outbox/agent_status_{job_id}.json",
        "message": f"job {job_id}",
    }
    (directory / f"agent_status_{job_id}.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_empty_wall_has_zero_counts_and_no_command_surface(tmp_path: Path) -> None:
    projection = read_wall_projection(TaskClaimStore(tmp_path, clock=Clock()), now=NOW)
    payload = projection.to_dict()
    assert payload["read_only"] is True
    assert payload["command_surface"] is False
    assert payload["counts"] == {
        "WORKING": 0,
        "WAITING": 0,
        "BLOCKED": 0,
        "NEEDS_DECISION": 0,
    }
    assert payload["rows"] == []
    table = format_wall_table(projection)
    assert "komut yok" in table
    assert "(açık satır yok)" in table
    assert "durdur" not in table


def test_active_and_queued_claims_split_working_and_waiting(tmp_path: Path) -> None:
    store = TaskClaimStore(tmp_path, clock=Clock())
    first = _claim(store, task="KA-001", owner="cursor", scope="src/lumos_board")
    assert first.accepted
    queued = _claim(
        store,
        task="KA-001",
        owner="codex",
        scope="src/lumos_board/wall.py",
        queue_on_conflict=True,
    )
    assert queued.claim is not None
    assert queued.claim.status is ClaimStatus.QUEUED
    projection = read_wall_projection(store, now=NOW)
    by_agent = {row.agent: row for row in projection.rows}
    assert by_agent["cursor"].state is WallState.WORKING
    assert by_agent["cursor"].decision_needed == ""
    assert by_agent["codex"].state is WallState.WAITING
    assert "cursor" in by_agent["codex"].waiting_on
    assert projection.counts["WORKING"] == 1
    assert projection.counts["WAITING"] == 1


def test_stale_heartbeat_is_blocked_not_a_command(tmp_path: Path) -> None:
    clock = Clock()
    store = TaskClaimStore(tmp_path, clock=clock)
    _claim(store, task="KA-001", owner="cursor", scope="src/lumos_board")
    clock.value = NOW + timedelta(seconds=121)
    projection = read_wall_projection(store, now=clock.value, stale_after_seconds=120)
    assert len(projection.rows) == 1
    row = projection.rows[0]
    assert row.state is WallState.BLOCKED
    assert row.waiting_on == "heartbeat"
    assert "sessiz" in row.decision_needed
    assert "durdur" not in row.decision_needed


def test_failed_status_and_owner_conflict_surface_on_wall(tmp_path: Path) -> None:
    store = TaskClaimStore(tmp_path, clock=Clock())
    failed_dir = tmp_path / "failed"
    claude_dir = tmp_path / "claude"
    codex_dir = tmp_path / "codex"
    _write_status(failed_dir, "jobfail", agent_id="kando.a", owner="agent-a", status="failed")
    _write_status(claude_dir, "shared", agent_id="claude.code", owner="claude.code", status="running")
    _write_status(codex_dir, "shared", agent_id="codex.cli", owner="codex.cli", status="running")
    projection = read_wall_projection(
        store,
        status_sources={"failed": failed_dir, "claude": claude_dir, "codex": codex_dir},
        now=NOW,
    )
    states = {row.state for row in projection.rows}
    assert WallState.BLOCKED in states
    assert WallState.NEEDS_DECISION in states
    decisions = " ".join(row.decision_needed for row in projection.rows)
    assert "Sahiplik çakışması" in decisions


def test_waiting_on_and_conflict_mask_secretlike_text(tmp_path: Path) -> None:
    store = TaskClaimStore(tmp_path, clock=Clock())
    first = _claim(
        store,
        task="KA-001",
        owner="cursor",
        scope="src/lumos_board",
    )
    assert first.accepted
    queued = _claim(
        store,
        task="KA-001",
        owner="api_key=sk-wallsecret",
        scope="src/lumos_board/wall.py",
        queue_on_conflict=True,
    )
    assert queued.claim is not None
    secret_dir = tmp_path / "secret"
    other_dir = tmp_path / "other"
    _write_status(
        secret_dir,
        "shared",
        agent_id="kando.a",
        owner="api_key=sk-wallsecret",
        status="running",
    )
    _write_status(
        other_dir,
        "shared",
        agent_id="kando.b",
        owner="codex.cli",
        status="running",
    )
    projection = read_wall_projection(
        store,
        status_sources={"secret": secret_dir, "other": other_dir},
        now=NOW,
    )
    blob = json.dumps(projection.to_dict())
    assert "sk-wallsecret" not in blob
    assert "[redacted]" in blob


def test_cli_list_is_the_wall_surface(tmp_path: Path, capsys) -> None:
    assert (
        claim_cli_main(
            [
                "--store",
                str(tmp_path),
                "claim",
                "--task",
                "KA-001",
                "--repo",
                "lumos-core",
                "--branch",
                "codex/ka-001",
                "--worktree",
                "/worktrees/ka-001",
                "--scope",
                "src/lumos_board",
                "--owner",
                "cursor",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert claim_cli_main(["--store", str(tmp_path), "list", "--format", "json"]) == 0
    list_payload = json.loads(capsys.readouterr().out)
    assert claim_cli_main(["--store", str(tmp_path), "wall", "--format", "json"]) == 0
    wall_payload = json.loads(capsys.readouterr().out)
    assert list_payload == wall_payload
    assert list_payload["read_only"] is True
    assert list_payload["command_surface"] is False
    assert list_payload["rows"][0]["state"] == "WORKING"
    assert "stop" not in list_payload
    assert "approve" not in list_payload

    assert claim_cli_main(["--store", str(tmp_path), "list"]) == 0
    table = capsys.readouterr().out
    assert "komut yok" in table
    assert "çalışıyor" in table

    assert claim_cli_main(["--store", str(tmp_path), "list", "--raw"]) == 0
    raw = json.loads(capsys.readouterr().out)
    assert "claims" in raw
    assert raw["claims"][0]["owner"] == "cursor"
