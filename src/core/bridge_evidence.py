"""Retain bridge views before replacement; never replay completed execution."""
from pathlib import Path

from core.evidence_settings import archive_removed_file


class BridgeEvidenceError(OSError):
    """Execution may have happened already; a persistence retry must not execute it."""

    execution_may_have_run = True


def preserve_bridge_views(base: Path, paths: tuple[Path, ...]) -> None:
    try:
        for path in paths:
            if path.exists():
                archive_removed_file(base, path, operation="bridge.view.replace")
    except (OSError, ValueError, TypeError) as exc:
        raise BridgeEvidenceError(
            "Bridge evidence unavailable; previous views preserved; execution may "
            "already have run; do not replay execution"
        ) from exc
