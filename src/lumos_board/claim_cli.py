"""Small command-line gate for Lumos Board task claims."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Sequence

from lumos_board.task_claim import (
    ClaimError,
    DelegationVerifier,
    OverrideApprovalVerifier,
    TaskClaimStore,
)
from lumos_board.wall import format_wall_table, read_wall_projection


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

    listing = subparsers.add_parser("list")
    listing.add_argument("--all", action="store_true")
    listing.add_argument(
        "--raw",
        action="store_true",
        help="Eski claim JSON dökümü; varsayılan duvar özetidir",
    )
    _add_wall_view_args(listing)

    wall = subparsers.add_parser("wall", help="list ile aynı duvar özeti; ikinci yüzey değil")
    _add_wall_view_args(wall)
    return parser


def _add_wall_view_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=("table", "json"), default="table")
    parser.add_argument(
        "--status-dir",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="İsteğe bağlı agent_status kaynağı (tekrarlanabilir)",
    )
    parser.add_argument("--stale-after", type=float, default=120.0)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
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
        store = TaskClaimStore(
            _store_dir(args.store),
            override_verifier=override_verifier,
            delegation_verifier=delegation_verifier,
        )
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
            )
            print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
            return 0 if result.accepted else 2
        if args.command == "heartbeat":
            value = store.heartbeat(args.claim_id, owner=args.owner, ttl_seconds=args.ttl)
        elif args.command == "release":
            value = store.release(args.claim_id, owner=args.owner)
        elif args.command == "attach-pr":
            value = store.attach_pr(args.claim_id, owner=args.owner, pr_ref=args.pr)
        elif args.command == "wall" or (
            args.command == "list" and not getattr(args, "raw", False)
        ):
            return _print_wall(store, args)
        else:
            values = [claim.to_dict() for claim in store.list_claims(include_closed=args.all)]
            print(json.dumps({"claims": values}, ensure_ascii=False, sort_keys=True))
            return 0
        print(json.dumps(value.to_dict(), ensure_ascii=False, sort_keys=True))
        return 0
    except ClaimError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2


def _print_wall(store: TaskClaimStore, args: argparse.Namespace) -> int:
    status_sources: dict[str, str] = {}
    for item in args.status_dir:
        if "=" not in item:
            raise ClaimError("--status-dir NAME=PATH olmalı")
        name, path = item.split("=", 1)
        if not name.strip() or not path.strip():
            raise ClaimError("--status-dir NAME=PATH olmalı")
        status_sources[name.strip()] = path.strip()
    projection = read_wall_projection(
        store,
        status_sources=status_sources or None,
        stale_after_seconds=args.stale_after,
    )
    if args.format == "json":
        print(json.dumps(projection.to_dict(), ensure_ascii=False, sort_keys=True))
    else:
        print(format_wall_table(projection), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
