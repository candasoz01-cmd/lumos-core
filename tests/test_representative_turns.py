"""Consecutive single-voice turn assembly — no network, deterministic clock."""

from __future__ import annotations

from representative.turns import (
    MEET_VAD_SILENCE_MS,
    SINGLE_OUTPUT_VOICE,
    TurnAssembler,
    looks_complete,
    looks_unfinished,
)


def test_meet_vad_is_later_than_legacy_600ms():
    assert MEET_VAD_SILENCE_MS >= 1000
    assert SINGLE_OUTPUT_VOICE == "onyx"


def test_looks_complete_requires_terminal_punctuation():
    assert looks_complete("Yarın saat üçte görüşürüz.") is True
    assert looks_complete("Are you joining the call?") is True
    assert looks_complete("Yarın saat üçte") is False
    assert looks_complete("") is False


def test_looks_unfinished_catches_conjunctions_and_short_stems():
    assert looks_unfinished("We should go and") is True
    assert looks_unfinished("Toplantıyı yarın") is True  # 2 words, no punct
    assert looks_unfinished("We should go and discuss the contract.") is False
    assert looks_unfinished("The remaining amount will be paid upon delivery.") is False


def test_incomplete_fragment_is_held_then_dropped():
    asm = TurnAssembler(merge_gap_ms=700, extra_hold_ms=400)
    assert asm.push("We should go and", speech_end_ts=1.0, now=1.0) == []
    dropped = asm.poll(now=1.5)
    assert len(dropped) == 1
    assert dropped[0].speakable is False
    assert dropped[0].reason == "incomplete_drop"
    assert dropped[0].text == "We should go and"


def test_punctuated_sentence_emits_immediately():
    asm = TurnAssembler()
    turns = asm.push("See you tomorrow.", speech_end_ts=2.0, now=2.0)
    assert len(turns) == 1
    assert turns[0].speakable is True
    assert turns[0].reason == "complete"
    assert turns[0].text == "See you tomorrow."


def test_split_sentence_is_merged_before_speaking():
    asm = TurnAssembler(merge_gap_ms=700, extra_hold_ms=400)
    assert asm.push("Yarın toplantıyı", speech_end_ts=1.0, now=1.0) == []
    turns = asm.push("saat üçte yapalım.", speech_end_ts=1.5, now=1.5)
    assert len(turns) == 1
    assert turns[0].speakable is True
    assert turns[0].text == "Yarın toplantıyı saat üçte yapalım."
    assert turns[0].reason == "complete"


def test_gap_flushes_previous_then_starts_new_sentence():
    asm = TurnAssembler(merge_gap_ms=700, extra_hold_ms=400)
    first = asm.push("The contract is ready to sign now.", speech_end_ts=1.0, now=1.0)
    assert [t.text for t in first] == ["The contract is ready to sign now."]
    later = asm.push("We meet tomorrow.", speech_end_ts=5.0, now=5.0)
    assert [t.text for t in later] == ["We meet tomorrow."]


def test_unpunctuated_but_long_enough_flushes_after_hold():
    asm = TurnAssembler(merge_gap_ms=700, extra_hold_ms=400)
    assert asm.push("the remaining amount will be paid today", speech_end_ts=1.0, now=1.0) == []
    held = asm.poll(now=1.2)
    assert held == []  # extra hold not expired
    flushed = asm.poll(now=1.5)
    assert len(flushed) == 1
    assert flushed[0].speakable is True
    assert flushed[0].reason == "hold_timeout"
    assert "remaining amount" in flushed[0].text


def test_two_close_fragments_without_punct_wait_for_hold():
    asm = TurnAssembler(merge_gap_ms=700, extra_hold_ms=400)
    assert asm.push("kalanı teslimatta", speech_end_ts=1.0, now=1.0) == []
    assert asm.push("ödenmesi gerekiyor", speech_end_ts=1.4, now=1.4) == []
    flushed = asm.poll(now=1.9)
    assert len(flushed) == 1
    assert flushed[0].speakable is True
    assert flushed[0].text == "kalanı teslimatta ödenmesi gerekiyor"
