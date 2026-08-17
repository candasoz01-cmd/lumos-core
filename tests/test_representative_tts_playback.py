"""Chunked TTS + barge-in-safe half-duplex — no network, no wall-clock sleep."""

from __future__ import annotations

import threading

from representative.audio import HalfDuplexGate
from representative.tts_playback import (
    ChunkedTtsPlayer,
    estimate_speech_seconds,
    split_tts_chunks,
)


def test_split_prefers_sentences_then_packs():
    text = "Hello there. How are you today? Fine."
    chunks = split_tts_chunks(text, max_chars=20)
    assert chunks[0] == "Hello there."
    assert chunks[1] == "How are you today?"
    packed = split_tts_chunks(text, max_chars=80)
    assert packed == [text]


def test_split_wraps_long_sentence():
    words = " ".join(f"word{i}" for i in range(40))
    chunks = split_tts_chunks(words, max_chars=40)
    assert len(chunks) > 1
    assert all(len(c) <= 40 for c in chunks)
    assert " ".join(chunks).replace("  ", " ") == words


class _Synth:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.block_rest = threading.Event()
        self.started_rest = threading.Event()

    def __call__(self, text: str, _lang: str) -> bytes:
        self.calls.append(text)
        if len(self.calls) > 1:
            self.started_rest.set()
            self.block_rest.wait(timeout=2.0)
        return text.encode()


def test_first_audio_returns_before_remaining_chunks():
    gate = HalfDuplexGate()
    holds: list[float] = []
    delivered: list[str] = []
    synth = _Synth()

    def sleeper(seconds: float) -> None:
        holds.append(seconds)

    def deliver(_payload: bytes, text: str, _lang: str) -> None:
        delivered.append(text)

    player = ChunkedTtsPlayer(
        synthesize=synth,
        deliver=deliver,
        gate=gate,
        sleeper=sleeper,
        hold_after_deliver=True,
        max_chars=40,
    )
    text = (
        "Alpha sentence ends here. Bravo sentence is the remainder. "
        "Charlie sentence would have blocked listening."
    )
    playback = player.speak(text, "en")
    first = split_tts_chunks(text, max_chars=40)[0]
    assert playback.chunks_planned >= 2
    assert playback.chunks_started == 1
    assert delivered == [first]
    assert synth.calls == [first]
    assert holds == [estimate_speech_seconds(first)]
    assert holds[0] < estimate_speech_seconds(text)
    assert gate.listening is True  # speak() returned; remaining not holding yet
    synth.block_rest.set()
    player.wait_idle(timeout=2.0)
    assert len(delivered) == playback.chunks_planned


def test_barge_in_drops_queued_chunks_without_sleeping_the_test():
    gate = HalfDuplexGate()
    delivered: list[str] = []
    synth = _Synth()

    player = ChunkedTtsPlayer(
        synthesize=synth,
        deliver=lambda _p, text, _l: delivered.append(text),
        gate=gate,
        sleeper=lambda _s: None,
        hold_after_deliver=True,
        max_chars=40,
    )
    text = "Keep the first clip. Drop this second clip. Drop the third clip too."
    player.speak(text, "en")
    assert synth.started_rest.wait(timeout=2.0)
    cancelled = player.barge_in(join=False)
    synth.block_rest.set()
    player.wait_idle(timeout=2.0)
    first = split_tts_chunks(text, max_chars=40)[0]
    assert delivered[0] == first
    assert cancelled >= 1 or len(delivered) < 3
    assert first in delivered
    # Remaining queue did not all play after barge-in.
    assert len(delivered) < 3


def test_gate_hold_is_per_chunk_not_full_paragraph():
    paragraph = (
        "One short clip. Another short clip follows after. "
        "A third clip would make a long consecutive hold."
    )
    chunks = split_tts_chunks(paragraph, max_chars=40)
    assert len(chunks) >= 2
    per_first = estimate_speech_seconds(chunks[0])
    full = estimate_speech_seconds(paragraph)
    assert per_first * 1.5 < full
