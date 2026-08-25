"""Chunked TTS + barge-in-safe half-duplex — no network, no wall-clock sleep."""

from __future__ import annotations

import threading

import pytest

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


# --------------------------------------------------------------------------
# Alt-aşama ölçümü (2026-08-25). `tts_to_first_audio` p50 2.49 sn ile en büyük
# aşamaydı ama üç ayrı işi tek sayıda topluyordu; hangisinin baskın olduğu
# ölçülmeden hiçbir optimizasyon dürüst olamaz. Bu testler ÖLÇÜMÜ sabitler,
# davranışı değil.
# --------------------------------------------------------------------------


class _StepClock:
    """Her okumada listedeki sıradaki değeri döndürür (duvar saati yok)."""

    def __init__(self, values: list[float]) -> None:
        self._values = list(values)
        self._i = 0

    def __call__(self) -> float:
        value = self._values[min(self._i, len(self._values) - 1)]
        self._i += 1
        return value


def _single_chunk_player(clock, gate=None, deliver=None):
    return ChunkedTtsPlayer(
        synthesize=lambda text, _lang: text.encode(),
        deliver=deliver or (lambda _p, _t, _l: None),
        gate=gate or HalfDuplexGate(),
        clock=clock,
        sleeper=lambda _s: None,
        hold_after_deliver=True,
        max_chars=200,
    )


def test_substage_timestamps_split_the_first_audio_window():
    # Saat okumaları sırayla: tts_start, synth_done, gate_acquired, deliver_done
    player = _single_chunk_player(_StepClock([100.0, 100.4, 100.5, 101.2]))

    playback = player.speak("Tek parça cümle.", "tr")

    assert playback.synth_ms == pytest.approx(400.0)
    assert playback.gate_wait_ms == pytest.approx(100.0)
    assert playback.deliver_ms == pytest.approx(700.0)
    # Üçü üst aşamayı TAM böler — kırılım toplamı tutmuyorsa ölçüm yalandır.
    total_ms = (playback.first_audio_ts - playback.tts_start_ts) * 1000.0
    assert total_ms == pytest.approx(1200.0)
    assert playback.synth_ms + playback.gate_wait_ms + playback.deliver_ms == pytest.approx(
        total_ms
    )


def test_first_audio_is_still_the_moment_delivery_returned():
    """first-audio TANIMI değişmedi: `_deliver` döndüğü an, sleeper'dan ÖNCE."""
    player = _single_chunk_player(_StepClock([10.0, 10.1, 10.1, 10.9]))

    playback = player.speak("Tek parça cümle.", "tr")

    assert playback.first_audio_ts == pytest.approx(10.9)
    assert playback.deliver_done_ts == pytest.approx(playback.first_audio_ts)


def test_blocking_gate_shows_up_as_gate_wait_not_as_synthesis():
    """Hipotez testi: kapı GERÇEKTEN bloklasaydı ölçüm onu yakalar mıydı?

    Bu, kapının bloklu olduğu İDDİASI değildir — enstrümanın kapı beklemesini
    sentezden ayırt edebildiğinin kanıtıdır. Gerçek `HalfDuplexGate` bir kilit
    değil, yeniden girişli bir sayaçtır; bu yüzden gerçek kayıtta bu değerin
    ~0 çıkması ÖLÇÜM HATASI DEĞİL, kodun hâlihazırdaki şeklidir.
    """
    ticks = _StepClock([0.0, 0.1, 3.1, 3.2])

    class _SlowGate:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return None

    player = _single_chunk_player(ticks, gate=_SlowGate())
    playback = player.speak("Tek parça cümle.", "tr")

    assert playback.gate_wait_ms == pytest.approx(3000.0)
    assert playback.synth_ms == pytest.approx(100.0)


def test_real_half_duplex_gate_is_not_a_blocking_lock():
    """Kod gerçeği: `HalfDuplexGate.__enter__` yalnız sayaç artırır.

    Kapı beklemesinin neden ~0 ölçüldüğünü açıklayan yapısal olgu. Kapı
    bloklayıcı bir kilide çevrilirse bu test kırılır ve kırılım yeniden
    yorumlanmalıdır — sessizce eskimesin diye buraya sabitlendi.
    """
    gate = HalfDuplexGate()
    with gate:
        assert gate.listening is False
        # Kilit olsaydı burada kilitlenirdi; sayaç olduğu için yeniden girilir.
        with gate:
            assert gate.listening is False
    assert gate.listening is True


def test_empty_text_leaves_substages_unmeasured_not_zero_measured():
    """Sentez hiç olmadıysa damga YOK (None) — 0.0 "ölçtük, sıfır" demektir."""
    player = _single_chunk_player(_StepClock([5.0]))

    playback = player.speak("   ", "tr")

    assert playback.chunks_planned == 0
    assert playback.synth_done_ts is None
    assert playback.gate_acquired_ts is None
    assert playback.deliver_done_ts is None
    # Türetilen süreler yine de güvenle 0.0 okunur.
    assert (playback.synth_ms, playback.gate_wait_ms, playback.deliver_ms) == (0.0, 0.0, 0.0)
