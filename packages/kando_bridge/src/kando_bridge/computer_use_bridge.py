"""Offline compatibility transport for the existing bridge tool-call adapter.

Pass ``offline_computer_use_transport`` explicitly as the adapter's ``http_fn``
to exercise request/result wiring without HTTP, approvals, or device access.
Nothing registers this function with the server or selects it automatically.
The integer response code is an in-memory protocol value, not an HTTP exchange.

Only command classification is checked here. This does not validate a live
action's parameters, scope, identity, approval, or post-action evidence. A real
executor and those gates remain in the separately authorized private layer.
"""

from types import MappingProxyType
from typing import Any

from kando_bridge.computer_use_executor import (
    ComputerUseAction,
    ComputerUseCategory,
    default_executor,
)

# These names come from pc_remote_tools' existing function schemas. Keep the
# proposal semantics of suggest_click: it must never become an actual click.
_CATEGORIES = MappingProxyType({
    "pc_open_url": ComputerUseCategory.NAVIGATE,
    "pc_read_screen_state": ComputerUseCategory.OBSERVE,
    "pc_type_text": ComputerUseCategory.TYPE,
    "pc_suggest_click": ComputerUseCategory.SUGGEST,
})


def offline_computer_use_transport(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict[str, Any]]:
    """Return disabled/rejected results; never send, approve, or execute.

    Compatible with the existing ``HttpJsonFn`` injection point. Approval-like
    metadata and arbitrary arguments are discarded, not consumed or echoed.
    App opening, file picking, approval creation, and unknown commands have no
    faithful action mapping here and are rejected rather than guessed.
    """
    del timeout  # Interface compatibility only; no timer or connection exists.
    executor = default_executor()
    rejected = executor.execute(None).public_dict()
    rejected.update(stub_only=True, transport="offline", live_ready=False)
    if type(method) is not str or method != "POST":
        return 405, rejected
    if type(path) is not str or path != "/tools/execute":
        return 404, rejected
    if query or type(body) is not dict:
        return 400, rejected
    command = body.get("command")
    if type(command) is not str or type(body.get("arguments")) is not dict:
        return 400, rejected
    category = _CATEGORIES.get(command)
    if category is None:
        return 400, rejected

    # Do not carry targets, selectors, text, tokens, or provider output across
    # this foundation boundary. Even approval-shaped input cannot enable it.
    result = executor.execute(ComputerUseAction(category=category)).public_dict()
    result.update(stub_only=True, transport="offline", live_ready=False)
    return 200, result
