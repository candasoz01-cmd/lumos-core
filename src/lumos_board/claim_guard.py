"""claim-guard: verify a PR's writes against the central Lumos Board.

Read-only. It never writes the board (CI has ``contents: read``), it reads the
board ref, the PR's commits and its diff, and reports violations.

What a violation is (and is not)
--------------------------------
Git author/committer fields are **not** evidence: one GitHub account may push
for several agents, and a human may co-author an agent's commit. Identity is
established by three facts that must agree:

1. the commit's ``Lumos-Agent:`` trailer (who says they wrote it),
2. the commit's ``Lumos-Claim:`` trailer → a claim on the central board whose
   ``owner`` is that agent, and
3. that claim belongs to this PR (same head branch or ``pr_ref``), directly
   or through a delegated child claim (the board only stores a child with a
   ``parent_claim_id`` after verifying a signed delegation token).

Violations:

* ``NO_PR_CLAIM`` – the PR has no claim on the central board.
* ``UNCLAIMED_PATH`` – a changed file is outside every PR claim's scope.
* ``FOREIGN_ACTIVE_CLAIM`` – a changed file is inside another agent's ACTIVE
  claim that is not part of this PR.
* ``UNATTRIBUTED_COMMIT`` – a non-merge commit carries no ``Lumos-Claim`` /
  ``Lumos-Agent`` trailers.
* ``UNKNOWN_CLAIM`` / ``CLAIM_NOT_FOR_THIS_PR`` / ``QUEUED_CLAIM`` – the
  referenced claim is missing, belongs elsewhere, or never had write rights.
* ``AGENT_NOT_CLAIM_OWNER`` – the trailer agent is not the claim's owner.
* ``COMMIT_OUTSIDE_CLAIM_SCOPE`` – the commit touched files its claim does not
  cover.

Limits: trailers are self-asserted. This stops uncoordinated agents (the
2026-10-12 incident) and makes every write attributable; it is not
cryptographic proof against a deliberately lying agent.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath

from lumos_board.central_store import DEFAULT_REF, STATE_FILE, parse_state_text
from lumos_board.task_claim import ClaimError, ClaimStatus, TaskClaim, _scope_overlap

GUARD_SCHEMA = "lumos.claim_guard_report.v1"


@dataclass(frozen=True)
class CommitInfo:
    sha: str
    files: tuple[str, ...]
    claim_ids: tuple[str, ...]
    agents: tuple[str, ...]


@dataclass(frozen=True)
class Violation:
    code: str
    detail: str
    commit: str | None = None
    path: str | None = None

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {"code": self.code, "detail": self.detail}
        if self.commit:
            out["commit"] = self.commit
        if self.path:
            out["path"] = self.path
        return out


def _covered(path: str, scopes: Sequence[str]) -> bool:
    candidate = PurePosixPath(path)
    return any(
        candidate == PurePosixPath(scope) or PurePosixPath(scope) in candidate.parents
        for scope in scopes
    )


def _effective_status(claim: TaskClaim, now: datetime) -> ClaimStatus:
    if claim.status is ClaimStatus.ACTIVE and claim.expires_at <= now:
        return ClaimStatus.EXPIRED
    return claim.status


def pr_claims(claims: Sequence[TaskClaim], *, branch: str, pr_ref: str | None) -> dict[str, TaskClaim]:
    """Claims bound to this PR, plus their delegated descendants."""
    bound = {
        c.claim_id: c
        for c in claims
        if c.branch == branch or (pr_ref is not None and c.pr_ref == pr_ref)
    }
    changed = True
    while changed:
        changed = False
        for c in claims:
            if c.claim_id not in bound and c.parent_claim_id in bound:
                bound[c.claim_id] = c
                changed = True
    return bound


def evaluate(
    claims: Sequence[TaskClaim],
    *,
    branch: str,
    pr_ref: str | None,
    changed_files: Sequence[str],
    commits: Sequence[CommitInfo],
    now: datetime,
) -> list[Violation]:
    violations: list[Violation] = []
    by_id = {c.claim_id: c for c in claims}
    mine = pr_claims(claims, branch=branch, pr_ref=pr_ref)
    writable = {
        cid: c for cid, c in mine.items() if c.status is not ClaimStatus.QUEUED
    }

    if not writable:
        violations.append(
            Violation("NO_PR_CLAIM", f"merkezi panoda '{branch}' dalı/PR için claim yok")
        )

    for path in changed_files:
        if writable and not any(_covered(path, c.scopes) for c in writable.values()):
            violations.append(Violation("UNCLAIMED_PATH", "değişen dosya PR claim kapsamı dışında", path=path))
        for other in claims:
            if other.claim_id in mine or _effective_status(other, now) is not ClaimStatus.ACTIVE:
                continue
            if any(_scope_overlap(path, scope) for scope in other.scopes):
                violations.append(
                    Violation(
                        "FOREIGN_ACTIVE_CLAIM",
                        f"dosya başka ajanın aktif claim'inde: {other.owner} / {other.task_id} ({other.claim_id})",
                        path=path,
                    )
                )

    for commit in commits:
        if not commit.claim_ids or not commit.agents:
            violations.append(
                Violation(
                    "UNATTRIBUTED_COMMIT",
                    "commit'te Lumos-Claim ve Lumos-Agent trailer'ları yok",
                    commit=commit.sha,
                )
            )
            continue
        if len(set(commit.agents)) != 1:
            violations.append(
                Violation("AGENT_NOT_CLAIM_OWNER", "commit birden fazla Lumos-Agent beyan ediyor", commit=commit.sha)
            )
            continue
        agent = commit.agents[0]
        commit_claims: list[TaskClaim] = []
        for claim_id in commit.claim_ids:
            claim = by_id.get(claim_id)
            if claim is None:
                violations.append(Violation("UNKNOWN_CLAIM", f"claim merkezi panoda yok: {claim_id}", commit=commit.sha))
                continue
            if claim_id not in mine:
                violations.append(
                    Violation(
                        "CLAIM_NOT_FOR_THIS_PR",
                        f"claim bu PR'a/dala bağlı değil: {claim_id} ({claim.branch})",
                        commit=commit.sha,
                    )
                )
                continue
            if claim.status is ClaimStatus.QUEUED:
                violations.append(Violation("QUEUED_CLAIM", f"kuyruktaki claim yazma yetkisi vermez: {claim_id}", commit=commit.sha))
                continue
            if claim.owner != agent:
                violations.append(
                    Violation(
                        "AGENT_NOT_CLAIM_OWNER",
                        f"Lumos-Agent '{agent}' claim sahibi '{claim.owner}' değil ve devir yok",
                        commit=commit.sha,
                    )
                )
                continue
            commit_claims.append(claim)
        if commit_claims:
            for path in commit.files:
                if not any(_covered(path, c.scopes) for c in commit_claims):
                    violations.append(
                        Violation(
                            "COMMIT_OUTSIDE_CLAIM_SCOPE",
                            "commit, beyan ettiği claim kapsamı dışında dosya değiştirdi",
                            commit=commit.sha,
                            path=path,
                        )
                    )
    return violations


# -- git collection (read-only) ----------------------------------------------


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise ClaimError(f"git {' '.join(args[:2])} başarısız: {' '.join(result.stderr.split())[:200]}")
    return result.stdout


def read_board(ref: str) -> list[TaskClaim]:
    return parse_state_text(_git("show", f"{ref}:{STATE_FILE}"))


def collect(base: str, head: str) -> tuple[list[str], list[CommitInfo]]:
    changed = [p for p in _git("diff", "--name-only", "--no-renames", f"{base}...{head}").splitlines() if p]
    commits: list[CommitInfo] = []
    for sha in _git("rev-list", "--no-merges", "--reverse", f"{base}..{head}").split():
        files = tuple(
            p for p in _git("diff-tree", "--no-commit-id", "--name-only", "--no-renames", "-r", sha).splitlines() if p
        )
        claim_ids = tuple(
            v.strip() for v in _git("show", "-s", "--format=%(trailers:key=Lumos-Claim,valueonly,separator=%x0A)", sha).splitlines() if v.strip()
        )
        agents = tuple(
            v.strip() for v in _git("show", "-s", "--format=%(trailers:key=Lumos-Agent,valueonly,separator=%x0A)", sha).splitlines() if v.strip()
        )
        commits.append(CommitInfo(sha, files, claim_ids, agents))
    return changed, commits


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m lumos_board.claim_guard")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--pr")
    parser.add_argument("--board-ref", default=os.environ.get("LUMOS_BOARD_GUARD_REF", "refs/remotes/origin/claude/lumos-board"))
    args = parser.parse_args(argv)
    try:
        claims = read_board(args.board_ref)
        changed, commits = collect(args.base, args.head)
    except ClaimError as exc:
        # Fail closed: an unreadable board is a failed check, never a pass.
        print(json.dumps({"schema": GUARD_SCHEMA, "ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    violations = evaluate(
        claims,
        branch=args.branch,
        pr_ref=args.pr,
        changed_files=changed,
        commits=commits,
        now=datetime.now(timezone.utc),
    )
    report = {
        "schema": GUARD_SCHEMA,
        "ok": not violations,
        "branch": args.branch,
        "pr": args.pr,
        "board_ref": args.board_ref,
        "default_board_ref": DEFAULT_REF,
        "changed_files": len(changed),
        "commits": len(commits),
        "violations": [v.to_dict() for v in violations],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    for v in violations:
        where = " ".join(x for x in (v.commit and v.commit[:9], v.path) if x)
        print(f"::error title=claim-guard {v.code}::{where} {v.detail}".strip(), file=sys.stderr)
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
