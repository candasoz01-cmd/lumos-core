"""JSON-RPC 2.0 handlers for MCP spec 2025-11-25 (tools only)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

PROTOCOL_VERSION = "2025-11-25"
SERVER_NAME = "lumos-alexa-plus"
SERVER_VERSION = "0.1.0"
TOOL_NAME = "propose_lumos_task"

_INVALID_REQUEST = -32600
_METHOD_NOT_FOUND = -32601
_INVALID_PARAMS = -32602

_TIME_RE = re.compile(r"\b(\d{1,2}:\d{2})\b")
_TOMORROW_RE = re.compile(r"\b(yarın|tomorrow)\b", re.IGNORECASE)


@dataclass
class Session:
    """One MCP Streamable HTTP session (initialize → subsequent calls)."""

    session_id: str
    initialized: bool = False


@dataclass
class RpcOutcome:
    """HTTP mapping for one JSON-RPC message."""

    status: int
    body: dict[str, Any] | None = None
    session_id: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


def _error(code: int, message: str, rpc_id: Any = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "error": {"code": code, "message": message},
    }
    if rpc_id is not None:
        payload["id"] = rpc_id
    else:
        payload["id"] = None
    return payload


def _result(rpc_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rpc_id, "result": result}


def propose_lumos_task(request: str) -> dict[str, Any]:
    """Deterministic proposal. Never creates or executes a task."""
    text = " ".join(str(request).split())
    if not text:
        raise ValueError("request is empty")
    title = re.sub(r"\s+görevi hazırla\s*$", "", text, flags=re.IGNORECASE).strip()
    title = title or text
    if len(title) > 80:
        title = title[:77] + "..."
    time_match = _TIME_RE.search(text)
    time_note = None
    if time_match and _TOMORROW_RE.search(text):
        time_note = f"Tomorrow {time_match.group(1)}"
    elif time_match:
        time_note = time_match.group(1)
    return {
        "title": title,
        "priority": "normal",
        "time_note": time_note,
        "requires_human_approval": True,
        "created": False,
        "writes_task": False,
    }


def tool_list() -> list[dict[str, Any]]:
    return [
        {
            "name": TOOL_NAME,
            "description": (
                "Propose a Lumos task for a human to approve. "
                "Does not create, schedule, or execute the task."
            ),
            "inputSchema": {
                "type": "object",
                "required": ["request"],
                "additionalProperties": False,
                "properties": {
                    "request": {
                        "type": "string",
                        "description": "What the person asked Alexa+ to prepare.",
                    }
                },
            },
        }
    ]


def handle_jsonrpc(
    message: dict[str, Any],
    session: Session | None,
    *,
    new_session_id: str | None = None,
) -> RpcOutcome:
    """Handle one JSON-RPC object. Caller owns session persistence."""
    if message.get("jsonrpc") != "2.0":
        return RpcOutcome(status=400, body=_error(_INVALID_REQUEST, "jsonrpc must be 2.0"))

    method = message.get("method")
    rpc_id = message.get("id", _MISSING)
    is_notification = rpc_id is _MISSING  # omitted id = notification
    params = message.get("params") or {}

    if method == "initialize":
        if is_notification:
            return RpcOutcome(status=400, body=_error(_INVALID_REQUEST, "initialize needs id"))
        client_version = ""
        if isinstance(params, dict):
            client_version = str(params.get("protocolVersion") or "")
        if client_version and client_version != PROTOCOL_VERSION:
            return RpcOutcome(
                status=400,
                body=_error(
                    _INVALID_PARAMS,
                    f"unsupported protocolVersion {client_version}",
                    rpc_id,
                ),
            )
        sid = new_session_id or (session.session_id if session else None)
        if not sid:
            return RpcOutcome(status=500, body=_error(-32603, "session id missing", rpc_id))
        return RpcOutcome(
            status=200,
            session_id=sid,
            body=_result(
                rpc_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {
                        "name": SERVER_NAME,
                        "version": SERVER_VERSION,
                    },
                },
            ),
        )

    if session is None:
        return RpcOutcome(status=400, body=_error(_INVALID_REQUEST, "MCP-Session-Id required"))

    if method == "notifications/initialized":
        if not is_notification:
            return RpcOutcome(
                status=400,
                body=_error(_INVALID_REQUEST, "initialized is a notification"),
            )
        session.initialized = True
        return RpcOutcome(status=202, body=None)

    if is_notification:
        return RpcOutcome(status=202, body=None)

    if not session.initialized and method != "ping":
        return RpcOutcome(
            status=400,
            body=_error(_INVALID_REQUEST, "session not initialized", rpc_id),
        )

    if method == "ping":
        return RpcOutcome(status=200, body=_result(rpc_id, {}))

    if method == "tools/list":
        return RpcOutcome(status=200, body=_result(rpc_id, {"tools": tool_list()}))

    if method == "tools/call":
        if not isinstance(params, dict):
            return RpcOutcome(
                status=200,
                body=_error(_INVALID_PARAMS, "params must be an object", rpc_id),
            )
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name != TOOL_NAME:
            return RpcOutcome(
                status=200,
                body=_error(_METHOD_NOT_FOUND, f"unknown tool {name!r}", rpc_id),
            )
        request = arguments.get("request") if isinstance(arguments, dict) else None
        try:
            proposal = propose_lumos_task(str(request or ""))
        except ValueError as exc:
            return RpcOutcome(
                status=200,
                body=_result(
                    rpc_id,
                    {
                        "content": [{"type": "text", "text": str(exc)}],
                        "isError": True,
                    },
                ),
            )
        return RpcOutcome(
            status=200,
            body=_result(
                rpc_id,
                {
                    "content": [
                        {"type": "text", "text": json.dumps(proposal, ensure_ascii=True)}
                    ],
                    "structuredContent": proposal,
                    "isError": False,
                },
            ),
        )

    return RpcOutcome(
        status=200,
        body=_error(_METHOD_NOT_FOUND, f"unknown method {method!r}", rpc_id),
    )


_MISSING = object()
