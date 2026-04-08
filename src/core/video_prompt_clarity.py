"""
Video görevi talimatı: soyut / belirsiz prompt tespiti.

Amaç: sahne, nesne veya aksiyon net değilse görev yürütülmeden önce tek cümlelik
netleştirme sorusu üretmek; varsayım yapılmaz.
"""
from __future__ import annotations

import re

_VAGUE_WORDS = re.compile(
    r"\b(bilinmeyen|bilinmez|garip|tuhaf|acayip|saçma|bir\s*şey|birşey|bi\s*şey|"
    r"şeyler|\bşey\b|rastgele|fark\s*etmez|herhangi|ne\s+olursa|soyut|belirsiz|"
    r"anlamsız|falan|filan|vs\.?|falan\s*filan|karmaşa|kaos|random)\b",
    re.IGNORECASE,
)

_ANALYSIS_VERBS = re.compile(
    r"\b(özet|özetle|transkript|altyazı|kesit|kes\b|analiz|incele|çıkar|bul\b|"
    r"tanı|tanımla|sesi|görüntüyü|frame|konu\s*konu)\b",
    re.IGNORECASE,
)

_SCENE_ANCHORS = re.compile(
    r"\b(sahne|nesne|karakter|diyalog|kamera|açı|ışık|renk|gece|gündüz|içeride|"
    r"dışarıda|yürü|koş|konuş|arabada|evde|ofiste|sokak|oda|kişi|adam|kadın|"
    r"çocuk|storyboard|plan|çekim|montaj|açılış|kapanış|youtube|tiktok|güneş|"
    r"batım|deniz|oda|masa|kapı|pencere)\b",
    re.IGNORECASE,
)


def video_prompt_has_media_ref_in_task_blob(task_blob: str) -> bool:
    """Görev metninde video dosyası veya URL referansı var mı (mevcut medya üzerinde iş)."""
    s = (task_blob or "").strip()
    if not s:
        return False
    if re.search(r"https?://\S+", s):
        return True
    if re.search(r"\b[\w./\\-]+\.(mp4|mov|webm|mkv|m4v)\b", s, re.I):
        return True
    if re.search(r"(?:dosya\s*yolu|kaynak\s*url)\s*:", s, re.I):
        return True
    return False


def is_video_task_prompt_ambiguous(
    prompt: str,
    *,
    has_media_ref: bool,
) -> bool:
    """
    Talimat belirsizse True — executor çalıştırılmamalı.

    Medya referansı var ve talimat boşsa: genelde «bu dosyayı işle»; belirsiz sayılmaz.
    """
    p = (prompt or "").strip()
    if not p:
        return False
    if len(p) >= 52:
        if not _VAGUE_WORDS.search(p):
            return False
    if _ANALYSIS_VERBS.search(p) and has_media_ref:
        return False
    if _VAGUE_WORDS.search(p):
        return True
    wc = len(p.split())
    if len(p) < 22 and wc <= 5 and not _SCENE_ANCHORS.search(p):
        return True
    if wc <= 3 and len(p) < 36 and not _SCENE_ANCHORS.search(p):
        return True
    return False


def video_prompt_clarification_question_tr(prompt: str) -> str:
    """Kullanıcı talimatından türetilmiş tek cümlelik netleştirme sorusu (Türkçe)."""
    p = (prompt or "").strip()
    excerpt = p if len(p) <= 44 else p[:41].rstrip() + "…"
    q = excerpt.replace("'", "’")
    if q:
        return (
            f"'{q}' derken nasıl bir sahne, nesne veya aksiyon düşünüyorsun?"
        )
    return (
        "Hangi sahneyi, nesneyi veya aksiyonu üretmek istediğini bir cümleyle "
        "tarif eder misin?"
    )
