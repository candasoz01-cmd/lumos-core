from __future__ import annotations

"""
Decision model: mutation seçenekleri için aday yaklaşım veri modeli.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List

from core.change_sensitivity import ChangeSensitivity


@dataclass(frozen=True)
class MutationOption:
    option_id: str
    description: str
    target_paths: List[Path]
    estimated_risk: float  # 0.0 (düşük) → 1.0 (yüksek)
    estimated_complexity: float  # 0.0 → 1.0
    estimated_success_probability: float  # 0.0 → 1.0
    estimated_impact: float  # 0.0 → 1.0
    sensitivity_summary: List[ChangeSensitivity]
    score: float
    rationale: str

