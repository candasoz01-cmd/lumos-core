"""bot_rig saf mantık testleri — ws/ağ olmadan (canlı doğrulama prova 2'de)."""

from __future__ import annotations

import pytest

from representative.bot_rig import (
    build_realtime_endpoint,
    estimate_speech_seconds,
    extract_audio_b64,
)


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
    assert 1.0 < short < long < 10.0


def test_resample_ratio():
    numpy = pytest.importorskip("numpy")
    from representative.bot_rig import resample_16k_to_24k

    pcm16k = numpy.arange(160, dtype=numpy.int16).tobytes()  # 10 ms @16k
    out = resample_16k_to_24k(pcm16k)
    assert len(out) == 240 * 2  # 10 ms @24k
    assert resample_16k_to_24k(b"") == b""
