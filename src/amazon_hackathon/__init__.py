"""Amazon Build, Ship, Shape 2026 — local Alexa+ and Ring simulators.

Branch-only demo slice. Not a live Amazon connector, not a FAZ-1 product
surface, and not a claim that Ring or Alexa+ integrations are complete.

Ring: synthetic devices shaped like Amazon Vision `/v1/devices`.
Alexa+: MCP spec `2025-11-25` over Streamable HTTP, plus an utterance simulator.
Neither path calls `api.amazonvision.com` or Alexa production hosts.
"""

from amazon_hackathon.alexa_plus_sim import (
    ALEXA_PLUS_MCP_PROTOCOL_VERSION,
    AlexaPlusSimulator,
    handle_mcp_jsonrpc,
)
from amazon_hackathon.ring_simulator import RingSandboxSimulator

__all__ = [
    "ALEXA_PLUS_MCP_PROTOCOL_VERSION",
    "AlexaPlusSimulator",
    "RingSandboxSimulator",
    "handle_mcp_jsonrpc",
]
