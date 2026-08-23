"""Belirsizlikte onarım istekleri (kurucu kararı, 2026-08-23).

Canlı prova kanıtı (41 söz): 12 söz eşik altı güvenle (0.50-0.70) ÇEVRİLDİ ve
karşı tarafa SESLENDİRİLDİ; 3 söz dili belirlenemediği için sessizce varsayılan
yöne (TR) düştü. Kurucu kararı bunun üzerine değişti:

- Eşik altı / güven sinyali olmayan çeviri artık karşı tarafa okunmaz;
  onun yerine konuşandan tekrar istenir.
- Dil belirlenemezse sessizce Türkçe varsayılmaz; yine tekrar istenir
  (bu durumda hangi dili konuştuğu bilinmediği için istek iki dilli).

Önceki kural (2026-08-17 seçenek C: "işaretle ama seslendir") canlı kanıtla
geçersiz kılınmıştır: yanlış olabilecek bir cümlenin karşı tarafın kulağına
gitmesi, kısa bir boşluktan daha pahalıdır.
"""

from __future__ import annotations

REPAIR_LINES = {
    "tr": "Çeviriden emin değilim, lütfen tekrar edin.",
    "en": "I am not confident in that translation. Please repeat.",
}


def repair_line(lang: str) -> str:
    """Konuşanın kendi dilinde tekrar isteği — tekrar edecek olan odur."""
    try:
        return REPAIR_LINES[lang]
    except KeyError:
        raise ValueError(f"repair line not defined for lang {lang!r}") from None


def bilingual_repair_line() -> str:
    """Dil belirlenemediğinde: hangi dili konuştuğu bilinmiyor, ikisi de söylenir."""
    return f"{REPAIR_LINES['tr']} {REPAIR_LINES['en']}"
