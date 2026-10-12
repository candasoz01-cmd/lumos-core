"""Central claim board: one shared lock for every agent (Claude, Cursor, Mac).

The remote here is a real bare git repository and every "agent" has its own
cache directory, exactly like separate clones on separate machines. The race
tests start real OS processes that fire at the same instant.
"""

from __future__ import annotations

import itertools
import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from lumos_board import claim_cli
from lumos_board.central_store import (
    DEFAULT_REF,
    CentralClaimStore,
    CentralStoreUnavailable,
    _CasLost,
)
from lumos_board.task_claim import ClaimStatus, ClaimStoreCorrupt, TaskClaimStore
from lumos_board.wall_observer import read_claims

SRC = str(Path(__file__).resolve().parents[1] / "src")


def _git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture()
def remote(tmp_path: Path) -> Path:
    path = tmp_path / "remote.git"
    _git("init", "--bare", "-q", str(path))
    return path


def _store(remote: Path, tmp_path: Path, name: str, **kwargs: object) -> CentralClaimStore:
    return CentralClaimStore(remote=str(remote), cache_dir=tmp_path / f"agent-{name}", **kwargs)


def _claim(store: CentralClaimStore, *, task: str, owner: str, scope: str, **kwargs: object):
    return store.claim(
        task_id=task,
        repo="lumos-core",
        branch=f"{owner}/{task}",
        worktree=f"/work/{owner}",
        owner=owner,
        scopes=[scope],
        **kwargs,
    )


def _board_log(remote: Path) -> list[str]:
    return _git("--git-dir", str(remote), "log", "--format=%H %P", DEFAULT_REF).splitlines()


def _board_state(remote: Path) -> dict:
    return json.loads(_git("--git-dir", str(remote), "show", f"{DEFAULT_REF}:claims.json"))


# -- one shared truth --------------------------------------------------------


def test_second_agent_sees_first_agents_claim_and_is_rejected(remote: Path, tmp_path: Path) -> None:
    claude = _store(remote, tmp_path, "claude")
    cursor = _store(remote, tmp_path, "cursor")

    first = _claim(claude, task="G1", owner="claude-cloud", scope="packages/kando_runtime/src/kando_runtime/lumos_gate.py")
    second = _claim(cursor, task="G1-cursor", owner="cursor-agent", scope="packages/kando_runtime/src/kando_runtime/lumos_gate.py")

    assert first.accepted is True
    assert second.accepted is False
    assert [c.reason for c in second.conflicts] == ["SCOPE_CONFLICT"]
    assert second.conflicts[0].owner == "claude-cloud"
    assert [c.owner for c in cursor.list_claims()] == ["claude-cloud"]


def test_duplicate_task_is_rejected_across_agents(remote: Path, tmp_path: Path) -> None:
    _claim(_store(remote, tmp_path, "mac"), task="KA-1", owner="mac", scope="a.py")
    result = _claim(_store(remote, tmp_path, "cursor"), task="KA-1", owner="cursor", scope="b.py")
    assert result.accepted is False
    assert [c.reason for c in result.conflicts] == ["DUPLICATE_TASK"]


def test_directory_scope_blocks_file_inside_it_across_agents(remote: Path, tmp_path: Path) -> None:
    _claim(_store(remote, tmp_path, "a"), task="T1", owner="a", scope="src/lumos_board")
    result = _claim(_store(remote, tmp_path, "b"), task="T2", owner="b", scope="src/lumos_board/claim_cli.py")
    assert result.accepted is False


def test_release_is_visible_to_other_agent_and_frees_scope(remote: Path, tmp_path: Path) -> None:
    a = _store(remote, tmp_path, "a")
    b = _store(remote, tmp_path, "b")
    held = _claim(a, task="T1", owner="a", scope="x.py")
    assert _claim(b, task="T2", owner="b", scope="x.py").accepted is False
    a.release(held.claim.claim_id, owner="a")
    assert _claim(b, task="T2", owner="b", scope="x.py").accepted is True


def test_queue_promotion_happens_on_the_shared_board(remote: Path, tmp_path: Path) -> None:
    a = _store(remote, tmp_path, "a")
    b = _store(remote, tmp_path, "b")
    held = _claim(a, task="T1", owner="a", scope="x.py")
    queued = _claim(b, task="T2", owner="b", scope="x.py", queue_on_conflict=True)
    assert queued.claim.status is ClaimStatus.QUEUED
    a.release(held.claim.claim_id, owner="a")
    statuses = {c.owner: c.status for c in b.list_claims()}
    assert statuses == {"b": ClaimStatus.ACTIVE}


def test_other_agent_cannot_release_or_heartbeat_foreign_claim(remote: Path, tmp_path: Path) -> None:
    held = _claim(_store(remote, tmp_path, "a"), task="T1", owner="a", scope="x.py")
    intruder = _store(remote, tmp_path, "b")
    with pytest.raises(Exception, match="sahibi"):
        intruder.release(held.claim.claim_id, owner="b")
    with pytest.raises(Exception, match="sahibi"):
        intruder.heartbeat(held.claim.claim_id, owner="b")


# -- atomicity: compare-and-swap on the remote ref ---------------------------


def test_lost_race_is_rerun_against_new_state_and_sees_winner(remote: Path, tmp_path: Path) -> None:
    winner = _store(remote, tmp_path, "winner")

    class RacingStore(CentralClaimStore):
        raced = False

        def _push(self, commit: str) -> None:
            if not RacingStore.raced:
                RacingStore.raced = True
                # The winner lands between our fetch and our push.
                assert _claim(winner, task="W", owner="winner", scope="x.py").accepted
            super()._push(commit)

    loser = RacingStore(remote=str(remote), cache_dir=tmp_path / "agent-loser")
    result = _claim(loser, task="L", owner="loser", scope="x.py")

    assert RacingStore.raced is True
    assert result.accepted is False
    assert result.conflicts[0].owner == "winner"
    owners = [c["owner"] for c in _board_state(remote)["claims"]]
    assert owners == ["winner"]


def test_board_history_is_linear_and_never_rewritten(remote: Path, tmp_path: Path) -> None:
    a = _store(remote, tmp_path, "a")
    held = _claim(a, task="T1", owner="a", scope="x.py")
    seen_after_first = _board_log(remote)[0].split()[0]
    a.attach_pr(held.claim.claim_id, owner="a", pr_ref="o/r#1")
    a.release(held.claim.claim_id, owner="a")
    log = _board_log(remote)
    assert len(log) == 3
    # every commit's parent is the previous one: pure fast-forward history
    for newer, older in itertools.pairwise(log):
        assert newer.split()[1] == older.split()[0]
    assert log[-1].split()[0] == seen_after_first
    events = _git("--git-dir", str(remote), "show", f"{DEFAULT_REF}:claim_events.jsonl").splitlines()
    assert [json.loads(e)["event"] for e in events] == [
        "CLAIM_ACQUIRED",
        "CLAIM_PR_ATTACHED",
        "CLAIM_RELEASED",
    ]


def test_read_only_listing_does_not_write_a_commit(remote: Path, tmp_path: Path) -> None:
    a = _store(remote, tmp_path, "a")
    _claim(a, task="T1", owner="a", scope="x.py")
    before = _board_log(remote)
    _store(remote, tmp_path, "b").list_claims()
    assert _board_log(remote) == before


def test_board_commits_disable_vercel_previews(remote: Path, tmp_path: Path) -> None:
    _claim(_store(remote, tmp_path, "a"), task="T1", owner="a", scope="x.py")
    vercel = json.loads(_git("--git-dir", str(remote), "show", f"{DEFAULT_REF}:vercel.json"))
    assert vercel == {"git": {"deploymentEnabled": False}}


_RACER = textwrap.dedent(
    """
    import json, sys, time
    sys.path.insert(0, {src!r})
    from pathlib import Path
    from lumos_board.central_store import CentralClaimStore
    remote, cache, owner, task, scope, start = sys.argv[1:7]
    store = CentralClaimStore(remote=remote, cache_dir=Path(cache))
    while time.time() < float(start):
        pass
    result = store.claim(task_id=task, repo="lumos-core", branch=owner, worktree="/w/" + owner,
                         owner=owner, scopes=[scope])
    print(json.dumps({{"owner": owner, "accepted": result.accepted,
                      "conflicts": [c.reason for c in result.conflicts]}}))
    """
)


@pytest.mark.parametrize("agents", [2, 6])
def test_real_concurrent_processes_exactly_one_wins(remote: Path, tmp_path: Path, agents: int) -> None:
    script = tmp_path / "racer.py"
    script.write_text(_RACER.format(src=SRC), encoding="utf-8")
    start = time.time() + 2.0
    procs = [
        subprocess.Popen(
            [sys.executable, str(script), str(remote), str(tmp_path / f"cache-{i}"),
             f"agent-{i}", f"TASK-{i}", "packages/kando_runtime/src/kando_runtime/lumos_gate.py", str(start)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for i in range(agents)
    ]
    results = []
    for proc in procs:
        out, err = proc.communicate(timeout=120)
        assert proc.returncode == 0, err
        results.append(json.loads(out.strip().splitlines()[-1]))

    winners = [r for r in results if r["accepted"]]
    losers = [r for r in results if not r["accepted"]]
    assert len(winners) == 1, results
    assert all(r["conflicts"] == ["SCOPE_CONFLICT"] for r in losers), results
    claims = _board_state(remote)["claims"]
    assert [(c["owner"], c["status"]) for c in claims] == [(winners[0]["owner"], "ACTIVE")]


def test_real_two_agent_cli_conflict(remote: Path, tmp_path: Path) -> None:
    """Two agents, two clones, the actual CLI: the second is refused (exit 2)."""
    env = dict(os.environ, PYTHONPATH=SRC, LUMOS_BOARD_REMOTE=str(remote))
    env.pop("LUMOS_BOARD_DIR", None)

    def run(agent: str, task: str) -> subprocess.CompletedProcess[str]:
        clone = tmp_path / f"clone-{agent}"
        clone.mkdir(exist_ok=True)
        _git("init", "-q", cwd=clone)
        return subprocess.run(
            [sys.executable, "-m", "lumos_board.claim_cli", "claim", "--task", task,
             "--repo", "lumos-core", "--branch", f"{agent}/x", "--worktree", str(clone),
             "--owner", agent, "--scope", "src/lumos_board/claim_cli.py"],
            cwd=clone, env=env, capture_output=True, text=True, timeout=120, check=False,
        )

    claude = run("claude-cloud", "CB-1")
    cursor = run("cursor-agent", "CB-2")
    assert claude.returncode == 0, claude.stdout + claude.stderr
    assert cursor.returncode == 2
    refused = json.loads(cursor.stdout)
    assert refused["accepted"] is False
    assert refused["conflicts"][0]["owner"] == "claude-cloud"
    # each clone's mirror shows the same single truth
    for agent in ("claude-cloud", "cursor-agent"):
        mirror = tmp_path / f"clone-{agent}" / ".lumos" / "board-central" / "mirror"
        assert [c.owner for c in read_claims(mirror)] == ["claude-cloud"]


# -- fail-closed ---------------------------------------------------------------


def test_unreachable_remote_fails_closed(tmp_path: Path) -> None:
    store = CentralClaimStore(remote=str(tmp_path / "does-not-exist.git"), cache_dir=tmp_path / "c")
    with pytest.raises(CentralStoreUnavailable):
        _claim(store, task="T", owner="a", scope="x.py")


def test_rejected_push_for_other_reason_fails_closed_without_retry_loop(remote: Path, tmp_path: Path) -> None:
    hook = remote / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\necho 'policy: denied' >&2\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    store = _store(remote, tmp_path, "a")
    started = time.monotonic()
    with pytest.raises(CentralStoreUnavailable, match="yazılamadı"):
        _claim(store, task="T", owner="a", scope="x.py")
    assert time.monotonic() - started < 30


def test_cas_exhaustion_fails_closed(remote: Path, tmp_path: Path) -> None:
    class AlwaysLoses(CentralClaimStore):
        def _push(self, commit: str) -> None:
            raise _CasLost()

    store = AlwaysLoses(remote=str(remote), cache_dir=tmp_path / "c", max_attempts=3)
    with pytest.raises(CentralStoreUnavailable, match="meşgul"):
        _claim(store, task="T", owner="a", scope="x.py")


def test_cli_never_falls_back_to_local_lock(tmp_path: Path) -> None:
    clone = tmp_path / "clone"
    clone.mkdir()
    _git("init", "-q", cwd=clone)
    env = dict(os.environ, PYTHONPATH=SRC, LUMOS_BOARD_REMOTE=str(tmp_path / "missing.git"))
    env.pop("LUMOS_BOARD_DIR", None)
    proc = subprocess.run(
        [sys.executable, "-m", "lumos_board.claim_cli", "claim", "--task", "T", "--repo", "lumos-core",
         "--branch", "b", "--worktree", str(clone), "--owner", "a", "--scope", "x.py"],
        cwd=clone, env=env, capture_output=True, text=True, timeout=120, check=False,
    )
    assert proc.returncode == 2
    assert "merkezi pano" in json.loads(proc.stdout)["error"]
    assert not (clone / ".lumos" / "board" / "claims.json").exists()
    mirror = clone / ".lumos" / "board-central" / "mirror" / "claims.json"
    assert not mirror.exists()


def test_corrupt_central_state_fails_closed(remote: Path, tmp_path: Path) -> None:
    _claim(_store(remote, tmp_path, "a"), task="T1", owner="a", scope="x.py")
    work = tmp_path / "vandal"
    _git("clone", "-q", "--branch", "claude/lumos-board", str(remote), str(work))
    (work / "claims.json").write_text("{not json", encoding="utf-8")
    _git("-c", "user.name=v", "-c", "user.email=v@x", "commit", "-qam", "corrupt", cwd=work)
    _git("push", "-q", "origin", "HEAD:claude/lumos-board", cwd=work)
    with pytest.raises(ClaimStoreCorrupt):
        _store(remote, tmp_path, "b").list_claims()


def test_cli_explicit_local_store_still_works(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = claim_cli.main(
        ["--store", str(tmp_path / "local"), "claim", "--task", "T", "--repo", "lumos-core",
         "--branch", "b", "--worktree", "/w", "--owner", "a", "--scope", "x.py"]
    )
    assert code == 0
    assert json.loads(capsys.readouterr().out)["accepted"] is True
    assert (tmp_path / "local" / "claims.json").exists()


# -- migration keeps existing records ------------------------------------------


def test_migrate_local_imports_open_claims_and_keeps_source(remote: Path, tmp_path: Path) -> None:
    local_dir = tmp_path / "old-board"
    local = TaskClaimStore(local_dir)
    open_claim = local.claim(task_id="OLD-1", repo="lumos-core", branch="b", worktree="/w",
                             owner="mac", scopes=["docs/a.md"]).claim
    done = local.claim(task_id="OLD-2", repo="lumos-core", branch="b", worktree="/w",
                       owner="mac", scopes=["docs/b.md"]).claim
    local.release(done.claim_id, owner="mac")
    source_before = (local_dir / "claims.json").read_bytes()

    central = _store(remote, tmp_path, "central")
    report = central.import_local(local_dir, actor="claude-cloud")

    assert report.imported == (open_claim.claim_id,)
    assert report.skipped_closed == (done.claim_id,)
    assert (local_dir / "claims.json").read_bytes() == source_before
    imported = central.list_claims()
    assert [(c.claim_id, c.owner, c.started_at) for c in imported] == [
        (open_claim.claim_id, "mac", open_claim.started_at)
    ]
    # idempotent
    again = central.import_local(local_dir, actor="claude-cloud")
    assert again.imported == () and again.already_present == (open_claim.claim_id,)
    # the imported claim now blocks other agents
    assert _claim(_store(remote, tmp_path, "cursor"), task="X", owner="cursor", scope="docs/a.md").accepted is False


def test_migrate_local_reports_conflicts_instead_of_merging(remote: Path, tmp_path: Path) -> None:
    central = _store(remote, tmp_path, "central")
    _claim(central, task="LIVE", owner="claude", scope="docs/a.md")
    local_dir = tmp_path / "old-board"
    TaskClaimStore(local_dir).claim(task_id="OLD", repo="lumos-core", branch="b", worktree="/w",
                                    owner="mac", scopes=["docs/a.md"])
    report = central.import_local(local_dir, actor="claude-cloud")
    assert report.imported == ()
    assert report.conflicts and report.conflicts[0]["owner"] == "mac"
    assert [c.owner for c in central.list_claims()] == ["claude"]


def test_mirror_is_readable_by_wall_observer(remote: Path, tmp_path: Path) -> None:
    a = _store(remote, tmp_path, "a")
    _claim(a, task="T1", owner="a", scope="x.py")
    b = _store(remote, tmp_path, "b")
    b.list_claims()
    assert [c.owner for c in read_claims(b.store_dir)] == ["a"]
