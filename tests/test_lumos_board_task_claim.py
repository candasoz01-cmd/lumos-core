from __future__ import annotations

import fcntl
import json
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lumos_board.claim_cli import main as claim_cli_main
from lumos_board.task_claim import (
    APPROVER_REGISTRY_SCHEMA,
    CLAIM_EVENT_SCHEMA,
    DELEGATION_OWNER_REGISTRY_SCHEMA,
    ClaimError,
    ClaimStatus,
    ClaimStoreCorrupt,
    DelegationVerifier,
    OverrideApprovalVerifier,
    TaskClaimStore,
    sign_delegation_token,
    sign_override_approval,
)


NOW = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)
APPROVAL_SECRET = b"a-secure-test-secret-that-is-32-bytes-minimum"
DELEGATION_SECRET = b"a-secure-delegation-secret-at-least-32-bytes"


class Clock:
    def __init__(self) -> None:
        self.value = NOW

    def __call__(self) -> datetime:
        return self.value


def _claim(store: TaskClaimStore, *, task: str, owner: str, scope: str, **kwargs: object):
    return store.claim(
        task_id=task,
        repo="lumos-core",
        branch=f"codex/{task.lower()}",
        worktree=f"/worktrees/{task.lower()}",
        owner=owner,
        scopes=[scope],
        **kwargs,
    )


def _events(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _verifier(tmp_path: Path, *approvers: str) -> OverrideApprovalVerifier:
    registry = tmp_path / "approvers.json"
    registry.write_text(
        json.dumps(
            {
                "schema": APPROVER_REGISTRY_SCHEMA,
                "approvers": [
                    {
                        "approver_id": approver,
                        "enabled": True,
                        "valid_until": (NOW + timedelta(days=1)).isoformat(),
                    }
                    for approver in approvers
                ],
            }
        ),
        encoding="utf-8",
    )
    return OverrideApprovalVerifier.from_registry_file(
        registry,
        secret=APPROVAL_SECRET.decode(),
    )


def _approval_token(
    *,
    approver: str = "security-admin",
    current_owner: str = "agent-a",
    new_owner: str = "agent-b",
    expires_at: datetime | None = None,
) -> str:
    return sign_override_approval(
        secret=APPROVAL_SECRET,
        approval_id=f"approval-{approver}-{new_owner}",
        approver_id=approver,
        task_id="KA-002",
        current_owner=current_owner,
        new_owner=new_owner,
        reason="owner unavailable",
        issued_at=NOW - timedelta(minutes=1),
        expires_at=expires_at or NOW + timedelta(minutes=10),
    )


def _delegation_verifier(tmp_path: Path, *owners: str) -> DelegationVerifier:
    registry = tmp_path / "delegation-owners.json"
    registry.write_text(
        json.dumps(
            {
                "schema": DELEGATION_OWNER_REGISTRY_SCHEMA,
                "owners": [
                    {
                        "owner_id": owner,
                        "enabled": True,
                        "valid_until": (NOW + timedelta(days=1)).isoformat(),
                    }
                    for owner in owners
                ],
            }
        ),
        encoding="utf-8",
    )
    return DelegationVerifier.from_registry_file(
        registry,
        secret=DELEGATION_SECRET.decode(),
    )


def _delegation_token(
    *,
    parent_claim_id: str,
    parent_owner: str = "lead",
    child_owner: str = "worker",
    child_task_id: str = "KA-002-doc",
    scope: str = "src/lumos_board/task_claim.py",
    expires_at: datetime | None = None,
) -> str:
    return sign_delegation_token(
        secret=DELEGATION_SECRET,
        delegation_id=f"delegation-{parent_claim_id}-{child_owner}",
        parent_claim_id=parent_claim_id,
        parent_owner=parent_owner,
        child_owner=child_owner,
        child_task_id=child_task_id,
        repo="lumos-core",
        scopes=[scope],
        issued_at=NOW - timedelta(minutes=1),
        expires_at=expires_at or NOW + timedelta(minutes=10),
    )


def test_duplicate_task_and_overlapping_scope_are_refused(tmp_path: Path) -> None:
    store = TaskClaimStore(tmp_path)
    first = _claim(store, task="KA-002", owner="agent-a", scope="src/lumos_board")

    duplicate = _claim(store, task="KA-002", owner="agent-b", scope="docs/other.md")
    overlap = _claim(store, task="KA-003", owner="agent-b", scope="src/lumos_board/task_claim.py")
    separate = _claim(store, task="KA-004", owner="agent-b", scope="docs/new.md")

    assert first.accepted is True
    assert duplicate.accepted is False
    assert duplicate.conflicts[0].reason == "DUPLICATE_TASK"
    assert overlap.accepted is False
    assert overlap.conflicts[0].reason == "SCOPE_CONFLICT"
    assert separate.accepted is True


def test_conflicting_claim_can_queue_without_becoming_active(tmp_path: Path) -> None:
    store = TaskClaimStore(tmp_path)
    _claim(store, task="KA-002", owner="agent-a", scope="src/lumos_board")

    queued = _claim(
        store,
        task="KA-003",
        owner="agent-b",
        scope="src/lumos_board/task_claim.py",
        queue_on_conflict=True,
    )

    assert queued.accepted is False
    assert queued.claim is not None
    assert queued.claim.status is ClaimStatus.QUEUED
    assert {claim.status for claim in store.list_claims()} == {ClaimStatus.ACTIVE, ClaimStatus.QUEUED}


def test_atomic_claim_allows_only_one_concurrent_owner(tmp_path: Path) -> None:
    barrier = threading.Barrier(2)
    results: list[bool] = []

    def attempt(owner: str) -> None:
        barrier.wait()
        result = _claim(
            TaskClaimStore(tmp_path),
            task="KA-002",
            owner=owner,
            scope="src/lumos_board/task_claim.py",
        )
        results.append(result.accepted)

    threads = [threading.Thread(target=attempt, args=(owner,)) for owner in ("agent-a", "agent-b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == [False, True]
    assert len(TaskClaimStore(tmp_path).list_claims()) == 1


def test_heartbeat_extends_lease_and_owner_is_enforced(tmp_path: Path) -> None:
    clock = Clock()
    store = TaskClaimStore(tmp_path, clock=clock)
    claim = _claim(store, task="KA-002", owner="agent-a", scope="src", ttl_seconds=30).claim
    assert claim is not None
    clock.value += timedelta(seconds=20)

    renewed = store.heartbeat(claim.claim_id, owner="agent-a", ttl_seconds=60)

    assert renewed.heartbeat_at == clock.value
    assert renewed.expires_at == clock.value + timedelta(seconds=60)
    with pytest.raises(ClaimError, match="sahibi"):
        store.release(claim.claim_id, owner="agent-b")


def test_stale_claim_expires_and_scope_can_be_reclaimed(tmp_path: Path) -> None:
    clock = Clock()
    store = TaskClaimStore(tmp_path, clock=clock)
    old = _claim(store, task="KA-002", owner="agent-a", scope="src", ttl_seconds=10).claim
    assert old is not None
    clock.value += timedelta(seconds=11)

    replacement = _claim(store, task="KA-002", owner="agent-b", scope="src")
    all_claims = store.list_claims(include_closed=True)

    assert replacement.accepted is True
    assert next(claim for claim in all_claims if claim.claim_id == old.claim_id).status is ClaimStatus.EXPIRED
    assert "CLAIM_EXPIRED" in [event["event"] for event in _events(store.audit_path)]


def test_child_claim_requires_verified_parent_owner_context(tmp_path: Path) -> None:
    store = TaskClaimStore(
        tmp_path,
        clock=Clock(),
        delegation_verifier=_delegation_verifier(tmp_path, "lead"),
    )
    parent = _claim(store, task="KA-002", owner="lead", scope="src/lumos_board").claim
    assert parent is not None

    child = _claim(
        store,
        task="KA-002-doc",
        owner="worker",
        scope="src/lumos_board/task_claim.py",
        parent_claim_id=parent.claim_id,
        delegation_token=_delegation_token(parent_claim_id=parent.claim_id),
    )

    assert child.accepted is True
    assert child.claim is not None
    assert child.claim.parent_claim_id == parent.claim_id
    event = _events(store.audit_path)[-1]
    assert event["details"]["delegation"] == {
        "delegation_id": f"delegation-{parent.claim_id}-worker",
        "parent_claim_id": parent.claim_id,
        "parent_owner": "lead",
        "verification_method": "HMAC_SHA256_OWNER_ALLOWLIST",
        "verified_at": NOW.isoformat().replace("+00:00", "Z"),
    }


def test_forged_or_wrong_context_delegation_is_rejected(tmp_path: Path) -> None:
    store = TaskClaimStore(
        tmp_path,
        clock=Clock(),
        delegation_verifier=_delegation_verifier(tmp_path, "lead"),
    )
    parent = _claim(store, task="KA-002", owner="lead", scope="src/lumos_board").claim
    assert parent is not None

    with pytest.raises(ClaimError, match="token geçersiz"):
        _claim(
            store,
            task="KA-002-bad",
            owner="worker-2",
            scope="src/lumos_board/claim_cli.py",
            parent_claim_id=parent.claim_id,
            delegation_token="lead",
        )

    wrong_context = _delegation_token(
        parent_claim_id=parent.claim_id,
        child_owner="someone-else",
        child_task_id="KA-002-bad",
        scope="src/lumos_board/claim_cli.py",
    )
    with pytest.raises(ClaimError, match="bağlamı eşleşmiyor"):
        _claim(
            store,
            task="KA-002-bad",
            owner="worker-2",
            scope="src/lumos_board/claim_cli.py",
            parent_claim_id=parent.claim_id,
            delegation_token=wrong_context,
        )


def test_non_allowlisted_or_expired_delegation_is_rejected(tmp_path: Path) -> None:
    store = TaskClaimStore(
        tmp_path,
        clock=Clock(),
        delegation_verifier=_delegation_verifier(tmp_path, "another-lead"),
    )
    parent = _claim(store, task="KA-002", owner="lead", scope="src/lumos_board").claim
    assert parent is not None

    with pytest.raises(ClaimError, match="allowlist"):
        _claim(
            store,
            task="KA-002-doc",
            owner="worker",
            scope="src/lumos_board/task_claim.py",
            parent_claim_id=parent.claim_id,
            delegation_token=_delegation_token(parent_claim_id=parent.claim_id),
        )

    expired_store = TaskClaimStore(
        tmp_path,
        clock=Clock(),
        delegation_verifier=_delegation_verifier(tmp_path, "lead"),
    )
    with pytest.raises(ClaimError, match="süresi"):
        _claim(
            expired_store,
            task="KA-002-doc",
            owner="worker",
            scope="src/lumos_board/task_claim.py",
            parent_claim_id=parent.claim_id,
            delegation_token=_delegation_token(
                parent_claim_id=parent.claim_id,
                expires_at=NOW - timedelta(seconds=1),
            ),
        )


def test_fake_human_override_is_rejected(tmp_path: Path) -> None:
    store = TaskClaimStore(tmp_path, clock=Clock(), override_verifier=_verifier(tmp_path, "security-admin"))
    original = _claim(store, task="KA-002", owner="agent-a", scope="src").claim
    assert original is not None

    with pytest.raises(ClaimError, match="token geçersiz"):
        _claim(
            store,
            task="KA-002",
            owner="agent-b",
            scope="src",
            override_token="human",
            override_reason="owner unavailable",
        )

    assert store.list_claims()[0].claim_id == original.claim_id


def test_owner_cannot_approve_own_override(tmp_path: Path) -> None:
    store = TaskClaimStore(tmp_path, clock=Clock(), override_verifier=_verifier(tmp_path, "agent-a"))
    _claim(store, task="KA-002", owner="agent-a", scope="src")

    with pytest.raises(ClaimError, match="owner'lardan farklı"):
        _claim(
            store,
            task="KA-002",
            owner="agent-b",
            scope="src",
            override_token=_approval_token(approver="agent-a"),
            override_reason="owner unavailable",
        )


def test_non_allowlisted_approver_is_rejected(tmp_path: Path) -> None:
    store = TaskClaimStore(tmp_path, clock=Clock(), override_verifier=_verifier(tmp_path, "security-admin"))
    _claim(store, task="KA-002", owner="agent-a", scope="src")

    with pytest.raises(ClaimError, match="allowlist"):
        _claim(
            store,
            task="KA-002",
            owner="agent-b",
            scope="src",
            override_token=_approval_token(approver="outsider"),
            override_reason="owner unavailable",
        )


def test_expired_override_approval_is_rejected(tmp_path: Path) -> None:
    store = TaskClaimStore(tmp_path, clock=Clock(), override_verifier=_verifier(tmp_path, "security-admin"))
    _claim(store, task="KA-002", owner="agent-a", scope="src")

    with pytest.raises(ClaimError, match="süresi"):
        _claim(
            store,
            task="KA-002",
            owner="agent-b",
            scope="src",
            override_token=_approval_token(expires_at=NOW - timedelta(seconds=1)),
            override_reason="owner unavailable",
        )


def test_valid_override_is_audited_and_old_owner_stays_revoked(tmp_path: Path) -> None:
    store = TaskClaimStore(tmp_path, clock=Clock(), override_verifier=_verifier(tmp_path, "security-admin"))
    original = _claim(store, task="KA-002", owner="agent-a", scope="src").claim
    assert original is not None

    replacement = _claim(
        store,
        task="KA-002",
        owner="agent-b",
        scope="src",
        override_token=_approval_token(),
        override_reason="owner unavailable",
    )

    assert replacement.accepted is True
    with pytest.raises(ClaimError, match="açık claim bulunamadı"):
        store.heartbeat(original.claim_id, owner="agent-a")
    claims = store.list_claims(include_closed=True)
    assert next(claim for claim in claims if claim.claim_id == original.claim_id).status is ClaimStatus.OVERRIDDEN
    event = next(event for event in _events(store.audit_path) if event["event"] == "CLAIM_OVERRIDDEN")
    assert event["actor"] == "security-admin"
    assert event["details"] == {
        "approval_id": "approval-security-admin-agent-b",
        "approver_id": "security-admin",
        "verification_method": "HMAC_SHA256_ALLOWLIST",
        "verified_at": NOW.isoformat().replace("+00:00", "Z"),
        "reason": "owner unavailable",
        "previous_owner": "agent-a",
        "new_owner": "agent-b",
    }


def test_two_simultaneous_overrides_have_one_winner(tmp_path: Path) -> None:
    clock = Clock()
    verifier = _verifier(tmp_path, "admin-one", "admin-two")
    store = TaskClaimStore(tmp_path, clock=clock, override_verifier=verifier)
    _claim(store, task="KA-002", owner="agent-a", scope="src")
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def attempt(approver: str, new_owner: str) -> None:
        barrier.wait()
        try:
            result = _claim(
                TaskClaimStore(tmp_path, clock=clock, override_verifier=verifier),
                task="KA-002",
                owner=new_owner,
                scope="src",
                override_token=_approval_token(approver=approver, new_owner=new_owner),
                override_reason="owner unavailable",
            )
            outcomes.append("accepted" if result.accepted else "refused")
        except ClaimError:
            outcomes.append("rejected")

    threads = [
        threading.Thread(target=attempt, args=("admin-one", "agent-b")),
        threading.Thread(target=attempt, args=("admin-two", "agent-c")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count("accepted") == 1
    assert outcomes.count("rejected") == 1
    assert [event["event"] for event in _events(store.audit_path)].count("CLAIM_OVERRIDDEN") == 1


def test_corrupt_approver_registry_fails_closed(tmp_path: Path) -> None:
    store = TaskClaimStore(tmp_path, clock=Clock())
    original = _claim(store, task="KA-002", owner="agent-a", scope="src").claim
    registry = tmp_path / "corrupt-approvers.json"
    registry.write_text("{broken", encoding="utf-8")

    with pytest.raises(ClaimError, match="registry okunamıyor"):
        OverrideApprovalVerifier.from_registry_file(registry, secret=APPROVAL_SECRET.decode())

    assert store.list_claims()[0].claim_id == original.claim_id


def test_pr_binding_and_release_are_recorded(tmp_path: Path) -> None:
    store = TaskClaimStore(tmp_path)
    claim = _claim(store, task="KA-002", owner="agent-a", scope="src").claim
    assert claim is not None

    attached = store.attach_pr(claim.claim_id, owner="agent-a", pr_ref="#631")
    released = store.release(claim.claim_id, owner="agent-a")

    assert attached.pr_ref == "#631"
    assert released.status is ClaimStatus.RELEASED
    events = _events(store.audit_path)
    assert all(event["schema"] == CLAIM_EVENT_SCHEMA for event in events)
    assert [event["event"] for event in events][-2:] == ["CLAIM_PR_ATTACHED", "CLAIM_RELEASED"]


def test_corrupt_store_fails_closed_without_overwrite(tmp_path: Path) -> None:
    state = tmp_path / "claims.json"
    tmp_path.mkdir(exist_ok=True)
    state.write_text("{broken", encoding="utf-8")

    with pytest.raises(ClaimStoreCorrupt):
        _claim(TaskClaimStore(tmp_path), task="KA-002", owner="agent-a", scope="src")

    assert state.read_text(encoding="utf-8") == "{broken"


def test_scope_must_be_repo_relative(tmp_path: Path) -> None:
    store = TaskClaimStore(tmp_path)
    with pytest.raises(ClaimError, match="repo-relative"):
        _claim(store, task="KA-002", owner="agent-a", scope="../secret")
    with pytest.raises(ClaimError, match="repo kökü"):
        _claim(store, task="KA-002", owner="agent-a", scope=".")


def test_cli_returns_conflict_exit_code_and_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    common = [
        "--store",
        str(tmp_path),
        "claim",
        "--task",
        "KA-002",
        "--repo",
        "lumos-core",
        "--branch",
        "codex/ka-002",
        "--worktree",
        "/worktrees/ka-002",
        "--scope",
        "src",
    ]
    assert claim_cli_main([*common, "--owner", "agent-a"]) == 0
    capsys.readouterr()

    assert claim_cli_main([*common, "--owner", "agent-b"]) == 2
    payload = json.loads(capsys.readouterr().out)

    assert payload["accepted"] is False
    assert payload["conflicts"][0]["reason"] == "DUPLICATE_TASK"


def test_delegated_child_cannot_reactivate_parent_task_id(tmp_path: Path) -> None:
    store = TaskClaimStore(
        tmp_path,
        clock=Clock(),
        delegation_verifier=_delegation_verifier(tmp_path, "lead"),
    )
    parent = _claim(store, task="KA-002", owner="lead", scope="src/lumos_board").claim
    assert parent is not None

    duplicate = _claim(
        store,
        task="KA-002",
        owner="worker",
        scope="src/lumos_board/task_claim.py",
        parent_claim_id=parent.claim_id,
        delegation_token=_delegation_token(
            parent_claim_id=parent.claim_id,
            child_task_id="KA-002",
        ),
    )

    assert duplicate.accepted is False
    assert duplicate.claim is None
    assert [conflict.reason for conflict in duplicate.conflicts] == ["DUPLICATE_TASK"]


def test_override_result_reports_no_blocking_conflicts(tmp_path: Path) -> None:
    store = TaskClaimStore(
        tmp_path, clock=Clock(), override_verifier=_verifier(tmp_path, "security-admin")
    )
    original = _claim(store, task="KA-002", owner="agent-a", scope="src").claim
    assert original is not None

    replacement = _claim(
        store,
        task="KA-002",
        owner="agent-b",
        scope="src",
        override_token=_approval_token(),
        override_reason="owner unavailable",
    )

    assert replacement.accepted is True
    assert replacement.conflicts == ()
    acquired = next(
        event
        for event in _events(store.audit_path)
        if event["event"] == "CLAIM_ACQUIRED" and event["owner"] == "agent-b"
    )
    assert acquired["details"]["overridden"] == [original.claim_id]


def test_queue_reserves_place_and_promotes_oldest_first(tmp_path: Path) -> None:
    store = TaskClaimStore(tmp_path)
    first = _claim(store, task="KA-A", owner="agent-a", scope="src").claim
    assert first is not None
    second = _claim(store, task="KA-B", owner="agent-b", scope="src", queue_on_conflict=True)
    third = _claim(store, task="KA-C", owner="agent-c", scope="src", queue_on_conflict=True)
    assert second.claim is not None and second.claim.status is ClaimStatus.QUEUED
    assert third.claim is not None and third.claim.status is ClaimStatus.QUEUED

    jumper = _claim(store, task="KA-D", owner="agent-d", scope="src")
    assert jumper.accepted is False

    store.release(first.claim_id, owner="agent-a")
    by_task = {claim.task_id: claim for claim in store.list_claims()}
    assert by_task["KA-B"].status is ClaimStatus.ACTIVE
    assert by_task["KA-C"].status is ClaimStatus.QUEUED
    promoted = next(event for event in _events(store.audit_path) if event["event"] == "CLAIM_PROMOTED")
    assert promoted["owner"] == "agent-b"


def test_failed_operation_leaves_no_audit_trace(tmp_path: Path) -> None:
    clock = Clock()
    store = TaskClaimStore(tmp_path, clock=clock)
    first = _claim(store, task="KA-A", owner="agent-a", scope="src", ttl_seconds=60).claim
    assert first is not None

    clock.value = NOW + timedelta(seconds=120)
    with pytest.raises(ClaimError, match="açık claim bulunamadı"):
        store.heartbeat(first.claim_id, owner="agent-a", ttl_seconds=60)

    events_after_failure = [event["event"] for event in _events(store.audit_path)]
    assert "CLAIM_EXPIRED" not in events_after_failure

    before = (store.state_path.read_bytes(), store.state_path.stat().st_mtime_ns)
    store.list_claims()
    after = (store.state_path.read_bytes(), store.state_path.stat().st_mtime_ns)
    assert after == before
    assert "CLAIM_EXPIRED" not in [event["event"] for event in _events(store.audit_path)]

    # Expire yazma yolunda kalır (list değil).
    replacement = _claim(store, task="KA-B", owner="agent-b", scope="src")
    assert replacement.accepted is True
    expired_events = [
        event for event in _events(store.audit_path) if event["event"] == "CLAIM_EXPIRED"
    ]
    assert len(expired_events) == 1


def test_parent_closure_cascades_to_children(tmp_path: Path) -> None:
    store = TaskClaimStore(
        tmp_path,
        clock=Clock(),
        delegation_verifier=_delegation_verifier(tmp_path, "lead"),
    )
    parent = _claim(store, task="KA-P", owner="lead", scope="src/lumos_board").claim
    assert parent is not None
    child = _claim(
        store,
        task="KA-P-sub",
        owner="worker",
        scope="src/lumos_board/task_claim.py",
        parent_claim_id=parent.claim_id,
        delegation_token=_delegation_token(
            parent_claim_id=parent.claim_id,
            child_task_id="KA-P-sub",
        ),
    ).claim
    assert child is not None

    store.release(parent.claim_id, owner="lead")

    closed = {claim.task_id: claim.status for claim in store.list_claims(include_closed=True)}
    assert closed["KA-P-sub"] is ClaimStatus.EXPIRED
    orphan_events = [
        event
        for event in _events(store.audit_path)
        if event["event"] == "CLAIM_EXPIRED" and event["details"].get("reason") == "parent_closed"
    ]
    assert [event["claim_id"] for event in orphan_events] == [child.claim_id]

    reclaimed = _claim(store, task="KA-N", owner="agent-x", scope="src/lumos_board/task_claim.py")
    assert reclaimed.accepted is True


def test_delegation_cannot_be_combined_with_override(tmp_path: Path) -> None:
    store = TaskClaimStore(
        tmp_path,
        clock=Clock(),
        override_verifier=_verifier(tmp_path, "security-admin"),
        delegation_verifier=_delegation_verifier(tmp_path, "agent-a"),
    )
    parent = _claim(store, task="KA-002", owner="agent-a", scope="src").claim
    assert parent is not None

    with pytest.raises(ClaimError, match="birleştirilemez"):
        _claim(
            store,
            task="KA-002",
            owner="agent-b",
            scope="src/task.py",
            parent_claim_id=parent.claim_id,
            delegation_token=_delegation_token(
                parent_claim_id=parent.claim_id,
                parent_owner="agent-a",
                child_owner="agent-b",
                child_task_id="KA-002",
                scope="src/task.py",
            ),
            override_token=_approval_token(),
            override_reason="owner unavailable",
        )

    assert store.list_claims()[0].claim_id == parent.claim_id


def test_multiple_queued_claims_promote_together_without_error(tmp_path: Path) -> None:
    store = TaskClaimStore(tmp_path)
    blocker = _claim(store, task="KA-A", owner="agent-a", scope="src").claim
    assert blocker is not None
    second = _claim(store, task="KA-B", owner="agent-b", scope="src/x.py", queue_on_conflict=True).claim
    third = _claim(store, task="KA-C", owner="agent-c", scope="src/y.py", queue_on_conflict=True).claim
    assert second is not None and third is not None

    store.release(blocker.claim_id, owner="agent-a")

    states = {claim.task_id: claim.status for claim in store.list_claims(include_closed=True)}
    assert states["KA-B"] is ClaimStatus.ACTIVE
    assert states["KA-C"] is ClaimStatus.ACTIVE


def test_override_succeeds_with_queued_waiters_and_preserves_queue(tmp_path: Path) -> None:
    store = TaskClaimStore(
        tmp_path, clock=Clock(), override_verifier=_verifier(tmp_path, "security-admin")
    )
    active = _claim(store, task="KA-002", owner="agent-a", scope="src").claim
    assert active is not None
    waiter = _claim(store, task="KA-W", owner="agent-w", scope="src/w.py", queue_on_conflict=True).claim
    assert waiter is not None and waiter.status is ClaimStatus.QUEUED

    replacement = _claim(
        store,
        task="KA-002",
        owner="agent-b",
        scope="src",
        override_token=_approval_token(),
        override_reason="owner unavailable",
    )

    assert replacement.accepted is True
    states = {claim.task_id: claim.status for claim in store.list_claims(include_closed=True)}
    assert states["KA-002"] is ClaimStatus.ACTIVE or ClaimStatus.OVERRIDDEN
    by_id = {claim.claim_id: claim.status for claim in store.list_claims(include_closed=True)}
    assert by_id[active.claim_id] is ClaimStatus.OVERRIDDEN
    assert by_id[waiter.claim_id] is ClaimStatus.QUEUED
    assert replacement.claim is not None and by_id[replacement.claim.claim_id] is ClaimStatus.ACTIVE


def test_override_promotes_waiters_blocked_only_by_old_lease(tmp_path: Path) -> None:
    store = TaskClaimStore(
        tmp_path, clock=Clock(), override_verifier=_verifier(tmp_path, "security-admin")
    )
    broad = _claim(store, task="KA-002", owner="agent-a", scope="src").claim
    assert broad is not None
    waiter = _claim(store, task="KA-W", owner="agent-w", scope="src/w.py", queue_on_conflict=True).claim
    assert waiter is not None and waiter.status is ClaimStatus.QUEUED

    replacement = _claim(
        store,
        task="KA-002",
        owner="agent-b",
        scope="src/b.py",
        override_token=_approval_token(),
        override_reason="owner unavailable",
    )

    assert replacement.accepted is True
    by_id = {claim.claim_id: claim.status for claim in store.list_claims(include_closed=True)}
    assert by_id[waiter.claim_id] is ClaimStatus.ACTIVE


def test_list_claims_is_byte_stable_and_skips_exclusive_lock(tmp_path: Path) -> None:
    store = TaskClaimStore(tmp_path)
    claimed = _claim(store, task="KA-L", owner="agent-a", scope="src").claim
    assert claimed is not None
    state = store.state_path
    audit = store.audit_path
    before_state = state.read_bytes()
    before_mtime = state.stat().st_mtime_ns
    before_audit = audit.read_bytes()
    before_audit_mtime = audit.stat().st_mtime_ns

    listed = store.list_claims()
    assert [item.claim_id for item in listed] == [claimed.claim_id]
    assert state.read_bytes() == before_state
    assert state.stat().st_mtime_ns == before_mtime
    assert audit.read_bytes() == before_audit
    assert audit.stat().st_mtime_ns == before_audit_mtime

    lock_held = threading.Event()
    release_lock = threading.Event()

    def hold_exclusive() -> None:
        with store.lock_path.open("a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            lock_held.set()
            release_lock.wait(timeout=5)
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    holder = threading.Thread(target=hold_exclusive)
    holder.start()
    assert lock_held.wait(timeout=2)
    started = time.monotonic()
    again = store.list_claims()
    elapsed = time.monotonic() - started
    release_lock.set()
    holder.join(timeout=2)
    assert [item.claim_id for item in again] == [claimed.claim_id]
    assert elapsed < 0.5


def test_cli_list_does_not_block_writer_or_rewrite_store(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    store = TaskClaimStore(tmp_path)
    claimed = _claim(store, task="KA-CLI", owner="agent-a", scope="src").claim
    assert claimed is not None
    before = store.state_path.read_bytes()
    before_mtime = store.state_path.stat().st_mtime_ns

    lock_held = threading.Event()
    release_lock = threading.Event()

    def hold_exclusive() -> None:
        with store.lock_path.open("a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            lock_held.set()
            release_lock.wait(timeout=5)
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    holder = threading.Thread(target=hold_exclusive)
    holder.start()
    assert lock_held.wait(timeout=2)
    started = time.monotonic()
    code = claim_cli_main(["--store", str(tmp_path), "list"])
    elapsed = time.monotonic() - started
    release_lock.set()
    holder.join(timeout=2)
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert elapsed < 0.5
    assert payload["claims"][0]["claim_id"] == claimed.claim_id
    assert store.state_path.read_bytes() == before
    assert store.state_path.stat().st_mtime_ns == before_mtime


def test_list_claims_preserves_corrupt_fail_closed(tmp_path: Path) -> None:
    state = tmp_path / "claims.json"
    tmp_path.mkdir(exist_ok=True)
    state.write_text("{broken", encoding="utf-8")
    store = TaskClaimStore(tmp_path)
    with pytest.raises(ClaimStoreCorrupt):
        store.list_claims()
    assert state.read_text(encoding="utf-8") == "{broken"
    assert claim_cli_main(["--store", str(tmp_path), "list"]) == 2

