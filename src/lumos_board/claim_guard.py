"""claim-guard: verify a PR's writes against the central Lumos Board.

Read-only. It never writes the board (CI has ``contents: read``), it reads the
board ref, the PR's commits and its diff, and reports violations.

What a violation is (and is not)
--------------------------------
Git author/committer fields are **not** evidence: one GitHub account may push
for several agents, and a human may co-author an agent's commit. The unsigned
``Lumos-Agent:`` trailer is **not** identity proof either. Who was allowed to
write a commit is decided at that commit's committer time:

1. the ``Lumos-Claim-Attestation`` payload's ``owner`` (the field the sibling
   HMAC job binds; this job does not see the signing secret and does not
   treat a bare trailer as a substitute),
2. the board's claim and handoff history for the cited claim at or before
   that committer time (a later handoff does not rewrite the past), and
3. that claim belongs to this PR (same head branch or ``pr_ref``), directly
   or through a delegated child claim (the board only stores a child with a
   ``parent_claim_id`` after verifying a signed delegation token).

History replay uses each event's recorded ``owner``, which is the lease
holder at that event. A current ``CLAIM_HANDOFF`` keeps the giver in
``owner`` until ``CLAIM_HANDOFF_ACCEPTED``. An older immediate handoff stored
the recipient in ``owner`` on ``CLAIM_HANDOFF`` itself. Events after the
committer time are ignored, so a later transfer cannot authorise a commit
the recipient did not hold, and cannot strip a commit the giver did hold.

Violations:

* ``NO_PR_CLAIM`` – the PR has no claim on the central board.
* ``UNCLAIMED_PATH`` – a changed file is outside every PR claim's scope.
* ``FOREIGN_ACTIVE_CLAIM`` – a changed file is inside another agent's ACTIVE
  claim that is not part of this PR.
* ``UNATTRIBUTED_COMMIT`` – a non-merge commit carries no ``Lumos-Claim`` /
  ``Lumos-Agent`` trailers.
* ``UNKNOWN_CLAIM`` / ``CLAIM_NOT_FOR_THIS_PR`` / ``QUEUED_CLAIM`` – the
  referenced claim is missing, belongs elsewhere, or never had write rights.
* ``IDENTITY_UNVERIFIED`` – no attestation owner, or the unsigned trailer
  disagrees with that owner. The trailer is not accepted as proof.
* ``AGENT_NOT_CLAIM_OWNER`` – the attestation owner was not the claim's owner
  at commit time.
* ``COMMIT_OUTSIDE_CLAIM_SCOPE`` – the commit touched files its claim does not
  cover.
* ``SUPERSEDED_BY_ACTIVE_CLAIM`` – at commit time, the commit touches a file
  that another agent held outside the cited claim's delegation family (e.g. A
  cites its RELEASED claim after B took the file). A claim acquired after the
  commit does not rewrite that commit.

Limits: this job never receives the write-gate secret. HMAC verification
stays in ``write-attestation`` / ``write-attestation-trusted``. Reading the
payload owner is not a signature check, so TD-45 item (2) stays open: a
forged payload still fails only the HMAC job. Both jobs must pass.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath

from lumos_board.central_store import DEFAULT_REF, EVENTS_FILE, STATE_FILE, parse_state_text
from lumos_board.task_claim import (
    CLAIM_EVENT_SCHEMA,
    ClaimError,
    ClaimStatus,
    TaskClaim,
    _b64url_decode,
    _parse_time,
    _scope_overlap,
)
from lumos_board.write_attestation import ATTESTATION_SCHEMA, ATTESTATION_TRAILER, VERIFICATION_METHOD

GUARD_SCHEMA = "lumos.claim_guard_report.v1"


@dataclass(frozen=True)
class CommitInfo:
    sha: str
    files: tuple[str, ...]
    claim_ids: tuple[str, ...]
    agents: tuple[str, ...]
    committed_at: datetime | None = None
    attested_owner: str | None = None
    attested_claim_ids: tuple[str, ...] = ()


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


def _held_at(claim: TaskClaim, moment: datetime) -> bool:
    """Did this claim hold its scopes at ``moment``? Later leases do not count."""
    if claim.status is ClaimStatus.QUEUED or claim.started_at > moment:
        return False
    if claim.status is ClaimStatus.ACTIVE:
        return claim.expires_at > moment
    if claim.closed_at is None:
        return False
    return claim.closed_at > moment


def owner_at(claim_id: str, moment: datetime, events: Sequence[Mapping[str, object]]) -> str | None:
    """Lease holder at ``moment``, from events at or before that instant.

    Returns None when history cannot prove an owner. The claim row's current
    owner is intentionally not a fallback: a later handoff must not speak for
    an earlier commit.
    """
    ordered: list[tuple[datetime, str]] = []
    for event in events:
        if event.get("claim_id") != claim_id:
            continue
        raw_at = event.get("at")
        recorded = event.get("owner")
        if not isinstance(raw_at, str) or not isinstance(recorded, str) or not recorded:
            return None
        try:
            at = _parse_time(raw_at)
        except ValueError:
            return None
        ordered.append((at, recorded))
    ordered.sort(key=lambda item: item[0])
    holder: str | None = None
    for at, recorded in ordered:
        # Committer time is whole seconds. An event later in that same second
        # is still this commit's instant; a later second is a different owner.
        if at.replace(microsecond=0) <= moment.replace(microsecond=0):
            holder = recorded
        else:
            break
    return holder


def _attestation_identity(token: str) -> tuple[str, str] | None:
    """Read owner and claim id from an attestation payload.

    The HMAC is not checked here. ``write-attestation`` does that with the
    proof key, and ``write-attestation-trusted`` does it with the production
    secret. This job must not accept the unsigned agent trailer instead.
    """
    try:
        encoded_payload, _signature = token.split(".", 1)
        payload = json.loads(_b64url_decode(encoded_payload))
    except (ValueError, json.JSONDecodeError, UnicodeError):
        return None
    if not isinstance(payload, dict) or payload.get("schema") != ATTESTATION_SCHEMA:
        return None
    if payload.get("verification_method") != VERIFICATION_METHOD:
        return None
    owner = payload.get("owner")
    claim_id = payload.get("claim_id")
    if not isinstance(owner, str) or not owner.strip():
        return None
    if not isinstance(claim_id, str) or not claim_id.strip():
        return None
    return owner.strip(), claim_id.strip()


def _commit_attestation(tokens: Sequence[str]) -> tuple[str | None, tuple[str, ...]]:
    if not tokens:
        return None, ()
    owners: list[str] = []
    claim_ids: list[str] = []
    for token in tokens:
        parsed = _attestation_identity(token)
        if parsed is None:
            return None, ()
        owner, claim_id = parsed
        owners.append(owner)
        claim_ids.append(claim_id)
    if len(set(owners)) != 1:
        return None, ()
    return owners[0], tuple(claim_ids)


def _identity_violation(commit: CommitInfo) -> Violation | None:
    if commit.committed_at is None or not commit.attested_owner or not commit.attested_claim_ids:
        return Violation(
            "IDENTITY_UNVERIFIED",
            "imzasız Lumos-Agent trailer'ı kimlik kanıtı değil",
            commit=commit.sha,
        )
    if set(commit.agents) != {commit.attested_owner}:
        return Violation(
            "IDENTITY_UNVERIFIED",
            "Lumos-Agent trailer'ı attestation sahibi ile uyuşmuyor; trailer kimlik kanıtı değil",
            commit=commit.sha,
        )
    if set(commit.attested_claim_ids) != set(commit.claim_ids):
        return Violation(
            "IDENTITY_UNVERIFIED",
            "attestation claim kümesi Lumos-Claim trailer'ı ile uyuşmuyor",
            commit=commit.sha,
        )
    return None


def _family(claims: Sequence[TaskClaim], roots: set[str]) -> set[str]:
    """Claim ids linked to ``roots`` by verified delegation (ancestors + descendants)."""
    by_id = {c.claim_id: c for c in claims}
    family = set(roots)
    changed = True
    while changed:
        changed = False
        for c in claims:
            if c.claim_id in family:
                parent = c.parent_claim_id
                if parent and parent in by_id and parent not in family:
                    family.add(parent)
                    changed = True
            elif c.parent_claim_id in family:
                family.add(c.claim_id)
                changed = True
    return family


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
    events: Sequence[Mapping[str, object]] = (),
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
            commit_claims.append(claim)
        if not commit_claims:
            continue
        gap = _identity_violation(commit)
        if gap is not None:
            violations.append(gap)
            commit_claims = []
            continue
        authorized: list[TaskClaim] = []
        assert commit.committed_at is not None
        assert commit.attested_owner is not None
        for claim in commit_claims:
            historical = owner_at(claim.claim_id, commit.committed_at, events)
            if historical != commit.attested_owner:
                shown = historical or "yok"
                violations.append(
                    Violation(
                        "AGENT_NOT_CLAIM_OWNER",
                        f"attestation sahibi '{commit.attested_owner}' commit anında claim sahibi '{shown}' değil",
                        commit=commit.sha,
                    )
                )
                continue
            authorized.append(claim)
        commit_claims = authorized
        if commit_claims:
            family = _family(claims, {c.claim_id for c in commit_claims})
            for path in commit.files:
                rivals = [
                    other
                    for other in claims
                    if other.claim_id not in family
                    and other.owner != commit.attested_owner
                    and _held_at(other, commit.committed_at)
                    and any(_scope_overlap(path, scope) for scope in other.scopes)
                ]
                for other in rivals:
                    violations.append(
                        Violation(
                            "SUPERSEDED_BY_ACTIVE_CLAIM",
                            f"dosya commit anında {other.owner} / {other.task_id} ({other.claim_id}) claim'inde",
                            commit=commit.sha,
                            path=path,
                        )
                    )
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


def read_events(ref: str) -> list[dict[str, object]]:
    text = _git("show", f"{ref}:{EVENTS_FILE}")
    events: list[dict[str, object]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ClaimError("claim olay kaydı okunamıyor") from exc
        if not isinstance(payload, dict) or payload.get("schema") != CLAIM_EVENT_SCHEMA:
            raise ClaimError("claim olay kaydı geçersiz")
        events.append(payload)
    return events


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
        attestation = tuple(
            v.strip()
            for v in _git(
                "show",
                "-s",
                f"--format=%(trailers:key={ATTESTATION_TRAILER},valueonly,separator=%x0A)",
                sha,
            ).splitlines()
            if v.strip()
        )
        attested_owner, attested_claim_ids = _commit_attestation(attestation)
        raw_time = _git("show", "-s", "--format=%cI", sha).strip()
        try:
            committed_at = _parse_time(raw_time)
        except ValueError as exc:
            raise ClaimError("commit zamanı okunamıyor") from exc
        commits.append(
            CommitInfo(sha, files, claim_ids, agents, committed_at, attested_owner, attested_claim_ids)
        )
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
        events = read_events(args.board_ref)
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
        events=events,
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
