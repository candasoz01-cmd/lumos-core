"""Payment Approval Bridge v0 contract tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from commerce.payment_approval_bridge import (
    PAYMENT_EXECUTION_ENABLED,
    ApprovalExpired,
    ExplicitApprovalRequired,
    IdempotencyConflict,
    IntentMismatch,
    InvalidLifecycleTransition,
    PaymentApprovalBridge,
    PaymentLifecycleState,
    PaymentReview,
    UserApproval,
    UserFlowAction,
    UserFlowCommand,
)
from commerce.payment_approval_bridge.lifecycle import advance_lifecycle

NOW = datetime(2026, 7, 29, 10, 0, tzinfo=timezone.utc)
DEADLINE = NOW + timedelta(minutes=5)


def _review() -> PaymentReview:
    return PaymentReview(
        request_id="pay_req_001",
        user_id="user_001",
        amount_minor=1250,
        currency="eur",
        payee_reference="merchant_public_ref",
        purpose="One-time purchase",
        effect_summary="Initiate a single EUR 12.50 payment intent",
    )


def _request_command() -> UserFlowCommand:
    return UserFlowCommand(
        action=UserFlowAction.REQUEST_APPROVAL,
        idempotency_key="request-approval-001",
        actor_kind="system",
        actor_id="lumos_user_flow",
        occurred_at=NOW + timedelta(seconds=1),
        approval_expires_at=DEADLINE,
    )


def _approval(review: PaymentReview, **changes: object) -> UserApproval:
    approval = UserApproval(
        approval_id="approval_001",
        request_id=review.request_id,
        user_id=review.user_id,
        intent_fingerprint=review.intent_fingerprint,
        approved_at=NOW + timedelta(seconds=2),
        approved=True,
    )
    return replace(approval, **changes)


def _approve_command(review: PaymentReview, **changes: object) -> UserFlowCommand:
    command = UserFlowCommand(
        action=UserFlowAction.APPROVE,
        idempotency_key="approve-payment-001",
        actor_kind="user",
        actor_id=review.user_id,
        occurred_at=NOW + timedelta(seconds=3),
        approval=_approval(review),
    )
    return replace(command, **changes)


def _awaiting_bridge() -> tuple[PaymentApprovalBridge, PaymentReview]:
    review = _review()
    bridge = PaymentApprovalBridge(review, created_at=NOW)
    bridge.apply(_request_command())
    return bridge, review


def test_lifecycle_forbids_direct_review_to_payment_initiated() -> None:
    bridge = PaymentApprovalBridge(_review(), created_at=NOW)

    with pytest.raises(InvalidLifecycleTransition):
        advance_lifecycle(
            bridge.snapshot,
            PaymentLifecycleState.PAYMENT_INITIATED,
            occurred_at=NOW + timedelta(seconds=1),
        )


def test_review_to_awaiting_approval_records_deadline_and_audit() -> None:
    bridge = PaymentApprovalBridge(_review(), created_at=NOW)

    result = bridge.apply(_request_command())

    assert result.snapshot.state is PaymentLifecycleState.AWAITING_APPROVAL
    assert bridge.approval_deadline == DEADLINE
    assert [event.event_type for event in result.audit_events] == ["approval_requested"]
    assert result.provider_execution is False
    assert PAYMENT_EXECUTION_ENABLED is False


def test_explicit_matching_user_approval_reaches_payment_initiated() -> None:
    bridge, review = _awaiting_bridge()

    result = bridge.apply(_approve_command(review))

    assert result.snapshot.state is PaymentLifecycleState.PAYMENT_INITIATED
    assert [event.event_type for event in result.audit_events] == [
        "user_approval_recorded",
        "payment_initiated",
    ]
    assert all(event.provider_execution is False for event in result.audit_events)


@pytest.mark.parametrize(
    ("command_change", "approval_change"),
    [
        ({}, {"approved": False}),
        ({"actor_kind": "agent"}, {}),
        ({"actor_id": "different-user"}, {}),
        ({}, {"user_id": "different-user"}),
        ({}, {"scope": "session"}),
    ],
)
def test_implicit_delegated_or_reused_approval_is_rejected(
    command_change: dict[str, object],
    approval_change: dict[str, object],
) -> None:
    bridge, review = _awaiting_bridge()
    approval = _approval(review, **approval_change)
    command = _approve_command(review, approval=approval, **command_change)

    with pytest.raises(ExplicitApprovalRequired):
        bridge.apply(command)

    assert bridge.snapshot.state is PaymentLifecycleState.AWAITING_APPROVAL


def test_approval_must_bind_to_exact_reviewed_intent() -> None:
    bridge, review = _awaiting_bridge()
    changed = _approval(review, intent_fingerprint="different-fingerprint")

    with pytest.raises(IntentMismatch):
        bridge.apply(_approve_command(review, approval=changed))

    assert bridge.snapshot.state is PaymentLifecycleState.AWAITING_APPROVAL


def test_same_idempotency_key_and_command_replays_without_duplicate_audit() -> None:
    bridge = PaymentApprovalBridge(_review(), created_at=NOW)
    command = _request_command()

    first = bridge.apply(command)
    replay = bridge.apply(command)

    assert replay.replayed is True
    assert replay.snapshot == first.snapshot
    assert replay.audit_events == ()
    assert len(bridge.audit_events) == 1


def test_idempotency_key_reuse_with_different_payload_is_rejected() -> None:
    bridge = PaymentApprovalBridge(_review(), created_at=NOW)
    command = _request_command()
    bridge.apply(command)
    changed = replace(command, approval_expires_at=DEADLINE + timedelta(minutes=1))

    with pytest.raises(IdempotencyConflict):
        bridge.apply(changed)


@pytest.mark.parametrize("start_with_approval_request", [False, True])
def test_user_can_cancel_only_before_payment_initiated(
    start_with_approval_request: bool,
) -> None:
    review = _review()
    bridge = PaymentApprovalBridge(review, created_at=NOW)
    if start_with_approval_request:
        bridge.apply(_request_command())
    command = UserFlowCommand(
        action=UserFlowAction.CANCEL,
        idempotency_key=f"cancel-payment-{start_with_approval_request}",
        actor_kind="user",
        actor_id=review.user_id,
        occurred_at=NOW + timedelta(seconds=4),
    )

    result = bridge.apply(command)

    assert result.snapshot.state is PaymentLifecycleState.CANCELLED
    assert result.audit_events[0].event_type == "payment_cancelled"
    with pytest.raises(InvalidLifecycleTransition):
        bridge.apply(replace(command, idempotency_key="cancel-again-001"))


def test_timeout_is_not_early_and_blocks_late_approval() -> None:
    bridge, review = _awaiting_bridge()
    early = UserFlowCommand(
        action=UserFlowAction.TIMEOUT,
        idempotency_key="timeout-early-001",
        actor_kind="system",
        actor_id="lumos_user_flow",
        occurred_at=DEADLINE - timedelta(microseconds=1),
    )
    with pytest.raises(ValueError):
        bridge.apply(early)

    late_approval = replace(_approve_command(review), occurred_at=DEADLINE)
    with pytest.raises(ApprovalExpired):
        bridge.apply(late_approval)

    timeout = replace(
        early,
        idempotency_key="timeout-final-001",
        occurred_at=DEADLINE,
    )
    result = bridge.apply(timeout)

    assert result.snapshot.state is PaymentLifecycleState.TIMED_OUT
    assert result.audit_events[0].event_type == "approval_timed_out"
    with pytest.raises(InvalidLifecycleTransition):
        bridge.apply(
            replace(
                _approve_command(review),
                idempotency_key="approve-after-timeout",
                occurred_at=DEADLINE + timedelta(seconds=1),
                approval=replace(
                    _approval(review),
                    approved_at=DEADLINE + timedelta(seconds=1),
                ),
            )
        )


def test_user_cannot_cancel_after_payment_initiated() -> None:
    bridge, review = _awaiting_bridge()
    bridge.apply(_approve_command(review))
    cancel = UserFlowCommand(
        action=UserFlowAction.CANCEL,
        idempotency_key="cancel-after-initiation",
        actor_kind="user",
        actor_id=review.user_id,
        occurred_at=NOW + timedelta(seconds=4),
    )

    with pytest.raises(InvalidLifecycleTransition):
        bridge.apply(cancel)


def test_audit_uses_digests_and_contains_no_raw_idempotency_or_payment_details() -> None:
    bridge = PaymentApprovalBridge(_review(), created_at=NOW)
    command = _request_command()

    bridge.apply(command)
    serialized = repr(bridge.audit_events)

    assert command.idempotency_key not in serialized
    assert "merchant_public_ref" not in serialized
    assert "1250" not in serialized
    assert len(bridge.audit_events[0].idempotency_key_digest) == 64


def test_contract_has_no_network_or_payment_provider_execution() -> None:
    package = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "commerce"
        / "payment_approval_bridge"
    )
    source = "\n".join(path.read_text(encoding="utf-8") for path in package.glob("*.py"))

    for forbidden in (
        "import requests",
        "import httpx",
        "urllib.request",
        "urlopen(",
        "stripe",
        "paypal",
    ):
        assert forbidden not in source.lower()
