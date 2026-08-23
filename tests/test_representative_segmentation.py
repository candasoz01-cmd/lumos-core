"""Parça birleştirme/eleme testleri (canlı prova 2026-08-23 bulguları)."""

import pytest

from representative.segmentation import (
    Fragment,
    UtteranceCoalescer,
    is_filler_only,
    looks_incomplete,
)


def frag(text: str, t: float) -> Fragment:
    """speech_end ve stt_final aynı ana sabitlenmiş basit parça."""
    return Fragment(text=text, speech_end_ts=t, stt_final_ts=t)


@pytest.mark.parametrize("text", ["Şey...", "Ee", "um", "  ", "hmm.", "…"])
def test_filler_only_fragments_are_recognised(text: str) -> None:
    assert is_filler_only(text) is True


@pytest.mark.parametrize("text", ["My...", "Translate.", "Okay.", "Evet, tamam."])
def test_content_is_never_called_filler(text: str) -> None:
    """Şüphedeki kelime elenmez — içerik kaybı gürültüden pahalıdır."""
    assert is_filler_only(text) is False


def test_filler_is_dropped_and_counted() -> None:
    c = UtteranceCoalescer()
    assert c.offer(frag("Şey...", 0.0)) == []
    assert c.dropped_fillers == ["Şey..."]


def test_full_sentence_passes_through_without_delay() -> None:
    """Normal söz beklemez: ek gecikme sıfır."""
    c = UtteranceCoalescer()
    out = c.offer(frag("Merhaba, nasılsınız?", 1.0))
    assert [s.text for s in out] == ["Merhaba, nasılsınız?"]
    assert out[0].merged is False
    assert c.pending() is False


def test_short_fragments_merge_into_one_utterance() -> None:
    c = UtteranceCoalescer(min_words=3, hold_s=0.8)
    assert c.offer(frag("My...", 1.0)) == []
    out = c.offer(frag("name is Candaş.", 1.4))
    assert [s.text for s in out] == ["My... name is Candaş."]
    assert out[0].merged is True and out[0].parts == 2


def test_merged_utterance_keeps_the_last_speech_end() -> None:
    """Dürüst ölçüm: konuşma son parçada bitti; gecikme oradan sayılır."""
    c = UtteranceCoalescer()
    c.offer(frag("My...", 1.0))
    out = c.offer(frag("name is Candaş.", 1.4))
    assert out[0].speech_end_ts == 1.4


def test_orphan_short_fragment_is_still_emitted_after_the_window() -> None:
    """İçerik yutulmaz: devamı gelmezse kısa söz tek başına çıkar."""
    c = UtteranceCoalescer(hold_s=0.8)
    assert c.offer(frag("Yarım kalan", 1.0)) == []
    assert c.due(1.5) == []  # pencere henüz açık
    out = c.due(1.9)
    assert [s.text for s in out] == ["Yarım kalan"]
    assert c.pending() is False


def test_late_fragment_does_not_glue_unrelated_sentences() -> None:
    """Pencere kapandıysa birleştirme yok: iki ayrı söz, sırayla."""
    c = UtteranceCoalescer(hold_s=0.8)
    c.offer(frag("Yarım kalan", 1.0))
    out = c.offer(frag("Bu tamamen başka bir cümle.", 5.0))
    assert [s.text for s in out] == ["Yarım kalan", "Bu tamamen başka bir cümle."]


def test_merging_stops_at_the_part_limit() -> None:
    c = UtteranceCoalescer(min_words=99, hold_s=1.0, max_parts=3)
    c.offer(frag("bir", 1.0))
    c.offer(frag("iki", 1.2))
    out = c.offer(frag("üç", 1.4))
    assert [s.text for s in out] == ["bir iki üç"]
    assert out[0].parts == 3
    assert c.pending() is False


def test_filler_between_fragments_does_not_break_the_merge() -> None:
    c = UtteranceCoalescer(hold_s=0.8)
    c.offer(frag("My...", 1.0))
    assert c.offer(frag("şey", 1.2)) == []
    out = c.offer(frag("name is Candaş.", 1.5))
    assert [s.text for s in out] == ["My... name is Candaş."]


@pytest.mark.parametrize(
    ("text", "incomplete"),
    [
        ("My...", True),  # üç nokta: yarım
        ("Kısa", True),  # noktalama yok + eşiğin altında
        ("Bu cümle yeterince uzun.", False),
        ("Hoş bulduk.", False),  # kısa AMA tamamlanmış cümle
        ("Okay.", False),
    ],
)
def test_incompleteness_signals(text: str, incomplete: bool) -> None:
    assert looks_incomplete(text, min_words=3) is incomplete


def test_short_but_complete_sentence_is_not_delayed() -> None:
    """Türkçede iki kelimelik cümle normaldir; gecikme eklenmez."""
    c = UtteranceCoalescer()
    out = c.offer(frag("Hoş bulduk.", 1.0))
    assert [s.text for s in out] == ["Hoş bulduk."]
    assert c.pending() is False
