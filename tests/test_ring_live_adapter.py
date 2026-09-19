from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from amazon_hackathon.ring_live_adapter import (
    RING_TOKEN_ENV,
    RingLiveAdapter,
    token_from_env,
)
from amazon_hackathon.ring_simulator import AMAZON_VISION_API_ORIGIN
from integrations.models import IntegrationRequest
from integrations.registry import register_default_integrations

FAKE_TOKEN = "eyJfake.playground.token"


class RecordingTransport:
    def __init__(self, status: int, body: bytes):
        self.status = status
        self.body = body
        self.calls: list[tuple[str, dict[str, str], float]] = []

    def __call__(self, url: str, headers: dict[str, str], timeout: float):
        self.calls.append((url, headers, timeout))
        return self.status, self.body


def test_missing_token_fails_closed_without_touching_transport():
    transport = RecordingTransport(200, b"{}")
    adapter = RingLiveAdapter(token=None, transport=transport)

    listed = adapter.list_devices()
    status = adapter.device_status("sim-doorbell-front")

    for payload in (listed, status):
        assert payload["error"] == "ring_token_missing"
        assert payload["execution_live"] is False
        assert payload["origin_not_contacted"] == AMAZON_VISION_API_ORIGIN
        assert "origin_contacted" not in payload
        assert payload["document"] == {}
    assert transport.calls == []


def test_live_list_devices_passes_document_through_and_marks_live():
    body = json.dumps(
        {
            "meta": {"time": "2026-09-19T00:00:00Z"},
            "data": [
                {
                    "type": "devices",
                    "id": "ava1.ring.device.abc123",
                    "attributes": {"name": "Front Door"},
                }
            ],
        }
    ).encode("utf-8")
    transport = RecordingTransport(200, body)
    adapter = RingLiveAdapter(token=FAKE_TOKEN, transport=transport)

    listed = adapter.list_devices()

    assert "error" not in listed
    assert listed["execution_live"] is True
    assert listed["origin_contacted"] == AMAZON_VISION_API_ORIGIN
    assert "origin_not_contacted" not in listed
    assert listed["http_status"] == 200
    assert listed["path"] == "/v1/devices"
    assert listed["document"]["data"][0]["id"] == "ava1.ring.device.abc123"
    (url, headers, timeout) = transport.calls[0]
    assert url == f"{AMAZON_VISION_API_ORIGIN}/v1/devices"
    assert headers == {"Authorization": f"Bearer {FAKE_TOKEN}"}
    assert timeout == 10.0


def test_live_status_normalizes_device_id_to_public_form():
    transport = RecordingTransport(200, b'{"data": {"attributes": {"online": true}}}')
    adapter = RingLiveAdapter(token=FAKE_TOKEN, transport=transport)

    result = adapter.device_status("abc123")

    assert result["path"] == "/v1/devices/ava1.ring.device.abc123/status"
    assert transport.calls[0][0].endswith("/v1/devices/ava1.ring.device.abc123/status")
    assert result["document"]["data"]["attributes"]["online"] is True


def test_expired_token_maps_to_single_actionable_error():
    transport = RecordingTransport(401, b'{"errors": [{"status": "401"}]}')
    adapter = RingLiveAdapter(token=FAKE_TOKEN, transport=transport)

    result = adapter.list_devices()

    assert result["error"] == "token_expired_or_invalid"
    assert result["http_status"] == 401
    assert result["document"]["errors"][0]["status"] == "401"


def test_missing_device_maps_to_device_not_found():
    transport = RecordingTransport(404, b'{"errors": [{"status": "404"}]}')
    adapter = RingLiveAdapter(token=FAKE_TOKEN, transport=transport)

    result = adapter.device_status("no-such-device")

    assert result["error"] == "device_not_found"
    assert result["http_status"] == 404


def test_network_failure_returns_envelope_instead_of_raising():
    def broken_transport(url, headers, timeout):
        raise OSError("connection refused")

    adapter = RingLiveAdapter(token=FAKE_TOKEN, transport=broken_transport)

    result = adapter.list_devices()

    assert result["error"] == "network_error"
    assert result["document"] == {}


def test_non_json_success_body_is_reported_not_trusted():
    transport = RecordingTransport(200, b"<html>gateway</html>")
    adapter = RingLiveAdapter(token=FAKE_TOKEN, transport=transport)

    result = adapter.list_devices()

    assert result["error"] == "invalid_json"
    assert result["document"] == {}


def test_token_never_leaks_into_envelopes():
    for transport in (
        RecordingTransport(200, b'{"data": []}'),
        RecordingTransport(401, b"{}"),
        RecordingTransport(500, b"boom"),
    ):
        adapter = RingLiveAdapter(token=FAKE_TOKEN, transport=transport)
        serialized = json.dumps(adapter.list_devices())
        assert FAKE_TOKEN not in serialized


def test_token_from_env_treats_blank_as_missing(monkeypatch):
    monkeypatch.delenv(RING_TOKEN_ENV, raising=False)
    assert token_from_env() is None
    monkeypatch.setenv(RING_TOKEN_ENV, "   ")
    assert token_from_env() is None
    monkeypatch.setenv(RING_TOKEN_ENV, FAKE_TOKEN)
    assert token_from_env() == FAKE_TOKEN


def test_registry_live_actions_fail_closed_without_env_token(monkeypatch):
    monkeypatch.delenv(RING_TOKEN_ENV, raising=False)
    reg = register_default_integrations()

    listed = reg.run(
        IntegrationRequest(provider="amazon_hackathon", action="ring_live_list_devices", payload={})
    )
    status = reg.run(
        IntegrationRequest(
            provider="amazon_hackathon",
            action="ring_live_status",
            payload={"device_id": "abc123"},
        )
    )

    for result in (listed, status):
        assert result.ok is False
        assert result.error == "ring_token_missing"
        assert result.data["execution_live"] is False
