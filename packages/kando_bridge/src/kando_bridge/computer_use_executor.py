"""Fail-closed contract for the private Lumos Computer Use executor.

This OSS module deliberately performs no browser or OS automation. It defines the
boundary that a private executor must satisfy after Lumos policy and approval gates
have authorized an action.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

EXECUTOR_CONTRACT_VERSION = "lumos.computer_use_executor.v1"


@dataclass(frozen=True)
class ComputerUseAction:
    """One already-scoped action presented to a private executor."""

    action: str
    target: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    task_id: str = ""
    approval_id: str = ""


@dataclass(frozen=True)
class ComputerUseResult:
    """Evidence-oriented result returned by a private executor."""

    ok: bool
    status: str
    action: str
    target: str
    evidence: Mapping[str, Any] = field(default_factory=dict)
    error: str = ""
    contract_version: str = EXECUTOR_CONTRACT_VERSION


class ComputerUseExecutor(Protocol):
    """Private implementation boundary; implementations must not bypass Lumos gates."""

    def execute(self, action: ComputerUseAction) -> ComputerUseResult:
        """Execute one previously authorized action and return verifiable evidence."""
        ...


class DisabledComputerUseExecutor:
    """Default executor: fail closed until a private implementation is explicitly wired."""

    def execute(self, action: ComputerUseAction) -> ComputerUseResult:
        return ComputerUseResult(
            ok=False,
            status="disabled",
            action=action.action,
            target=action.target,
            error="computer_use_executor_not_configured",
            evidence={"real_execution": False},
        )


def executor_contract_payload() -> dict[str, Any]:
    """Public, secret-free description of the private executor boundary."""
    return {
        "contract_version": EXECUTOR_CONTRACT_VERSION,
        "default": "disabled",
        "real_execution": False,
        "requirements": [
            "lumos_policy_gate_passed",
            "task_scope_present",
            "explicit_approval_for_external_effects",
            "no_secret_exposure",
            "post_action_evidence",
            "fail_closed_on_uncertainty",
        ],
    }
