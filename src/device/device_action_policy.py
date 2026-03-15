"""
Device action policy: recommend device-level actions and gate execution on
explicit user approval. Logic only; no process termination, no UI.

Consumes report-shaped data (e.g. from device_guard), suggests actions, and
exposes approval-oriented APIs: can_execute_action, requires_confirmation,
get_execution_policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from device.intent_surface_mapper import (
    SURFACE_PRIVACY_CAMERA,
    SURFACE_SYSTEM_BATTERY,
    SURFACE_SYSTEM_NETWORK,
    SURFACE_SYSTEM_PROCESSES,
)

# ---------------------------------------------------------------------------
# Action categories
# ---------------------------------------------------------------------------

class ActionCategory(str, Enum):
    """Category of device action; drives execution policy."""

    READ_ONLY = "read_only"               # No side effects; can be auto (e.g. show report).
    OPTIMIZATION = "optimization"         # E.g. suggest closing apps; requires confirmation.
    PERMISSION_CHANGE = "permission_change"  # Revoke/grant; must never auto.
    PROCESS_CONTROL = "process_control"    # Stop/kill; requires confirmation, never auto when we add it.
    SECURITY_SENSITIVE = "security_sensitive"  # Security-critical; must never auto.


# ---------------------------------------------------------------------------
# Execution policy
# ---------------------------------------------------------------------------

class ExecutionPolicy(str, Enum):
    """Whether an action may run without confirmation."""

    AUTO = "auto"           # May be auto-executed (e.g. read_only).
    CONFIRM = "confirm"      # Must have explicit user confirmation before execution.
    NEVER_AUTO = "never_auto"  # Must never be auto-executed; only with explicit user approval.


# ---------------------------------------------------------------------------
# Suggested action structure
# ---------------------------------------------------------------------------

@dataclass
class SuggestedAction:
    """A single suggested device action (logic-only representation)."""

    action_id: str
    description: str
    requires_confirmation: bool
    surface: str
    category: str = ""
    details: dict[str, Any] | None = None  # Optional payload (e.g. count, pids).

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "description": self.description,
            "requires_confirmation": self.requires_confirmation,
            "surface": self.surface,
            "category": self.category,
            "details": self.details or {},
        }


# ---------------------------------------------------------------------------
# Action registry: action_id -> (category, surface, description_template)
# ---------------------------------------------------------------------------

_ACTION_REGISTRY: dict[str, tuple[ActionCategory, str, str]] = {
    "show_device_report": (ActionCategory.READ_ONLY, SURFACE_SYSTEM_PROCESSES, "Show device efficiency report"),
    "stop_background_processes": (ActionCategory.PROCESS_CONTROL, SURFACE_SYSTEM_PROCESSES, "Stop {count} unnecessary background processes"),
    "review_high_cpu": (ActionCategory.OPTIMIZATION, SURFACE_SYSTEM_PROCESSES, "Review {count} high-CPU processes"),
    "review_high_memory": (ActionCategory.OPTIMIZATION, SURFACE_SYSTEM_PROCESSES, "Review {count} high-memory processes"),
    "review_sensitive_access": (ActionCategory.PERMISSION_CHANGE, SURFACE_PRIVACY_CAMERA, "Review {count} apps with sensitive access"),
    "review_suspicious": (ActionCategory.SECURITY_SENSITIVE, SURFACE_SYSTEM_PROCESSES, "Review {count} suspicious processes"),
    "open_battery_surface": (ActionCategory.READ_ONLY, SURFACE_SYSTEM_BATTERY, "Open battery usage"),
    "open_network_surface": (ActionCategory.READ_ONLY, SURFACE_SYSTEM_NETWORK, "Open network activity"),
}


def _category_to_policy(category: ActionCategory) -> ExecutionPolicy:
    if category == ActionCategory.READ_ONLY:
        return ExecutionPolicy.AUTO
    if category in (ActionCategory.PERMISSION_CHANGE, ActionCategory.SECURITY_SENSITIVE):
        return ExecutionPolicy.NEVER_AUTO
    return ExecutionPolicy.CONFIRM  # OPTIMIZATION, PROCESS_CONTROL


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_execution_policy(action_id: str) -> ExecutionPolicy | None:
    """
    Determine whether an action can be auto-executed, requires confirmation,
    or must never be auto-executed. Returns None if action_id is unknown.
    """
    entry = _ACTION_REGISTRY.get(action_id)
    if not entry:
        return None
    category, _, _ = entry
    return _category_to_policy(category)


def can_execute_action(action_id: str) -> bool:
    """
    True if the action is known and is allowed to be executed (with user
    approval when required). Unknown actions return False.
    """
    return action_id in _ACTION_REGISTRY


def requires_confirmation(action_id: str) -> bool:
    """
    True if the action must not run without explicit user confirmation.
    True for CONFIRM and NEVER_AUTO; False for AUTO. Unknown actions return True (safe default).
    """
    policy = get_execution_policy(action_id)
    if policy is None:
        return True
    return policy in (ExecutionPolicy.CONFIRM, ExecutionPolicy.NEVER_AUTO)


def suggest_actions(report: dict[str, Any]) -> list[dict[str, Any]]:
    """
    From a device report (e.g. DeviceGuardReport.to_dict()), suggest actions.
    Returns a list of suggested-action dicts with action_id, description,
    requires_confirmation, surface, category, and optional details.

    Does not perform any I/O or process control; only derives suggestions
    from report structure.
    """
    out: list[dict[str, Any]] = []
    # Always offer read-only report
    _append(out, "show_device_report", {})

    bg = report.get("background_services") or []
    if bg:
        _append(out, "stop_background_processes", {"count": len(bg)}, count=len(bg))

    high_cpu = report.get("high_cpu") or []
    if high_cpu:
        _append(out, "review_high_cpu", {"count": len(high_cpu)}, count=len(high_cpu))

    high_mem = report.get("high_memory") or []
    if high_mem:
        _append(out, "review_high_memory", {"count": len(high_mem)}, count=len(high_mem))

    sensitive = report.get("sensitive_access") or []
    if sensitive:
        _append(out, "review_sensitive_access", {"count": len(sensitive)}, count=len(sensitive))

    suspicious = report.get("suspicious") or []
    if suspicious:
        _append(out, "review_suspicious", {"count": len(suspicious)}, count=len(suspicious))

    return out


def _append(
    out: list[dict[str, Any]],
    action_id: str,
    details: dict[str, Any],
    count: int | None = None,
) -> None:
    entry = _ACTION_REGISTRY.get(action_id)
    if not entry:
        return
    category, surface, template = entry
    description = template.format(count=count) if count is not None else template
    policy = _category_to_policy(category)
    out.append(
        SuggestedAction(
            action_id=action_id,
            description=description,
            requires_confirmation=(policy != ExecutionPolicy.AUTO),
            surface=surface,
            category=category.value,
            details=details,
        ).to_dict()
    )


def register_action(
    action_id: str,
    category: ActionCategory,
    surface: str,
    description_template: str,
) -> None:
    """Register a new action for policy and suggestions. Extendable at runtime."""
    _ACTION_REGISTRY[action_id] = (category, surface, description_template)


# ---------------------------------------------------------------------------
# How this module works with system_monitor, device_guard, intent_surface_mapper
# ---------------------------------------------------------------------------
#
# 1. system_monitor
#    - system_monitor.scan_system_state() produces raw metrics (processes, CPU, memory, network).
#    - device_action_policy does not call system_monitor directly. It consumes already-aggregated
#      report data (see device_guard).
#
# 2. device_guard
#    - DeviceGuard.run() uses system_monitor and emits DeviceGuardReport (efficiency, high_cpu,
#      background_services, sensitive_access, suspicious).
#    - suggest_actions(report) expects a dict of that shape (e.g. report.to_dict()). From it we
#      suggest actions like "stop_background_processes" or "review_sensitive_access" and attach
#      surface ids (e.g. system.processes, privacy.camera).
#
# 3. intent_surface_mapper
#    - intent_surface_mapper resolves user text ("pilimi ne tüketiyor") to a surface (system.battery).
#    - device_action_policy uses the same surface identifiers (system.processes, system.battery,
#      privacy.camera, etc.) so that when we suggest an action with surface "system.battery", a UI
#    - or executor can use intent_surface_mapper to open that surface, or vice versa: user asks
#      "pilimi ne tüketiyor" -> surface system.battery -> policy can suggest "open_battery_surface".
#    - Shared surface namespace keeps "where to show / where to open" consistent across intent
#      resolution and action suggestions.
#
# Flow (future integration):
#    scan_system_state() -> DeviceGuard.run() -> report
#    suggest_actions(report) -> list of { action_id, surface, requires_confirmation, ... }
#    User says "arka planda ne çalışıyor" -> resolve_intent_surface() -> surface system.processes
#    UI shows suggested actions for that surface + asks confirmation for process_control.
#    can_execute_action(id) and requires_confirmation(id) gate whether to run or prompt.
