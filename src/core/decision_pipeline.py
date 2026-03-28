"""
Decision pipeline orchestrator: mevcut decision modüllerini tek akışta çalıştırır.

Akış:
  Explorer → Simulator → Ranker → Runner → evolution_tracker.record_execution
  → (opsiyonel) strategy_updater.apply_decision_feedback_updates
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from core.decision_explorer import generate_candidate_options
from core.decision_ranker import rank_options
from core.decision_runner import DecisionExecutionResult, execute_decision
from core.decision_simulator import simulate_option
from core.decision_history import record_decision_history
from core.evolution_tracker import DECISION_FEEDBACK_LOG_PATH, record_execution
from core.strategy_updater import apply_decision_feedback_updates

__all__ = ("infer_lumos_base_for_decision", "run_decision_pipeline")


def infer_lumos_base_for_decision(paths: Iterable[Path]) -> Optional[Path]:
    """
    Hedef yollarından .lumos kökünü bulur (yoksa None).
    base_dir verilmediğinde protected_target için zayıf kalan durumu giderir.
    """
    for p in paths:
        cur = Path(p).expanduser().resolve()
        if cur.is_file():
            cur = cur.parent
        for ancestor in [cur, *cur.parents]:
            if ancestor.name == ".lumos":
                return ancestor
    return None


def run_decision_pipeline(
    goal: str,
    target_paths: Iterable[Path],
    base_dir: Optional[Path] = None,
    update_weights_after_run: bool = True,
) -> Optional[DecisionExecutionResult]:
    """
    Explorer → Simulator → Ranker → Runner (decision-to-patch) → Feedback.

    - target_paths boşsa veya aday üretilemezse None döner.
    - En yüksek skorlu aday seçilir; runner best option'dan PatchProposal üretir,
      validate_proposal_against_filesystem ve isteğe bağlı sandbox çalıştırır; apply yapılmaz.
    - base_dir verilirse protected_target için kullanılır; None ise seçilen adayın
      target_paths üzerinden .lumos kökü çıkarılır (infer_lumos_base_for_decision).
    - record_execution ile lumos_decision_feedback.jsonl'a yazılır.
    - update_weights_after_run=True ise bu run sonucu decision_feedback log'dan
      işlenip weights güncellenir; bir sonraki ranking load_weights() ile yeni ağırlıkları kullanır.
    """
    paths = list(target_paths)
    if not paths:
        return None
    options = generate_candidate_options(goal, paths)
    if not options:
        return None

    simulations = [simulate_option(opt) for opt in options]
    ranked = rank_options(options, simulations)
    if not ranked:
        return None
    best_option = ranked[0].option

    targets_for_base = list(best_option.target_paths) if best_option.target_paths else paths
    effective_base = (
        base_dir if base_dir is not None else infer_lumos_base_for_decision(targets_for_base)
    )
    result = execute_decision(best_option, base_dir=effective_base)
    record_execution(result)
    record_decision_history(result, goal)
    if update_weights_after_run:
        apply_decision_feedback_updates(feedback_log_path=DECISION_FEEDBACK_LOG_PATH)
    return result
