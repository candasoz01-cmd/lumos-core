"""Hackathon registry hook: Alexa+ sim + Ring sandbox. Not a live connector."""

from __future__ import annotations

from amazon_hackathon.alexa_plus_sim import AlexaPlusSimulator, handle_mcp_jsonrpc
from amazon_hackathon.ring_live_adapter import RingLiveAdapter, token_from_env
from amazon_hackathon.ring_simulator import RingSandboxSimulator
from integrations.models import IntegrationRequest, IntegrationResult

_RING = RingSandboxSimulator()
_ALEXA = AlexaPlusSimulator(ring=_RING)


def _ring_live() -> RingLiveAdapter:
    # Token is read per call: Playground tokens expire in ~30 minutes.
    return RingLiveAdapter(token=token_from_env())


def run_amazon_hackathon_action(request: IntegrationRequest) -> IntegrationResult:
    action = request.action.strip().lower()
    payload = request.payload if isinstance(request.payload, dict) else {}

    if action == "ring_list_devices":
        return IntegrationResult(True, request.provider, request.action, _RING.list_devices())

    if action == "ring_status":
        device_id = str(payload.get("device_id") or "")
        data = _RING.device_status(device_id)
        ok = "error" not in data
        return IntegrationResult(ok, request.provider, request.action, data, data.get("error", ""))

    if action == "ring_live_list_devices":
        data = _ring_live().list_devices()
        ok = "error" not in data
        return IntegrationResult(ok, request.provider, request.action, data, data.get("error", ""))

    if action == "ring_live_status":
        device_id = str(payload.get("device_id") or "")
        data = _ring_live().device_status(device_id)
        ok = "error" not in data
        return IntegrationResult(ok, request.provider, request.action, data, data.get("error", ""))

    if action == "ring_inject_event":
        data = _RING.inject_event(
            str(payload.get("device_id") or ""),
            str(payload.get("kind") or "motion"),
            str(payload.get("summary") or "simulated visitor"),
        )
        return IntegrationResult(bool(data.get("ok")), request.provider, request.action, data, str(data.get("error") or ""))

    if action == "alexa_simulate_utterance":
        data = _ALEXA.simulate_utterance(str(payload.get("utterance") or ""))
        return IntegrationResult(bool(data.get("ok")), request.provider, request.action, data, str(data.get("error") or ""))

    if action == "mcp_initialize":
        data = handle_mcp_jsonrpc(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            ring=_RING,
        )
        return IntegrationResult(True, request.provider, request.action, data)

    return IntegrationResult(False, request.provider, request.action, {}, "unsupported_amazon_hackathon_action")


def register_amazon_hackathon_provider(register) -> None:
    for action in (
        "ring_list_devices",
        "ring_status",
        "ring_live_list_devices",
        "ring_live_status",
        "ring_inject_event",
        "alexa_simulate_utterance",
        "mcp_initialize",
    ):
        register("amazon_hackathon", action, run_amazon_hackathon_action)
