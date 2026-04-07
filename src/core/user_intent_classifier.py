"""
Kullanıcı mesajı niyet sınıflandırması: TASK | CHAT | HYBRID | UNCERTAIN.

Amaç: tek kelime listesi değil; işlem beklentisi, diyalog/epistemik ton ve
çoklu cümle bağlamını birlikte değerlendiren okunabilir bir kural katmanı.

Genişletme:
- Eşik sabitleri: THRESHOLDS
- Sinyal aileleri: _operational_signals, _dialogic_signals (regex + ağırlık)
- İsteğe bağlı ikinci aşama: skorları normalize edip ağırlıklı toplayan _combine_scores

Debug: classify_user_message_intent(..., debug=True) → (sonuç, skor özeti)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

IntentLabel = Literal["TASK", "CHAT", "HYBRID", "UNCERTAIN"]


@dataclass(frozen=True)
class IntentClassification:
    label: IntentLabel
    confidence: float
    reason: str
    action_required: bool
    clarification_needed: bool

    def as_dict(self) -> dict[str, str | float | bool]:
        return {
            "label": self.label,
            "confidence": self.confidence,
            "reason": self.reason,
            "action_required": self.action_required,
            "clarification_needed": self.clarification_needed,
        }


# --- Eşikler (sonradan veriyle ayarlanabilir) ---
THRESHOLDS = {
    "strong_task": 0.52,
    "strong_chat": 0.48,
    "weak_axis": 0.26,
    "uncertain_margin": 0.14,
    "clause_task": 0.38,
    "clause_chat": 0.26,
    "max_single_signal": 0.95,
}

# Anlamlı sözcük: en az bir harf/rakam
_TOKEN_RE = re.compile(r"[0-9A-Za-z_çğıöşüÇĞİÖŞÜ]+")


def _tokens(s: str) -> list[str]:
    return _TOKEN_RE.findall(s or "")


def _word_count(s: str) -> int:
    return len(_tokens(s))


def _split_clauses(text: str) -> list[str]:
    """Cümle / bağlaç / virgül ile böl; hibrit (önce sohbet sonra iş) yakalamak için."""
    t = (text or "").strip()
    if not t:
        return []
    parts = re.split(
        r"(?<=[.!?])\s+|\n+|,\s+|\s*;\s*|"
        r"\s+(?:ama|ancak|fakat|lakin|sonra|şimdi|bu arada|"
        r"but|however|then|now|also)\s+",
        t,
        flags=re.IGNORECASE,
    )
    return [p.strip() for p in parts if p and p.strip()]


# İşlem fiilleri: tek başına değil; token sayısı veya dosya yolu ile güçlenir
_OP_VERBS_RE = re.compile(
    r"\b("
    r"oluştur|olustur|yarat|üret|uret|sil|kaldır|kaldir|ekle|çıkar|cikar|"
    r"düzelt|gider|güncelle|guncelle|uygula|çalıştır|calistir|başlat|baslat|"
    r"yürüt|yurut|tetikle|refaktör|refaktor|refactor|implemente|uyarla|"
    r"toparla|sadeleştir|sadelestir|düzenle|duzenle|özetle|ozetle|birleştir|birlestir|ayır|ayir|taşı|"
    r"tası|yeniden yaz|yeniden\s+yaz|patch|commit|push|merge|deploy|"
    r"run|execute|fix|add|remove|delete|create|implement|apply|build|"
    r"install|update|migrate|rename|move|copy|generate|start|stop|restart"
    r")\w*\b",
    re.IGNORECASE,
)

# Dosya / modül benzeri hedef
_PATH_LIKE_RE = re.compile(
    r"(?:^|\s)([\w./\\~-]+\.(?:py|ts|tsx|js|mjs|cjs|md|json|ya?ml|toml|sh|rs|go|java|kt|swift))\b",
    re.IGNORECASE,
)

# Açık komut / gövde değişikliği isteği (nesne zayıf olsa bile güçlü sinyal)
_DIRECT_OP_RE = re.compile(
    r"\b("
    r"migration|migrasyon|schema|seed|build|deploy|"
    r"dosyayı|dosyayi|dosyayı|bu dosyayı|şu dosyayı|su dosyayi|"
    r"bu klasörü|su klasoru|repo|kodu|kodunu|fonksiyonu|fonksiyon|"
    r"modülü|modulu|sınıfı|sinifi|satırı|satirlari|hata|bug|issue|"
    r"akışı|akisi|flow|pipeline|workflow|script|komutu|testi|"
    r"the file|this file|that file|the repo|the code|the function|"
    r"the module|the class|the bug|the error|the script"
    r")\b",
    re.IGNORECASE,
)

# Diyalog / epistemik (soru işareti ayrı ele alınır)
_DIALOGIC_RE = re.compile(
    r"\b("
    r"neden|niçin|nicin|niye|why\b|how\s+come|"
    r"ne\s+demek|what\s+does\s+.*\s+mean|"
    r"sence|ne\s+dersin|what\s+do\s+you\s+think|would\s+you\s+agree|"
    r"nasıl\s+yorumlar|how\s+would\s+you\s+interpret|"
    r"doğru\s+mu|dogru\s+mu|is\s+that\s+correct|does\s+that\s+make\s+sense|"
    r"anlamadım|anlamiyorum|don't\s+understand|can\s+you\s+explain|"
    r"açıklar\s+mısın|aciklar\s+misin|help\s+me\s+understand|"
    r"burada\s+ne\s+görüyorsun|what\s+do\s+you\s+see|"
    r"bu\s+fikir|this\s+idea|hakkında\s+ne\s+düşün|what\s+do\s+you\s+think\s+about"
    r")\w*",
    re.IGNORECASE,
)

# "Nasıl X yapılır" → öğrenme / sohbet (işlem emri değil)
_HOW_TO_RE = re.compile(
    r"\b(nasıl|how\s+(?:do|can|should|would)\s+(?:i|we|you))\b.*\b("
    r"yapılır|yapilir|yaparım|yaparim|üretirim|uretirim|çalıştırılır|calistirilir|"
    r"install|run|use|make|build)\w*\b",
    re.IGNORECASE | re.DOTALL,
)

# Kısa nezaket / selam (uzun metinde tek başına chat yapmaz)
_SOCIAL_SHORT_RE = re.compile(
    r"^(?:merhaba|selam|hey|hi|hello|thanks|teşekkür|tesekkur|sağol|sagol|ok|tamam|thanks?\s*!*)\s*$",
    re.IGNORECASE,
)


def _operational_score(fragment: str) -> tuple[float, list[str]]:
    """İşlem beklentisi: fiil + bağlam veya dosya yolu."""
    notes: list[str] = []
    s = (fragment or "").strip()
    if not s:
        return 0.0, notes
    score = 0.0
    wc = _word_count(s)

    if _PATH_LIKE_RE.search(s):
        score += 0.42
        notes.append("path_like")

    verb_m = _OP_VERBS_RE.search(s)
    if verb_m:
        notes.append("op_verb")
        if _PATH_LIKE_RE.search(s) or _DIRECT_OP_RE.search(s):
            score += 0.48
            notes.append("verb_plus_target")
        elif wc >= 4:
            score += 0.4
            notes.append("verb_plus_context")
        elif wc >= 2:
            score += 0.44
            notes.append("short_imperative")
        else:
            score += 0.25
            notes.append("bare_verb")

    elif _DIRECT_OP_RE.search(s) and wc >= 3:
        score += 0.22
        notes.append("direct_object_lang")

    return min(THRESHOLDS["max_single_signal"], score), notes


def _dialogic_score(fragment: str) -> tuple[float, list[str]]:
    notes: list[str] = []
    s = (fragment or "").strip()
    if not s:
        return 0.0, notes
    score = 0.0
    wc = _word_count(s)

    if _SOCIAL_SHORT_RE.match(s.strip()):
        return 0.72, ["social_short"]

    if "?" in s:
        score += 0.22
        notes.append("question_mark")

    if _HOW_TO_RE.search(s):
        score += 0.45
        notes.append("how_to_explore")
    elif _DIALOGIC_RE.search(s):
        score += 0.38
        notes.append("dialogic_phrase")

    if re.search(r"\b(bence|sanırım|sanirim|i think|imo|in my view)\b", s, re.I):
        score += 0.44 if wc >= 3 else 0.14
        notes.append("opinion_frame" if wc >= 3 else "reflective_soft")

    if re.search(r"\b(anlatayım|let me explain|i('ll| will) explain)\b", s, re.I):
        score += 0.38
        notes.append("narrate_intent")

    if wc <= 2 and score > 0:
        score = min(0.85, score + 0.08)

    return min(THRESHOLDS["max_single_signal"], score), notes


def _aggregate_scores(
    text: str,
) -> tuple[float, float, list[str], list[str], bool]:
    """(task_score, chat_score, task_notes, chat_notes, force_hybrid)."""
    clauses = _split_clauses(text)
    if len(clauses) <= 1:
        clauses = [text.strip()] if text.strip() else []

    task_notes: list[str] = []
    chat_notes: list[str] = []
    max_t = 0.0
    max_c = 0.0
    sum_t = 0.0
    sum_c = 0.0

    for i, cl in enumerate(clauses):
        ts, tn = _operational_score(cl)
        cs, cn = _dialogic_score(cl)
        max_t = max(max_t, ts)
        max_c = max(max_c, cs)
        sum_t += ts
        sum_c += cs
        task_notes.extend([f"c{i}:{x}" for x in tn])
        chat_notes.extend([f"c{i}:{x}" for x in cn])

    n = max(len(clauses), 1)
    blend_t = min(1.0, 0.55 * max_t + 0.45 * min(1.0, sum_t / n))
    blend_c = min(1.0, 0.55 * max_c + 0.45 * min(1.0, sum_c / n))

    has_task_clause = any(
        _operational_score(c)[0] >= THRESHOLDS["clause_task"] for c in clauses
    )
    has_chat_clause = any(
        _dialogic_score(c)[0] >= THRESHOLDS["clause_chat"] for c in clauses
    )

    force_hybrid = len(clauses) >= 2 and has_task_clause and has_chat_clause

    if not force_hybrid and len(clauses) == 1 and clauses[0].strip():
        only = clauses[0]
        ot, _ = _operational_score(only)
        oc, _ = _dialogic_score(only)
        mixed_epistemic = bool(
            re.search(r"\b(neden|niçin|why|anlat|explain|oluştu|olustu)\b", only, re.I)
        )
        if (
            ot >= THRESHOLDS["clause_task"]
            and oc >= THRESHOLDS["clause_chat"]
            and _OP_VERBS_RE.search(only)
            and mixed_epistemic
        ):
            force_hybrid = True
            task_notes.append("single_clause_mixed_epistemic_task")

    if force_hybrid:
        task_notes.append("multi_clause_task_chat")
        blend_t = max(blend_t, THRESHOLDS["strong_task"] + 0.04)
        blend_c = max(blend_c, THRESHOLDS["strong_chat"] + 0.04)

    return blend_t, blend_c, task_notes, chat_notes, force_hybrid


def _pick_label(
    task_s: float, chat_s: float
) -> tuple[IntentLabel, float, str, bool, bool]:
    st = THRESHOLDS["strong_task"]
    sc = THRESHOLDS["strong_chat"]
    wk = THRESHOLDS["weak_axis"]
    mg = THRESHOLDS["uncertain_margin"]

    action_required = False
    clarification_needed = False

    both_strong = task_s >= st and chat_s >= sc
    task_only_strong = task_s >= st and chat_s < wk
    chat_only_strong = chat_s >= sc and task_s < wk

    if both_strong:
        conf = min(0.92, (task_s + chat_s) / 2 + 0.15)
        return (
            "HYBRID",
            conf,
            "Hem işlem hem diyalog/epistemik sinyaller anlamlı; çift niyet.",
            True,
            False,
        )

    if task_only_strong:
        conf = min(0.94, task_s + 0.12)
        return (
            "TASK",
            conf,
            "Net işlem beklentisi; diyalog sinyali zayıf.",
            True,
            False,
        )

    if chat_only_strong:
        conf = min(0.92, chat_s + 0.1)
        return (
            "CHAT",
            conf,
            "Sohbet / anlama / görüş sinyali baskın; zayıf işlem emri.",
            False,
            False,
        )

    diff = abs(task_s - chat_s)
    top = max(task_s, chat_s)

    if diff < mg and top < 0.58:
        clarification_needed = True
        return (
            "UNCERTAIN",
            max(0.25, top * 0.65),
            "Skorlar yakın veya düşük; niyet net ayrışmıyor.",
            False,
            True,
        )

    if task_s > chat_s + mg:
        conf = min(0.88, task_s + 0.05)
        action_required = task_s >= 0.4
        clarification_needed = task_s < st and task_s >= 0.35
        return (
            "TASK" if task_s >= 0.4 else "UNCERTAIN",
            conf if task_s >= 0.4 else max(0.3, task_s),
            "İşlem sinyali biraz önde; eşik altında belirsizlik."
            if task_s < st
            else "İşlem sinyali diyalogdan belirgin şekilde güçlü.",
            action_required,
            clarification_needed,
        )

    if chat_s > task_s + mg:
        conf = min(0.88, chat_s + 0.05)
        return (
            "CHAT",
            conf,
            "Diyalog sinyali işlemden belirgin şekilde güçlü.",
            False,
            False,
        )

    clarification_needed = True
    return (
        "UNCERTAIN",
        max(0.28, top * 0.55),
        "Üstün sinyal yok; güvenli taraf için netleştirme önerilir.",
        False,
        True,
    )


def classify_user_message_intent(
    text: str, *, debug: bool = False
) -> IntentClassification | tuple[IntentClassification, dict[str, object]]:
    """
    Kullanıcı mesajını TASK | CHAT | HYBRID | UNCERTAIN olarak sınıflandırır.
    debug=True iken (sonuç, {"task_score", "chat_score", ...}) döner.
    """
    raw = (text or "").strip()
    if not raw:
        empty = IntentClassification(
            label="UNCERTAIN",
            confidence=0.0,
            reason="Boş mesaj.",
            action_required=False,
            clarification_needed=True,
        )
        if debug:
            return empty, {"task_score": 0.0, "chat_score": 0.0, "notes": [], "force_hybrid": False}
        return empty

    task_s, chat_s, tn, cn, force_hybrid = _aggregate_scores(raw)
    if force_hybrid:
        conf = min(0.9, (task_s + chat_s) / 2 + 0.12)
        out = IntentClassification(
            label="HYBRID",
            confidence=round(max(0.0, min(1.0, conf)), 3),
            reason="Ayrı cümlelerde veya aynı metinde hem işlem hem açıklama/görüş sinyali.",
            action_required=True,
            clarification_needed=False,
        )
        if debug:
            return out, {
                "task_score": round(task_s, 4),
                "chat_score": round(chat_s, 4),
                "task_notes": tn[:12],
                "chat_notes": cn[:12],
                "force_hybrid": True,
            }
        return out

    label, conf, reason, ar, clar = _pick_label(task_s, chat_s)

    out = IntentClassification(
        label=label,
        confidence=round(max(0.0, min(1.0, conf)), 3),
        reason=reason,
        action_required=ar,
        clarification_needed=clar,
    )
    if debug:
        dbg = {
            "task_score": round(task_s, 4),
            "chat_score": round(chat_s, 4),
            "task_notes": tn[:12],
            "chat_notes": cn[:12],
            "force_hybrid": False,
        }
        return out, dbg
    return out


# Dokümantasyon: örnek girdi → beklenen etiket (testlerde doğrulanır; regresyon için).
EXAMPLE_CASES: list[tuple[str, IntentLabel, str]] = [
    ("README.md oluştur ve projeyi özetle", "TASK", "dosya + oluştur/özetle → güçlü iş"),
    ("bence bu yapı karışık, bir toparla", "HYBRID", "görüş + toparla"),
    ("mantığını anlatayım, sonra dosyayı düzenle", "HYBRID", "çok cümle: anlat + düzenle"),
    (
        "şu hatayı düzelt ve kısaca neden oluştuğunu anlat",
        "HYBRID",
        "tek metinde düzelt + neden/anlat",
    ),
    ("src/app.ts dosyasına logging ekle", "TASK", "path + ekle"),
    ("migration'ı çalıştır", "TASK", "kısa işlem emri"),
    ("nasıl video üretirim?", "CHAT", "nasıl-yapılır"),
    ("sence bu mimari karar doğru mu?", "CHAT", "görüş sorusu"),
    ("bu neden böyle çalışıyor?", "CHAT", "epistemik soru"),
    ("x", "UNCERTAIN", "tek harf"),
    ("şunu yap", "UNCERTAIN", "belirsiz nesne, zayıf bağlam"),
]
