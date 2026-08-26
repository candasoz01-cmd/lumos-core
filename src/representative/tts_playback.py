"""Chunked TTS playback — first-audio early, barge-in-safe half-duplex.

Recall `output_audio` takes a whole MP3 clip (no PCM stream). Consecutive
interpretation therefore cannot true-stream into Meet; the product lever is
short sentence chunks: synthesize+send the first clip, return first-audio,
play remaining clips in the background, and drop the queue on barge-in.

Half-duplex: the gate stays closed only for the clip currently going out
(plus a short echo tail), not for the estimated duration of the full
paragraph. That was the 2026-08-17 bottleneck: `0.075 * len(full) + 1.0`
held the gate through the entire translation and dropped inbound speech.
"""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from representative.audio import HalfDuplexGate

# ~13 chars/s speech; echo tail covers Meet/speaker→mic decay, not a full
# extra second of deafness on every clip.
CHARS_PER_SEC = 13.3
HOLD_S_PER_CHAR = 1.0 / CHARS_PER_SEC
ECHO_TAIL_S = 0.25
MIN_HOLD_S = 0.35
MAX_CHUNK_CHARS = 90

SynthesizeFn = Callable[[str, str], bytes]
DeliverFn = Callable[[bytes, str, str], None]
ClockFn = Callable[[], float]
SleepFn = Callable[[float], None]


def estimate_speech_seconds(text: str) -> float:
    """Gate hold for ONE clip — not the leftover paragraph."""
    return max(MIN_HOLD_S, HOLD_S_PER_CHAR * len(text) + ECHO_TAIL_S)


def split_tts_chunks(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Sentence-first split, then pack/hard-wrap to max_chars.

    Empty input yields a single empty chunk so callers can no-op uniformly.
    """
    stripped = text.strip()
    if not stripped:
        return [""]
    parts = [
        p.strip()
        for p in re.split(r"(?<=[.!?…])\s+", stripped)
        if p.strip()
    ]
    if len(parts) == 1 and len(parts[0]) <= max_chars:
        return parts
    packed: list[str] = []
    buf = ""
    for part in parts:
        if not buf:
            buf = part
        elif len(buf) + 1 + len(part) <= max_chars:
            buf = f"{buf} {part}"
        else:
            packed.extend(_wrap_long(buf, max_chars))
            buf = part
    if buf:
        packed.extend(_wrap_long(buf, max_chars))
    return packed or [stripped]


def _wrap_long(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    out: list[str] = []
    buf = ""
    for word in words:
        candidate = word if not buf else f"{buf} {word}"
        if len(candidate) <= max_chars:
            buf = candidate
            continue
        if buf:
            out.append(buf)
        if len(word) <= max_chars:
            buf = word
        else:
            for i in range(0, len(word), max_chars):
                piece = word[i : i + max_chars]
                if len(piece) == max_chars:
                    out.append(piece)
                else:
                    buf = piece
    if buf:
        out.append(buf)
    return out


def _span_ms(start: float | None, end: float | None) -> float:
    """İki damga arası ms. Damgalardan biri yoksa 0.0 — uydurma yok."""
    if start is None or end is None:
        return 0.0
    return max(0.0, (end - start) * 1000.0)


@dataclass(frozen=True)
class TtsPlayback:
    tts_start_ts: float
    first_audio_ts: float
    chunks_planned: int
    chunks_started: int
    # Alt-aşama damgaları (2026-08-25, ÖLÇÜM işi — davranış değişmedi).
    # `first_audio_ts` tek bir toplam veriyordu; 2026-08-24 Meet provasında bu
    # toplam p50 2.49 sn ile en büyük aşamaydı ama NEDEN'i dosyadan
    # okunamıyordu. Üç damga üç ayrı işi ayırır: OpenAI TTS gidiş-dönüşü,
    # yarı-çift-yönlü kapının alınması, Recall output_audio POST'u.
    #
    # Ölçüm yoksa None kalır — 0.0 varsayılanı "ölçtük, sıfır çıktı" gibi
    # okunurdu. Damgasız oynatıcılar ve eski kayıtlar 0.0 görür.
    synth_done_ts: float | None = None
    gate_acquired_ts: float | None = None
    deliver_done_ts: float | None = None

    @property
    def synth_ms(self) -> float:
        """tts-start → `_synthesize` döndü (OpenAI TTS gidiş-dönüşü)."""
        return _span_ms(self.tts_start_ts, self.synth_done_ts)

    @property
    def gate_wait_ms(self) -> float:
        """`_synthesize` döndü → kapı alındı (yarı-çift-yönlü bekleme)."""
        return _span_ms(self.synth_done_ts, self.gate_acquired_ts)

    @property
    def deliver_ms(self) -> float:
        """kapı alındı → `_deliver` döndü (base64 + Recall output_audio POST)."""
        return _span_ms(self.gate_acquired_ts, self.deliver_done_ts)


class ChunkedTtsPlayer:
    """First chunk is blocking (defines first-audio); the rest are interruptible."""

    def __init__(
        self,
        synthesize: SynthesizeFn,
        deliver: DeliverFn,
        gate: HalfDuplexGate,
        clock: ClockFn = time.monotonic,
        sleeper: SleepFn = time.sleep,
        hold_after_deliver: bool = True,
        max_chars: int = MAX_CHUNK_CHARS,
    ) -> None:
        self._synthesize = synthesize
        self._deliver = deliver
        self._gate = gate
        self._clock = clock
        self._sleeper = sleeper
        self._hold_after_deliver = hold_after_deliver
        self._max_chars = max_chars
        self._lock = threading.Lock()
        self._pending: list[tuple[str, str]] = []
        self._cancel = threading.Event()
        self._worker: threading.Thread | None = None

    def barge_in(self, join: bool = True) -> int:
        """Drop queued clips. The clip already in Meet finishes (echo-safe)."""
        with self._lock:
            cancelled = len(self._pending)
            self._pending.clear()
        self._cancel.set()
        worker = self._worker
        if (
            join
            and worker is not None
            and worker is not threading.current_thread()
            and worker.is_alive()
        ):
            worker.join(timeout=8.0)
        return cancelled

    def wait_idle(self, timeout: float = 2.0) -> None:
        worker = self._worker
        if worker is not None:
            worker.join(timeout=timeout)

    def speak(self, text: str, lang: str) -> TtsPlayback:
        chunks = [c for c in split_tts_chunks(text, max_chars=self._max_chars) if c]
        if not chunks:
            now = self._clock()
            return TtsPlayback(now, now, 0, 0)
        self._cancel.clear()
        tts_start = self._clock()
        first = chunks[0]
        payload = self._synthesize(first, lang)
        synth_done = self._clock()
        with self._gate:
            gate_acquired = self._clock()
            self._deliver(payload, first, lang)
            deliver_done = self._clock()
            # first-audio TANIMI DEĞİŞMEDİ: teslim POST'u döndüğü an. Eskiden
            # burada ayrı bir saat okuması vardı; aynı an, tek okuma.
            first_audio = deliver_done
            if self._hold_after_deliver:
                self._sleeper(estimate_speech_seconds(first))
        rest = chunks[1:]
        if rest:
            with self._lock:
                self._pending.extend((chunk, lang) for chunk in rest)
            self._kick_worker()
        return TtsPlayback(
            tts_start_ts=tts_start,
            first_audio_ts=first_audio,
            chunks_planned=len(chunks),
            chunks_started=1,
            synth_done_ts=synth_done,
            gate_acquired_ts=gate_acquired,
            deliver_done_ts=deliver_done,
        )

    def _kick_worker(self) -> None:
        with self._lock:
            if self._worker is not None and self._worker.is_alive():
                return
            self._worker = threading.Thread(target=self._run_pending, daemon=True)
            self._worker.start()

    def _run_pending(self) -> None:
        while True:
            with self._lock:
                if not self._pending:
                    return
                text, lang = self._pending.pop(0)
            if self._cancel.is_set():
                with self._lock:
                    self._pending.clear()
                return
            payload = self._synthesize(text, lang)
            if self._cancel.is_set():
                return
            with self._gate:
                self._deliver(payload, text, lang)
                if self._hold_after_deliver:
                    self._sleeper(estimate_speech_seconds(text))
