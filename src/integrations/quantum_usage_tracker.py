"""Quantum layer usage tracker — delegates to shared resource_mode_advisor."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from integrations.resource_mode_advisor import (
    CONNECTS_PER_DAY_ACTIVE,
    EVENTS_PER_WEEK_ACTIVE,
    LOOKBACK_DAYS,
    ResourceLayer,
    apply_mode_change,
    propose_mode_change,
    recommend_mode,
    record_event,
)

QuantumUsageAction = Literal["list_catalog", "connect", "disconnect", "job"]
QuantumUsageMode = Literal["active", "passive", "insufficient_data"]

_QUANTUM = ResourceLayer.QUANTUM

# Re-export thresholds for tests and docs.
__all__ = [
    "CONNECTS_PER_DAY_ACTIVE",
    "EVENTS_PER_WEEK_ACTIVE",
    "LOOKBACK_DAYS",
    "QuantumUsageAction",
    "QuantumUsageMode",
    "record_quantum_usage",
    "recommend_usage_mode",
    "propose_quantum_mode_change",
    "apply_quantum_mode_change",
]


def record_quantum_usage(
    action: QuantumUsageAction,
    *,
    provider_id: str = "",
    base_dir: Path | None = None,
) -> None:
    metadata: dict[str, str] = {}
    if provider_id:
        metadata["provider_id"] = provider_id.strip().lower()
    record_event(_QUANTUM, action, metadata or None, base_dir=base_dir)


def recommend_usage_mode(
    *,
    base_dir: Path | None = None,
    lookback_days: int = LOOKBACK_DAYS,
) -> dict[str, Any]:
    rec = recommend_mode(_QUANTUM, base_dir=base_dir, lookback_days=lookback_days)
    return {
        "recommended_mode": rec["recommended_mode"],
        "default_mode": rec["default_mode"],
        "reason": rec["reason"],
        "connects_last_24h": rec["stats"]["connects_last_24h"],
        "events_last_7d": rec["stats"]["events_last_7d"],
        "idle_days": rec["stats"]["idle_days"],
        "thresholds": rec["thresholds"],
    }


def propose_quantum_mode_change(*, base_dir: Path | None = None) -> dict[str, Any]:
    return propose_mode_change(_QUANTUM, base_dir=base_dir)


def apply_quantum_mode_change(
    mode: QuantumUsageMode,
    *,
    user_approved: bool = True,
    base_dir: Path | None = None,
):
    return apply_mode_change(
        _QUANTUM,
        mode,
        user_approved=user_approved,
        base_dir=base_dir,
    )
