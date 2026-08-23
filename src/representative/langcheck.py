"""Deterministic TR/EN output-language check (kalem 2, 2026-08-16).

Test 6 bulgusu: karışık dilli girdide çevirmen yönü ters çevirebiliyor;
istem kilidi çoğunu tuttu ama tamamını tutmadı. Kurucu kuralı: hedef dili
deterministik kontrol et → yanlışsa EN FAZLA 1 yeniden çeviri → ikinci çıktı
da yanlışsa TTS'e VERME (fail-closed, işaretle). Retry döngüsü yok.

Kapsam bilinçli dar: yalnız tr/en (Faz 0 çifti). Kısa/nötr çıktı ("Okay.")
"unknown" döner ve GEÇER — kısa sözleri yanlış bloklamak, kaçırmaktan kötü.
"""

from __future__ import annotations

_TR_CHARS = set("çğıöşüÇĞİÖŞÜ")

# Genişletme (2026-08-23): canlı provada "Hey Hasan, speak English!" gibi
# cümleler hiç sinyal üretmediği için sessizce varsayılan yöne düşüyordu.
# Eklenenler bilinçli olarak İŞLEV/GÜNLÜK KONUŞMA kelimeleridir; alan sözcüğü
# (ör. "translate") eklenmez — o, kaydı ezberlemek olurdu.
_TR_WORDS = frozenset(
    "ve bir bu şu için ama biz ben siz evet hayır olarak ile de da ne mi mı mu "
    "değil çok olacak var yok olan kadar sonra önce daha en gibi ise diye "
    "tamam nasıl neden niye kim nerede şimdi yani işte öyle böyle şöyle hep "
    "hiç az iyi güzel tabii lütfen merhaba selam teşekkür sağ olsun beni bana "
    "senin benim bizim onun şey her hangi başka aynı kendi".split()
)
_EN_WORDS = frozenset(
    "the and is are was were will would of to in for you we it that this on at "
    "with not be have has can my your our they he she i as by from yes no okay "
    "hey hi hello please thanks thank sorry what how when where why who which "
    "do does did but or if so there here just know think want need get going "
    "right sure well very more than then now about out up all some any speak "
    "english turkish let me him her them was been being am".split()
)

# Türkçe biçimbirim izleri: işlev kelimesi olmayan cümlelerde tek sinyal bu
# olabilir ("Bakıyordum.", "Gelecekmiş."). Bilinçli olarak UZUN ekler seçildi;
# kısa ekler ("-di", "-lar") İngilizce kelimelere de uyup gürültü üretir.
_TR_SUFFIXES = (
    "yorum", "yoruz", "yorsun", "yordu", "yor", "acak", "ecek", "mış", "miş",
    "muş", "müş", "ları", "leri", "lık", "lik", "luk", "lük", "mak", "mek",
    "dır", "dir", "dur", "dür", "tır", "tir",
)


def detect_lang(text: str) -> str:
    """Returns "tr", "en" or "unknown" (unknown = insufficient signal).

    Karar kuralı: skor >= 2 kendi başına yeter; skor == 1 ancak karşı taraf
    SIFIRSA yeter (kısa çıktılar: "My forty percent." / "Evet."). İkisi de
    sinyalsizse unknown → bloklanmaz.
    """
    tr_score = sum(2 for ch in text if ch in _TR_CHARS)
    words = [w.strip(".,!?;:'\"()[]…").casefold() for w in text.split()]
    tr_score += sum(1 for w in words if w in _TR_WORDS)
    # Biçimbirim izi yalnız işlev kelimesi olmayan uzunca kelimelerde sayılır.
    tr_score += sum(
        1
        for w in words
        if w not in _TR_WORDS and len(w) >= 6 and w.endswith(_TR_SUFFIXES)
    )
    en_score = sum(1 for w in words if w in _EN_WORDS)
    if tr_score > en_score and (tr_score >= 2 or en_score == 0):
        return "tr" if tr_score >= 1 else "unknown"
    if en_score > tr_score and (en_score >= 2 or tr_score == 0):
        return "en" if en_score >= 1 else "unknown"
    return "unknown"
