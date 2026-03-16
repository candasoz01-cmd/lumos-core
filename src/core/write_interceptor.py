from __future__ import annotations

# ruff: noqa: E402

"""
Write interceptor: core/protected path'ler için direct write yerine patch lifecycle kullanımı.

Bu katman:
- Hedef path'in core/protected olup olmadığını workspace_contract üzerinden belirler.
- Protected/core için:
  - direct write girişimlerini audit'e "DIRECT_WRITE_ATTEMPT" olarak loglar,
  - yazımı patch_pipeline üzerinden yönlendirmeyi uygular.
- Non-core hedeflerde mevcut davranışı korur.

Notlar:
- Şu an için yalnızca "replace_file" tarzı tam içerik overwrite senaryosunu destekler.
- Patch apply, non-protected için hızlı yol; protected için üst katmanın READY_FOR_APPLY + gate
  akışını kullanması beklenir.
"""

from dataclasses import dataclass
from pathlib import Path

from core.guard_audit import GuardEvent, record_guard_event
from core.change_sensitivity import ChangeSensitivity, classify_sensitivity
from core.patch_pipeline import (
    ProtectedApplyForbidden,
    apply_patch,
    propose_text_patch,
    validate_proposal_against_filesystem,
)
from core.evolution_log import record_event
from core.workspace_contract import CoreWriteForbidden, is_core_state_path


@dataclass(frozen=True)
class WriteRequest:
    target_path: Path
    content: str
    base_dir: Path
    sandbox_mode: bool
    caller: str
    source: str = "unknown"
    user_initiated: bool = False


def is_protected_core_path(base_dir: Path, target_path: Path) -> bool:
    """
    Çalışma kökü altında core/protected state path mi?

    workspace_contract.is_core_state_path ile hizalıdır.
    """
    return is_core_state_path(base_dir, target_path)


def intercept_write(
    req: WriteRequest,
    *,
    allow_direct_non_core: bool = True,
) -> None:
    """
    Yazım isteğini yakala ve gerekli durumda patch pipeline'a yönlendir.

    Davranış:
    - sandbox_mode=True ve hedef core/protected ise:
      - CoreWriteForbidden yükseltir (mevcut guard ile uyumlu).
    - protected/core path:
      - Direct write girişimini audit'e loglar.
      - Patch proposal üretir, validation çalıştırır.
      - Apply için ProtectedApplyForbidden gate'ini korur (READY_FOR_APPLY + allow_protected_apply üst katmanın sorumluluğunda).
    - non-core path:
      - allow_direct_non_core=True ise doğrudan yazım yapılır.
    """
    target = req.target_path
    base = req.base_dir
    protected = is_protected_core_path(base, target)
    sensitivity = classify_sensitivity(target)

    # Sandbox modunda core/protected path'e yazım mevcut guard ile zaten yasak.
    if req.sandbox_mode and protected:
        raise CoreWriteForbidden(
            "Sandbox modunda protected/core path'e direct write yasak",
        )

    # Sensitivity tabanlı yönlendirme:
    # - CRITICAL / HIGH → patch pipeline'a yönlendirilir.
    # - NORMAL → sandbox devrede değilse direct write, aksi halde mevcut guard'lara güvenilir.
    # - LOW → direct write (mevcut davranış).
    if sensitivity in (ChangeSensitivity.LOW, ChangeSensitivity.NORMAL) and not protected:
        # Non-core ve düşük/normal hassasiyet: doğrudan yaz; audit entry üret.
        record_guard_event(
            GuardEvent(
                action="write",
                decision="allow",
                path=target,
                sandbox_mode=req.sandbox_mode,
                reason=f"direct_write_{sensitivity.name}",
                caller=req.caller,
            ),
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(req.content, encoding="utf-8")
        return

    # Protected/core veya HIGH/CRITICAL hassasiyet: direct write girişimini audit'e yaz.
    record_guard_event(
        GuardEvent(
            action="write",
            decision="deny",
            path=target,
            sandbox_mode=req.sandbox_mode,
            reason=f"DIRECT_WRITE_ATTEMPT_sensitivity_{sensitivity.name}",
            caller=req.caller,
        ),
    )
    record_event(
        plan_id=None,
        patch_ids=[],
        action_type="DIRECT_WRITE_REDIRECTED",
        result="denied",
        affected_paths=[str(target)],
        sensitivity_levels=[sensitivity.name],
        rollback_occurred=False,
        conflict_detected=False,
    )

    # Protected hedef için patch proposal üret.
    proposal = propose_text_patch(
        target,
        req.content,
        reason="write_interceptor_protected_core_update",
        caller=req.caller,
        source=req.source,
        user_initiated=req.user_initiated,
        protected_target=True,
    )

    # Fingerprint doğrulaması: drift varsa apply seviyesinde review zorunlu olacak.
    _ = validate_proposal_against_filesystem(proposal)

    # Apply için lifecycle gate'i zorla:
    # - allow_protected_apply=False → ProtectedApplyForbidden; üst katman READY_FOR_APPLY + gate ayarını yapmalı.
    try:
        apply_patch(
            proposal,
            assume_reviewed=req.user_initiated,
            allow_protected_apply=False,
        )
    except ProtectedApplyForbidden:
        # Protected apply henüz izinli değil; sadece proposal + validation ile sınırlı kal.
        # Bu durumda apply devreye alınmadı; üst katman patch_registry üzerinden
        # lifecycle'ı tamamlayabilir.
        record_guard_event(
            GuardEvent(
                action="patch",
                decision="deny",
                path=target,
                sandbox_mode=req.sandbox_mode,
                reason="protected_apply_blocked_by_lifecycle_gate",
                caller="core.write_interceptor.intercept_write",
            ),
        )
        return

