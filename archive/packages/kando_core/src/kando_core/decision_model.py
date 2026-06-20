from __future__ import annotations

# ruff: noqa: E402

"""Decision model for candidate mutation options."""

from dataclasses import dataclass
from pathlib import Path
from typing import List

from core.change_sensitivity import ChangeSensitivity


@dataclass(frozen=True)
class MutationOption:
    option_id: str
    description: str
    target_paths: List[Path]
    estimated_risk: float
    estimated_complexity: float
    estimated_success_probability: float
    estimated_impact: float
    sensitivity_summary: List[ChangeSensitivity]
    score: float
    rationale: str

