"""
Verification layer: verifiers decide whether executor result can be considered verified.
"""
from task_engine.verification.engine import VerificationEngine, Verifier
from task_engine.verification.results import VerificationResult
from task_engine.verification.default_verifiers import (
    analyze_verifier,
    default_verifier,
    plan_verifier,
    read_verifier,
    safe_local_verifier,
)

__all__ = [
    "VerificationEngine",
    "Verifier",
    "VerificationResult",
    "analyze_verifier",
    "default_verifier",
    "plan_verifier",
    "read_verifier",
    "safe_local_verifier",
]


def get_default_verification_engine() -> VerificationEngine:
    """Build verification engine with default verifiers per step.kind."""
    from task_engine.profiles import (
        STEP_TYPE_ANALYZE,
        STEP_TYPE_PLAN,
        STEP_TYPE_READ,
        STEP_TYPE_SAFE_LOCAL,
        STEP_TYPE_WRITE_LOCAL,
    )
    eng = VerificationEngine(default_verifier=default_verifier)
    eng.register(STEP_TYPE_READ, read_verifier)
    eng.register(STEP_TYPE_ANALYZE, analyze_verifier)
    eng.register(STEP_TYPE_PLAN, plan_verifier)
    eng.register(STEP_TYPE_SAFE_LOCAL, safe_local_verifier)
    eng.register(STEP_TYPE_WRITE_LOCAL, safe_local_verifier)
    return eng
