"""Amazon Hackathon 2026 — Alexa+ MCP server (contest-period, not Lumos core).

Issue: candasoz01-cmd/lumos-core#854. Transport: MCP 2025-11-25 Streamable HTTP.
The older `/alexa-plus-simulasyon` web page is historical and is not this server.
"""

from __future__ import annotations

from alexa_plus_mcp.protocol import (
    PROTOCOL_VERSION,
    SERVER_NAME,
    TOOL_NAME,
    handle_jsonrpc,
)
from alexa_plus_mcp.oauth import AuthServer
from alexa_plus_mcp.server import serve

__all__ = [
    "PROTOCOL_VERSION",
    "SERVER_NAME",
    "TOOL_NAME",
    "AuthServer",
    "handle_jsonrpc",
    "serve",
]
