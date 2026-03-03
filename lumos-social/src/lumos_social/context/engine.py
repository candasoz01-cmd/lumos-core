"""Context engine: ingest interactions, report stats and importance score."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT_DIR = Path(".data")
_CONTEXT_FILE = "lumos_social_context.json"


@dataclass
class Interaction:
    """Single interaction: who, message, when."""

    name: str
    message: str
    ts: str  # ISO8601
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _context_path(base_dir: Path) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / _CONTEXT_FILE


def _load_interactions(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("interactions", []) if isinstance(data, dict) else []
    except Exception:
        return []


def _save_interactions(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"interactions": items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class ContextEngine:
    """Ingest interactions; report stats and importance score per name."""

    def __init__(self, base_dir: Path | str | None = None) -> None:
        self._base_dir = Path(base_dir or _DEFAULT_DIR)
        self._path = _context_path(self._base_dir)

    def ingest(self, name: str, message: str, ts: str) -> None:
        """Append one interaction. ts: ISO8601 (e.g. 2026-03-03T20:30:00Z)."""
        items = _load_interactions(self._path)
        items.append(
            {
                "name": name.strip(),
                "message": (message or "").strip(),
                "ts": ts.strip(),
            }
        )
        _save_interactions(self._path, items)

    def report(self, name: str) -> dict:
        """Stats for name: interaction_count, last_ts, importance_score."""
        items = _load_interactions(self._path)
        name = name.strip()
        subset = [x for x in items if (x.get("name") or "").strip() == name]
        if not subset:
            return {
                "name": name,
                "interaction_count": 0,
                "last_ts": None,
                "importance_score": 0.0,
            }
        times = []
        for x in subset:
            ts = x.get("ts") or ""
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                times.append(dt.timestamp())
            except Exception:
                pass
        last_ts = max(times) if times else None
        count = len(subset)
        # Importance: more interactions + recency boost (simple)
        recency = (last_ts or 0) / 1e10  # normalize
        importance_score = min(100.0, count * 10.0 + recency * 10)
        return {
            "name": name,
            "interaction_count": count,
            "last_ts": datetime.fromtimestamp(last_ts, tz=timezone.utc).isoformat()
            if last_ts
            else None,
            "importance_score": round(importance_score, 1),
        }


_engine: ContextEngine | None = None


def get_engine(base_dir: Path | str | None = None) -> ContextEngine:
    global _engine
    if _engine is None:
        _engine = ContextEngine(base_dir)
    return _engine
