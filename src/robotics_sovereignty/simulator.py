"""Offline reference simulator for the Robotics Sovereignty Layer v0.1.

This module performs no network, firmware, sensor, or actuator I/O. It models
policy decisions and safe-state transitions so the normative contract can be
tested without claiming control of a real robot.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable


class RobotState(str, Enum):
    SAFE_STOPPED = "safe_stopped"
    READY = "ready"
    MOVING = "moving"
    EMERGENCY_STOPPED = "emergency_stopped"


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class Command:
    action: str
    source: str = "lumos_local"
    capability: str | None = None
    owner_signature_valid: bool = False
    explicit_owner_approval: bool = False
    destination: str | None = None


@dataclass(frozen=True)
class CommandResult:
    decision: Decision
    reason: str
    state: RobotState


@dataclass(frozen=True)
class AuditRecord:
    sequence: int
    event: str
    decision: str
    reason: str
    state: str
    previous_hash: str
    details: dict[str, Any]
    digest: str


@dataclass(frozen=True)
class SovereigntyPolicy:
    allowed_capabilities: frozenset[str]
    owner_allowlisted_destinations: frozenset[str] = frozenset()
    trusted_local_sources: frozenset[str] = frozenset(
        {"lumos_local", "local_owner"}
    )

    @classmethod
    def from_capabilities(
        cls,
        capabilities: Iterable[str],
        *,
        owner_allowlisted_destinations: Iterable[str] = (),
    ) -> SovereigntyPolicy:
        return cls(
            allowed_capabilities=frozenset(capabilities),
            owner_allowlisted_destinations=frozenset(
                owner_allowlisted_destinations
            ),
        )


class SovereigntySimulator:
    """Fail-closed state machine with a tamper-evident in-memory audit chain."""

    _ACTION_CAPABILITIES = {
        "move": "motion.move",
        "stop": "motion.stop",
        "read_camera": "sensor.camera.read",
        "read_microphone": "sensor.microphone.read",
        "read_location": "sensor.location.read",
        "export_sensor_data": "sensor.data.export",
        "install_firmware_update": "firmware.update",
    }

    def __init__(self, policy: SovereigntyPolicy) -> None:
        self.policy = policy
        self.state = RobotState.SAFE_STOPPED
        self.network_locked_down = True
        self._audit: list[AuditRecord] = []
        self._record(
            "boot",
            Decision.ALLOW,
            "offline_safe_default",
            {"network_locked_down": True},
        )

    @property
    def audit_records(self) -> tuple[AuditRecord, ...]:
        return tuple(self._audit)

    def activate_local_control(self, *, owner_signature_valid: bool) -> CommandResult:
        if not owner_signature_valid:
            return self._deny("activate", "invalid_local_owner_signature")
        if self.state == RobotState.EMERGENCY_STOPPED:
            return self._deny("activate", "physical_reset_required")
        self.state = RobotState.READY
        return self._allow("activate", "local_control_ready")

    def submit(self, command: Command) -> CommandResult:
        if self.state == RobotState.EMERGENCY_STOPPED:
            return self._deny(command.action, "physical_reset_required")
        if command.source not in self.policy.trusted_local_sources:
            return self._deny(command.action, "untrusted_or_remote_source")
        if command.action in {"vendor_kill_switch", "hidden_service_command"}:
            return self._deny(command.action, "manufacturer_control_forbidden")

        required = self._ACTION_CAPABILITIES.get(command.action)
        if required is None:
            return self._deny(command.action, "unknown_action_fail_closed")
        if command.capability != required:
            return self._deny(command.action, "capability_mismatch")
        if required not in self.policy.allowed_capabilities:
            return self._deny(command.action, "capability_not_granted")

        if command.action == "move":
            if self.state not in {RobotState.READY, RobotState.MOVING}:
                return self._deny(command.action, "local_control_not_ready")
            self.state = RobotState.MOVING
            return self._allow(command.action, "capability_granted")

        if command.action == "stop":
            self.state = RobotState.SAFE_STOPPED
            return self._allow(command.action, "safe_stop_applied")

        if command.action == "export_sensor_data":
            if not command.owner_signature_valid:
                return self._deny(command.action, "invalid_local_owner_signature")
            if not command.explicit_owner_approval:
                return self._deny(command.action, "explicit_owner_approval_required")
            if command.destination not in self.policy.owner_allowlisted_destinations:
                return self._deny(command.action, "destination_not_allowlisted")
            return self._allow(
                command.action,
                "owner_authorized_egress",
                {"destination": command.destination},
            )

        if command.action == "install_firmware_update":
            if not command.owner_signature_valid:
                return self._deny(command.action, "invalid_local_owner_signature")
            if not command.explicit_owner_approval:
                return self._deny(command.action, "explicit_owner_approval_required")
            if self.state == RobotState.MOVING:
                return self._deny(command.action, "update_forbidden_while_moving")
            return self._allow(command.action, "local_owner_update_authorized")

        return self._allow(command.action, "local_read_capability_granted")

    def lumos_heartbeat_lost(self) -> CommandResult:
        if self.state != RobotState.EMERGENCY_STOPPED:
            self.state = RobotState.SAFE_STOPPED
        return self._allow("lumos_heartbeat_lost", "safe_stop_applied")

    def enforce_network_lockdown(self) -> CommandResult:
        """Model cutting persistent outbound connections without doing I/O."""
        self.network_locked_down = True
        return self._allow(
            "network_lockdown",
            "persistent_outbound_connections_blocked",
            {"network_locked_down": True},
        )

    def physical_emergency_stop(self) -> CommandResult:
        self.state = RobotState.EMERGENCY_STOPPED
        return self._allow("physical_emergency_stop", "hardware_priority_stop")

    def verify_audit_chain(self) -> bool:
        previous_hash = "GENESIS"
        for record in self._audit:
            if record.previous_hash != previous_hash:
                return False
            payload = self._audit_payload(
                sequence=record.sequence,
                event=record.event,
                decision=record.decision,
                reason=record.reason,
                state=record.state,
                previous_hash=record.previous_hash,
                details=record.details,
            )
            if self._digest(payload) != record.digest:
                return False
            previous_hash = record.digest
        return True

    def _allow(
        self,
        event: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> CommandResult:
        self._record(event, Decision.ALLOW, reason, details or {})
        return CommandResult(Decision.ALLOW, reason, self.state)

    def _deny(self, event: str, reason: str) -> CommandResult:
        self._record(event, Decision.DENY, reason, {})
        return CommandResult(Decision.DENY, reason, self.state)

    def _record(
        self,
        event: str,
        decision: Decision,
        reason: str,
        details: dict[str, Any],
    ) -> None:
        previous_hash = self._audit[-1].digest if self._audit else "GENESIS"
        sequence = len(self._audit) + 1
        payload = self._audit_payload(
            sequence=sequence,
            event=event,
            decision=decision.value,
            reason=reason,
            state=self.state.value,
            previous_hash=previous_hash,
            details=details,
        )
        self._audit.append(
            AuditRecord(
                sequence=sequence,
                event=event,
                decision=decision.value,
                reason=reason,
                state=self.state.value,
                previous_hash=previous_hash,
                details=dict(details),
                digest=self._digest(payload),
            )
        )

    @staticmethod
    def _audit_payload(**values: Any) -> str:
        return json.dumps(
            values,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _digest(payload: str) -> str:
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
