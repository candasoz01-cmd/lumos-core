"""
Köprü: görev hattına gitmeden önce mesaj niyeti — task | chat.

task: emir kipi + net eylem fiili + nesne (veya rapor/komut bildirimi).
chat: soru, merak, görüş, yorum — görev motoruna gönderilmez.
"""
from __future__ import annotations

import json
import re
from typing import Literal

from kando_runtime.lumos_gate import (
    _ACTION_RE,
    _parse_target_instruction,
    explicit_imperative_action_and_object,
    meaningful_tokens,
    user_command_meets_task_structure,
)

_CHAT_QUESTION_OR_DIALOG_RE = re.compile(
    r"\b("
    r"nasıl|neden|niçin|nicin|ne zaman|kim|nerede|nereye|nereden|hangi|kaç|kaçta|"
    r"mi\b|mı\b|mu\b|mü\b|misin|mısın|musun|müsün|miyim|midir|nedir|niye|"
    r"merak ettim|merak ediyorum|merak|emin misin|emin|sanırım|sanıyorum|galiba|"
    r"bence|bana göre|şöyle düşünüyorum|teşekkür|teşekkürler|sağol|özür|"
    r"merhaba|selam|günaydın|iyi günler|acaba|belki|nasılsın|nasılsınız|"
    r"ne dersin|önerin|öneriler|uygun mu|hakkında|hakkinda"
    r")\w*",
    re.I,
)

_CHAT_SOFT_RE = re.compile(
    r"\b("
    r"istiyorum|ediyorum|sanıyorum|düşünüyorum|dusunuyorum|merak|"
    r"biliyor musun|yapalım mı|ister misin|neyi düşünüyorsun"
    r")\w*",
    re.I,
)

# Görev bildirimi / teknik komut parçası (sohbet değil).
# «çelişki/conflict» kelimeleri bilinçle dışarıda: rapor/hata bağlamında yanlış task sınıfı tetiklenmesin.
_NOMINAL_TASK_RE = re.compile(
    r"\b("
    r"komut|talimat|görev|gorev|"
    r"durum|rapor|hata|bug|issue|risk|özet|ozet"
    r")\w*",
    re.I,
)

_FIRST_PERSON_SOFT_RE = re.compile(
    r"\b(istiyorum|ediyorum|sanıyorum|düşünüyorum|dusunuyorum|merak ed|yapalım mı)\b",
    re.I,
)


def extract_user_text_for_intent(raw: bytes, content_type: str | None) -> str:
    """POST /task gövdesinden niyet sınıflandırması için kullanıcı komut metni."""
    ct = (content_type or "").split(";")[0].strip().lower()
    try:
        dec = raw.decode("utf-8")
    except UnicodeDecodeError:
        return ""
    if not dec.strip():
        return ""
    if ct == "application/json" or dec.strip().startswith("{"):
        try:
            obj = json.loads(dec)
        except json.JSONDecodeError:
            return ""
        if not isinstance(obj, dict):
            return ""
        for k in ("task", "goal", "text"):
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                return v.replace("TARGET:", "").strip()
        raw_text = obj.get("raw_text")
        if isinstance(raw_text, str) and raw_text.strip():
            rel, body = _parse_target_instruction(raw_text)
            if (body or "").strip():
                return body.strip()
            lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
            rest = [ln for ln in lines if not ln.upper().startswith("TARGET:")]
            if rest:
                return "\n".join(rest).strip()
            return raw_text.strip()
        return ""
    blob = dec.strip()
    rel, body = _parse_target_instruction(blob)
    if (body or "").strip():
        return body.strip()
    return blob


def _chat_question_signals(low: str) -> bool:
    """Soru / interrogative — görev emrinden önce ayrı ele alınır."""
    if "?" in low:
        return True
    if _CHAT_QUESTION_OR_DIALOG_RE.search(low):
        return True
    return False


def _chat_soft_signals(low: str) -> bool:
    """Yorum, nezaket, yumuşak istek — açık emir+nesne yoksa sohbet."""
    return bool(_CHAT_SOFT_RE.search(low))


def _chat_signals(low: str) -> bool:
    return _chat_question_signals(low) or _chat_soft_signals(low)


def _nominal_task_signal(low: str) -> bool:
    if any(x in low for x in (" oluştur", "create ", ".py oluştur", ".txt oluştur", " içine ", " yaz", "write ")):
        return True
    if _chat_signals(low):
        return False
    if not _NOMINAL_TASK_RE.search(low):
        return False
    return len(meaningful_tokens(low)) >= 2


def _imperative_ok(low: str) -> bool:
    if _FIRST_PERSON_SOFT_RE.search(low):
        return False
    return True


def _core_task_signal(text: str) -> bool:
    """Zorunlu: net eylem fiili + lumos_gate ile aynı nesne/çift sözcük kuralı."""
    low = text.lower()
    if not _imperative_ok(low):
        return False
    if not _ACTION_RE.search(low):
        return False
    return user_command_meets_task_structure(text)


def classify_bridge_message_intent(text: str) -> Literal["task", "chat"]:
    """
    Öncelik: (1) açık emir fiili + nesne → task; (2) soru/diyalog → chat;
    (3) nominal görev; (4) yumuşak sohbet; (5) çekirdek görev yapısı.
    """
    t = (text or "").strip()
    if not t:
        return "chat"
    low = t.lower()
    # 1) Kesin görev: açık fiil + nesne (720p, 0.10p vb. nitelik engel olmaz).
    if explicit_imperative_action_and_object(t):
        return "task"
    # 2) Soru / interrogative — «nasıl video üretirim» gibi.
    if _chat_question_signals(low):
        return "chat"
    if _nominal_task_signal(low):
        return "task"
    if _chat_soft_signals(low):
        return "chat"
    if _core_task_signal(t):
        return "task"
    return "chat"


def classify_bridge_message_intent_from_request(
    raw: bytes, content_type: str | None
) -> tuple[Literal["task", "chat"], str]:
    """(intent, extracted_text) — boş metinde task varsayımı yok."""
    ext = extract_user_text_for_intent(raw, content_type)
    if not ext.strip():
        return "task", ext
    return classify_bridge_message_intent(ext), ext
