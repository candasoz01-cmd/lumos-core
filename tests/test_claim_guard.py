"""claim-guard (CI) and the pre-commit gate (hooks) against the central board."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lumos_board import claim_guard
from lumos_board.claim_cli import check_write_permission
from lumos_board.claim_guard import CommitInfo, evaluate
from lumos_board.task_claim import (
    CLAIM_EVENT_SCHEMA,
    DELEGATION_OWNER_REGISTRY_SCHEMA,
    DelegationVerifier,
    TaskClaimStore,
    sign_delegation_token,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = str(REPO_ROOT / "src")
HOOKS = REPO_ROOT / "ops" / "claim_guard" / "hooks"
BRANCH = "claude/g1"
PR = "o/r#930"
NOW = datetime.now(timezone.utc)


def _codes(violations) -> list[str]:
    return sorted(v.code for v in violations)


@pytest.fixture()
def store(tmp_path: Path) -> TaskClaimStore:
    return TaskClaimStore(tmp_path / "board")


def _claim(store: TaskClaimStore, *, task: str, owner: str, scopes: list[str], branch: str = BRANCH, **kw):
    result = store.claim(task_id=task, repo="lumos-core", branch=branch, worktree="/w",
                         owner=owner, scopes=scopes, **kw)
    return result.claim


def _all(store: TaskClaimStore):
    return store.list_claims(include_closed=True)


def _load_events(store: TaskClaimStore) -> list[dict[str, object]]:
    if not store.audit_path.exists():
        return []
    return [json.loads(line) for line in store.audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _commit(
    sha: str,
    files: list[str],
    claim_ids: list[str],
    agents: list[str],
    at: datetime | None = None,
    *,
    attested_owner: str | None = None,
    attest: bool = True,
) -> CommitInfo:
    owner = attested_owner
    if attest and owner is None and len(set(agents)) == 1 and agents[0]:
        owner = agents[0]
    if not attest:
        owner = None
    return CommitInfo(
        sha,
        tuple(files),
        tuple(claim_ids),
        tuple(agents),
        at,
        owner,
        tuple(claim_ids) if owner else (),
    )


def _go(store: TaskClaimStore, files: list[str], commits: list[CommitInfo], now: datetime | None = None, claims=None):
    return evaluate(
        _all(store) if claims is None else claims,
        branch=BRANCH,
        pr_ref=PR,
        changed_files=files,
        commits=commits,
        now=now or NOW,
        events=_load_events(store),
    )


GATE = "packages/kando_runtime/src/kando_runtime/lumos_gate.py"


def test_clean_pr_passes(store: TaskClaimStore) -> None:
    c = _claim(store, task="G1", owner="claude-cloud", scopes=[GATE])
    v = _go(store, [GATE], [_commit("a1", [GATE], [c.claim_id], ["claude-cloud"], c.started_at)])
    assert v == []


def test_different_git_author_alone_is_not_a_violation(store: TaskClaimStore) -> None:
    """Author/committer are never read. The attestation owner must match history."""
    c = _claim(store, task="G1", owner="claude-cloud", scopes=[GATE])
    # CommitInfo has no author field on purpose; a commit pushed by any account
    # or co-authored by a human passes when attestation owner and history agree.
    v = _go(store, [GATE], [_commit("a1", [GATE], [c.claim_id], ["claude-cloud"], c.started_at)])
    assert v == []
    assert "author" not in CommitInfo.__dataclass_fields__


def test_reproduces_2026_10_12_incident_unclaimed_second_agent_commit(store: TaskClaimStore) -> None:
    c = _claim(store, task="G1", owner="claude-cloud", scopes=[GATE])
    commits = [
        _commit("c3b289a", [GATE], [c.claim_id], ["claude-cloud"], c.started_at),
        _commit("e43924f", [GATE], [], []),  # Cursor, no claim, same branch, same file
    ]
    v = _go(store, [GATE], commits)
    assert _codes(v) == ["UNATTRIBUTED_COMMIT"]
    assert v[0].commit == "e43924f"


def test_second_agent_borrowing_first_agents_claim_is_rejected(store: TaskClaimStore) -> None:
    c = _claim(store, task="G1", owner="claude-cloud", scopes=[GATE])
    v = _go(store, [GATE], [_commit("e4", [GATE], [c.claim_id], ["cursor-agent"], c.started_at)])
    assert _codes(v) == ["AGENT_NOT_CLAIM_OWNER"]


def test_verified_delegation_lets_second_agent_write(tmp_path: Path) -> None:
    secret = "s" * 32
    registry = tmp_path / "owners.json"
    registry.write_text(json.dumps({"schema": DELEGATION_OWNER_REGISTRY_SCHEMA,
                                    "owners": [{"owner_id": "claude-cloud", "enabled": True,
                                                "valid_until": (NOW + timedelta(days=1)).isoformat()}]}),
                        encoding="utf-8")
    verifier = DelegationVerifier.from_registry_file(registry, secret=secret)
    store = TaskClaimStore(tmp_path / "board", delegation_verifier=verifier)
    parent = _claim(store, task="G1", owner="claude-cloud", scopes=["packages/kando_runtime"])
    token = sign_delegation_token(
        secret=secret.encode(), delegation_id="d1", parent_claim_id=parent.claim_id,
        parent_owner="claude-cloud", child_owner="cursor-agent", child_task_id="G1-sub",
        repo="lumos-core", scopes=[GATE], issued_at=NOW, expires_at=NOW + timedelta(hours=1),
    )
    child = _claim(store, task="G1-sub", owner="cursor-agent", scopes=[GATE], branch="cursor/sub",
                   parent_claim_id=parent.claim_id, delegation_token=token)
    v = _go(store, [GATE], [_commit("d1", [GATE], [child.claim_id], ["cursor-agent"], child.started_at)])
    assert v == []


def test_no_claim_for_pr(store: TaskClaimStore) -> None:
    v = evaluate(_all(store), branch=BRANCH, pr_ref=PR, changed_files=[GATE],
                 commits=[_commit("a", [GATE], ["x"], ["claude-cloud"])], now=NOW)
    assert "NO_PR_CLAIM" in _codes(v)


def test_pr_ref_binding_counts_even_if_branch_differs(store: TaskClaimStore) -> None:
    c = _claim(store, task="G1", owner="claude-cloud", scopes=[GATE], branch="old-name")
    store.attach_pr(c.claim_id, owner="claude-cloud", pr_ref=PR)
    v = _go(store, [GATE], [_commit("a", [GATE], [c.claim_id], ["claude-cloud"], c.started_at)])
    assert v == []


def test_unclaimed_path_and_commit_outside_scope(store: TaskClaimStore) -> None:
    c = _claim(store, task="G1", owner="claude-cloud", scopes=[GATE])
    v = _go(store, [GATE, "server.py"], [_commit("a", [GATE, "server.py"], [c.claim_id], ["claude-cloud"], c.started_at)])
    assert _codes(v) == ["COMMIT_OUTSIDE_CLAIM_SCOPE", "UNCLAIMED_PATH"]


def test_foreign_active_claim_blocks_and_expired_does_not(store: TaskClaimStore) -> None:
    mine = _claim(store, task="G1", owner="claude-cloud", scopes=[GATE])
    other = _claim(store, task="X", owner="cursor-agent", scopes=["server.py"], branch="cursor/x")
    files = [GATE, "server.py"]
    # mine does not cover server.py either; we look for the foreign hit
    commit = [_commit("a", [GATE], [mine.claim_id], ["claude-cloud"], mine.started_at)]
    v = _go(store, files, commit, now=NOW)
    assert "FOREIGN_ACTIVE_CLAIM" in _codes(v)
    later = other.expires_at + timedelta(seconds=1)
    v2 = _go(store, files, commit, now=later)
    assert "FOREIGN_ACTIVE_CLAIM" not in _codes(v2)


def test_claim_from_other_branch_and_unknown_claim(store: TaskClaimStore) -> None:
    _claim(store, task="G1", owner="claude-cloud", scopes=[GATE])
    other = _claim(store, task="X", owner="claude-cloud", scopes=["docs/x.md"], branch="claude/other")
    v = evaluate(_all(store), branch=BRANCH, pr_ref=PR, changed_files=[GATE],
                 commits=[_commit("a", [GATE], [other.claim_id], ["claude-cloud"]),
                          _commit("b", [GATE], ["nope"], ["claude-cloud"])], now=NOW)
    assert _codes(v) == ["CLAIM_NOT_FOR_THIS_PR", "UNKNOWN_CLAIM"]


def test_queued_claim_gives_no_write_right(store: TaskClaimStore) -> None:
    _claim(store, task="A", owner="cursor-agent", scopes=[GATE], branch="cursor/a")
    queued = store.claim(task_id="G1", repo="lumos-core", branch=BRANCH, worktree="/w",
                         owner="claude-cloud", scopes=[GATE], queue_on_conflict=True).claim
    v = evaluate(_all(store), branch=BRANCH, pr_ref=PR, changed_files=[GATE],
                 commits=[_commit("a", [GATE], [queued.claim_id], ["claude-cloud"])], now=NOW)
    assert "QUEUED_CLAIM" in _codes(v) and "NO_PR_CLAIM" in _codes(v)


def test_check_write_permission(store: TaskClaimStore) -> None:
    mine = _claim(store, task="G1", owner="claude-cloud", scopes=["src/a"])
    _claim(store, task="X", owner="cursor-agent", scopes=["src/b.py"], branch="cursor/x")
    claims = store.list_claims()
    ok = check_write_permission(claims, branch=BRANCH, owner="claude-cloud", paths=["src/a/x.py"])
    assert ok["ok"] is True and ok["claim_ids"] == [mine.claim_id]
    other_agent = check_write_permission(claims, branch=BRANCH, owner="cursor-agent", paths=["src/a/x.py"])
    assert other_agent["ok"] is False and other_agent["foreign"][0]["owner"] == "claude-cloud"
    foreign = check_write_permission(claims, branch=BRANCH, owner="claude-cloud", paths=["src/b.py"])
    assert foreign["ok"] is False and foreign["uncovered"] == ["src/b.py"]


# -- end to end with real git ---------------------------------------------------


def _git(cwd: Path, *args: str, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, env=env, check=check)


@pytest.fixture()
def world(tmp_path: Path):
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", "-q", "-b", "main", str(remote))
    seed = tmp_path / "seed"
    seed.mkdir()
    _git(seed, "init", "-q", "-b", "main")
    shutil.copytree(REPO_ROOT / "src" / "lumos_board", seed / "src" / "lumos_board")
    (seed / "app.py").write_text("x = 1\n", encoding="utf-8")
    (seed / "other.py").write_text("y = 1\n", encoding="utf-8")
    _git(seed, "add", ".")
    _git(seed, "-c", "user.name=s", "-c", "user.email=s@x", "commit", "-qm", "seed")
    _git(seed, "remote", "add", "origin", str(remote))
    _git(seed, "push", "-q", "origin", "main")
    return remote, tmp_path


def _agent_clone(remote: Path, tmp_path: Path, agent: str, branch: str) -> tuple[Path, dict[str, str]]:
    clone = tmp_path / f"clone-{agent}"
    _git(tmp_path, "clone", "-q", str(remote), str(clone))
    _git(clone, "checkout", "-q", "-b", branch)
    _git(clone, "config", "core.hooksPath", str(HOOKS))
    _git(clone, "config", "user.name", "same-github-account")
    _git(clone, "config", "user.email", "same@example.com")
    env = dict(os.environ, LUMOS_AGENT=agent, LUMOS_BOARD_REMOTE=str(remote),
               PYTHONPATH=SRC, GIT_TERMINAL_PROMPT="0")
    env.pop("LUMOS_BOARD_DIR", None)
    return clone, env


def _cli(clone: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-m", "lumos_board.claim_cli", *args], cwd=clone,
                          env=env, capture_output=True, text=True, timeout=120, check=False)


def test_hooks_block_commit_before_it_exists_and_attribute_allowed_ones(world) -> None:
    remote, tmp_path = world
    claude, env_c = _agent_clone(remote, tmp_path, "claude-cloud", "claude/g1")
    cursor, env_x = _agent_clone(remote, tmp_path, "cursor-agent", "claude/g1")

    # no claim yet -> claude's own commit is refused
    (claude / "app.py").write_text("x = 2\n", encoding="utf-8")
    _git(claude, "add", "app.py")
    refused = _git(claude, "commit", "-qm", "no claim", env=env_c, check=False)
    assert refused.returncode != 0
    assert "claim-guard" in refused.stderr

    claim = _cli(claude, env_c, "claim", "--task", "G1", "--repo", "lumos-core", "--branch", "claude/g1",
                 "--worktree", str(claude), "--owner", "claude-cloud", "--scope", "app.py")
    assert claim.returncode == 0, claim.stdout + claim.stderr
    claim_id = json.loads(claim.stdout)["claim"]["claim_id"]

    allowed = _git(claude, "commit", "-qm", "claimed change", env=env_c, check=False)
    assert allowed.returncode == 0, allowed.stderr
    body = _git(claude, "log", "-1", "--format=%B").stdout
    assert f"Lumos-Claim: {claim_id}" in body and "Lumos-Agent: claude-cloud" in body

    # the second agent, same branch name, same file -> refused before commit
    before = _git(cursor, "rev-parse", "HEAD").stdout
    (cursor / "app.py").write_text("x = 3\n", encoding="utf-8")
    _git(cursor, "add", "app.py")
    blocked = _git(cursor, "commit", "-qm", "intrude", env=env_x, check=False)
    assert blocked.returncode != 0
    assert "claude-cloud" in blocked.stderr
    assert _git(cursor, "rev-parse", "HEAD").stdout == before

    # claude cannot sneak in a file outside its claim either
    (claude / "other.py").write_text("y = 2\n", encoding="utf-8")
    _git(claude, "add", "other.py")
    assert _git(claude, "commit", "-qm", "outside", env=env_c, check=False).returncode != 0


def test_hook_refuses_when_central_board_unreachable(world) -> None:
    remote, tmp_path = world
    clone, env = _agent_clone(remote, tmp_path, "claude-cloud", "claude/g1")
    env["LUMOS_BOARD_REMOTE"] = str(tmp_path / "gone.git")
    (clone / "app.py").write_text("x = 9\n", encoding="utf-8")
    _git(clone, "add", "app.py")
    result = _git(clone, "commit", "-qm", "offline", env=env, check=False)
    assert result.returncode != 0
    assert "merkezi pano" in result.stderr


def test_guard_cli_end_to_end(world, monkeypatch: pytest.MonkeyPatch) -> None:
    remote, tmp_path = world
    claude, env_c = _agent_clone(remote, tmp_path, "claude-cloud", "claude/g1")
    claimed = _cli(claude, env_c, "claim", "--task", "G1", "--repo", "lumos-core", "--branch", "claude/g1",
                   "--worktree", str(claude), "--owner", "claude-cloud", "--scope", "app.py")
    assert claimed.returncode == 0, claimed.stderr
    claim_id = json.loads(claimed.stdout)["claim"]["claim_id"]
    (claude / "app.py").write_text("x = 2\n", encoding="utf-8")
    _git(claude, "add", "app.py")
    payload = json.dumps(
        {
            "schema": "lumos.claim_commit_attestation.v1",
            "owner": "claude-cloud",
            "claim_id": claim_id,
            "verification_method": "hmac-sha256",
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    token = base64.urlsafe_b64encode(payload).rstrip(b"=").decode() + ".e30"
    assert _git(claude, "commit", "-qm", f"ok\n\nLumos-Claim-Attestation: {token}", env=env_c).returncode == 0
    # an unattributed commit sneaks in without hooks (e.g. an agent that ignores them)
    (claude / "app.py").write_text("x = 3\n", encoding="utf-8")
    _git(claude, "-c", "core.hooksPath=/dev/null", "commit", "-qam", "sneaky")
    _git(claude, "fetch", "-q", "origin", "+refs/heads/claude/lumos-board:refs/remotes/origin/claude/lumos-board")
    base = _git(claude, "rev-parse", "origin/main").stdout.strip()

    monkeypatch.chdir(claude)
    head = _git(claude, "rev-parse", "HEAD").stdout.strip()
    assert claim_guard.main(["--base", base, "--head", f"{head}~1", "--branch", "claude/g1", "--pr", PR]) == 0
    assert claim_guard.main(["--base", base, "--head", head, "--branch", "claude/g1", "--pr", PR]) == 1
    # unreadable board -> failure, never a pass
    assert claim_guard.main(["--base", base, "--head", head, "--branch", "claude/g1",
                             "--board-ref", "refs/remotes/origin/missing"]) == 2


def test_message_only_amend_keeps_working_but_not_for_another_agent(world) -> None:
    remote, tmp_path = world
    claude, env_c = _agent_clone(remote, tmp_path, "claude-cloud", "claude/g1")
    assert _cli(claude, env_c, "claim", "--task", "G1", "--repo", "lumos-core", "--branch", "claude/g1",
                "--worktree", str(claude), "--owner", "claude-cloud", "--scope", "app.py").returncode == 0
    (claude / "app.py").write_text("x = 2\n", encoding="utf-8")
    _git(claude, "add", "app.py")
    assert _git(claude, "commit", "-qm", "first", env=env_c).returncode == 0

    amended = _git(claude, "commit", "--amend", "-qm", "reworded\n\n" +
                   _git(claude, "log", "-1", "--format=%(trailers)").stdout, env=env_c, check=False)
    assert amended.returncode == 0, amended.stderr
    assert _git(claude, "log", "-1", "--format=%s").stdout.strip() == "reworded"

    env_x = dict(env_c, LUMOS_AGENT="cursor-agent")
    hijack = _git(claude, "commit", "--amend", "-qm", "hijack\n\n" +
                  _git(claude, "log", "-1", "--format=%(trailers)").stdout, env=env_x, check=False)
    assert hijack.returncode != 0
    plain = _git(claude, "commit", "--amend", "-qm", "no trailers", env=env_c, check=False)
    assert plain.returncode != 0


@pytest.mark.parametrize("agent", ["a b", "$(id)", "x;y", ""])
def test_hooks_reject_malformed_agent_identity(world, agent: str) -> None:
    remote, tmp_path = world
    clone, env = _agent_clone(remote, tmp_path, "claude-cloud", "claude/g1")
    env["LUMOS_AGENT"] = agent
    (clone / "app.py").write_text("x = 5\n", encoding="utf-8")
    _git(clone, "add", "app.py")
    assert _git(clone, "commit", "-qm", "m", env=env, check=False).returncode != 0


def test_stale_claim_cannot_authorise_write_after_another_agent_took_the_file(store: TaskClaimStore) -> None:
    """Review 164f105: A cites its RELEASED claim after B holds the file ACTIVE."""
    a = _claim(store, task="A", owner="agent-a", scopes=[GATE])
    store.release(a.claim_id, owner="agent-a")
    b = _claim(store, task="B", owner="agent-b", scopes=[GATE])
    moment = b.started_at
    v = _go(store, [GATE], [
        _commit("late", [GATE], [a.claim_id], ["agent-a"], moment),
        _commit("ok", [GATE], [b.claim_id], ["agent-b"], moment),
    ], now=moment)
    assert _codes(v) == ["SUPERSEDED_BY_ACTIVE_CLAIM"]
    assert v[0].commit == "late"


def test_released_claim_still_attributes_finished_work_when_nobody_else_holds_it(store: TaskClaimStore) -> None:
    a = _claim(store, task="A", owner="agent-a", scopes=[GATE])
    store.release(a.claim_id, owner="agent-a")
    v = _go(store, [GATE], [_commit("done", [GATE], [a.claim_id], ["agent-a"], a.started_at)])
    assert v == []


def test_override_takeover_flags_old_owner_commits_after_takeover(tmp_path: Path) -> None:
    """Expired claim of A, B now ACTIVE on the same file: A's cited claim is stale.

    Both stores share one fixed clock. A lease of 60s must be past ``later``
    even when this module was imported long before the test body runs.
    """
    opened = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
    later = opened + timedelta(seconds=120)
    store = TaskClaimStore(tmp_path / "board", clock=lambda: opened)
    a = _claim(store, task="A", owner="agent-a", scopes=[GATE], ttl_seconds=60)
    clocked = TaskClaimStore(tmp_path / "board", clock=lambda: later)
    b = clocked.claim(task_id="B", repo="lumos-core", branch=BRANCH, worktree="/w",
                      owner="agent-b", scopes=[GATE]).claim
    v = _go(clocked, [GATE], [
        _commit("late", [GATE], [a.claim_id], ["agent-a"], later),
        _commit("b1", [GATE], [b.claim_id], ["agent-b"], later),
    ], now=later, claims=clocked.list_claims(include_closed=True))
    assert _codes(v) == ["SUPERSEDED_BY_ACTIVE_CLAIM"]


def _tests() -> dict[str, object]:
    return {"command": "pytest", "passed": 1, "failed": 0, "skipped": 0}


def test_accepted_handoff_keeps_the_earlier_owner_and_rejects_backdating(tmp_path: Path) -> None:
    """A later accept must not unauthorize the giver or authorize the recipient early."""
    opened = datetime(2026, 10, 13, 13, 0, tzinfo=timezone.utc)
    written = opened + timedelta(minutes=10)
    handed = opened + timedelta(minutes=20)
    moment = {"now": opened}
    store = TaskClaimStore(tmp_path / "board", clock=lambda: moment["now"], published_ref=lambda **_: None)
    claim = _claim(store, task="TD-45", owner="cursor-cloud", scopes=[GATE])
    moment["now"] = handed
    store.handoff(
        claim.claim_id,
        owner="cursor-cloud",
        to_owner="board-receiver",
        commit="a" * 40,
        tree="b" * 40,
        branch=BRANCH,
        tests=_tests(),
    )
    store.accept_handoff(claim.claim_id, owner="board-receiver")
    assert store.list_claims(include_closed=True)[0].owner == "board-receiver"
    early = _commit("early", [GATE], [claim.claim_id], ["cursor-cloud"], written)
    backdated = _commit("backdated", [GATE], [claim.claim_id], ["board-receiver"], written)
    after = _commit("after", [GATE], [claim.claim_id], ["board-receiver"], handed)
    v = _go(store, [GATE], [early, backdated, after], now=handed + timedelta(minutes=1))
    by_sha = {item.commit: item.code for item in v}
    assert "early" not in by_sha
    assert "after" not in by_sha
    assert by_sha["backdated"] == "AGENT_NOT_CLAIM_OWNER"


def test_unaccepted_offer_does_not_authorize_the_recipient(tmp_path: Path) -> None:
    opened = datetime(2026, 10, 13, 13, 0, tzinfo=timezone.utc)
    offered = opened + timedelta(minutes=15)
    moment = {"now": opened}
    store = TaskClaimStore(tmp_path / "board", clock=lambda: moment["now"], published_ref=lambda **_: None)
    claim = _claim(store, task="TD-45", owner="cursor-cloud", scopes=[GATE])
    moment["now"] = offered
    store.handoff(
        claim.claim_id,
        owner="cursor-cloud",
        to_owner="board-receiver",
        commit="a" * 40,
        tree="b" * 40,
        branch=BRANCH,
        tests=_tests(),
    )
    assert store.list_claims(include_closed=True)[0].owner == "cursor-cloud"
    v = _go(store, [GATE], [
        _commit("giver", [GATE], [claim.claim_id], ["cursor-cloud"], offered),
        _commit("recipient", [GATE], [claim.claim_id], ["board-receiver"], offered),
    ], now=offered)
    by_sha = {item.commit: item.code for item in v}
    assert "giver" not in by_sha
    assert by_sha["recipient"] == "AGENT_NOT_CLAIM_OWNER"


def test_legacy_immediate_handoff_does_not_rewrite_the_earlier_commit(tmp_path: Path) -> None:
    """The live #942 handoff stored the recipient on CLAIM_HANDOFF itself."""
    opened = datetime(2026, 10, 13, 12, 51, tzinfo=timezone.utc)
    written = datetime(2026, 10, 13, 13, 2, tzinfo=timezone.utc)
    handed = datetime(2026, 10, 13, 13, 16, tzinfo=timezone.utc)
    moment = {"now": opened}
    store = TaskClaimStore(tmp_path / "board", clock=lambda: moment["now"], published_ref=lambda **_: None)
    claim = _claim(store, task="TD-45", owner="cursor-cloud", scopes=[GATE])
    events = _load_events(store)
    events.append({
        "schema": CLAIM_EVENT_SCHEMA,
        "event": "CLAIM_HANDOFF",
        "at": handed.isoformat().replace("+00:00", "Z"),
        "claim_id": claim.claim_id,
        "owner": "board-receiver",
        "actor": "cursor-cloud",
        "details": {"from_owner": "cursor-cloud", "to_owner": "board-receiver"},
    })
    current = replace(claim, owner="board-receiver")
    early = _commit("05607991", [GATE], [claim.claim_id], ["cursor-cloud"], written)
    stolen = _commit("stolen", [GATE], [claim.claim_id], ["board-receiver"], written)
    v = evaluate(
        [current],
        branch=BRANCH,
        pr_ref=PR,
        changed_files=[GATE],
        commits=[early, stolen],
        now=handed + timedelta(hours=1),
        events=events,
    )
    by_sha = {item.commit: item.code for item in v}
    assert "05607991" not in by_sha
    assert by_sha["stolen"] == "AGENT_NOT_CLAIM_OWNER"


def test_unsigned_agent_trailer_is_not_identity_proof(store: TaskClaimStore) -> None:
    c = _claim(store, task="G1", owner="claude-cloud", scopes=[GATE])
    bare = _commit("bare", [GATE], [c.claim_id], ["claude-cloud"], c.started_at, attest=False)
    mismatch = _commit(
        "mismatch",
        [GATE],
        [c.claim_id],
        ["claude-cloud"],
        c.started_at,
        attested_owner="cursor-agent",
    )
    v = _go(store, [GATE], [bare, mismatch])
    assert _codes(v) == ["IDENTITY_UNVERIFIED", "IDENTITY_UNVERIFIED"]
    assert {item.commit for item in v} == {"bare", "mismatch"}
