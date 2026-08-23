"""Belirsizlikte onarım istekleri (kurucu kararı, 2026-08-23).

Canlı prova kanıtı (41 söz): 12 söz eşik altı güvenle (0.50-0.70) ÇEVRİLDİ ve
karşı tarafa SESLENDİRİLDİ; 3 söz dili belirlenemediği için sessizce varsayılan
yöne (TR) düştü. Kurucu kararı bunun üzerine değişti:

- Eşik altı / güven sinyali olmayan çeviri artık karşı tarafa okunmaz;
  onun yerine tekrar istenir.
- Dil belirlenemezse sessizce Türkçe varsayılmaz; yine tekrar istenir
  (bu durumda hangi dili konuştuğu bilinmediği için istek iki dilli).

KİMİN DUYDUĞU (dürüstlük notu, kurucu düzeltmesi 2026-08-23): tekrar isteği
yalnız konuşana GİTMEZ. Meet'te tek ortak ses kanalı vardır ve bot çıktısını
oraya basar — istek TÜM KATILIMCILAR tarafından duyulur. Dilin konuşana göre
seçilmesi kime hitap edildiğini belli etmek içindir, kanalı özelleştirmek
için değil; kişiye özel kanal Faz 0'da YOKTUR.

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
    """Tekrar isteği, tekrar edecek kişinin dilinde kurulur.

    Dil seçimi hitaptır, gizlilik değil: cümle ortak ses kanalından herkese
    duyulur (bkz. modül başlığı).
    """
    try:
        return REPAIR_LINES[lang]
    except KeyError:
        raise ValueError(f"repair line not defined for lang {lang!r}") from None


def bilingual_repair_line() -> str:
    """Dil belirlenemediğinde iki dilde sorulur; yine herkes duyar."""
    return f"{REPAIR_LINES['tr']} {REPAIR_LINES['en']}"
