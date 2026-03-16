from __future__ import annotations

# ruff: noqa: E402

"""
Evolution log: Lumos'un kendi gelişim geçmişini üst seviyede kaydeden katman.

Amaç:
- Plan → patch → transaction → result akışını tek bir event akışında görünür kılmak.
- Önemli lifecycle olaylarını append-only bir JSONL log'a yazmak.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional
import json
import uuid


# Varsayılan log path; testler LOG_PATH değerini override edebilir.
LOG_PATH: Path = Path("logs") / "lumos_evolution.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class EvolutionEvent:
    event_id: str
    timestamp: str
    plan_id: Optional[str]
    patch_ids: List[str]
    action_type: str
    result: str
    affected_paths: List[str]
    sensitivity_levels: List[str]
    rollback_occurred: bool
    conflict_detected: bool


def record_event(
    *,
    plan_id: Optional[str],
    patch_ids: Iterable[str],
    action_type: str,
    result: str = "ok",
    affected_paths: Iterable[str] = (),
    sensitivity_levels: Iterable[str] = (),
    rollback_occurred: bool = False,
    conflict_detected: bool = False,
) -> None:
    """
    Evolution event'i append-only JSONL log'a yaz.

    Bu fonksiyon best-effort çalışır; log yazımı hata verirse exception fırlatmaz.
    """
    event = EvolutionEvent(
        event_id=str(uuid.uuid4()),
        timestamp=_now_iso(),
        plan_id=plan_id,
        patch_ids=list(patch_ids),
        action_type=action_type,
        result=result,
        affected_paths=list(affected_paths),
        sensitivity_levels=list(sensitivity_levels),
        rollback_occurred=rollback_occurred,
        conflict_detected=conflict_detected,
    )
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
    except Exception:
        # Evolution log hiçbir zaman ana akışı bozmaz.
        return


def _read_all_events() -> List[dict]:
    if not LOG_PATH.is_file():
        return []
    out: List[dict] = []
    try:
        for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except Exception:
        return []
    return out


def get_recent_events(n: int) -> List[dict]:
    events = _read_all_events()
    if n <= 0:
        return []
    return events[-n:]


def get_failed_patches() -> List[dict]:
    events = _read_all_events()
    return [e for e in events if e.get("action_type") in ("PATCH_FAILED", "PLAN_FAILED")]


def get_rollbacks() -> List[dict]:
    events = _read_all_events()
    return [e for e in events if e.get("rollback_occurred")]


def get_conflict_stats() -> dict:
    events = _read_all_events()
    conflicts = [e for e in events if e.get("conflict_detected")]
    return {
        "total_events": len(events),
        "conflict_events": len(conflicts),
        "conflict_ratio": (len(conflicts) / len(events)) if events else 0.0,
    }

