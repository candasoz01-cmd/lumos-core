"""Identify which CheckRun may be consumed as ADR-028 standing evidence.

A CheckRun **name is not authority**. Live proof: `#793` produced two runs
called ``standing-class`` on the same commit — one red from the trusted
``pull_request_target`` workflow, one green forged by a workflow the pull
request had rewritten and declared as ``on: pull_request``. Consuming the
name alone would have read the forged green as a standing signal.

The question is not "is there a green check?" but "who produced the green
check, and in which event context?".

A run is trusted evidence only when **all** of these hold:

1. ``event`` is ``pull_request_target``
2. ``workflow_path`` is the canonical standing-class workflow
3. the workflow definition came from the base/default branch context
4. the evaluation matches this pull request and its current head/base
5. ``conclusion`` is ``success``

Anything from ``pull_request`` — same name or different — produces no
standing authority. Renaming the job (e.g. ``standing-class-trusted``) is a
readability aid for humans and logs, **not** a security boundary: an
attacker can name their forged workflow anything.

Fail-closed: unknown, missing, ambiguous, or mismatched runs yield no
authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TRUSTED_EVENT = "pull_request_target"
CANONICAL_WORKFLOW_PATH = ".github/workflows/standing-class.yml"
CONCLUSION_SUCCESS = "success"


@dataclass(frozen=True)
class CheckRunRecord:
    """One CheckRun as reported by the GitHub API, with its run context."""

    name: str
    event: str
    workflow_path: str
    conclusion: str
    head_sha: str
    base_sha: str
    pull_request_number: int | None = None
    workflow_ref: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def _branch_context_is_base(record: CheckRunRecord, default_branch: str) -> bool:
    """Did the workflow definition come from the base/default branch?

    ``workflow_ref`` looks like ``owner/repo/.github/workflows/x.yml@refs/heads/main``.
    Empty is not a pass: absence of evidence is not evidence.
    """
    if not record.workflow_ref:
        return False
    return record.workflow_ref.endswith(f"@refs/heads/{default_branch}")


def evaluate_run(
    record: CheckRunRecord,
    *,
    pull_request_number: int,
    head_sha: str,
    base_sha: str,
    default_branch: str = "main",
) -> dict[str, Any]:
    """Return why this run is or is not trusted standing evidence."""
    failures: list[str] = []
    if record.event != TRUSTED_EVENT:
        failures.append(f"event_not_trusted:{record.event or 'missing'}")
    if record.workflow_path != CANONICAL_WORKFLOW_PATH:
        failures.append(f"workflow_not_canonical:{record.workflow_path or 'missing'}")
    if not _branch_context_is_base(record, default_branch):
        failures.append("workflow_ref_not_base_branch")
    if record.pull_request_number != pull_request_number:
        failures.append("pull_request_mismatch")
    if record.head_sha != head_sha:
        failures.append("head_sha_mismatch")
    if record.base_sha != base_sha:
        failures.append("base_sha_mismatch")
    if record.conclusion != CONCLUSION_SUCCESS:
        failures.append(f"conclusion_not_success:{record.conclusion or 'missing'}")
    return {"trusted": not failures, "name": record.name, "reasons": failures}


def standing_evidence(
    records: list[CheckRunRecord] | tuple[CheckRunRecord, ...],
    *,
    pull_request_number: int,
    head_sha: str,
    base_sha: str,
    default_branch: str = "main",
) -> dict[str, Any]:
    """Decide whether trusted standing evidence exists across all runs.

    A forged green run never grants authority, and it never cancels a trusted
    red one: the trusted run is selected by context, not by name or by picking
    the most favourable result.
    """
    evaluations = [
        evaluate_run(
            record,
            pull_request_number=pull_request_number,
            head_sha=head_sha,
            base_sha=base_sha,
            default_branch=default_branch,
        )
        for record in records
    ]
    trusted = [row for row in evaluations if row["trusted"]]
    # A canonical trusted-context run that merely failed still counts as a
    # verdict; it must not be ignored in favour of an untrusted green one.
    trusted_context = [
        record
        for record in records
        if record.event == TRUSTED_EVENT
        and record.workflow_path == CANONICAL_WORKFLOW_PATH
        and _branch_context_is_base(record, default_branch)
    ]
    return {
        "standing_authorized": bool(trusted),
        "trusted_run_present": bool(trusted_context),
        "evaluations": evaluations,
        "reason": (
            "trusted_success"
            if trusted
            else ("trusted_run_not_success" if trusted_context else "no_trusted_run")
        ),
    }
