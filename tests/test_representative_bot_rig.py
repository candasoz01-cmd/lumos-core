"""bot_rig saf mantık testleri — ws/ağ olmadan (canlı doğrulama prova 2'de)."""

from __future__ import annotations

import threading

import pytest

from representative.bot_rig import (
    DisclosureInputGuard,
    build_realtime_endpoint,
    extract_audio_b64,
    start_verified_tunnel,
)
from representative.tts_playback import estimate_speech_seconds


def test_extract_audio_accepts_known_shapes_and_drops_unknown():
    assert extract_audio_b64({"event": "audio_mixed_raw.data", "data": {"data": {"buffer": "QUJD"}}}) == "QUJD"
    assert extract_audio_b64({"event": "audio_mixed_raw.data", "data": {"buffer": "QUJD"}}) == "QUJD"
    assert extract_audio_b64({"event": "transcript.data", "data": {}}) is None  # başka olay
    assert extract_audio_b64({"data": {"buffer": "QUJD"}}) is None  # olay adı yok
    assert extract_audio_b64({"event": "audio_mixed_raw.data", "data": {"data": {"buffer": ""}}}) is None


def test_realtime_endpoint_requires_wss():
    ep = build_realtime_endpoint("wss://example.ngrok-free.dev")
    assert ep["events"] == ["audio_mixed_raw.data"]
    with pytest.raises(ValueError):
        build_realtime_endpoint("ws://example.dev")  # şifresiz kanal fail-closed
    with pytest.raises(ValueError):
        build_realtime_endpoint("https://example.dev")


def test_speech_duration_estimate_scales_with_text():
    short = estimate_speech_seconds("Evet.")
    long = estimate_speech_seconds("Bu oldukça uzun bir cümledir ve klip süresi artmalıdır.")
    assert 0.3 < short < long < 10.0
    paragraph = (
        "First sentence stays short. Second sentence is also a clip. "
        "Third sentence would have held the gate for the whole paragraph."
    )
    from representative.tts_playback import split_tts_chunks

    first = split_tts_chunks(paragraph)[0]
    assert estimate_speech_seconds(first) < estimate_speech_seconds(paragraph)


def test_resample_ratio():
    numpy = pytest.importorskip("numpy")
    from representative.bot_rig import resample_16k_to_24k

    pcm16k = numpy.arange(160, dtype=numpy.int16).tobytes()  # 10 ms @16k
    out = resample_16k_to_24k(pcm16k)
    assert len(out) == 240 * 2  # 10 ms @24k
    assert resample_16k_to_24k(b"") == b""


def test_terminal_status_detection():
    from representative.bot_rig import is_terminal_status

    for code in ("call_ended", "done", "fatal"):
        assert is_terminal_status(code) is True
    for code in ("joining_call", "in_waiting_room", "in_call_recording", None):
        assert is_terminal_status(code) is False


def test_disclosure_guard_drops_bot_echo_then_opens():
    guard = DisclosureInputGuard(duration_s=5.0)

    assert guard.allows_audio(99.0) is False
    guard.mark_connected(100.0)
    assert guard.allows_audio(104.99) is False
    assert guard.allows_audio(105.0) is True

    guard.mark_connected(200.0)  # reconnect/message does not extend the first guard
    assert guard.allows_audio(200.0) is True


def test_verified_tunnel_rotates_failed_address_before_bot_creation(monkeypatch):
    class Proc:
        def __init__(self):
            self.terminated = False

        def terminate(self):
            self.terminated = True

    first = Proc()
    second = Proc()
    starts = iter(((first, "wss://bad.example"), (second, "wss://good.example")))
    verified = []

    monkeypatch.setattr("representative.bot_rig.start_cloudflared", lambda _port: next(starts))
    monkeypatch.setattr(
        "representative.bot_rig.start_ngrok",
        lambda _port: pytest.fail("ngrok fallback was not expected"),
    )

    def verify(url, _event):
        verified.append(url)
        if "bad" in url:
            raise RuntimeError("dns")

    monkeypatch.setattr("representative.bot_rig.verify_tunnel", verify)

    proc, url = start_verified_tunnel(8765, threading.Event(), attempts=2)

    assert first.terminated is True
    assert proc is second
    assert url == "wss://good.example"
    assert verified == ["wss://bad.example", "wss://good.example"]
