from __future__ import annotations

from dataclasses import dataclass
from typing import List

from core.adaptive_weights import load_weights
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
    Ağırlıklar .lumos/weights.json'dan okunur; yoksa varsayılan 0.4/0.3/0.3 kullanılır.
    """
    weights = load_weights()
    ranked: List[RankedOption] = []
    for option, simulation in zip(options, simulations):
        score = (
            option.estimated_success_probability * weights.success_weight
            + (1 - simulation.estimated_risk) * weights.risk_weight
            + option.estimated_impact * weights.impact_weight
        )
        ranked.append(RankedOption(option=option, simulation=simulation, final_score=score))
    ranked.sort(key=lambda r: r.final_score, reverse=True)
    return ranked
