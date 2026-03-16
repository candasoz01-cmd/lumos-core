from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from core.adaptive_weights import load_weights
from core.decision_model import MutationOption
from core.decision_simulator import SimulationResult
from core.decision_quality_estimator import estimate_decision_quality
from core.strategy_updater import get_memory_bias_score_for_option


@dataclass
class RankedOption:
    option: MutationOption
    simulation: SimulationResult
    final_score: float


def _option_dict_for_estimator(option: MutationOption) -> dict:
    """Build dict for estimate_decision_quality from MutationOption."""
    strategy = "minimal"
    if option.option_id and "-" in option.option_id:
        prefix = option.option_id.split("-", 1)[0].lower()
        if prefix in ("minimal", "aggressive", "medium"):
            strategy = prefix
    return {
        "strategy": strategy,
        "estimated_impact": option.estimated_impact,
    }


def _quality_score_from_estimate(estimate: dict) -> float:
    """Derive a single additive score from estimator output. In [-0.2, 0.2]."""
    try:
        success = float(estimate.get("predicted_success", 0.5))
        risk = float(estimate.get("predicted_risk", 0.5))
        return (success - risk) * 0.2
    except (TypeError, ValueError):
        return 0.0


def rank_options(
    options: List[MutationOption],
    simulations: List[SimulationResult],
    *,
    history_path: Optional[Path] = None,
    feedback_path: Optional[Path] = None,
    memory_patterns_path: Optional[Path] = None,
) -> List[RankedOption]:
    """
    Seçenekleri final_score ile değerlendirir, yüksekten düşüğe sıralar.
    options[i] ile simulations[i] eşleşir (aynı sıra).
    Ağırlıklar .lumos/weights.json'dan okunur; yoksa varsayılan 0.4/0.3/0.3 kullanılır.
    final_score = base_score + quality_score + memory_bias (estimator/memory unavailable → 0).
    """
    weights = load_weights()
    ranked: List[RankedOption] = []
    for option, simulation in zip(options, simulations):
        base_score = (
            option.estimated_success_probability * weights.success_weight
            + (1 - simulation.estimated_risk) * weights.risk_weight
            + option.estimated_impact * weights.impact_weight
        )
        quality_score = 0.0
        try:
            opt_dict = _option_dict_for_estimator(option)
            estimate = estimate_decision_quality(
                opt_dict,
                {},
                history_path=history_path,
                feedback_path=feedback_path,
                memory_patterns_path=memory_patterns_path,
            )
            quality_score = _quality_score_from_estimate(estimate)
        except Exception:
            quality_score = 0.0
        memory_bias = 0.0
        try:
            memory_bias = get_memory_bias_score_for_option(
                option.option_id,
                memory_patterns_path=memory_patterns_path,
            )
        except Exception:
            memory_bias = 0.0
        final_score = base_score + quality_score + memory_bias
        ranked.append(RankedOption(option=option, simulation=simulation, final_score=final_score))
    ranked.sort(key=lambda r: r.final_score, reverse=True)
    return ranked
