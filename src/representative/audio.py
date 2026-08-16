"""Microphone-side primitives: utterance endpointing + half-duplex echo guard.

Pure python (no numpy/sounddevice imports here) so CI can test the logic with
synthetic PCM frames. Hardware capture lives in local_rig's --audio mode.

Echo/feedback design (slice test T7): consecutive interpretation is naturally
half-duplex — while our TTS speaks, incoming mic frames are dropped by
HalfDuplexGate, so the speaker→mic→translation feedback loop can never form.
"""

from __future__ import annotations

import math
from array import array
from dataclasses import dataclass


def frame_rms(frame: bytes) -> float:
    """RMS of a little-endian int16 mono PCM frame."""
    samples = array("h")
    samples.frombytes(frame)
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


class HalfDuplexGate:
    """Open = listening; closed while our own TTS is speaking."""

    def __init__(self) -> None:
        self._speaking_depth = 0

    @property
    def listening(self) -> bool:
        return self._speaking_depth == 0

    def __enter__(self) -> "HalfDuplexGate":
        self._speaking_depth += 1
        return self

    def __exit__(self, *exc: object) -> None:
        self._speaking_depth = max(0, self._speaking_depth - 1)


@dataclass(frozen=True)
class SegmenterConfig:
    sample_rate: int = 16000
    frame_ms: int = 30
    rms_threshold: float = 500.0  # int16 scale; calibrated on-device in rig
    end_silence_ms: int = 700  # pause length that ends an utterance
    min_utterance_ms: int = 300  # shorter bursts are discarded as noise


class UtteranceSegmenter:
    """Energy-based endpointing: feed PCM frames, get finished utterances.

    feed() returns the completed utterance's PCM bytes when a long-enough
    speech run is followed by end_silence_ms of quiet, else None. Frames
    arriving while the gate is closed are dropped entirely (T7).
    """

    def __init__(self, config: SegmenterConfig, gate: HalfDuplexGate | None = None) -> None:
        self._config = config
        self._gate = gate
        self._speech: bytearray = bytearray()
        self._silence_ms = 0

    @property
    def config(self) -> SegmenterConfig:
        return self._config

    def _reset(self) -> None:
        self._speech = bytearray()
        self._silence_ms = 0

    def feed(self, frame: bytes) -> bytes | None:
        cfg = self._config
        if self._gate is not None and not self._gate.listening:
            self._reset()
            return None
        if frame_rms(frame) >= cfg.rms_threshold:
            self._speech.extend(frame)
            self._silence_ms = 0
            return None
        if not self._speech:
            return None
        self._silence_ms += cfg.frame_ms
        if self._silence_ms < cfg.end_silence_ms:
            self._speech.extend(frame)  # keep short intra-speech pauses
            return None
        utterance = bytes(self._speech)
        self._reset()
        speech_ms = (len(utterance) / 2 / cfg.sample_rate) * 1000.0
        if speech_ms < cfg.min_utterance_ms:
            return None
        return utterance
