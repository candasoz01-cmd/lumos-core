"""Small command-line gate for Lumos Board task claims."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from lumos_board.central_store import DEFAULT_REF, CentralClaimStore
from lumos_board.write_attestation import ClaimGuard as WriteAttestationGuard
from lumos_board.write_gate import WriteGate
from lumos_board.founder_approval import (
    FounderApprovalStore,
    FounderApproverRegistry,
)
from lumos_board.task_claim import (
    ClaimError,
    ClaimStatus,
    DelegationVerifier,
    OverrideApprovalVerifier,
    TaskClaim,
    TaskClaimStore,
    _scope_overlap,
)


def _store_dir(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    configured = os.environ.get("LUMOS_BOARD_DIR")
    if configured:
        return Path(configured)
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ClaimError("--store veya LUMOS_BOARD_DIR gerekli") from exc
    common_path = Path(common)
    if not common_path.is_absolute():
        common_path = Path.cwd() / common_path
    return common_path.resolve().parent / ".lumos" / "board"


def _git_common_dir() -> Path:
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ClaimError("merkezi pano için git deposu içinde çalışılmalı") from exc
    path = Path(common)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _central_remote() -> str:
    configured = os.environ.get("LUMOS_BOARD_REMOTE", "").strip()
    if configured:
        return configured
    try:
        return subprocess.run(
            ["git", "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ClaimError("merkezi pano remote'u bulunamadı (LUMOS_BOARD_REMOTE veya origin)") from exc


def _claim_store(
    explicit_store: str | None,
    *,
    override_verifier: OverrideApprovalVerifier | None = None,
    delegation_verifier: DelegationVerifier | None = None,
) -> TaskClaimStore:
    """Claims are central by default; local only when explicitly requested.

    No silent fallback: if the central board is unreachable the command fails
    (exit 2) instead of writing a lock that other agents cannot see.
    """
    local_dir = explicit_store or os.environ.get("LUMOS_BOARD_DIR")
    if local_dir:
        return TaskClaimStore(
            Path(local_dir),
            override_verifier=override_verifier,
            delegation_verifier=delegation_verifier,
        )
    cache = os.environ.get("LUMOS_BOARD_CACHE_DIR")
    cache_dir = Path(cache) if cache else _git_common_dir().parent / ".lumos" / "board-central"
    return CentralClaimStore(
        remote=_central_remote(),
        ref=os.environ.get("LUMOS_BOARD_REF", DEFAULT_REF),
        cache_dir=cache_dir,
        override_verifier=override_verifier,
        delegation_verifier=delegation_verifier,
    )


def check_write_permission(
    claims: Sequence[TaskClaim], *, branch: str, owner: str, paths: Sequence[str]
) -> dict[str, object]:
    """May ``owner`` write ``paths`` on ``branch`` right now? (pre-commit gate)

    Yes only if every path is inside an ACTIVE claim of this owner on this
    branch and no other ACTIVE claim (outside that owner's claim family)
    overlaps it. Used by ops/claim_guard/hooks to stop a commit before it
    exists.
    """
    owned = [
        c for c in claims
        if c.status is ClaimStatus.ACTIVE and c.owner == owner and c.branch == branch
    ]
    family = {c.claim_id for c in owned}
    changed = True
    while changed:  # parents of my delegated claims and my own children
        changed = False
        for c in claims:
            if c.claim_id in family:
                continue
            if c.parent_claim_id in family or any(
                o.parent_claim_id == c.claim_id for o in claims if o.claim_id in family
            ):
                family.add(c.claim_id)
                changed = True
    uncovered: list[str] = []
    foreign: list[dict[str, object]] = []
    used: set[str] = set()
    for raw in paths:
        path = raw.strip().replace("\\", "/")
        covering = [c for c in owned if any(path == s or path.startswith(s + "/") for s in c.scopes)]
        if covering:
            used.update(c.claim_id for c in covering)
        else:
            uncovered.append(path)
        for other in claims:
            if other.status is not ClaimStatus.ACTIVE or other.claim_id in family:
                continue
            if any(_scope_overlap(path, scope) for scope in other.scopes):
                foreign.append({"path": path, "owner": other.owner, "task_id": other.task_id, "claim_id": other.claim_id})
    return {
        "ok": not uncovered and not foreign and bool(paths),
        "claim_ids": sorted(used),
        "uncovered": uncovered,
        "foreign": foreign,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m lumos_board.claim_cli")
    parser.add_argument("--store")
    subparsers = parser.add_subparsers(dest="command", required=True)

    claim = subparsers.add_parser("claim")
    claim.add_argument("--task", required=True)
    claim.add_argument("--repo", required=True)
    claim.add_argument("--branch", required=True)
    claim.add_argument("--worktree", required=True)
    claim.add_argument("--owner", required=True)
    claim.add_argument("--scope", action="append", required=True)
    claim.add_argument("--topic", action="append", default=[], dest="topics")
    claim.add_argument("--ttl", type=int, default=1800)
    claim.add_argument("--queue", action="store_true")
    claim.add_argument("--parent")
    claim.add_argument("--delegation-token")
    claim.add_argument("--override-token")
    claim.add_argument("--override-reason")

    heartbeat = subparsers.add_parser("heartbeat")
    heartbeat.add_argument("claim_id")
    heartbeat.add_argument("--owner", required=True)
    heartbeat.add_argument("--ttl", type=int, default=1800)

    release = subparsers.add_parser("release")
    release.add_argument("claim_id")
    release.add_argument("--owner", required=True)

    attach_pr = subparsers.add_parser("attach-pr")
    attach_pr.add_argument("claim_id")
    attach_pr.add_argument("--owner", required=True)
    attach_pr.add_argument("--pr", required=True)

    result = subparsers.add_parser("result")
    result.add_argument("claim_id")
    result.add_argument("--owner", required=True)
    result.add_argument("--commit", required=True)
    result.add_argument("--tree", required=True)
    result.add_argument("--branch", required=True)
    result.add_argument("--tests", required=True)

    handoff = subparsers.add_parser("handoff")
    handoff.add_argument("claim_id")
    handoff.add_argument("--owner", required=True)
    handoff.add_argument("--to", required=True, dest="to_owner")
    handoff.add_argument("--commit", required=True)
    handoff.add_argument("--tree", required=True)
    handoff.add_argument("--branch", required=True)
    handoff.add_argument("--tests", required=True)
    handoff.add_argument("--ttl", type=int, default=1800)

    listing = subparsers.add_parser("list")
    listing.add_argument("--all", action="store_true")

    write_check = subparsers.add_parser("write-check")
    write_check.add_argument("--token")
    write_check.add_argument("--owner", required=True)
    write_check.add_argument("--path", action="append", required=True, dest="paths")

    write_attest = subparsers.add_parser("write-attest")
    write_attest_cmds = write_attest.add_subparsers(dest="attest_command", required=True)
    attest = write_attest_cmds.add_parser("attest")
    attest.add_argument("--token", required=True)
    attest.add_argument("--owner", required=True)
    attest.add_argument("--claim-id", required=True)
    attest.add_argument("--task", required=True)
    attest.add_argument("--scope", action="append", required=True)
    attest.add_argument("--path", action="append", required=True, dest="paths")
    attest.add_argument("--parent-sha", required=True)
    attest_verify = write_attest_cmds.add_parser("verify")
    attest_verify.add_argument("--repo", default=".")
    attest_verify.add_argument("--base", required=True)
    attest_verify.add_argument("--head", required=True)

    check = subparsers.add_parser("check")
    check.add_argument("--branch", required=True)
    check.add_argument("--owner", required=True)
    check.add_argument("--path", action="append", default=[])
    check.add_argument("--paths-from-stdin", action="store_true")

    migrate = subparsers.add_parser("migrate-local")
    migrate.add_argument("--from", dest="source", required=True)
    migrate.add_argument("--actor", required=True)

    approval = subparsers.add_parser("approval")
    approval_commands = approval.add_subparsers(dest="approval_command", required=True)

    request = approval_commands.add_parser("request")
    request.add_argument("--task", required=True)
    request.add_argument("--gate", required=True)
    request.add_argument("--action", required=True)
    request.add_argument("--head-sha", required=True)

    grant = approval_commands.add_parser("grant")
    grant.add_argument("approval_id")
    grant.add_argument("--approved-by", required=True)

    check = approval_commands.add_parser("check")
    check.add_argument("--task", required=True)
    check.add_argument("--gate", required=True)
    check.add_argument("--action", required=True)
    check.add_argument("--head-sha", required=True)

    approval_commands.add_parser("list")
    return parser


def _approval_main(args: argparse.Namespace) -> int:
    registry = None
    if args.approval_command == "grant":
        registry_path = os.environ.get("LUMOS_FOUNDER_APPROVER_REGISTRY")
        if not registry_path:
            raise ClaimError("onay için LUMOS_FOUNDER_APPROVER_REGISTRY gerekli")
        registry = FounderApproverRegistry.from_registry_file(Path(registry_path))
    store = FounderApprovalStore(_store_dir(args.store), registry=registry)
    if args.approval_command == "request":
        approval = store.request(
            task=args.task, gate=args.gate, action=args.action, head_sha=args.head_sha
        )
        print(
            json.dumps(
                {"approval": approval.to_dict(), "already_approved": approval.is_approved},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    if args.approval_command == "grant":
        approval = store.grant(args.approval_id, approved_by=args.approved_by)
        print(json.dumps(approval.to_dict(), ensure_ascii=False, sort_keys=True))
        return 0
    if args.approval_command == "check":
        approval = store.check(
            task=args.task, gate=args.gate, action=args.action, head_sha=args.head_sha
        )
        if approval is None:
            print(json.dumps({"approved": False}, ensure_ascii=False, sort_keys=True))
            return 2
        print(
            json.dumps(
                {"approved": True, "approval": approval.to_dict()},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    values = [approval.to_dict() for approval in store.list_approvals()]
    print(json.dumps({"approvals": values}, ensure_ascii=False, sort_keys=True))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "approval":
            return _approval_main(args)
        override_verifier = None
        delegation_verifier = None
        if args.command == "claim" and args.override_token:
            registry = os.environ.get("LUMOS_OVERRIDE_APPROVER_REGISTRY")
            secret = os.environ.get("LUMOS_OVERRIDE_APPROVAL_SECRET")
            if not registry or not secret:
                raise ClaimError("override için approver registry ve approval secret gerekli")
            override_verifier = OverrideApprovalVerifier.from_registry_file(Path(registry), secret=secret)
        if args.command == "claim" and args.delegation_token:
            registry = os.environ.get("LUMOS_DELEGATION_OWNER_REGISTRY")
            secret = os.environ.get("LUMOS_DELEGATION_SECRET")
            if not registry or not secret:
                raise ClaimError("delegation için owner registry ve secret gerekli")
            delegation_verifier = DelegationVerifier.from_registry_file(Path(registry), secret=secret)
        store = _claim_store(
            args.store,
            override_verifier=override_verifier,
            delegation_verifier=delegation_verifier,
        )
        write_gate = WriteGate(store, secret=os.environ.get("LUMOS_WRITE_GATE_SECRET"))
        if args.command == "write-check":
            decision = write_gate.check(
                token=args.token, owner=args.owner, paths=args.paths
            )
            print(json.dumps(decision.to_dict(), ensure_ascii=False, sort_keys=True))
            return 0 if decision.allowed else 2
        if args.command == "write-attest":
            guard = WriteAttestationGuard(secret=os.environ.get("LUMOS_WRITE_GATE_SECRET"))
            if args.attest_command == "verify":
                verdict = guard.verify_range(
                    Path(args.repo), base=args.base, head=args.head
                )
                print(json.dumps(verdict.to_dict(), ensure_ascii=False, sort_keys=True))
                return 0 if verdict.allowed else 2
            token = guard.attest(
                write_gate=write_gate,
                token=args.token,
                owner=args.owner,
                paths=args.paths,
                parent_sha=args.parent_sha,
                claim_id=args.claim_id,
                task_id=args.task,
                scopes=args.scope,
            )
            print(json.dumps({"attestation": token}, ensure_ascii=False, sort_keys=True))
            return 0
        if args.command == "check":
            paths = list(args.path)
            if args.paths_from_stdin:
                paths += [line for line in sys.stdin.read().splitlines() if line.strip()]
            report = check_write_permission(
                store.list_claims(), branch=args.branch, owner=args.owner, paths=paths
            )
            print(json.dumps(report, ensure_ascii=False, sort_keys=True))
            return 0 if report["ok"] else 2
        if args.command == "migrate-local":
            if not isinstance(store, CentralClaimStore):
                raise ClaimError("migrate-local yalnız merkezi panoya yazar; --store/LUMOS_BOARD_DIR verme")
            report = store.import_local(Path(args.source), actor=args.actor)
            print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
            return 2 if report.conflicts or report.needs_reclaim else 0
        if args.command == "claim":
            result = store.claim(
                task_id=args.task,
                repo=args.repo,
                branch=args.branch,
                worktree=args.worktree,
                owner=args.owner,
                scopes=args.scope,
                ttl_seconds=args.ttl,
                queue_on_conflict=args.queue,
                parent_claim_id=args.parent,
                delegation_token=args.delegation_token,
                override_token=args.override_token,
                override_reason=args.override_reason,
                topics=args.topics,
            )
            payload = result.to_dict()
            if result.accepted and result.claim is not None and write_gate.configured():
                payload["write_token"] = write_gate.issue(result.claim)
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            return 0 if result.accepted else 2
        if args.command == "heartbeat":
            value = store.heartbeat(args.claim_id, owner=args.owner, ttl_seconds=args.ttl)
        elif args.command == "release":
            value = store.release(args.claim_id, owner=args.owner)
            write_gate.revoke(args.claim_id)
        elif args.command == "attach-pr":
            value = store.attach_pr(args.claim_id, owner=args.owner, pr_ref=args.pr)
        elif args.command in {"result", "handoff"}:
            try:
                tests = json.loads(args.tests)
            except json.JSONDecodeError as exc:
                raise ClaimError("test sonucu JSON olmalı") from exc
            if args.command == "result":
                value = store.record_result(
                    args.claim_id,
                    owner=args.owner,
                    commit=args.commit,
                    tree=args.tree,
                    branch=args.branch,
                    tests=tests,
                )
            else:
                value = store.handoff(
                    args.claim_id,
                    owner=args.owner,
                    to_owner=args.to_owner,
                    commit=args.commit,
                    tree=args.tree,
                    branch=args.branch,
                    tests=tests,
                    ttl_seconds=args.ttl,
                )
        else:
            values = [claim.to_dict() for claim in store.list_claims(include_closed=args.all)]
            print(json.dumps({"claims": values}, ensure_ascii=False, sort_keys=True))
            return 0
        print(json.dumps(value.to_dict(), ensure_ascii=False, sort_keys=True))
        return 0
    except ClaimError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
