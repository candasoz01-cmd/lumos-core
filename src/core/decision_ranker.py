from __future__ import annotations

from dataclasses import dataclass
from typing import List

from core.decision_model import MutationOption
from core.decision_simulator import SimulationResult


@dataclass
class RankedOption:
    option: MutationOption
    simulation: SimulationResult
    final_score: float


def rank_options(
    options: List[MutationOption],
    simulations: List[SimulationResult],
) -> List[RankedOption]:
    """
    Seçenekleri final_score ile değerlendirir, yüksekten düşüğe sıralar.
    options[i] ile simulations[i] eşleşir (aynı sıra).
    """
    ranked: List[RankedOption] = []
    for option, simulation in zip(options, simulations):
        score = (
            option.estimated_success_probability * 0.4
            + (1 - simulation.estimated_risk) * 0.3
            + option.estimated_impact * 0.3
        )
        ranked.append(RankedOption(option=option, simulation=simulation, final_score=score))
    ranked.sort(key=lambda r: r.final_score, reverse=True)
    return ranked
