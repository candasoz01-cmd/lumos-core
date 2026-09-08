"""Loopback-only controlled bridge client — token LAN'a çıkmasın."""

from __future__ import annotations

from kando.controlled_bridge_client import call_controlled


def test_non_loopback_host_does_not_send_request(monkeypatch) -> None:
    monkeypatch.setenv("KANDO_BRIDGE_HOST", "8.8.8.8")
    monkeypatch.setenv("KANDO_BRIDGE_SECRET", "should-not-leave")
    out = call_controlled({"permission": "file_rw", "command": "ping"})
    assert out["ok"] is False
    assert out["error"] == "bridge_host_not_loopback"


def test_loopback_url_is_accepted_shape(monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_CONTROLLED_BRIDGE_URL", "http://127.0.0.1:9")
    monkeypatch.delenv("KANDO_BRIDGE_SECRET", raising=False)
    out = call_controlled({"permission": "file_rw", "command": "ping"}, timeout=0.2)
    assert out["ok"] is False
    assert out["error"] != "bridge_host_not_loopback"
