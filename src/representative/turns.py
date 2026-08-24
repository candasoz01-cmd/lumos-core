"""Consecutive single-voice turn assembly for Meet interpretation.

Live overlapping speech plus a short VAD (600 ms) plus chunked first-audio
made the avatar answer mid-sentence. Parliamentary consecutive interpretation
does the opposite: separate speakers in the back, wait for a finished thought,
translate it, then play **one** shared voice.

This module is the output policy. It does not do speaker diarization (that
stays mixed-audio STT for now). It holds VAD fragments until the text looks
like a finished sentence, then yields one speakable turn. Incomplete fragments
are not spoken.

Meet default VAD is higher than the local-rig 800 ms: slightly late and clean
beats 0.5 s early and interruptive (user decision 2026-08-24).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Server VAD silence before a fragment is even offered. 600 ms split
# overlapping meeting speech; 800 ms was already the local-rig floor.
MEET_VAD_SILENCE_MS = 1100
# Merge two VAD fragments that are really one sentence split at a pause.
TURN_MERGE_GAP_MS = 700
# Extra hold after an unpunctuated fragment, on top of VAD silence.
TURN_EXTRA_HOLD_MS = 400
# Single TTS timbre for every speaker's interpretation.
SINGLE_OUTPUT_VOICE = "onyx"

_TERMINAL_RE = re.compile(r"[.!?…][\"'»”’)]*$")
_TRAILING_CONJUNCTIONS = frozenset(
    {
        "and",
        "or",
        "but",
        "because",
        "that",
        "if",
        "when",
        "so",
        "the",
        "a",
        "an",
        "ve",
        "veya",
        "ama",
        "fakat",
        "çünkü",
        "ki",
        "eğer",
        "ile",
        "bir",
        "da",
        "de",
    }
)


@dataclass(frozen=True)
class AssembledTurn:
    """One consecutive-interpreter output unit — speak only when speakable."""

    text: str
    speech_end_ts: float
    speakable: bool
    reason: str  # complete | hold_timeout | incomplete_drop


def looks_complete(text: str) -> bool:
    """True when the fragment already looks like a finished sentence."""
    stripped = text.strip()
    if not stripped:
        return False
    return _TERMINAL_RE.search(stripped) is not None


def looks_unfinished(text: str) -> bool:
    """True when speaking now would almost certainly cut a thought short."""
    stripped = text.strip()
    if not stripped or looks_complete(stripped):
        return False
    if stripped.endswith((",", ";", ":")):
        return True
    last = stripped.rstrip(" ,;:").split()[-1].casefold()
    if last in _TRAILING_CONJUNCTIONS:
        return True
    return len(stripped.split()) < 4


class TurnAssembler:
    """Holds STT fragments until a meaningful sentence is ready to speak.

    Clock is injected via `now` on every call so tests stay deterministic.
    """

    def __init__(
        self,
        merge_gap_ms: int = TURN_MERGE_GAP_MS,
        extra_hold_ms: int = TURN_EXTRA_HOLD_MS,
    ) -> None:
        self._merge_gap_s = merge_gap_ms / 1000.0
        self._extra_hold_s = extra_hold_ms / 1000.0
        self._parts: list[str] = []
        self._speech_end_ts = 0.0
        self._last_at = 0.0

    def push(self, text: str, speech_end_ts: float, now: float) -> list[AssembledTurn]:
        stripped = text.strip()
        if not stripped:
            return []
        out: list[AssembledTurn] = []
        if self._parts and not self._is_continuation(speech_end_ts):
            flushed = self._flush(reason="gap")
            if flushed is not None:
                out.append(flushed)
        if self._parts:
            self._parts.append(stripped)
        else:
            self._parts = [stripped]
        self._speech_end_ts = speech_end_ts
        self._last_at = now
        if looks_complete(self._joined()):
            emitted = self._emit(reason="complete")
            if emitted is not None:
                out.append(emitted)
        return out

    def poll(self, now: float) -> list[AssembledTurn]:
        if not self._parts:
            return []
        if (now - self._last_at) < self._extra_hold_s:
            return []
        flushed = self._flush(reason="hold")
        return [flushed] if flushed is not None else []

    def _is_continuation(self, speech_end_ts: float) -> bool:
        return (speech_end_ts - self._speech_end_ts) <= self._merge_gap_s

    def _joined(self) -> str:
        return " ".join(self._parts)

    def _flush(self, reason: str) -> AssembledTurn | None:
        text = self._joined().strip()
        if not text:
            self._reset()
            return None
        if looks_complete(text):
            return self._emit(reason="complete")
        if not looks_unfinished(text) and len(text.split()) >= 4:
            return self._emit(reason="hold_timeout" if reason == "hold" else "gap_timeout")
        return self._emit(reason="incomplete_drop", speakable=False)

    def _emit(self, reason: str, speakable: bool | None = None) -> AssembledTurn | None:
        text = self._joined().strip()
        speech_end = self._speech_end_ts
        self._reset()
        if not text:
            return None
        if speakable is None:
            speakable = True
        return AssembledTurn(
            text=text,
            speech_end_ts=speech_end,
            speakable=speakable,
            reason=reason,
        )

    def _reset(self) -> None:
        self._parts = []
        self._speech_end_ts = 0.0
        self._last_at = 0.0
