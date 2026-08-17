"""Söz-başına TR↔EN yön yönlendirmesi (canlı insan testi 4 bulgusu, 2026-08-17).

Canlı testte yön **oturum başında sabitleniyordu** (`--source-lang tr
--target-lang en`): karşı taraf İngilizce konuşunca zincir onu hâlâ "TR→EN"
sanıp EN girdiyi EN'e "çeviriyor" ve bot papağan gibi aynı cümleyi
tekrarlıyordu. Toplantı tek yönlü değildir; yön her söz için yeniden
belirlenmelidir.

Kural (bilinçli olarak basit ve deterministik):
- Duyulan metnin dili tespit edilir (`langcheck.detect_lang`, tr/en/unknown).
- Tespit edilen dil **kaynak**, çiftin diğer üyesi **hedef** olur → kaynak ile
  hedef asla aynı olamaz, yani papağan yapısal olarak imkânsızdır.
- Tespit "unknown" ise (kısa/nötr söz: "Okay.") yön değiştirilmez; yapılandırılan
  varsayılan yön kullanılır. Kısa sözü yanlış yöne atmaktansa varsayılanda
  bırakmak tercih edilir — çıktı-dili post-check (`InterpreterPipeline`) zaten
  ikinci savunma hattıdır.

Bu modül ağ/ses bilmez; yalnız metin → yön kararı verir, böylece kayıtlı prova
satırlarıyla botsuz doğrulanabilir.
"""

from __future__ import annotations

from dataclasses import dataclass

from representative.langcheck import detect_lang


@dataclass(frozen=True)
class Direction:
    source_lang: str
    target_lang: str


@dataclass(frozen=True)
class RoutingDecision:
    direction: Direction
    detected: str  # "tr" | "en" | "unknown"
    reason: str  # "detected" | "fallback_unknown" | "fixed"


class DirectionRouter:
    """Her söz için yönü yeniden belirler; `bidirectional=False` eski davranış."""

    def __init__(self, default_direction: Direction, bidirectional: bool = True) -> None:
        if default_direction.source_lang == default_direction.target_lang:
            raise ValueError("source and target language must differ")
        pair = {default_direction.source_lang, default_direction.target_lang}
        if pair != {"tr", "en"}:
            # Faz 0 çifti bilinçli olarak yalnız tr/en; başka çift sessizce
            # yanlış yönlendirilmesin diye erken hata verilir.
            raise ValueError("Faz 0 only supports the tr/en pair")
        self._default = default_direction
        self._bidirectional = bidirectional

    @property
    def default_direction(self) -> Direction:
        return self._default

    @property
    def bidirectional(self) -> bool:
        return self._bidirectional

    def route(self, text: str) -> RoutingDecision:
        if not self._bidirectional:
            return RoutingDecision(self._default, detect_lang(text), "fixed")
        detected = detect_lang(text)
        if detected == "unknown":
            return RoutingDecision(self._default, detected, "fallback_unknown")
        target = "en" if detected == "tr" else "tr"
        return RoutingDecision(Direction(detected, target), detected, "detected")
