"""
Compressed memory pattern dataclasses for Lumos decision/evolution logs.
Used by memory_compressor to persist short reusable patterns that can guide future strategy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any


@dataclass
class MemoryPattern:
    """A single compressed pattern extracted from runtime logs."""

    pattern_id: str
    source: str
    summary: str
    confidence: float
    evidence_count: int
    recommended_bias: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-serializable dict."""
        return {
            "pattern_id": self.pattern_id,
            "source": self.source,
            "summary": self.summary,
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
            "recommended_bias": dict(self.recommended_bias),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryPattern:
        """Deserialize from a dict (e.g. from JSON)."""
        return cls(
            pattern_id=str(data.get("pattern_id", "")),
            source=str(data.get("source", "")),
            summary=str(data.get("summary", "")),
            confidence=float(data.get("confidence", 0.0)),
            evidence_count=int(data.get("evidence_count", 0)),
            recommended_bias=dict(data.get("recommended_bias", {})),
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, s: str) -> MemoryPattern:
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(s))
