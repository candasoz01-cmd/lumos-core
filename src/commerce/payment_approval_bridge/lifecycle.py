"""Payment Approval Bridge v0 lifecycle contract.

``payment_initiated`` means only that the contract accepted one explicitly
approved payment intent. This module has no executor and cannot call a payment
provider or move money.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Final

LIFECYCLE_SCHEMA_VERSION: Final = "lumos.payment_approval.lifecycle.v0"
PAYMENT_EXECUTION_ENABLED: Final = False


class PaymentLifecycleState(str, Enum):
    REVIEW = "review"
    AWAITING_APPROVAL = "awaiting_approval"
    PAYMENT_INITIATED = "payment_initiated"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


TERMINAL_STATES: Final = frozenset(
    {
        PaymentLifecycleState.PAYMENT_INITIATED,
        PaymentLifecycleState.CANCELLED,
        PaymentLifecycleState.TIMED_OUT,
    }
)

ALLOWED_TRANSITIONS: Final = {
    PaymentLifecycleState.REVIEW: frozenset(
        {
            PaymentLifecycleState.AWAITING_APPROVAL,
            PaymentLifecycleState.CANCELLED,
        }
    ),
    PaymentLifecycleState.AWAITING_APPROVAL: frozenset(
        {
            PaymentLifecycleState.PAYMENT_INITIATED,
            PaymentLifecycleState.CANCELLED,
            PaymentLifecycleState.TIMED_OUT,
        }
    ),
    PaymentLifecycleState.PAYMENT_INITIATED: frozenset(),
    PaymentLifecycleState.CANCELLED: frozenset(),
    PaymentLifecycleState.TIMED_OUT: frozenset(),
}


class LifecycleContractError(ValueError):
    """Base error for a lifecycle contract violation."""


class InvalidLifecycleTransition(LifecycleContractError):
    """Raised when a state change is outside the v0 transition table."""


def require_aware_time(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise LifecycleContractError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class PaymentLifecycleSnapshot:
    request_id: str
    state: PaymentLifecycleState
    revision: int
    updated_at: datetime
    schema_version: str = LIFECYCLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise LifecycleContractError("request_id is required")
        if self.revision < 0:
            raise LifecycleContractError("revision cannot be negative")
        require_aware_time(self.updated_at, "updated_at")


def advance_lifecycle(
    snapshot: PaymentLifecycleSnapshot,
    target: PaymentLifecycleState,
    *,
    occurred_at: datetime,
) -> PaymentLifecycleSnapshot:
    """Return the next immutable lifecycle snapshot after contract validation."""

    require_aware_time(occurred_at, "occurred_at")
    if occurred_at < snapshot.updated_at:
        raise LifecycleContractError("occurred_at cannot precede the current snapshot")
    if target not in ALLOWED_TRANSITIONS[snapshot.state]:
        raise InvalidLifecycleTransition(f"{snapshot.state.value} -> {target.value} is not allowed")
    return replace(
        snapshot,
        state=target,
        revision=snapshot.revision + 1,
        updated_at=occurred_at,
    )
