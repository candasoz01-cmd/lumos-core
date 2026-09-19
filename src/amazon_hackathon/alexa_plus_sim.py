"""Alexa+ simulated experience + MCP Streamable HTTP JSON-RPC (2025-11-25).

Hackathon path: a self-hosted MCP surface over Streamable HTTP, plus a local
utterance simulator. Alexa production and the Alexa AI CLI add-on registry
are not contacted.

MCP spec minimum for this slice: `initialize`, `tools/list`, `tools/call`.
Transport: HTTP POST `application/json` (Streamable HTTP JSON response).
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from amazon_hackathon.ring_simulator import RingSandboxSimulator

ALEXA_PLUS_MCP_PROTOCOL_VERSION = "2025-11-25"
SERVER_NAME = "lumos-alexa-plus-sim"
SERVER_VERSION = "0.1.0"

_TOOLS = (
    {
        "name": "front_door_status",
        "description": "Read simulated Ring front-door / camera status. Not live.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "latest_visitor_event",
        "description": "Return the latest simulated Ring visitor event.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "request_door_unlock",
        "description": "Request a door unlock. Sandbox never actuates. Approval required.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "string"},
                "approved": {"type": "boolean"},
            },
            "required": ["device_id"],
        },
    },
)


class AlexaPlusSimulator:
    """Local Alexa+ client stand-in. Calls MCP tools that read the Ring sandbox."""

    def __init__(self, ring: RingSandboxSimulator | None = None) -> None:
        self.ring = ring or RingSandboxSimulator()

    def simulate_utterance(self, utterance: str) -> dict[str, Any]:
        text = utterance.strip().lower()
        if not text:
            return {"ok": False, "error": "utterance_required", "execution_live": False}
        if any(token in text for token in ("unlock", "aç", "kilit")):
            payload = handle_mcp_jsonrpc(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "request_door_unlock",
                        "arguments": {"device_id": "sim-doorbell-front", "approved": False},
                    },
                },
                ring=self.ring,
            )
            return {"ok": True, "path": "request_door_unlock", "execution_live": False, "mcp": payload}
        if any(token in text for token in ("visitor", "someone", "doorbell", "kapı", "ziyaret")):
            payload = handle_mcp_jsonrpc(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "latest_visitor_event", "arguments": {}},
                },
                ring=self.ring,
            )
            return {"ok": True, "path": "latest_visitor_event", "execution_live": False, "mcp": payload}
        payload = handle_mcp_jsonrpc(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "front_door_status", "arguments": {}},
            },
            ring=self.ring,
        )
        return {"ok": True, "path": "front_door_status", "execution_live": False, "mcp": payload}


def handle_mcp_jsonrpc(
    message: dict[str, Any],
    *,
    ring: RingSandboxSimulator | None = None,
) -> dict[str, Any]:
    sandbox = ring or RingSandboxSimulator()
    msg_id = message.get("id")
    method = str(message.get("method") or "")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": ALEXA_PLUS_MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        }

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": list(_TOOLS)}}

    if method == "tools/call":
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        name = str(params.get("name") or "")
        arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        result = _call_tool(name, arguments, sandbox)
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"method_not_found:{method}"},
    }


def _call_tool(name: str, arguments: dict[str, Any], ring: RingSandboxSimulator) -> dict[str, Any]:
    if name == "front_door_status":
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "devices": ring.list_devices(),
                            "front_door": ring.device_status("sim-doorbell-front"),
                        },
                        ensure_ascii=True,
                    ),
                }
            ],
            "isError": False,
        }
    if name == "latest_visitor_event":
        return {
            "content": [{"type": "text", "text": json.dumps(ring.latest_event(), ensure_ascii=True)}],
            "isError": False,
        }
    if name == "request_door_unlock":
        device_id = str(arguments.get("device_id") or "")
        approved = arguments.get("approved") is True
        payload = ring.request_unlock(device_id, approved=approved)
        return {
            "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=True)}],
            "isError": not payload.get("ok", False),
        }
    return {
        "content": [{"type": "text", "text": json.dumps({"error": "unknown_tool"}, ensure_ascii=True)}],
        "isError": True,
    }


class _McpHandler(BaseHTTPRequestHandler):
    ring: RingSandboxSimulator

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path not in {"/", "/mcp"}:
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            message = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._write(400, {"jsonrpc": "2.0", "error": {"code": -32700, "message": "parse_error"}})
            return
        if not isinstance(message, dict):
            self._write(400, {"jsonrpc": "2.0", "error": {"code": -32600, "message": "invalid_request"}})
            return
        payload = handle_mcp_jsonrpc(message, ring=self.ring)
        self._write(200, payload)

    def _write(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve_mcp(host: str, port: int, ring: RingSandboxSimulator | None = None) -> ThreadingHTTPServer:
    """Bind a local Streamable HTTP MCP endpoint. Caller must shut down the server."""

    handler = type("BoundMcpHandler", (_McpHandler,), {"ring": ring or RingSandboxSimulator()})
    return ThreadingHTTPServer((host, port), handler)
