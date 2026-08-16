"""Deterministic post-STT term correction for the Lumos glossary.

Test 3 + bench bulgusu (2026-08-14): TR konuşma içindeki İngilizce marka
adlarını ("We Lock AI") HER STT modeli bozuyor (viluk / ve ilocikali /
WeLogica'a). Model değiştirmek çözmüyor; sınırlı sözlüğe karşı deterministik
fuzzy düzeltme çözüyor.

Eşik tarihi: 0.55 ilk sürümdü; test 4'te (2026-08-14) GERÇEK KONUŞMADA yanlış
pozitif üretti — "Lumos projesini" (0.62) "Lumos temsilcisi"ne çevrildi, anlam
bozuldu. Korumalı bant 0.70'e çekildi: gerçek düzeltmeler 0.78-0.97 bandında
kalıyor, yanlış pozitif 0.62 kesiliyor. Bilinçli kapsam dışı: "viluk" (0.31)
ve "WeLogica'a" (0.59) — bunlar STT tarafında (bulut model + istem) çözülür;
düzelticinin altın kuralı: EMİN DEĞİLSEN DOKUNMA.
"""

from __future__ import annotations

from difflib import SequenceMatcher

LUMOS_TERMS = ["We Lock AI", "Lumos temsilcisi", "ChatLumos", "Lumos"]

# Gerçek Türkçe kelimeler — fuzzy eşleşme bunları içeren aralığa ASLA dokunmaz
# (2026-08-16 marka turu: "ve lojistik olarak" gerçek lojistik cümlesinde de
# geçebilir; markaya çevirmek anlam bozar. Bu aralıklar çevrilmeden geçer ve
# çevirmen katmanı düşük güvenle işaretler — "düzelt" değil "işaretle").
REAL_WORD_STOPLIST = frozenset(
    {"lojistik", "lojistigi", "biyolojik", "lokanta", "villa", "kilit"}
)

_TR_FOLD = str.maketrans(
    {"w": "v", "q": "k", "ç": "c", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ı": "i"}
)


def _norm(text: str) -> str:
    folded = text.casefold().translate(_TR_FOLD).replace("x", "ks")
    return "".join(ch for ch in folded if ch.isalnum())


def is_prompt_echo(text: str, prompt: str, threshold: float = 0.60) -> bool:
    """Detects STT output that is just the terms prompt parroted back.

    Test 4 bulgusu (2026-08-14): bulut STT gürültü/sessizlikte terim istemini
    transkripsiyon diye geri döndürdü (26 kaydın 9'u). Bu çıktı çeviriye
    girmeden düşürülmeli — istem metni hiçbir gerçek sözün içeriği olamaz.
    """
    return SequenceMatcher(None, _norm(text), _norm(prompt)).ratio() >= threshold


class TermCorrector:
    """Replaces near-miss STT output spans with canonical glossary terms."""

    def __init__(self, terms: list[str] | None = None, threshold: float = 0.70) -> None:
        # Uzun terimler önce: "Lumos temsilcisi" varken "Lumos" tek başına
        # eşleşip parçayı bölmesin.
        self._terms = sorted(terms if terms is not None else LUMOS_TERMS, key=len, reverse=True)
        self._threshold = threshold

    def _match(self, span: str, term: str) -> bool:
        if any(_norm(word) in REAL_WORD_STOPLIST for word in span.split()):
            return False
        n_span, n_term = _norm(span), _norm(term)
        if not n_span:
            return False
        ratio = SequenceMatcher(None, n_span, n_term).ratio()
        if ratio >= 0.80:  # çok güçlü eşleşme: önek gürültüsü olsa da geçer
            return True
        # 0.55-0.80 bandı: ilk-harf koruması şart ("lokanta" 0.53'ün üstüne
        # çıkabilen sınır vakaları burada elenir)
        return ratio >= self._threshold and n_span[0] == n_term[0]

    def correct(self, text: str) -> str:
        words = text.split()
        for term in self._terms:
            term_len = len(term.split())
            for window in range(1, term_len + 2):
                i = 0
                while i + window <= len(words):
                    span = " ".join(words[i : i + window])
                    if _norm(span) == _norm(term):
                        words[i : i + window] = term.split()  # zaten doğru; biçimi sabitle
                        i += term_len
                        continue
                    if self._match(span, term):
                        words[i : i + window] = term.split()
                        i += term_len
                        continue
                    i += 1
        return " ".join(words)
