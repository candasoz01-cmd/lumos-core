"""Söz parçalarını birleştirme/eleme (kurucu sırası, 2026-08-23).

Canlı prova bulgusu: 41 sözün 12'si iki kelime veya daha kısaydı ("Şey...",
"My...", "Okay.", "Translate."). Bunlar ayrı birer söz sanılıp ayrı ayrı
çevrildi; hem anlamsız çeviri üretti hem de dil tespitini sinyalsiz bıraktı.
Kök sebep VAD: 600 ms sessizlik konuşmanın ortasındaki soluğu söz sonu sayıyor.

Tasarım kararları (kod yazmadan önce cevaplananlar):

- GİRİŞ: STT'nin ürettiği her parça `offer()`'a verilir; çıktı, çevrilmeye
  HAZIR sözlerdir. Zamanlayıcı yok — `due()` çağıran taraf saati verir, böylece
  modül saf ve botsuz test edilebilir kalır.
- ELEME: yalnız dolgu sesleri ("şey", "ee", "um") atılır. İçerik taşıyan hiçbir
  parça atılmaz; atılanlar sayılır, sessizce yok olmaz.
- BEKLETME: kısa/yarım parça en fazla `hold_s` kadar bekletilir; devamı
  gelirse birleşir, gelmezse TEK BAŞINA yayımlanır. İçerik yutulmaz.
- GECİKME: normal uzunluktaki söz HİÇ beklemez (ek gecikme sıfır). Bedeli
  yalnız kısa parçalar öder, en fazla hold_s. Gecikme zaten hedefin üstünde
  olduğu için bu sınır bilinçli olarak dar tutuldu.
- DÜRÜST ÖLÇÜM: birleşmiş sözün `speech_end_ts`'i SON parçanınkidir — konuşma
  gerçekten orada bitmiştir. İlkininki kullanılsa gecikme olduğundan uzun,
  bekleme yok sayılsa olduğundan kısa görünürdü.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Tek başına anlam taşımayan sesler. Liste bilinçli KISA: şüphede olan kelime
# elenmez, çevrilir (içerik kaybı, gürültüden pahalıdır).
FILLER_TOKENS = frozenset(
    "şey şeyy ee eee ııı hmm mmm mm ha he ah eh um uh uhm erm hm".split()
)
_STRIP = " \t\n.,!?;:'\"()[]…"


def _tokens(text: str) -> list[str]:
    return [t for t in (w.strip(_STRIP).casefold() for w in text.split()) if t]


def is_filler_only(text: str) -> bool:
    """Yalnız dolgu sesi mi? Boş metin de dolgu sayılır (çevrilecek şey yok)."""
    tokens = _tokens(text)
    return not tokens or all(t in FILLER_TOKENS for t in tokens)


def looks_incomplete(text: str, min_words: int) -> bool:
    """Devamını beklemeye değer mi?

    Sıra önemli:
    1. Üç nokta ile kesilmişse ("My...") yarımdır — beklenir.
    2. Cümle sonu noktalaması varsa (. ! ?) TAMAMDIR — kısa olsa bile
       beklenmez. Türkçede iki kelimelik cümle normaldir ("Hoş bulduk.");
       ilk taslak bunları bekleterek her kısa cümleye gecikme ekliyordu.
    3. Noktalama yoksa kelime sayısına bakılır (STT cümleyi ortadan kesmiş
       olabilir).
    """
    stripped = text.strip()
    if stripped.endswith("...") or stripped.endswith("…"):
        return True
    if stripped and stripped[-1] in ".!?":
        return False
    return len(_tokens(text)) < min_words


@dataclass(frozen=True)
class Fragment:
    """STT'den gelen ham parça."""

    text: str
    speech_end_ts: float
    stt_final_ts: float


@dataclass(frozen=True)
class Segment:
    """Çevrilmeye hazır söz."""

    text: str
    speech_end_ts: float
    stt_final_ts: float
    parts: int = 1
    merged: bool = False


@dataclass
class _Held:
    text: str
    speech_end_ts: float
    stt_final_ts: float
    parts: int
    deadline: float


@dataclass
class UtteranceCoalescer:
    """Kısa parçaları bekletip birleştirir, dolgu seslerini eler.

    `offer()` ve `due()` çevrilmeye hazır sözlerin listesini döndürür (0, 1 ya
    da 2 öğe: bekletilen bir parça yeni parçayla birleşemiyorsa ikisi de
    sırayla çıkar).
    """

    min_words: int = 3
    hold_s: float = 0.8
    max_parts: int = 3
    dropped_fillers: list[str] = field(default_factory=list)
    _held: _Held | None = None

    def offer(self, fragment: Fragment) -> list[Segment]:
        if is_filler_only(fragment.text):
            # Dolgu sesi bekletilen parçayı da bozmaz; sayılır ve düşer.
            self.dropped_fillers.append(fragment.text.strip())
            return []

        held = self._held
        if held is None:
            return self._admit(fragment)

        if fragment.stt_final_ts <= held.deadline:
            merged_text = f"{held.text} {fragment.text.strip()}".strip()
            parts = held.parts + 1
            self._held = None
            merged = Fragment(merged_text, fragment.speech_end_ts, fragment.stt_final_ts)
            if parts >= self.max_parts:
                # Üst sınır: sonsuz birikme yok, olduğu gibi yayımlanır.
                return [self._segment(merged, parts=parts, merged=True)]
            return self._admit(merged, parts=parts, merged=True)

        # Pencere kapandı: bekletilen tek başına çıkar, yenisi sıraya girer.
        self._held = None
        flushed = self._segment(
            Fragment(held.text, held.speech_end_ts, held.stt_final_ts),
            parts=held.parts,
            merged=held.parts > 1,
        )
        return [flushed, *self._admit(fragment)]

    def due(self, now: float) -> list[Segment]:
        """Bekleme süresi dolan parçayı yayımlar (devamı gelmedi)."""
        held = self._held
        if held is None or now < held.deadline:
            return []
        self._held = None
        return [
            self._segment(
                Fragment(held.text, held.speech_end_ts, held.stt_final_ts),
                parts=held.parts,
                merged=held.parts > 1,
            )
        ]

    def pending(self) -> bool:
        return self._held is not None

    def _admit(
        self, fragment: Fragment, parts: int = 1, merged: bool = False
    ) -> list[Segment]:
        if looks_incomplete(fragment.text, self.min_words):
            self._held = _Held(
                text=fragment.text.strip(),
                speech_end_ts=fragment.speech_end_ts,
                stt_final_ts=fragment.stt_final_ts,
                parts=parts,
                deadline=fragment.stt_final_ts + self.hold_s,
            )
            return []
        return [self._segment(fragment, parts=parts, merged=merged)]

    @staticmethod
    def _segment(fragment: Fragment, parts: int, merged: bool) -> Segment:
        return Segment(
            text=fragment.text.strip(),
            speech_end_ts=fragment.speech_end_ts,
            stt_final_ts=fragment.stt_final_ts,
            parts=parts,
            merged=merged,
        )
