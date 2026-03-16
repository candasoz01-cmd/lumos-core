from __future__ import annotations

"""
Patch pipeline: proposal → validation → (sandbox) → controlled apply.

Bu modül, core/protected hedefler için "generate != apply" ilkesini uygular:

- AI veya üst katman doğrudan dosya overwrite etmez.
- Önce PatchProposal üretilir (patch_model).
- İsteğe bağlı sandbox doğrulaması yapılır.
- Guard/audit ile birlikte controlled apply aşaması ayrı bir kapıdan geçer.

Notlar:
- Varsayılan davranış: protected_target=True ise doğrudan apply kapalıdır.
- Non-core hedefler için pipeline yine kullanılabilir; apply izni daha gevşektir.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
import tempfile

from core.guard_audit import GuardEvent, GuardDecision, GuardAction, record_guard_event
from core.patch_model import PatchProposal, PatchMetadata
from core.evolution_log import record_event
from core.patch_registry import (
    PatchRecord,
    mark_ready_for_apply,
    mark_validated,
    record_apply_error,
    record_sandbox_result,
    register_proposal,
)
from core.patch_transaction import apply_with_transaction


PatchValidationStatus = Literal["ok", "fingerprint_mismatch"]


@dataclass(frozen=True)
class PatchValidationResult:
    status: PatchValidationStatus
    message: str
    requires_review: bool
    protected_target: bool


class ProtectedApplyForbidden(Exception):
    """
    Protected/core hedef için kontrolsüz apply girişimi.

    Bu istisna, generate ve apply aşamalarını birbirinden ayıran ana kapıdır.
    """


def _read_text_if_exists(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def propose_text_patch(
    target_path: Path,
    new_content: str,
    *,
    reason: str,
    caller: str,
    source: str = "agent",
    user_initiated: bool = False,
    protected_target: bool = False,
) -> PatchProposal:
    """
    Hedef dosya için "replace_file" türünde patch önerisi üret.

    - Dosya varsa mevcut içerik okunur; yoksa boş string kullanılır.
    - PatchMetadata içinde protected_target ve requires_review bayrakları set edilir.
    """
    original_text = _read_text_if_exists(target_path)
    metadata = PatchMetadata(
        reason=reason,
        caller=caller,
        source=source,
        user_initiated=user_initiated,
        protected_target=protected_target,
        requires_review=protected_target,
    )

    proposal = PatchProposal.new_replace_file(
        target_path=target_path,
        original_text=original_text,
        proposed_text=new_content,
        metadata=metadata,
    )

    record_guard_event(
        GuardEvent(
            action="patch",
            decision="allow",
            path=target_path,
            sandbox_mode=False,
            reason="proposal_created_protected" if protected_target else "proposal_created",
            caller=caller,
        ),
    )
    # Lifecycle: registry'de PROPOSED state'i ile kaydet.
    register_proposal(proposal)
    # Evolution: PATCH_PROPOSED
    record_event(
        plan_id=None,
        patch_ids=[proposal.id],
        action_type="PATCH_PROPOSED",
        affected_paths=[str(proposal.target_path)],
        sensitivity_levels=[],
    )
    return proposal


def validate_proposal_against_filesystem(proposal: PatchProposal) -> PatchValidationResult:
    """
    PatchProposal'ı mevcut dosya durumu ile karşılaştır.

    - original_fingerprint, şu anki dosya içeriğinden yeniden hesaplanan fingerprint ile
      eşleşiyorsa "ok" döner.
    - Eşleşmiyorsa "fingerprint_mismatch" ile uyarı verir; apply aşamasında bu bilgi
      üst katman tarafından kullanılabilir.
    """
    current_text = _read_text_if_exists(proposal.target_path)
    from core.patch_model import PatchFingerprint  # yerel import; döngüden kaçınmak için

    current_fp = PatchFingerprint.from_text(current_text)
    if current_fp.hex_digest != proposal.original_fingerprint.hex_digest:
        # Drift: fingerprint uyuşmazlığı; lifecycle state PROPOSED olarak kalır.
        return PatchValidationResult(
            status="fingerprint_mismatch",
            message="Current file content does not match proposal fingerprint.",
            requires_review=True,
            protected_target=proposal.metadata.protected_target,
        )

    # Lifecycle: fingerprint eşleşiyorsa VALIDATED state'ine geçir.
    mark_validated(proposal.id)
    return PatchValidationResult(
        status="ok",
        message="Proposal fingerprint matches current file content.",
        requires_review=proposal.metadata.requires_review,
        protected_target=proposal.metadata.protected_target,
    )


def run_sandbox_validation(proposal: PatchProposal) -> Path:
    """
    Sandbox doğrulaması: önerilen içeriği geçici bir dosyaya yazar.

    - Gerçek hedef dosyaya dokunmaz.
    - Dönen path, üst katman tarafından ek kontroller (ör. parse, import, test) için kullanılabilir.
    """
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
        f.write(proposal.proposed_text)
        temp_path = Path(f.name)

    record_guard_event(
        GuardEvent(
            action="patch",
            decision="allow",
            path=temp_path,
            sandbox_mode=True,
            reason="sandbox_validation_write",
            caller="core.patch_pipeline.run_sandbox_validation",
        ),
    )
    # Lifecycle: sandbox sonucu registry'ye kaydet.
    record_sandbox_result(proposal.id, temp_path)
    return temp_path


def apply_patch(
    proposal: PatchProposal,
    *,
    assume_reviewed: bool = False,
    allow_protected_apply: bool = False,
) -> None:
    """
    Patch'i kontrollü şekilde uygula.

    Kurallar:
    - protected_target=True ve allow_protected_apply=False ise ProtectedApplyForbidden fırlatılır.
    - assume_reviewed=False ve proposal.metadata.requires_review=True ise ProtectedApplyForbidden fırlatılır.

    Böylece:
    - Non-core hedefler için generate+apply zinciri üst katmanda tek adımda çağrılabilir.
    - Core/protected hedefler için generate ve apply ayrılır; apply için açık gate gerekir.
    """
    protected = proposal.metadata.protected_target
    needs_review = proposal.metadata.requires_review

    # Lifecycle: kayıt varsa state'e göre koruma uygula.
    rec: PatchRecord | None = register_proposal(proposal)
    if protected:
        # Protected hedeflerde:
        # - allow_protected_apply=True zorunlu.
        # - READY_FOR_APPLY state'i zorunlu (review/apply gate).
        if not allow_protected_apply:
            record_guard_event(
                GuardEvent(
                    action="patch",
                    decision="deny",
                    path=proposal.target_path,
                    sandbox_mode=False,
                    reason="protected_target_apply_blocked",
                    caller="core.patch_pipeline.apply_patch",
                ),
            )
            record_apply_error(proposal.id, "protected_apply_without_allow_flag")
            raise ProtectedApplyForbidden(
                "Protected/core target requires explicit allow_protected_apply=True gate.",
            )
        if rec is not None and rec.state != "READY_FOR_APPLY":
            record_guard_event(
                GuardEvent(
                    action="patch",
                    decision="deny",
                    path=proposal.target_path,
                    sandbox_mode=False,
                    reason=f"protected_apply_from_invalid_state_{rec.state}",
                    caller="core.patch_pipeline.apply_patch",
                ),
            )
            record_apply_error(proposal.id, f"protected_apply_from_invalid_state_{rec.state}")
            raise ProtectedApplyForbidden(
                "Protected/core target must be in READY_FOR_APPLY state before apply.",
            )

    if needs_review and not assume_reviewed:
        record_guard_event(
            GuardEvent(
                action="patch",
                decision="deny",
                path=proposal.target_path,
                sandbox_mode=False,
                reason="requires_review_before_apply",
                caller="core.patch_pipeline.apply_patch",
            ),
        )
        record_apply_error(proposal.id, "apply_attempt_without_review_flag")
        raise ProtectedApplyForbidden(
            "PatchProposal requires review before apply; set assume_reviewed=True after review.",
        )

    # Transactional apply: lock + conflict kontrolü + atomic write + registry güncellemesi.
    apply_with_transaction(proposal)


