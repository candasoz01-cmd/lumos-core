"""Demo-safe Computer Use action/result contract.

The only public executor is disabled. Importing or calling it does not start a
browser, network client, subprocess, or OS action, and it does not load a
private runtime or adapter. Production Computer Use remains OD-012
implementation-pending. Unexecuted work is never completed, real, or success.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Protocol

EXECUTOR_CONTRACT_VERSION = "lumos.computer_use_executor.v1"

STATUS_DISABLED = "disabled"
STATUS_REJECTED = "rejected"
RESULT_KIND_UNEXECUTED = "unexecuted"
ERROR_DISABLED = "computer_use_disabled"
ERROR_REJECTED = "computer_use_rejected"
CATEGORY_UNKNOWN = "unknown"

_FORBIDDEN_OUTCOMES = frozenset({
    "completed",
    "real",
    "success",
    "tamamlandi",
})
_ALLOWED_STATUS = frozenset({STATUS_DISABLED, STATUS_REJECTED})
_ALLOWED_ERRORS = frozenset({ERROR_DISABLED, ERROR_REJECTED})


class ComputerUseCategory(str, Enum):
    """Closed set of action categories. None of them run in this module."""

    READ = "read"
    OBSERVE = "observe"
    SUGGEST = "suggest"
    CLICK = "click"
    NAVIGATE = "navigate"
    TYPE = "type"
    EXTERNAL_WRITE = "external_write"
    SEND = "send"
    EMAIL = "email"
    FILE_SEND = "file_send"
    DELETE = "delete"
    PAYMENT = "payment"
    DOMAIN = "domain"


RECOGNIZED_ACTION_CATEGORIES: tuple[str, ...] = tuple(
    category.value for category in ComputerUseCategory
)
_RECOGNIZED = frozenset(RECOGNIZED_ACTION_CATEGORIES)


def _require_str(value: object, message: str) -> str:
    if not isinstance(value, str):
        raise TypeError(message)
    return value


@dataclass(frozen=True, slots=True, repr=False)
class ComputerUseAction:
    """Immutable request. Arguments stay on the request and are not executed."""

    category: ComputerUseCategory
    target: str = ""
    arguments: Mapping[str, Any] = field(default_factory=dict)
    task_id: str = ""
    approval_id: str = ""

    def __post_init__(self) -> None:
        category = self.category
        if isinstance(category, ComputerUseCategory):
            normalized = category
        elif isinstance(category, str) and category in _RECOGNIZED:
            normalized = ComputerUseCategory(category)
        elif isinstance(category, str):
            raise ValueError("unknown computer-use category")
        else:
            raise TypeError("category must be a recognized computer-use category")
        target = _require_str(self.target, "target must be a string")
        task_id = _require_str(self.task_id, "task_id must be a string")
        approval_id = _require_str(self.approval_id, "approval_id must be a string")
        arguments = self.arguments
        if isinstance(arguments, (str, bytes)) or not isinstance(arguments, Mapping):
            raise TypeError("arguments must be a mapping")
        try:
            copied = dict(arguments)
        except Exception:
            raise TypeError("arguments must be a mapping") from None
        frozen_arguments = MappingProxyType(copied)
        object.__setattr__(self, "category", normalized)
        object.__setattr__(self, "target", target)
        object.__setattr__(self, "task_id", task_id)
        object.__setattr__(self, "approval_id", approval_id)
        object.__setattr__(self, "arguments", frozen_arguments)

    def __repr__(self) -> str:
        category = self.category.value
        return (
            "ComputerUseAction("
            f"category={category!r}, "
            "target=<redacted>, "
            "arguments=<redacted>, "
            "task_id=<redacted>, "
            "approval_id=<redacted>)"
        )


@dataclass(frozen=True, slots=True)
class ComputerUseResult:
    """Unexecuted public result. Success-shaped values are rejected."""

    ok: bool
    status: str
    result_kind: str
    category: str
    error: str
    completed: bool = False
    real: bool = False
    success: bool = False
    real_execution: bool = False
    contract_version: str = EXECUTOR_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.ok is not False:
            raise ValueError("unexecuted computer-use result cannot succeed")
        if self.status not in _ALLOWED_STATUS or self.status in _FORBIDDEN_OUTCOMES:
            raise ValueError("computer-use status must be disabled or rejected")
        if (
            self.result_kind != RESULT_KIND_UNEXECUTED
            or self.result_kind in _FORBIDDEN_OUTCOMES
        ):
            raise ValueError("computer-use result_kind must be unexecuted")
        if self.category != CATEGORY_UNKNOWN and self.category not in _RECOGNIZED:
            raise ValueError("computer-use category must be recognized or unknown")
        if self.error not in _ALLOWED_ERRORS:
            raise ValueError("computer-use error must be a fixed code")
        if (
            self.completed is not False
            or self.real is not False
            or self.success is not False
            or self.real_execution is not False
        ):
            raise ValueError("unexecuted computer-use result cannot be completed or real")
        if self.contract_version != EXECUTOR_CONTRACT_VERSION:
            raise ValueError("unexpected computer-use contract version")

    def public_dict(self) -> dict[str, Any]:
        """Secret-free view. Request payloads are intentionally absent."""

        return {
            "ok": False,
            "status": self.status,
            "result_kind": self.result_kind,
            "category": self.category,
            "error": self.error,
            "completed": False,
            "real": False,
            "success": False,
            "real_execution": False,
            "contract_version": self.contract_version,
        }


class ComputerUseExecutor(Protocol):
    """Boundary for a private executor. This module does not activate one."""

    def execute(self, action: ComputerUseAction) -> ComputerUseResult:
        """Return verifiable evidence for one already-authorized action."""


def _unexecuted(status: str, error: str, category: str) -> ComputerUseResult:
    return ComputerUseResult(
        ok=False,
        status=status,
        result_kind=RESULT_KIND_UNEXECUTED,
        category=category,
        error=error,
        completed=False,
        real=False,
        success=False,
        real_execution=False,
    )


def _recognized_category(action: object) -> str | None:
    if not isinstance(action, ComputerUseAction):
        return None
    category = action.category.value
    if category in _RECOGNIZED:
        return category
    return None


@dataclass(frozen=True, slots=True)
class DisabledComputerUseExecutor:
    """Default executor. Approval-like fields do not turn it on."""

    def execute(self, action: object) -> ComputerUseResult:
        category = _recognized_category(action)
        if category is None:
            return _unexecuted(STATUS_REJECTED, ERROR_REJECTED, CATEGORY_UNKNOWN)
        return _unexecuted(STATUS_DISABLED, ERROR_DISABLED, category)


def default_executor() -> DisabledComputerUseExecutor:
    """Return the only executor available in this public module."""

    return DisabledComputerUseExecutor()


def executor_contract_payload() -> dict[str, Any]:
    """Public description of the boundary. Contains no secrets or endpoints."""

    return {
        "contract_version": EXECUTOR_CONTRACT_VERSION,
        "default": "disabled",
        "real_execution": False,
        "completed": False,
        "success": False,
        "runtime": "private_not_in_this_module",
        "categories": list(RECOGNIZED_ACTION_CATEGORIES),
        "requirements": [
            "lumos_policy_gate_passed",
            "task_scope_present",
            "explicit_approval_for_external_effects",
            "no_secret_exposure",
            "fail_closed_on_uncertainty",
            "no_completed_or_real_without_execution",
        ],
    }


__all__ = [
    "CATEGORY_UNKNOWN",
    "ERROR_DISABLED",
    "ERROR_REJECTED",
    "EXECUTOR_CONTRACT_VERSION",
    "RECOGNIZED_ACTION_CATEGORIES",
    "RESULT_KIND_UNEXECUTED",
    "STATUS_DISABLED",
    "STATUS_REJECTED",
    "ComputerUseAction",
    "ComputerUseCategory",
    "ComputerUseExecutor",
    "ComputerUseResult",
    "DisabledComputerUseExecutor",
    "default_executor",
    "executor_contract_payload",
]
