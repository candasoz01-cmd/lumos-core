from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from amazon_hackathon.alexa_plus_sim import (
    ALEXA_PLUS_MCP_PROTOCOL_VERSION,
    AlexaPlusSimulator,
    handle_mcp_jsonrpc,
    serve_mcp,
)
from amazon_hackathon.ring_simulator import (
    AMAZON_VISION_API_ORIGIN,
    JSONAPI_DEVICE_TYPE,
    JSONAPI_DOCUMENT_MEMBERS,
    JSONAPI_STATUS_TYPE,
    RingSandboxSimulator,
    public_device_id,
    public_status_id,
)
from integrations.models import IntegrationRequest
from integrations.registry import register_default_integrations


def _assert_list_status_envelope(payload: dict, *, path: str, has_error: bool) -> dict:
    assert payload["execution_live"] is False
    assert payload["origin_not_contacted"] == AMAZON_VISION_API_ORIGIN
    assert payload["path"] == path
    assert "data" not in payload
    assert "errors" not in payload
    assert "meta" not in payload
    document = payload["document"]
    assert set(document) <= JSONAPI_DOCUMENT_MEMBERS
    assert "time" in document["meta"]
    assert document["meta"]["time"].endswith("Z")
    if has_error:
        assert payload["error"] == "device_not_found"
    else:
        assert "error" not in payload
    return document


def test_ring_sandbox_lists_synthetic_devices_without_live_origin():
    sandbox = RingSandboxSimulator()
    listed = sandbox.list_devices()
    document = _assert_list_status_envelope(listed, path="/v1/devices", has_error=False)

    ids = {item["id"] for item in document["data"]}
    assert ids == {
        public_device_id("sim-doorbell-front"),
        public_device_id("sim-camera-driveway"),
    }
    for item in document["data"]:
        assert item["type"] == JSONAPI_DEVICE_TYPE
        assert "name" in item["attributes"]
        assert set(item["relationships"]) == {
            "status",
            "capabilities",
            "configurations",
            "location",
        }
        related = item["relationships"]["status"]["links"]["related"]
        assert related == f"/v1/devices/{item['id']}/status"
        assert "online" not in item
        assert "locked" not in item.get("attributes", {})
    assert "urlopen" not in Path("src/amazon_hackathon/ring_simulator.py").read_text(encoding="utf-8")


def test_ring_status_is_jsonapi_device_status_without_lock_field():
    sandbox = RingSandboxSimulator()
    by_short = sandbox.device_status("sim-doorbell-front")
    by_public = sandbox.device_status(public_device_id("sim-doorbell-front"))
    missing = sandbox.device_status("no-such-device")
    public_id = public_device_id("sim-doorbell-front")

    for payload in (by_short, by_public):
        document = _assert_list_status_envelope(
            payload, path=f"/v1/devices/{public_id}/status", has_error=False
        )
        assert document["data"]["type"] == JSONAPI_STATUS_TYPE
        assert document["data"]["id"] == public_status_id("sim-doorbell-front")
        assert document["data"]["attributes"] == {"online": True}
        assert "locked" not in document["data"]
        assert "locked" not in document["data"]["attributes"]
    missing_doc = _assert_list_status_envelope(
        missing,
        path=f"/v1/devices/{public_device_id('no-such-device')}/status",
        has_error=True,
    )
    assert missing_doc["errors"] == [
        {
            "status": "404",
            "title": "Not Found",
            "detail": "The requested resource could not be found",
        }
    ]
    assert "data" not in missing_doc


def test_ring_unlock_is_gated_and_never_actuates():
    sandbox = RingSandboxSimulator()
    denied = sandbox.request_unlock("sim-doorbell-front", approved=False)
    approved = sandbox.request_unlock("sim-doorbell-front", approved=True)

    assert denied["error"] == "approval_required"
    assert denied["execution_started"] is False
    assert approved["error"] == "sandbox_unlock_not_executed"
    assert sandbox._devices["sim-doorbell-front"]["attributes"]["locked"] is True


def test_mcp_initialize_uses_required_protocol_version():
    payload = handle_mcp_jsonrpc({"jsonrpc": "2.0", "id": 7, "method": "initialize", "params": {}})

    listed = handle_mcp_jsonrpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

    assert payload["result"]["protocolVersion"] == ALEXA_PLUS_MCP_PROTOCOL_VERSION == "2025-11-25"
    names = {tool["name"] for tool in listed["result"]["tools"]}
    assert names == {"front_door_status", "latest_visitor_event", "request_door_unlock"}


def test_alexa_utterance_calls_ring_sandbox_at_runtime():
    ring = RingSandboxSimulator()
    ring.inject_event("sim-doorbell-front", "doorbell", "visitor at front door")
    alexa = AlexaPlusSimulator(ring=ring)

    result = alexa.simulate_utterance("Is someone at the door?")
    event = json.loads(result["mcp"]["result"]["content"][0]["text"])

    assert result["path"] == "latest_visitor_event"
    assert result["execution_live"] is False
    assert event["event"]["kind"] == "doorbell"


def test_streamable_http_mcp_initialize_roundtrip():
    server = serve_mcp("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        request = Request(
            f"http://127.0.0.1:{port}/mcp",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["result"]["protocolVersion"] == "2025-11-25"
        assert payload["result"]["serverInfo"]["name"] == "lumos-alexa-plus-sim"
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_registry_runtime_hook_calls_simulators():
    reg = register_default_integrations()
    listed = reg.run(IntegrationRequest(provider="amazon_hackathon", action="ring_list_devices", payload={}))
    init = reg.run(IntegrationRequest(provider="amazon_hackathon", action="mcp_initialize", payload={}))
    spoken = reg.run(
        IntegrationRequest(
            provider="amazon_hackathon",
            action="alexa_simulate_utterance",
            payload={"utterance": "front door status"},
        )
    )

    assert listed.ok is True
    assert listed.data["execution_live"] is False
    assert init.data["result"]["protocolVersion"] == "2025-11-25"
    assert spoken.ok is True
    assert spoken.data["execution_live"] is False


def test_provider_ring_status_ok_and_error_follow_envelope_error_key():
    reg = register_default_integrations()
    hit = reg.run(
        IntegrationRequest(
            provider="amazon_hackathon",
            action="ring_status",
            payload={"device_id": "sim-doorbell-front"},
        )
    )
    missing = reg.run(
        IntegrationRequest(
            provider="amazon_hackathon",
            action="ring_status",
            payload={"device_id": "no-such-device"},
        )
    )

    assert hit.ok is True
    assert hit.error == ""
    assert "error" not in hit.data
    assert hit.data["document"]["data"]["type"] == JSONAPI_STATUS_TYPE
    assert missing.ok is False
    assert missing.error == "device_not_found"
    assert missing.data["error"] == "device_not_found"
    assert "data" not in missing.data["document"]
    assert missing.data["document"]["errors"][0]["status"] == "404"
