"""video_prompt_clarity: belirsiz video talimatı tespiti."""
from __future__ import annotations

from core.video_prompt_clarity import (
    is_video_task_prompt_ambiguous,
    video_prompt_clarification_question_tr,
    video_prompt_has_media_ref_in_task_blob,
)


def test_empty_prompt_never_ambiguous() -> None:
    assert is_video_task_prompt_ambiguous("", has_media_ref=False) is False
    assert is_video_task_prompt_ambiguous("", has_media_ref=True) is False


def test_vague_keywords() -> None:
    assert is_video_task_prompt_ambiguous("bilinmeyen", has_media_ref=False) is True
    assert is_video_task_prompt_ambiguous("garip şeyler olsun", has_media_ref=False) is True


def test_short_without_anchors() -> None:
    assert is_video_task_prompt_ambiguous("x", has_media_ref=False) is True


def test_analysis_with_ref_not_ambiguous() -> None:
    assert (
        is_video_task_prompt_ambiguous("özetle ve analiz et", has_media_ref=True)
        is False
    )


def test_detailed_prompt() -> None:
    long_clear = (
        "10 saniye, sabit kamera, gece sokakta yürüyen iki kişi, diyalog yok, sadece ambient ses"
    )
    assert is_video_task_prompt_ambiguous(long_clear, has_media_ref=False) is False


def test_media_ref_in_blob() -> None:
    assert video_prompt_has_media_ref_in_task_blob("Dosya yolu: clip.mp4") is True
    assert video_prompt_has_media_ref_in_task_blob("Kaynak URL: https://x.com/a.mp4") is True
    assert video_prompt_has_media_ref_in_task_blob("Talimat: sadece metin") is False


def test_question_tr() -> None:
    q = video_prompt_clarification_question_tr("bilinmeyen den gelenler")
    assert "bilinmeyen" in q.lower()
    assert "sahne" in q.lower() or "nesne" in q.lower()
