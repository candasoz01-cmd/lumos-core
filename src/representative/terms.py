"""Deterministic post-STT term correction for the Lumos glossary.

Test 3 + bench bulgusu (2026-08-14): TR konuşma içindeki İngilizce marka
adlarını ("We Lock AI") HER STT modeli bozuyor (viluk / ve ilocikali /
WeLogica'a). Model değiştirmek çözmüyor; sınırlı sözlüğe karşı deterministik
fuzzy düzeltme çözüyor. Eşik deneysel: gerçek bozulmalar 0.59-0.97 bandında,
kontrol kelimeleri ≤0.53 — eşik 0.55 + ilk-harf koruması ("lokanta" 0.53'te
ilk harfle elenir). "viluk" (0.31) bilinçli kapsam dışı: o kadar uzak girdiyi
düzeltmek yanlış pozitif riskine değmez.
"""

from __future__ import annotations

from difflib import SequenceMatcher

LUMOS_TERMS = ["We Lock AI", "Lumos temsilcisi", "ChatLumos", "Lumos"]

_TR_FOLD = str.maketrans(
    {"w": "v", "q": "k", "ç": "c", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ı": "i"}
)


def _norm(text: str) -> str:
    folded = text.casefold().translate(_TR_FOLD).replace("x", "ks")
    return "".join(ch for ch in folded if ch.isalnum())


class TermCorrector:
    """Replaces near-miss STT output spans with canonical glossary terms."""

    def __init__(self, terms: list[str] | None = None, threshold: float = 0.55) -> None:
        # Uzun terimler önce: "Lumos temsilcisi" varken "Lumos" tek başına
        # eşleşip parçayı bölmesin.
        self._terms = sorted(terms if terms is not None else LUMOS_TERMS, key=len, reverse=True)
        self._threshold = threshold

    def _match(self, span: str, term: str) -> bool:
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
