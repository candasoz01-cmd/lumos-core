from __future__ import annotations

# ruff: noqa: E402

"""
Decision explorer: change_plan öncesinde çoklu aday yaklaşım üretip skorlayan katman.

Akış:
goal/request
→ candidate MutationOption listesi
→ seçenekleri puanla
→ en iyi adayı seç
→ seçilen adaydan ChangePlan üret
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple
import uuid

from core.change_sensitivity import ChangeSensitivity, classify_sensitivity
from core.decision_model import MutationOption
from core.evolution_log import record_event
from core.change_plan import ChangePlan


@dataclass(frozen=True)
class DecisionExplorerConfig:
    enabled: bool = True


def _summarize_sensitivity(target_paths: Iterable[Path]) -> List[ChangeSensitivity]:
    return [classify_sensitivity(p) for p in target_paths]


def _compute_score(
    *,
    risk: float,
    complexity: float,
    success: float,
    impact: float,
    sensitivities: List[ChangeSensitivity],
) -> float:
    """
    Basit, açıklanabilir skor fonksiyonu.

    Heuristic:
    - Düşük risk ve complexity, yüksek success ve impact tercih edilir.
    - HIGH/CRITICAL sensitivity durumunda risk penalize edilir.
    """
    base = (success * 0.4) + (impact * 0.3) - (risk * 0.2) - (complexity * 0.1)
    penalty = 0.0
    if any(s in (ChangeSensitivity.HIGH, ChangeSensitivity.CRITICAL) for s in sensitivities):
        penalty = 0.1
    return base - penalty


def _make_option(
    *,
    kind: str,
    description: str,
    target_paths: List[Path],
    risk: float,
    complexity: float,
    success: float,
    impact: float,
) -> MutationOption:
    sensitivities = _summarize_sensitivity(target_paths)
    score = _compute_score(
        risk=risk,
        complexity=complexity,
        success=success,
        impact=impact,
        sensitivities=sensitivities,
    )
    rationale = (
        f"{kind}: risk={risk:.2f}, complexity={complexity:.2f}, "
        f"success={success:.2f}, impact={impact:.2f}, sensitivities="
        f"{[s.name for s in sensitivities]}, score={score:.3f}"
    )
    return MutationOption(
        option_id=f"{kind}-{uuid.uuid4()}",
        description=description,
        target_paths=target_paths,
        estimated_risk=risk,
        estimated_complexity=complexity,
        estimated_success_probability=success,
        estimated_impact=impact,
        sensitivity_summary=sensitivities,
        score=score,
        rationale=rationale,
    )


def generate_candidate_options(
    goal_description: str,
    target_paths: Iterable[Path],
) -> List[MutationOption]:
    """
    Verilen hedef ve target_paths için en az 3 aday seçenek üret.

    - minimal değişiklik
    - orta seviye iyileştirme
    - daha kapsamlı ama riskli iyileştirme
    """
    paths = list(target_paths)
    if not paths:
        return []

    options: List[MutationOption] = []

    options.append(
        _make_option(
            kind="minimal",
            description=f"Minimal, dar kapsamlı değişiklik: {goal_description}",
            target_paths=paths,
            risk=0.1,
            complexity=0.2,
            success=0.9,
            impact=0.4,
        ),
    )
    options.append(
        _make_option(
            kind="medium",
            description=f"Orta seviye iyileştirme: {goal_description}",
            target_paths=paths,
            risk=0.3,
            complexity=0.4,
            success=0.8,
            impact=0.6,
        ),
    )
    options.append(
        _make_option(
            kind="aggressive",
            description=f"Daha kapsamlı ama riskli iyileştirme: {goal_description}",
            target_paths=paths,
            risk=0.6,
            complexity=0.7,
            success=0.6,
            impact=0.9,
        ),
    )

    # Evolution: DECISION_OPTIONS_GENERATED
    record_event(
        plan_id=None,
        patch_ids=[],
        action_type="DECISION_OPTIONS_GENERATED",
        result="ok",
        affected_paths=[str(p) for p in paths],
        sensitivity_levels=[
            s.name
            for s in _summarize_sensitivity(paths)
        ],
        rollback_occurred=False,
        conflict_detected=False,
    )

    return options


def select_best_option(options: List[MutationOption]) -> Tuple[MutationOption, List[MutationOption]]:
    """
    En yüksek skorlu adayı seç; tüm adayları skorlarına göre sıralı döndür.
    """
    sorted_opts = sorted(options, key=lambda o: o.score, reverse=True)
    best = sorted_opts[0]
    # Evolution: DECISION_OPTION_SELECTED
    record_event(
        plan_id=None,
        patch_ids=[],
        action_type="DECISION_OPTION_SELECTED",
        result="ok",
        affected_paths=[str(p) for p in best.target_paths],
        sensitivity_levels=[s.name for s in best.sensitivity_summary],
        rollback_occurred=False,
        conflict_detected=False,
    )
    return best, sorted_opts


def create_plan_from_option(
    goal_description: str,
    option: MutationOption,
) -> ChangePlan:
    """
    Seçilen seçenekten minimal bir ChangePlan üret.

    Not: Şu an için sadece target_paths'i taşıyan boş patch listesi ile plan oluşturmak,
    ileride gerçek PatchProposal listesiyle doldurulmak üzere bir iskelet sağlar.
    """
    # Boş patch listesi ile plan oluşturmak RFC'si: call site gerçek patch'leri ekleyecek.
    plan = ChangePlan.new(goal_description, [])
    return plan

