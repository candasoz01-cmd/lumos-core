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


def test_speaking_state_starts_after_upload_not_before() -> None:
    """Idle timer yükleme süresini saymamalı.

    speaking_for upload'dan ÖNCE çağrılırsa sayaç ağ süresi boyunca işler ve
    Meet hâlâ sesi çalarken avatar idle'a döner.
    """
    import inspect

    from representative import bot_rig

    src = inspect.getsource(bot_rig.RecallSpeaker._deliver)
    speak_at = src.index("self._ingress.speak(")
    avatar_at = src.index("self._avatar.speaking_for(")
    assert speak_at < avatar_at, "speaking_for, speak() çağrısından sonra gelmeli"


def test_incomplete_assembled_turn_does_not_barge_in_or_speak():
    from collections import deque
    from types import SimpleNamespace

    from representative.bot_rig import speak_assembled_turns
    from representative.turns import AssembledTurn

    class _Pipe:
        def __init__(self) -> None:
            self.interrupts = 0
            self.processed: list[str] = []
            self.unspoken: list[tuple[str, str]] = []

        def interrupt_playback(self) -> int:
            self.interrupts += 1
            return 0

        def record_unspoken(self, text, **kw):
            self.unspoken.append((text, kw.get("flag_reason")))
            return SimpleNamespace(delivered=False)

        def process(self, utterance):
            self.processed.append(utterance.text)
            return SimpleNamespace(
                delivered=True,
                translated_text="ok",
                latency_ms=1.0,
                stt_ms=0.0,
                translate_ms=0.0,
                tts_to_first_audio_ms=0.0,
            )

    class _Router:
        def route(self, text: str):
            return SimpleNamespace(
                direction=SimpleNamespace(source_lang="tr", target_lang="en"),
                reason="detected",
                detected="tr",
            )

    class _Suppressor:
        def should_drop(self, _text: str, _now: float) -> bool:
            return False

    pipe = _Pipe()
    spoken = speak_assembled_turns(
        [
            AssembledTurn(
                text="We should go and",
                speech_end_ts=1.0,
                speakable=False,
                reason="incomplete_drop",
            )
        ],
        pipeline=pipe,
        router=_Router(),
        suppressor=_Suppressor(),
        recent=deque(),
        now=1.0,
    )
    assert spoken == 0
    assert pipe.interrupts == 0
    assert pipe.processed == []
    # Kurucu kararı (2026-08-24): davranış aynı (ses yok), ama artık iz bırakır
    # — aksi hâlde turn tutma davranışı prova dosyasından ölçülemiyor.
    assert pipe.unspoken == [("We should go and", "held_partial_incomplete_drop")]


def test_complete_assembled_turn_speaks_once_with_barge_in():
    from collections import deque
    from types import SimpleNamespace

    from representative.bot_rig import speak_assembled_turns
    from representative.turns import AssembledTurn

    class _Pipe:
        def __init__(self) -> None:
            self.interrupts = 0
            self.processed: list[str] = []
            self.unspoken: list[tuple[str, str]] = []

        def interrupt_playback(self) -> int:
            self.interrupts += 1
            return 0

        def record_unspoken(self, text, **kw):
            self.unspoken.append((text, kw.get("flag_reason")))
            return SimpleNamespace(delivered=False)

        def process(self, utterance):
            self.processed.append(utterance.text)
            return SimpleNamespace(
                delivered=True,
                translated_text="See you tomorrow.",
                latency_ms=10.0,
                stt_ms=1.0,
                translate_ms=2.0,
                tts_to_first_audio_ms=3.0,
            )

    class _Router:
        def route(self, text: str):
            return SimpleNamespace(
                direction=SimpleNamespace(source_lang="tr", target_lang="en"),
                reason="detected",
                detected="tr",
            )

    class _Suppressor:
        def should_drop(self, _text: str, _now: float) -> bool:
            return False

    pipe = _Pipe()
    spoken = speak_assembled_turns(
        [
            AssembledTurn(
                text="Yarın görüşürüz.",
                speech_end_ts=2.0,
                speakable=True,
                reason="complete",
            )
        ],
        pipeline=pipe,
        router=_Router(),
        suppressor=_Suppressor(),
        recent=deque(),
        now=2.0,
    )
    assert spoken == 1
    assert pipe.interrupts == 1
    assert pipe.processed == ["Yarın görüşürüz."]


def test_meet_main_wires_consecutive_vad_and_single_voice():
    import inspect

    from representative import bot_rig
    from representative.turns import MEET_VAD_SILENCE_MS, SINGLE_OUTPUT_VOICE

    src = inspect.getsource(bot_rig.main)
    assert "TurnAssembler" in src
    assert "vad_silence_ms=args.vad_silence_ms" in src
    assert MEET_VAD_SILENCE_MS >= 1000
    synth = inspect.getsource(bot_rig.RecallSpeaker._synthesize)
    assert "SINGLE_OUTPUT_VOICE" in synth
    assert SINGLE_OUTPUT_VOICE == "onyx"
