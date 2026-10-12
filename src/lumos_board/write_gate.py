"""Task controller over the existing central claim lock.

Does not open a second store, CLI, or lease. Callers ask the current
``TaskClaimStore`` (``claims.lock``) whether this owner may write these
paths on this task. Cooperative skip is no longer enough once a caller
uses this gate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from lumos_board.task_claim import TaskClaim, TaskClaimStore


def assert_write(
    store: TaskClaimStore,
    *,
    task_id: str,
    owner: str,
    repo: str,
    scopes: Sequence[str],
    claim_id: str | None = None,
) -> TaskClaim:
    """Fail-closed write permission check on the shared claim lock."""
    return store.assert_write(
        task_id=task_id,
        owner=owner,
        repo=repo,
        scopes=scopes,
        claim_id=claim_id,
    )


def store_from_dir(store_dir: Path) -> TaskClaimStore:
    return TaskClaimStore(store_dir)
