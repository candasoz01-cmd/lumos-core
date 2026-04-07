"""
Default verifiers per step.kind. Safe, non-destructive.
Verifiers decide whether executor result can be considered verified.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from task_engine.action_registry import ExecutionContext
from task_engine.verification.results import VerificationResult

if TYPE_CHECKING:
    from task_engine.engine import TaskRecord, TaskStep


def read_verifier(
    step: "TaskStep",
    task: "TaskRecord",
    context: ExecutionContext,
    ok: bool,
    output: str,
    error: str,
    verified_from_executor: bool,
) -> VerificationResult:
    """verified=True only if disk read succeeded, executor onayladı ve stdout boş değil."""
    if not ok or error:
        return VerificationResult(
            verified=False,
            reason="read_failed",
            details=error or "Okuma tamamlanamadı.",
        )
    out = (output or "").strip()
    if not out:
        return VerificationResult(
            verified=False,
            reason="no_data",
            details="Okuma çıktısı boş; başarılı sayılmaz.",
        )
    if verified_from_executor:
        return VerificationResult(
            verified=True,
            reason="data_read",
            details=out,
        )
    return VerificationResult(
        verified=False,
        reason="no_data",
        details=out or "Okuma doğrulanamadı.",
    )


def analyze_verifier(
    step: "TaskStep",
    task: "TaskRecord",
    context: ExecutionContext,
    ok: bool,
    output: str,
    error: str,
    verified_from_executor: bool,
) -> VerificationResult:
    """Usually verified=False unless explicit proof input existed and analysis ran on it."""
    if not ok or error:
        return VerificationResult(
            verified=False,
            reason="analyze_failed",
            details=error or "Analiz tamamlanamadı.",
        )
    # No explicit proof of input + analysis in current safe implementation
    return VerificationResult(
        verified=False,
        reason="simulation",
        details="Analiz simülasyonu; doğrulama yapılmadı.",
    )


def plan_verifier(
    step: "TaskStep",
    task: "TaskRecord",
    context: ExecutionContext,
    ok: bool,
    output: str,
    error: str,
    verified_from_executor: bool,
) -> VerificationResult:
    """verified=False by default; treated as simulation unless explicit verification possible."""
    if not ok or error:
        return VerificationResult(
            verified=False,
            reason="plan_failed",
            details=error or "Planlama tamamlanamadı.",
        )
    return VerificationResult(
        verified=False,
        reason="simulation",
        details="Plan simülasyonu; doğrulama yapılmadı.",
    )


def safe_local_verifier(
    step: "TaskStep",
    task: "TaskRecord",
    context: ExecutionContext,
    ok: bool,
    output: str,
    error: str,
    verified_from_executor: bool,
) -> VerificationResult:
    """
    patch_apply_executor tek dosya başarısında verified_from_executor=True döner (apply+verify bitti).
    Çok dosya pending çıktısı False döner — onay beklenir, burada doğrulanmış sayılmaz.
    """
    if not ok or error:
        return VerificationResult(
            verified=False,
            reason="safe_local_failed",
            details=error or "Yerel işlem tamamlanamadı.",
        )
    out = output or ""
    if "patch_pending_approval" in out or "patch_multi_pending" in out:
        return VerificationResult(
            verified=False,
            reason="patch_pending_approval",
            details="Çok dosya / onay bekleniyor; henüz uygulanmış sayılmaz.",
        )
    if verified_from_executor:
        return VerificationResult(
            verified=True,
            reason="patch_applied_verified",
            details=out[:2000] or "Patch uygulandı ve doğrulandı.",
        )
    if "tamamlandı" in out.lower():
        return VerificationResult(
            verified=True,
            reason="local_confirmed",
            details=out or "Güvenli yerel iş doğrulandı.",
        )
    return VerificationResult(
        verified=False,
        reason="simulation",
        details=out or "Yerel iş çıktısı doğrulanamadı.",
    )


def default_verifier(
    step: "TaskStep",
    task: "TaskRecord",
    context: ExecutionContext,
    ok: bool,
    output: str,
    error: str,
    verified_from_executor: bool,
) -> VerificationResult:
    """Default: treat as simulation (verified=False) when no kind-specific verifier applies."""
    if not ok or error:
        return VerificationResult(
            verified=False,
            reason="failed",
            details=error or "Adım tamamlanamadı.",
        )
    return VerificationResult(
        verified=False,
        reason="simulation",
        details="Varsayılan simülasyon; doğrulama yapılmadı.",
    )
