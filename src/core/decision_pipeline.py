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
from core.evolution_tracker import DECISION_FEEDBACK_LOG_PATH, record_execution
from core.strategy_updater import apply_decision_feedback_updates


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
    - base_dir verilirse protected_target hesaplaması için kullanılır.
      Note: base_dir=None iken protected kontrolü zayıflar; autonomous apply açılmadan
      önce base_dir zorunlu hale getirilmelidir.
    - record_execution ile lumos_decision_feedback.jsonl'a yazılır.
    - update_weights_after_run=True ise bu run sonucu decision_feedback log'dan
      işlenip weights güncellenir; bir sonraki ranking load_weights() ile yeni ağırlıkları kullanır.
    """
    paths = list(target_paths)
    options = generate_candidate_options(goal, paths)
    if not options:
        return None

    simulations = [simulate_option(opt) for opt in options]
    ranked = rank_options(options, simulations)
    best_option = ranked[0].option

    result = execute_decision(best_option, base_dir=base_dir)
    record_execution(result)
    if update_weights_after_run:
        apply_decision_feedback_updates(feedback_log_path=DECISION_FEEDBACK_LOG_PATH)
    return result
