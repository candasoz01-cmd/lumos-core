"""Contract-only user flow for Payment Approval Bridge v0.

The bridge maps explicit user-flow commands onto lifecycle transitions. It is
an in-memory reference contract: no persistence, network, provider, checkout,
or payment execution is present.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Final

from commerce.payment_approval_bridge.lifecycle import (
    InvalidLifecycleTransition,
    PAYMENT_EXECUTION_ENABLED,
    PaymentLifecycleSnapshot,
    PaymentLifecycleState,
    advance_lifecycle,
    require_aware_time,
)

USER_FLOW_SCHEMA_VERSION: Final = "lumos.payment_approval.user_flow.v0"
AUDIT_SCHEMA_VERSION: Final = "lumos.payment_approval.audit.v0"
APPROVAL_SCOPE: Final = "single_payment"


class UserFlowAction(str, Enum):
    REQUEST_APPROVAL = "request_approval"
    APPROVE = "approve"
    CANCEL = "cancel"
    TIMEOUT = "timeout"


class UserFlowContractError(ValueError):
    """Base error for a user-flow contract violation."""


class ExplicitApprovalRequired(UserFlowContractError):
    """Raised when approval is absent, implicit, delegated, or stale."""


class IntentMismatch(UserFlowContractError):
    """Raised when approval does not bind to the exact reviewed intent."""


class ApprovalExpired(UserFlowContractError):
    """Raised when an approval is attempted at or after its deadline."""


class IdempotencyConflict(UserFlowContractError):
    """Raised when one idempotency key is reused for a different command."""


@dataclass(frozen=True, slots=True)
class PaymentReview:
    request_id: str
    user_id: str
    amount_minor: int
    currency: str
    payee_reference: str
    purpose: str
    effect_summary: str
    intent_fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        request_id = self.request_id.strip()
        user_id = self.user_id.strip()
        currency = self.currency.strip().upper()
        payee_reference = self.payee_reference.strip()
        purpose = self.purpose.strip()
        effect_summary = self.effect_summary.strip()
        if not request_id or not user_id:
            raise UserFlowContractError("request_id and user_id are required")
        if self.amount_minor <= 0:
            raise UserFlowContractError("amount_minor must be positive")
        if len(currency) != 3 or not currency.isalpha():
            raise UserFlowContractError("currency must be a three-letter code")
        if not payee_reference or not purpose or not effect_summary:
            raise UserFlowContractError(
                "payee_reference, purpose, and effect_summary are required"
            )
        object.__setattr__(self, "request_id", request_id)
        object.__setattr__(self, "user_id", user_id)
        object.__setattr__(self, "currency", currency)
        object.__setattr__(self, "payee_reference", payee_reference)
        object.__setattr__(self, "purpose", purpose)
        object.__setattr__(self, "effect_summary", effect_summary)
        payload = {
            "amount_minor": self.amount_minor,
            "currency": currency,
            "effect_summary": effect_summary,
            "payee_reference": payee_reference,
            "purpose": purpose,
            "request_id": request_id,
            "user_id": user_id,
        }
        object.__setattr__(self, "intent_fingerprint", _digest(payload))


@dataclass(frozen=True, slots=True)
class UserApproval:
    approval_id: str
    request_id: str
    user_id: str
    intent_fingerprint: str
    approved_at: datetime
    approved: bool
    scope: str = APPROVAL_SCOPE

    def __post_init__(self) -> None:
        require_aware_time(self.approved_at, "approved_at")


@dataclass(frozen=True, slots=True)
class UserFlowCommand:
    action: UserFlowAction
    idempotency_key: str
    actor_kind: str
    actor_id: str
    occurred_at: datetime
    approval_expires_at: datetime | None = None
    approval: UserApproval | None = None
    schema_version: str = USER_FLOW_SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_aware_time(self.occurred_at, "occurred_at")
        if self.approval_expires_at is not None:
            require_aware_time(self.approval_expires_at, "approval_expires_at")
        if len(self.idempotency_key.strip()) < 8:
            raise UserFlowContractError("idempotency_key must contain at least 8 characters")
        if not self.actor_kind.strip() or not self.actor_id.strip():
            raise UserFlowContractError("actor_kind and actor_id are required")


@dataclass(frozen=True, slots=True)
class PaymentAuditEvent:
    event_id: str
    event_type: str
    request_id: str
    from_state: PaymentLifecycleState
    to_state: PaymentLifecycleState
    occurred_at: datetime
    actor_kind: str
    actor_id: str
    intent_fingerprint: str
    idempotency_key_digest: str
    approval_id: str | None = None
    provider_execution: bool = PAYMENT_EXECUTION_ENABLED
    schema_version: str = AUDIT_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class UserFlowResult:
    snapshot: PaymentLifecycleSnapshot
    audit_events: tuple[PaymentAuditEvent, ...]
    replayed: bool = False
    provider_execution: bool = PAYMENT_EXECUTION_ENABLED


@dataclass(frozen=True, slots=True)
class _IdempotencyRecord:
    command_digest: str
    snapshot: PaymentLifecycleSnapshot


class PaymentApprovalBridge:
    """In-memory reference bridge between user_flow and lifecycle contracts."""

    def __init__(self, review: PaymentReview, *, created_at: datetime) -> None:
        require_aware_time(created_at, "created_at")
        self.review = review
        self.snapshot = PaymentLifecycleSnapshot(
            request_id=review.request_id,
            state=PaymentLifecycleState.REVIEW,
            revision=0,
            updated_at=created_at,
        )
        self._approval_deadline: datetime | None = None
        self._audit_events: tuple[PaymentAuditEvent, ...] = ()
        self._idempotency: dict[str, _IdempotencyRecord] = {}

    @property
    def approval_deadline(self) -> datetime | None:
        return self._approval_deadline

    @property
    def audit_events(self) -> tuple[PaymentAuditEvent, ...]:
        return self._audit_events

    def apply(self, command: UserFlowCommand) -> UserFlowResult:
        command_digest = _command_digest(command)
        idempotency_key = command.idempotency_key.strip()
        existing = self._idempotency.get(idempotency_key)
        if existing is not None:
            if existing.command_digest != command_digest:
                raise IdempotencyConflict(
                    "idempotency key cannot be reused for a different command"
                )
            return UserFlowResult(
                snapshot=existing.snapshot,
                audit_events=(),
                replayed=True,
            )

        if command.action is UserFlowAction.REQUEST_APPROVAL:
            result = self._request_approval(command)
        elif command.action is UserFlowAction.APPROVE:
            result = self._approve(command)
        elif command.action is UserFlowAction.CANCEL:
            result = self._cancel(command)
        elif command.action is UserFlowAction.TIMEOUT:
            result = self._timeout(command)
        else:  # pragma: no cover - Enum keeps this defensive branch unreachable.
            raise UserFlowContractError(f"unknown user-flow action: {command.action}")

        self._idempotency[idempotency_key] = _IdempotencyRecord(
            command_digest=command_digest,
            snapshot=result.snapshot,
        )
        return result

    def _request_approval(self, command: UserFlowCommand) -> UserFlowResult:
        if command.approval is not None:
            raise UserFlowContractError("request_approval cannot carry approval evidence")
        deadline = command.approval_expires_at
        if deadline is None or deadline <= command.occurred_at:
            raise UserFlowContractError("approval deadline must be in the future")
        previous = self.snapshot
        self.snapshot = advance_lifecycle(
            previous,
            PaymentLifecycleState.AWAITING_APPROVAL,
            occurred_at=command.occurred_at,
        )
        self._approval_deadline = deadline
        return self._record(
            command,
            previous,
            (("approval_requested", None),),
        )

    def _approve(self, command: UserFlowCommand) -> UserFlowResult:
        if self.snapshot.state is not PaymentLifecycleState.AWAITING_APPROVAL:
            raise InvalidLifecycleTransition(
                f"{self.snapshot.state.value} -> "
                f"{PaymentLifecycleState.PAYMENT_INITIATED.value} is not allowed"
            )
        deadline = self._approval_deadline
        if deadline is None:
            raise ExplicitApprovalRequired("approval was not requested")
        if command.occurred_at >= deadline:
            raise ApprovalExpired("approval deadline has passed")
        approval = command.approval
        if approval is None or approval.approved is not True:
            raise ExplicitApprovalRequired("explicit user approval is required")
        if command.actor_kind != "user":
            raise ExplicitApprovalRequired("approval actor must be the user")
        if command.actor_id != self.review.user_id or approval.user_id != self.review.user_id:
            raise ExplicitApprovalRequired("approval must come from the reviewed user")
        if approval.scope != APPROVAL_SCOPE:
            raise ExplicitApprovalRequired("approval scope must be single_payment")
        if not approval.approval_id.strip():
            raise ExplicitApprovalRequired("approval_id is required")
        if approval.request_id != self.review.request_id:
            raise IntentMismatch("approval request_id does not match the review")
        if approval.intent_fingerprint != self.review.intent_fingerprint:
            raise IntentMismatch("approval intent fingerprint does not match the review")
        if approval.approved_at < self.snapshot.updated_at:
            raise ExplicitApprovalRequired("approval predates the approval request")
        if approval.approved_at > command.occurred_at:
            raise ExplicitApprovalRequired("approval timestamp cannot be in the future")

        previous = self.snapshot
        self.snapshot = advance_lifecycle(
            previous,
            PaymentLifecycleState.PAYMENT_INITIATED,
            occurred_at=command.occurred_at,
        )
        return self._record(
            command,
            previous,
            (
                ("user_approval_recorded", approval.approval_id),
                ("payment_initiated", approval.approval_id),
            ),
        )

    def _cancel(self, command: UserFlowCommand) -> UserFlowResult:
        if command.approval is not None or command.approval_expires_at is not None:
            raise UserFlowContractError("cancel cannot carry approval data")
        if command.actor_kind != "user" or command.actor_id != self.review.user_id:
            raise ExplicitApprovalRequired("only the reviewed user can cancel")
        previous = self.snapshot
        self.snapshot = advance_lifecycle(
            previous,
            PaymentLifecycleState.CANCELLED,
            occurred_at=command.occurred_at,
        )
        return self._record(
            command,
            previous,
            (("payment_cancelled", None),),
        )

    def _timeout(self, command: UserFlowCommand) -> UserFlowResult:
        if command.approval is not None or command.approval_expires_at is not None:
            raise UserFlowContractError("timeout cannot carry approval data")
        if command.actor_kind != "system":
            raise UserFlowContractError("timeout actor must be system")
        deadline = self._approval_deadline
        if deadline is None or command.occurred_at < deadline:
            raise UserFlowContractError("approval cannot time out before its deadline")
        previous = self.snapshot
        self.snapshot = advance_lifecycle(
            previous,
            PaymentLifecycleState.TIMED_OUT,
            occurred_at=command.occurred_at,
        )
        return self._record(
            command,
            previous,
            (("approval_timed_out", None),),
        )

    def _record(
        self,
        command: UserFlowCommand,
        previous: PaymentLifecycleSnapshot,
        event_specs: tuple[tuple[str, str | None], ...],
    ) -> UserFlowResult:
        key_digest = hashlib.sha256(command.idempotency_key.strip().encode()).hexdigest()
        new_events = tuple(
            PaymentAuditEvent(
                event_id=f"{self.review.request_id}:{len(self._audit_events) + index + 1}",
                event_type=event_type,
                request_id=self.review.request_id,
                from_state=previous.state,
                to_state=self.snapshot.state,
                occurred_at=command.occurred_at,
                actor_kind=command.actor_kind,
                actor_id=command.actor_id,
                intent_fingerprint=self.review.intent_fingerprint,
                idempotency_key_digest=key_digest,
                approval_id=approval_id,
            )
            for index, (event_type, approval_id) in enumerate(event_specs)
        )
        self._audit_events += new_events
        return UserFlowResult(snapshot=self.snapshot, audit_events=new_events)


def _digest(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()


def _command_digest(command: UserFlowCommand) -> str:
    approval = command.approval
    payload: dict[str, object] = {
        "action": command.action.value,
        "actor_id": command.actor_id,
        "actor_kind": command.actor_kind,
        "approval": None,
        "approval_expires_at": _iso(command.approval_expires_at),
        "occurred_at": _iso(command.occurred_at),
        "schema_version": command.schema_version,
    }
    if approval is not None:
        payload["approval"] = {
            "approval_id": approval.approval_id,
            "approved": approval.approved,
            "approved_at": _iso(approval.approved_at),
            "intent_fingerprint": approval.intent_fingerprint,
            "request_id": approval.request_id,
            "scope": approval.scope,
            "user_id": approval.user_id,
        }
    return _digest(payload)
