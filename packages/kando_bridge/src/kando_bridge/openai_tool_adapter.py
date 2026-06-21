"""
OpenAI Responses API tool-loop adapter — Lumos PC remote bridge MVP (PR-RB-07).

Connects OpenAI tool/function call output to kando_bridge POST /tools/execute,
then reuses RB-05 mobile approval client and RB-06 LAN relay (optional).

Mock OpenAI response (Responses API function_call item — CI ``--mock`` default):

    {
        "id": "fc_mock_pc_open_url",
        "type": "function_call",
        "name": "pc_open_url",
        "call_id": "call_mock_001",
        "arguments": "{\\"url\\": \\"https://example.com\\"}"
    }

Full response wrapper also accepted::

    {"output": [<function_call item above>]}

Alternate shapes parsed by :func:`parse_openai_tool_calls`:
- ``type=tool_call`` with ``function.name`` / ``function.arguments``
- Chat-style ``tool_calls[]`` with nested ``function``
- Top-level ``name`` + ``arguments`` when ``type`` omitted

No real OS automation — stub executor only after user approval on disk.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable

from kando_bridge.mobile_approval_client import approve_pending, http_json
from kando_bridge.pc_remote_tools import (
    ALL_COMMANDS,
    CMD_OPEN_URL,
    openai_tool_definitions,
)

HttpJsonFn = Callable[..., tuple[int, Any]]
ApproveFn = Callable[[str, str], dict[str, Any]]


@dataclass(frozen=True)
class ParsedToolCall:
    name: str
    arguments: dict[str, Any]
    call_id: str = ""


def load_openai_tools() -> list[dict[str, Any]]:
    """Tool definitions for Responses API ``tools=`` parameter."""
    return openai_tool_definitions()


def mock_pc_open_url_response(*, url: str = "https://example.com") -> dict[str, Any]:
    """Canned Responses API output item for CI and ``--mock`` demo."""
    return {
        "id": "fc_mock_pc_open_url",
        "type": "function_call",
        "name": CMD_OPEN_URL,
        "call_id": "call_mock_pc_open_url",
        "arguments": json.dumps({"url": url}, ensure_ascii=False),
    }


def mock_openai_response_payload(*, url: str = "https://example.com") -> dict[str, Any]:
    """Full Responses API-shaped payload with ``output`` array."""
    return {"output": [mock_pc_open_url_response(url=url)]}


def _coerce_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _item_to_tool_call(item: Any) -> ParsedToolCall | None:
    if item is None:
        return None
    if isinstance(item, dict):
        typ = str(item.get("type") or "").strip().lower()
        call_id = str(item.get("call_id") or item.get("id") or "").strip()
        if typ in ("function_call", "tool_call", "function"):
            name = str(item.get("name") or "").strip()
            args = _coerce_arguments(item.get("arguments"))
            if not name and isinstance(item.get("function"), dict):
                fn = item["function"]
                name = str(fn.get("name") or "").strip()
                args = _coerce_arguments(fn.get("arguments"))
            if name:
                return ParsedToolCall(name=name, arguments=args, call_id=call_id)
        fn = item.get("function")
        if isinstance(fn, dict):
            name = str(fn.get("name") or "").strip()
            if name:
                return ParsedToolCall(
                    name=name,
                    arguments=_coerce_arguments(fn.get("arguments")),
                    call_id=call_id,
                )
        name = str(item.get("name") or "").strip()
        if name and ("arguments" in item or typ == ""):
            return ParsedToolCall(
                name=name,
                arguments=_coerce_arguments(item.get("arguments")),
                call_id=call_id,
            )
        return None
    typ = str(getattr(item, "type", "") or "").strip().lower()
    call_id = str(getattr(item, "call_id", None) or getattr(item, "id", "") or "").strip()
    name = str(getattr(item, "name", "") or "").strip()
    args_raw = getattr(item, "arguments", None)
    if typ in ("function_call", "tool_call", "function") and name:
        return ParsedToolCall(name=name, arguments=_coerce_arguments(args_raw), call_id=call_id)
    fn = getattr(item, "function", None)
    if fn is not None:
        fn_name = str(getattr(fn, "name", "") or "").strip()
        if fn_name:
            fn_args = getattr(fn, "arguments", None)
            return ParsedToolCall(name=fn_name, arguments=_coerce_arguments(fn_args), call_id=call_id)
    return None


def parse_openai_tool_calls(response_or_item: Any) -> list[ParsedToolCall]:
    """Extract bridge tool calls from Responses API output (flexible shapes)."""
    if response_or_item is None:
        return []

    if isinstance(response_or_item, ParsedToolCall):
        return [response_or_item]

    direct = _item_to_tool_call(response_or_item)
    if direct is not None and not isinstance(response_or_item, dict):
        return [direct]

    items: list[Any] = []
    if isinstance(response_or_item, dict):
        if isinstance(response_or_item.get("output"), list):
            items.extend(response_or_item["output"])
        elif isinstance(response_or_item.get("tool_calls"), list):
            items.extend(response_or_item["tool_calls"])
        else:
            items.append(response_or_item)
    else:
        output = getattr(response_or_item, "output", None)
        if isinstance(output, list):
            items.extend(output)
        else:
            items.append(response_or_item)

    out: list[ParsedToolCall] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        parsed = _item_to_tool_call(item)
        if parsed is None:
            continue
        key = (parsed.name, json.dumps(parsed.arguments, sort_keys=True))
        if key in seen:
            continue
        seen.add(key)
        out.append(parsed)
    return out


def tool_call_to_execute_body(
    tool_call: ParsedToolCall | dict[str, Any],
    *,
    requested_by: str = "openai_tool_adapter",
    target_device: str = "local",
    approval_token: str | None = None,
    approval_id: str | None = None,
) -> dict[str, Any]:
    """Map parsed OpenAI tool call → POST /tools/execute JSON body."""
    if isinstance(tool_call, dict):
        name = str(tool_call.get("name") or tool_call.get("command") or "").strip()
        arguments = tool_call.get("arguments")
        if not isinstance(arguments, dict):
            arguments = _coerce_arguments(arguments)
        parsed = ParsedToolCall(name=name, arguments=arguments)
    else:
        parsed = tool_call

    body: dict[str, Any] = {
        "command": parsed.name,
        "arguments": parsed.arguments,
        "requested_by": requested_by,
        "target_device": target_device,
    }
    if approval_token:
        body["approval_token"] = approval_token
    if approval_id:
        body["approval_id"] = approval_id
    return body


def post_tools_execute(
    body: dict[str, Any],
    *,
    http_fn: HttpJsonFn | None = None,
) -> tuple[int, dict[str, Any]]:
    """POST /tools/execute via bridge HTTP client."""
    fn = http_fn or http_json
    status, data = fn("POST", "/tools/execute", body=body)
    if not isinstance(data, dict):
        return status, {"ok": False, "error": "invalid_response", "http_status": status}
    data.setdefault("http_status", status)
    return status, data


def approve_and_reexecute(
    tool_call: ParsedToolCall,
    pending: dict[str, Any],
    *,
    http_fn: HttpJsonFn | None = None,
    approve_fn: ApproveFn | None = None,
) -> tuple[int, dict[str, Any]]:
    """Approve pending record then re-POST /tools/execute with approval token."""
    approval_id = str(pending.get("approval_id") or "").strip()
    approval_token = str(pending.get("approval_token") or "").strip()
    if not approval_id or not approval_token:
        return 400, {
            "ok": False,
            "stage": "approve",
            "error": "pending_missing_tokens",
            "pending": pending,
        }

    approve = approve_fn or approve_pending
    approve_out = approve(approval_id, approval_token)
    if not approve_out.get("accepted"):
        return int(approve_out.get("http_status") or 403), {
            "ok": False,
            "stage": "approve",
            "error": approve_out.get("error") or "approval_rejected",
            "approve": approve_out,
            "pending": pending,
        }

    body = tool_call_to_execute_body(
        tool_call,
        approval_token=approval_token,
        approval_id=approval_id,
    )
    status, execute_out = post_tools_execute(body, http_fn=http_fn)
    return status, {
        "ok": bool(execute_out.get("ok")),
        "stage": "executed",
        "approve": approve_out,
        "execute": execute_out,
        "pending": pending,
    }


def run_tool_call_loop(
    tool_call: ParsedToolCall,
    *,
    http_fn: HttpJsonFn | None = None,
    approve_fn: ApproveFn | None = None,
    auto_approve: bool = False,
) -> dict[str, Any]:
    """
    Single tool call: bridge execute → pending (if needed) → approve → stub execute.

    Default ``auto_approve=False`` — user must approve via mobile web UI or CLI.
    Returns a summary dict with ``stage`` in (direct, pending, executed, error).
    """
    if tool_call.name not in ALL_COMMANDS:
        return {
            "ok": False,
            "stage": "error",
            "error": "unknown_command",
            "command": tool_call.name,
        }

    body = tool_call_to_execute_body(tool_call)
    status, first = post_tools_execute(body, http_fn=http_fn)

    if first.get("status") == "stub" and first.get("ok"):
        return {"ok": True, "stage": "direct", "execute": first, "http_status": status}

    if first.get("status") != "pending_approval":
        return {
            "ok": False,
            "stage": "error",
            "error": first.get("error") or first.get("status") or "execute_failed",
            "execute": first,
            "http_status": status,
        }

    if not auto_approve:
        return {
            "ok": False,
            "stage": "pending",
            "pending": first,
            "http_status": status,
            "message": "approval_required — call approve_and_reexecute after user consent",
        }

    exec_status, loop_out = approve_and_reexecute(
        tool_call,
        first,
        http_fn=http_fn,
        approve_fn=approve_fn,
    )
    loop_out["http_status"] = exec_status
    loop_out["tool_call"] = {
        "name": tool_call.name,
        "arguments": tool_call.arguments,
        "call_id": tool_call.call_id,
    }
    return loop_out


def run_openai_response_loop(
    response_or_item: Any,
    *,
    http_fn: HttpJsonFn | None = None,
    approve_fn: ApproveFn | None = None,
    auto_approve: bool = False,
) -> list[dict[str, Any]]:
    """Parse OpenAI output and run bridge loop for each tool call."""
    calls = parse_openai_tool_calls(response_or_item)
    return [
        run_tool_call_loop(
            tc,
            http_fn=http_fn,
            approve_fn=approve_fn,
            auto_approve=auto_approve,
        )
        for tc in calls
    ]


def fetch_live_openai_response(
    user_input: str,
    *,
    model: str | None = None,
    api_key: str | None = None,
) -> Any:
    """
    Call OpenAI Responses API with PC remote tools.

    Requires OPENAI_API_KEY in environment (or explicit api_key).
    """
    key = (api_key or os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY tanımlı değil — --live için gerekli veya --mock kullanın."
        )
    from openai import OpenAI

    client = OpenAI(api_key=key)
    chosen_model = (model or os.environ.get("OPENAI_MODEL") or "gpt-4.1-mini").strip()
    return client.responses.create(
        model=chosen_model,
        input=user_input,
        tools=load_openai_tools(),
    )


def tool_result_for_model(execute_payload: dict[str, Any]) -> dict[str, Any]:
    """Compact tool result suitable for a follow-up Responses API turn."""
    return {
        "ok": execute_payload.get("ok"),
        "status": execute_payload.get("status"),
        "command": execute_payload.get("command"),
        "simulated": execute_payload.get("simulated"),
        "error": execute_payload.get("error"),
        "stub_only": execute_payload.get("stub_only", True),
    }
