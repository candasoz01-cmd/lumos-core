from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from core.decision_model import MutationOption
from core.patch_model import PatchProposal
from core.patch_pipeline import (
    propose_text_patch,
    validate_proposal_against_filesystem,
    run_sandbox_validation,
    PatchValidationResult,
)
from core.workspace_contract import is_core_state_path


def _read_text_if_exists(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


@dataclass(frozen=True)
class DecisionExecutionResult:
    option: MutationOption
    success: bool
    notes: str
    proposal_ids: Tuple[str, ...] = ()
    proposal_summary: str = ""
    proposal_diff: str = ""
    decision_explanation: str = ""

    @property
    def proposal_diff_preview(self) -> str:
        """Kısa diff görünürlüğü; uygulama yapılmaz. proposal_diff ile aynı içerik."""
        return self.proposal_diff


def explain_decision(option: MutationOption) -> str:
    """
    Seçilen option için insan okunabilir, deterministik açıklama üretir.
    LLM kullanılmaz; template tabanlı.
    """
    kind = option.option_id.split("-")[0] if "-" in option.option_id else "seçenek"
    kind_label = {
        "minimal": "Minimal değişiklik",
        "medium": "Orta seviye değişiklik",
        "aggressive": "Kapsamlı değişiklik",
    }.get(kind, kind.capitalize() + " değişiklik")

    risk_pct = int(round(option.estimated_risk * 100))
    success_pct = int(round(option.estimated_success_probability * 100))
    complexity_pct = int(round(option.estimated_complexity * 100))

    risk_label = "düşük" if option.estimated_risk < 0.3 else "orta" if option.estimated_risk < 0.6 else "yüksek"
    success_label = "yüksek" if option.estimated_success_probability >= 0.8 else "orta" if option.estimated_success_probability >= 0.5 else "düşük"
    complexity_label = "düşük" if option.estimated_complexity < 0.4 else "orta" if option.estimated_complexity < 0.7 else "yüksek"

    sens = option.sensitivity_summary
    if not sens:
        sensitivity_phrase = "hedef dosya bilinen sensitivity sınıfında değil."
    else:
        names = [s.name for s in sens]
        if len(names) == 1:
            sensitivity_phrase = f"hedef dosya {names[0]} sensitivity içeriyor."
        else:
            sensitivity_phrase = f"hedef dosyalar {', '.join(names)} sensitivity içeriyor."

    return (
        f"{kind_label} seçildi çünkü risk {risk_label} (%{risk_pct}), "
        f"karmaşıklık {complexity_label} (%{complexity_pct}), başarı olasılığı {success_label} (%{success_pct}) ve {sensitivity_phrase}"
    )


def _is_protected(base_dir: Optional[Path], target_path: Path) -> bool:
    # When base_dir is None, we cannot resolve core state; protected is treated as False.
    # TODO: Before autonomous apply is enabled, base_dir must be made mandatory so
    # protected_target is correctly set for core paths.
    if base_dir is None:
        return False
    return is_core_state_path(base_dir, target_path)


def option_to_proposals(
    option: MutationOption,
    base_dir: Optional[Path] = None,
) -> List[PatchProposal]:
    """
    Best option'tan PatchProposal listesi üret; dosyaya yazma yapılmaz.

    Her target_path için mevcut içerik okunur ve aynı içerikle (no-op) proposal üretilir.
    Böylece pipeline (propose → validate → sandbox) çalışır; apply çağrılmaz.
    """
    proposals: List[PatchProposal] = []
    for target_path in option.target_paths:
        current_text = _read_text_if_exists(target_path)
        protected = _is_protected(base_dir, target_path)
        proposal = propose_text_patch(
            target_path,
            current_text,
            reason=option.description,
            caller="core.decision_runner.option_to_proposals",
            source="decision_pipeline",
            user_initiated=False,
            protected_target=protected,
        )
        proposals.append(proposal)
    return proposals


def execute_decision(
    option: MutationOption,
    base_dir: Optional[Path] = None,
    run_validation: bool = True,
    run_sandbox: bool = True,
) -> DecisionExecutionResult:
    """
    Decision-to-patch bridge: best option → PatchProposal → validation → sonuç.
    Apply yapılmaz; sadece proposal üretilir ve isteğe bağlı sandbox doğrulaması çalıştırılır.
    """
    if not option.target_paths:
        return DecisionExecutionResult(
            option=option,
            success=False,
            notes="No target_paths defined for option.",
            decision_explanation=explain_decision(option),
        )

    proposals = option_to_proposals(option, base_dir)
    proposal_ids = tuple(p.id for p in proposals)
    validations: List[PatchValidationResult] = []
    sandbox_paths: List[Path] = []

    if run_validation:
        for p in proposals:
            validations.append(validate_proposal_against_filesystem(p))

    if run_sandbox:
        for p in proposals:
            sandbox_paths.append(run_sandbox_validation(p))

    status_ok = all(v.status == "ok" for v in validations) if validations else True
    summary_parts = [
        f"Proposals produced: {len(proposals)}",
        f"ids={list(proposal_ids)}",
    ]
    if validations:
        summary_parts.append(
            f"validation={[v.status for v in validations]}",
        )
    if sandbox_paths:
        summary_parts.append(f"sandbox_paths={[str(p) for p in sandbox_paths]}")
    summary_parts.append("Diff preview in proposal_diff (no apply).")
    proposal_summary = "; ".join(summary_parts)

    # Unified diff for all proposals (one block per file)
    diff_parts: List[str] = []
    for p in proposals:
        if p.diff_text:
            diff_parts.append(f"--- {p.target_path}\n{p.diff_text}")
    proposal_diff = "\n".join(diff_parts)

    notes = (
        "Decision-to-patch bridge: proposal produced, optional validation and sandbox run; "
        "no apply. " + proposal_summary
    )

    return DecisionExecutionResult(
        option=option,
        success=status_ok,
        notes=notes,
        proposal_ids=proposal_ids,
        proposal_summary=proposal_summary,
        proposal_diff=proposal_diff,
        decision_explanation=explain_decision(option),
    )


def format_result_preview(result: DecisionExecutionResult) -> str:
    """
    CLI için diff preview metni: açıklama + summary + proposal_diff.
    Apply yapılmaz; sadece görünürlük.
    """
    lines: List[str] = []
    if result.decision_explanation:
        lines.append(result.decision_explanation)
    lines.append(result.proposal_summary)
    if result.proposal_diff:
        lines.append("")
        lines.append("--- diff preview ---")
        lines.append(result.proposal_diff)
    return "\n".join(lines)

