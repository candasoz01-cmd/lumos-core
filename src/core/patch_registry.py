from __future__ import annotations

"""
Patch registry ve lifecycle state yönetimi.

Bu modül, PatchProposal nesnelerinin lifecycle'ını yönetir:

- PROPOSED → VALIDATED → READY_FOR_APPLY → APPLIED → (isteğe bağlı) ROLLED_BACK
- Her patch için basit bir in-memory kayıt tutulur.
- Sandbox ve apply sonuçları kaydedilir.

Notlar:
- Registry process içi in-memory'dir; multi-process dayanıklılık hedeflenmez.
- Amaç: patch'lerin durumu, audit ve olası rollback için merkezi bir gerçeklik kaynağı sağlamak.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Literal, Optional

from core.patch_model import PatchFingerprint, PatchProposal
from core.guard_audit import GuardEvent, record_guard_event
from core.evolution_log import record_event


PatchState = Literal[
    "PROPOSED",
    "VALIDATED",
    "READY_FOR_APPLY",
    "APPLYING",
    "APPLIED",
    "REJECTED",
    "FAILED",
    "FAILED_CONFLICT",
    "ROLLED_BACK",
]


@dataclass(frozen=True)
class PatchRecord:
    patch_id: str
    proposal: PatchProposal
    state: PatchState
    created_at: datetime
    updated_at: datetime
    sandbox_result: Optional[dict] = None
    apply_result: Optional[dict] = None


_REGISTRY: Dict[str, PatchRecord] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def register_proposal(proposal: PatchProposal) -> PatchRecord:
    """
    Yeni bir proposal için registry kaydı oluştur.

    - Varsayılan state: PROPOSED.
    - Eğer aynı id ile kayıt zaten varsa, mevcut kayıt döndürülür.
    """
    existing = _REGISTRY.get(proposal.id)
    if existing is not None:
        return existing
    ts = _now()
    record = PatchRecord(
        patch_id=proposal.id,
        proposal=proposal,
        state="PROPOSED",
        created_at=ts,
        updated_at=ts,
        sandbox_result=None,
        apply_result=None,
    )
    _REGISTRY[proposal.id] = record
    record_guard_event(
        GuardEvent(
            action="patch",
            decision="allow",
            path=proposal.target_path,
            sandbox_mode=False,
            reason="patch_state_PROPOSED",
            caller="core.patch_registry.register_proposal",
        ),
    )
    return record


def get_record(patch_id: str) -> Optional[PatchRecord]:
    return _REGISTRY.get(patch_id)


def set_state(patch_id: str, new_state: PatchState) -> Optional[PatchRecord]:
    rec = _REGISTRY.get(patch_id)
    if rec is None:
        return None
    updated = replace(rec, state=new_state, updated_at=_now())
    _REGISTRY[patch_id] = updated
    record_guard_event(
        GuardEvent(
            action="patch",
            decision="allow",
            path=updated.proposal.target_path,
            sandbox_mode=False,
            reason=f"patch_state_{new_state}",
            caller="core.patch_registry.set_state",
        ),
    )
    return updated


def mark_validated(patch_id: str) -> Optional[PatchRecord]:
    return set_state(patch_id, "VALIDATED")


def mark_ready_for_apply(patch_id: str) -> Optional[PatchRecord]:
    """
    Patch review aşamasından geçmiş ve apply için hazır.
    """
    return set_state(patch_id, "READY_FOR_APPLY")


def mark_rejected(patch_id: str, reason: str) -> Optional[PatchRecord]:
    rec = _REGISTRY.get(patch_id)
    if rec is None:
        return None
    payload = {"status": "rejected", "reason": reason}
    updated = replace(
        rec,
        state="REJECTED",
        updated_at=_now(),
        apply_result=payload,
    )
    _REGISTRY[patch_id] = updated
    return updated


def record_sandbox_result(patch_id: str, temp_path: Path) -> Optional[PatchRecord]:
    rec = _REGISTRY.get(patch_id)
    if rec is None:
        return None
    payload = {
        "status": "ok",
        "temp_path": str(temp_path),
    }
    updated = replace(
        rec,
        updated_at=_now(),
        sandbox_result=payload,
    )
    _REGISTRY[patch_id] = updated
    record_guard_event(
        GuardEvent(
            action="patch",
            decision="allow",
            path=rec.proposal.target_path,
            sandbox_mode=True,
            reason="patch_sandbox_validated",
            caller="core.patch_registry.record_sandbox_result",
        ),
    )
    return updated


def record_apply_success(patch_id: str) -> Optional[PatchRecord]:
    rec = _REGISTRY.get(patch_id)
    if rec is None:
        return None
    payload = {"status": "applied"}
    updated = replace(
        rec,
        state="APPLIED",
        updated_at=_now(),
        apply_result=payload,
    )
    _REGISTRY[patch_id] = updated
    record_guard_event(
        GuardEvent(
            action="patch",
            decision="allow",
            path=rec.proposal.target_path,
            sandbox_mode=False,
            reason="patch_applied",
            caller="core.patch_registry.record_apply_success",
        ),
    )
    return updated


def record_apply_error(patch_id: str, message: str) -> Optional[PatchRecord]:
    rec = _REGISTRY.get(patch_id)
    if rec is None:
        return None
    payload = {"status": "error", "message": message}
    updated = replace(
        rec,
        updated_at=_now(),
        apply_result=payload,
    )
    _REGISTRY[patch_id] = updated
    record_guard_event(
        GuardEvent(
            action="patch",
            decision="deny",
            path=rec.proposal.target_path,
            sandbox_mode=False,
            reason=f"patch_apply_error:{message}",
            caller="core.patch_registry.record_apply_error",
        ),
    )
    return updated


def rollback_patch(
    patch_id: str,
) -> Optional[PatchRecord]:
    """
    APPLIED durumundaki bir patch'i geri al.

    Kurallar:
    - Sadece state=APPLIED için rollback denenir.
    - Mevcut dosya içeriği, proposal.proposed_text fingerprint'i ile eşleşmiyorsa
      (başka bir değişiklik olmuşsa) rollback yapılmaz; apply_result hata ile güncellenir.
    - Eşleşiyorsa, original_text dosyaya yazılır ve state=ROLLED_BACK olur.
    """
    rec = _REGISTRY.get(patch_id)
    if rec is None:
        return None
    if rec.state != "APPLIED":
        return record_apply_error(
            patch_id,
            f"rollback_not_allowed_from_state_{rec.state}",
        )

    proposal = rec.proposal
    path = proposal.target_path
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    current_fp = PatchFingerprint.from_text(current)
    proposed_fp = PatchFingerprint.from_text(proposal.proposed_text)

    if current_fp.hex_digest != proposed_fp.hex_digest:
        # Dosya beklenen applied içeriğe uymuyor; rollback riskli.
        return record_apply_error(
            patch_id,
            "rollback_aborted_due_to_content_drift",
        )

    # Eski içeriğe dön.
    record_guard_event(
        GuardEvent(
            action="patch",
            decision="allow",
            path=path,
            sandbox_mode=False,
            reason="patch_rollback_started",
            caller="core.patch_registry.rollback_patch",
        ),
    )
    path.write_text(proposal.original_text, encoding="utf-8")
    updated = replace(
        rec,
        state="ROLLED_BACK",
        updated_at=_now(),
        apply_result={"status": "rolled_back"},
    )
    _REGISTRY[patch_id] = updated
    record_guard_event(
        GuardEvent(
            action="patch",
            decision="allow",
            path=path,
            sandbox_mode=False,
            reason="patch_rolled_back",
            caller="core.patch_registry.rollback_patch",
        ),
    )
    record_event(
        plan_id=None,
        patch_ids=[patch_id],
        action_type="PATCH_ROLLED_BACK",
        result="rolled_back",
        affected_paths=[str(path)],
        sensitivity_levels=[],
        rollback_occurred=True,
        conflict_detected=False,
    )
    return updated


def clear_registry() -> None:
    """
    Testler için helper: tüm kayıtları temizler.
    """
    _REGISTRY.clear()

