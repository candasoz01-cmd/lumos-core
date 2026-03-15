"""
Verification result: whether the intended outcome of a step can be considered verified.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of verifying an executor result. Safe, non-destructive."""
    verified: bool
    reason: str
    details: str = ""
