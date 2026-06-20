from __future__ import annotations

# ruff: noqa: E402

"""
Patch transaction ve atomic apply katmanı.

Amaç:
- Aynı dosyaya eşzamanlı patch apply girişimlerinde basit bir lock mekanizması sağlamak.
- Apply sırasında dosya içeriğinin fingerprint'ini tekrar kontrol ederek conflict tespiti yapmak.
- Atomic write (temp dosya + rename) ile dosyanın yarım kalmasını engellemek.
- PatchRegistry ile APPLYING / FAILED / FAILED_CONFLICT state ve zaman alanlarını güncellemek.
"""

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Dict

from core.guard_audit import GuardEvent, record_guard_event
from core.patch_model import PatchFingerprint, PatchProposal
from core.patch_registry import (
    get_record,
    record_apply_error,
    register_proposal,
)
from core.evolution_log import record_event


_LOCKS: Dict[Path, Lock] = {}
_LOCKS_GUARD = Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_lock(path: Path) -> Lock:
    with _LOCKS_GUARD:
        lock = _LOCKS.get(path)
        if lock is None:
            lock = Lock()
            _LOCKS[path] = lock
        return lock


def _atomic_write(path: Path, content: str) -> None:
    """
    Atomic write: temp dosyaya yaz, sonra rename ile hedefe taşı.

    - Aynı filesystem üzerinde rename genellikle atomic kabul edilir.
    """
    tmp = path.with_suffix(path.suffix + ".tmp_patch_apply")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def apply_with_transaction(proposal: PatchProposal) -> None:
    """
    PatchProposal için transactional apply:

    - Dosya bazlı lock alır.
    - APPLYING state'ine geçirir, apply_started_at ve lock_wait_time günceller.
    - Mevcut dosya içeriğinin fingerprint'ini tekrar kontrol eder:
      - Uyuşmazsa FAILED_CONFLICT state, conflict_detected=True.
    - Atomic write ile proposed_text'i yazar.
    - Başarıyla tamamlanırsa APPLIED state ve apply_finished_at güncellenir.
    - Hata durumunda FAILED state'e düşer.
    """
    target = proposal.target_path
    lock = _get_lock(target)

    # Registry kaydını garanti altına al
    rec = register_proposal(proposal)

    t0 = monotonic()
    lock.acquire()
    wait = monotonic() - t0

    try:
        # APPLYING state + metrikler
        current = get_record(proposal.id)
        if current is None:
            current = rec

        apply_started_at = _now()
        updated = replace(
            current,
            state="APPLYING",  # type: ignore[arg-type]
            updated_at=apply_started_at,
            apply_result={
                **(current.apply_result or {}),
                "apply_started_at": apply_started_at.isoformat(),
                "lock_wait_time": wait,
                "conflict_detected": False,
            },
        )
        from core.patch_registry import _REGISTRY  # type: ignore[attr-defined]

        _REGISTRY[proposal.id] = updated  # noqa: SLF001

        # Conflict kontrolü: mevcut içerik halen original_fingerprint ile uyumlu mu?
        current_text = target.read_text(encoding="utf-8") if target.is_file() else ""
        current_fp = PatchFingerprint.from_text(current_text)
        if current_fp.hex_digest != proposal.original_fingerprint.hex_digest:
            # Conflict: başka bir apply araya girmiş.
            conflict_result = {
                **(updated.apply_result or {}),
                "conflict_detected": True,
                "status": "error",
                "message": "fingerprint_conflict_during_apply",
            }
            conflict_rec = replace(
                updated,
                state="FAILED_CONFLICT",  # type: ignore[arg-type]
                updated_at=_now(),
                apply_result=conflict_result,
            )
            _REGISTRY[proposal.id] = conflict_rec  # noqa: SLF001
            record_guard_event(
                GuardEvent(
                    action="patch",
                    decision="deny",
                    path=target,
                    sandbox_mode=False,
                    reason="patch_apply_conflict_detected",
                    caller="core.patch_transaction.apply_with_transaction",
                ),
            )
            record_event(
                plan_id=None,
                patch_ids=[proposal.id],
                action_type="TRANSACTION_CONFLICT",
                result="error",
                affected_paths=[str(target)],
                sensitivity_levels=[],
                rollback_occurred=False,
                conflict_detected=True,
            )
            return

        # Atomic write
        _atomic_write(target, proposal.proposed_text)

        # Başarı: apply_finished_at
        finished = _now()
        success_result = {
            **(updated.apply_result or {}),
            "status": "applied",
            "apply_started_at": apply_started_at.isoformat(),
            "apply_finished_at": finished.isoformat(),
            "lock_wait_time": wait,
            "conflict_detected": False,
        }
        success_rec = replace(
            updated,
            state="APPLIED",  # type: ignore[arg-type]
            updated_at=finished,
            apply_result=success_result,
        )
        _REGISTRY[proposal.id] = success_rec  # noqa: SLF001
        record_guard_event(
            GuardEvent(
                action="patch",
                decision="allow",
                path=target,
                sandbox_mode=False,
                reason="patch_applied_transactional",
                caller="core.patch_transaction.apply_with_transaction",
            ),
        )
        record_event(
            plan_id=None,
            patch_ids=[proposal.id],
            action_type="PATCH_APPLIED",
            result="applied",
            affected_paths=[str(target)],
            sensitivity_levels=[],
            rollback_occurred=False,
            conflict_detected=False,
        )
    except Exception as exc:  # noqa: BLE001
        record_apply_error(proposal.id, f"transaction_apply_error:{type(exc).__name__}")
        record_event(
            plan_id=None,
            patch_ids=[proposal.id],
            action_type="PATCH_FAILED",
            result=f"transaction_apply_error:{type(exc).__name__}",
            affected_paths=[str(target)],
            sensitivity_levels=[],
            rollback_occurred=False,
            conflict_detected=False,
        )
        raise
    finally:
        lock.release()

