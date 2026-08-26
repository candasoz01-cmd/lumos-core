"""Interpreter pipeline core: stage contracts, confidence gate, latency.

Contract rules (ADR-023 Faz 0, slice doc T1-T6):
- The pipeline never adds to or rewrites translator output (T3/T4).
- Low or missing confidence is flagged, never silently passed (T1/T2).
- Every utterance is appended to a bilingual transcript with latency (T5).
"""

from __future__ import annotations

import json
import re
import statistics
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, fields
from typing import Protocol

from representative.latency import (
    evaluate_first_audio_budget,
    largest_wait_stage,
    percentile_ms,
)
from representative.repair import repair_line
from representative.tts_playback import TtsPlayback


@dataclass(frozen=True)
class Utterance:
    """One finished source-language utterance entering the pipeline."""

    text: str
    source_lang: str  # "tr" | "en"
    target_lang: str
    speech_end_ts: float  # seconds, from the pipeline clock
    # Son birkaç önceki söz (kaynak metin) — çevirmen bağlamı; marka onarımı
    # ve gönderme çözümü için (test 6 sonrası eklendi). Boş olabilir.
    context: tuple[str, ...] = ()
    # STT-final damgası: transkript hazır olduğu an. Yoksa speech_end ile
    # aynı sayılır (metin/stdin rig — STT yok).
    stt_final_ts: float | None = None
    # Bu söz kaç STT parçasından birleşti (1 = birleşme yok). Kayda geçer,
    # çünkü "birleşme güven skorunu nasıl etkiledi?" sorusu ancak birleşmiş
    # sözler işaretliyse ölçülebilir (kurucu ölçüm sırası, 2026-08-23).
    parts: int = 1
    # Yön kararı muhasebesi (2026-08-24 Meet provası): yön kararı konsola
    # basılıyordu ama jsonl'e HİÇ yazılmıyordu, bu yüzden "What?" satırının
    # neden tr→en gittiği dosyadan okunamadı. Karar girdiyle taşınır ki kayıt
    # tek başına teşhis edilebilsin.
    direction_reason: str = ""  # detected | fallback_unknown | fixed | ""
    detected_language: str = ""  # tr | en | unknown — KULLANILAN yönden ayrı
    # Tespit güveni. DİKKAT: kayıttaki `confidence` ile AYNI ŞEY DEĞİLDİR —
    # o, çeviri güveni olup ConfidenceGate'i besler. Bu alan dil tespitine
    # aittir. `detect_lang` kural tabanlıdır, kalibre bir skor ÜRETMEZ;
    # uydurulmuş sayı yazmaktansa None kalır (bkz. rapor).
    language_detection_confidence: float | None = None
    # Bağımsız söz-sonu doğrulaması (2026-08-26). `speech_end_ts` ÖLÇÜLMÜŞ değil,
    # sunucunun `speech_stopped` olayından sabit geri sayımla TÜRETİLMİŞTİR; bu
    # alan aynı ses akışından enerji tabanlı ikinci bir gözlemle arasındaki farkı
    # taşır (bkz. representative.speech_end_probe). None = ölçüm yok.
    server_stop_minus_local_end_ms: float | None = None


@dataclass(frozen=True)
class TranslationResult:
    text: str
    confidence: float | None  # None = provider gave no signal
    provider: str


class Translator(Protocol):
    def translate(self, utterance: Utterance) -> TranslationResult: ...


class TextToSpeech(Protocol):
    def speak(self, text: str, lang: str) -> TtsPlayback | None: ...


@dataclass(frozen=True)
class GateDecision:
    deliver: bool
    flagged: bool
    reason: str


class ConfidenceGate:
    """Blocks low-confidence translations; missing confidence counts as low.

    KURUCU KARARI 2026-08-23 (canlı prova kanıtı — 41 sözün 12'si 0.50-0.70
    güvenle seslendirilmişti): eşik altı çeviri karşı tarafa OKUNMAZ. Yerine
    konuşandan tekrar istenir (`representative.repair`). Bu, 2026-08-17
    "işaretle ama seslendir" kararının (seçenek C) yerini alır — gerekçe:
    yanlış olabilecek cümle karşı tarafın kulağına gitmemeli, kısa boşluk
    daha ucuz.

    Güven sinyali hiç yoksa da teslim edilmez: bilmemek, iyi bilmek değildir.
    """

    def __init__(self, threshold: float) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be within [0, 1]")
        self.threshold = threshold

    def evaluate(self, result: TranslationResult) -> GateDecision:
        if result.confidence is None:
            return GateDecision(deliver=False, flagged=True, reason="no_confidence_signal")
        if result.confidence < self.threshold:
            return GateDecision(deliver=False, flagged=True, reason="below_threshold")
        return GateDecision(deliver=True, flagged=False, reason="ok")


@dataclass(frozen=True)
class UtteranceRecord:
    source_text: str
    source_lang: str
    translated_text: str
    target_lang: str
    confidence: float | None
    flagged: bool
    flag_reason: str
    latency_ms: float
    recorded_at: float
    # Kalem 2 (2026-08-16): çıktı-dili post-check muhasebesi.
    # delivered=False → çıktı TTS'e verilmedi (fail-closed);
    # postcheck_ms = post-check'in eklediği süre (retry çevirisi dahil) —
    # kalem 3 gecikme optimizasyonunda maliyet ayrı görülsün diye ayrı alan.
    delivered: bool = True
    # Kurucu kararı 2026-08-23: teslim edilmeyen çeviride tekrar isteği
    # seslendirilir. Alan ek olduğu için eski jsonl okunmaya devam eder.
    repair_spoken: bool = False
    # Kaç STT parçasından birleşti (1 = tekil söz). Aynı şekilde ek alan.
    parts: int = 1
    postcheck_ms: float = 0.0
    retried: bool = False
    # Aşama kırılımı: p90 sivrilmesinin HANGİ aşamadan geldiği tek toplam
    # süreden okunamıyordu. Zincir: speech-end → STT-final → translation-ready
    # → TTS-start → first-audio. Alanlar ek olduğu için eski jsonl kayıtları
    # okunmaya devam eder.
    stt_ms: float = 0.0
    translate_ms: float = 0.0
    # AD YANILTICI, BİLEREK KORUNUYOR. Gerçek sınır:
    #     translation_ready -> teslim POST'u döndü
    # Meet'te sesin DUYULDUĞU an DEĞİL. Yeniden adlandırmak sessiz sıfır
    # üretir — `latency.py` alan adını sabit yazar ve `r.get(field, 0.0)`
    # eksik alanı hata değil 0 sayar; 52 tarihsel kayıt bu ada bağlı.
    # AÇIK BOŞLUK: sesin toplantıda gerçekten duyulduğu an hâlâ HİÇBİR
    # yerde ölçülmüyor; Recall POST döndükten sonraki kodlama/aktarım
    # süresi bu sayının dışındadır ve buradan çıkarsanamaz.
    tts_to_first_audio_ms: float = 0.0
    # `tts_to_first_audio_ms`in üç parçası (2026-08-25 ölçüm işi). Toplamları
    # ona eşittir; hangi parçanın baskın olduğu ancak böyle okunur. Varsayılan
    # 0.0 — `record_unspoken()` bu alanların HİÇBİRİNİ yazmaz ve yazmamalı.
    tts_synth_ms: float = 0.0  # tts-start -> _synthesize döndü
    tts_gate_wait_ms: float = 0.0  # _synthesize döndü -> kapı alındı
    tts_deliver_ms: float = 0.0  # kapı alındı -> _deliver döndü
    e2e_first_audio_ms: float = 0.0
    # Yön teşhisi (2026-08-24): `direction` KULLANILAN yön, `detected_language`
    # tespitin GERÇEKTEN döndürdüğü dil. İkisi ayrı tutulur çünkü "tespit
    # çalıştı ve yanıldı" ile "tespit hiç çalışmadı, varsayılana düşüldü"
    # farklı hatalardır ve dosyadan ayırt edilebilmeleri gerekir.
    direction: str = ""  # ör. "tr->en"
    direction_reason: str = ""
    detected_language: str = ""
    # Çeviri güveni olan `confidence` ile KARIŞTIRILMAMALI.
    language_detection_confidence: float | None = None
    # Sunucunun durma olayı ile YEREL enerji tabanlı söz sonu arasındaki fark.
    # Beklenen ≈ MEET_VAD_SILENCE_MS. Sistematik olarak BÜYÜKSE `speech_end_ts`
    # geri sayması yetersiz demektir ve `e2e_first_audio_ms` olduğundan İYİ
    # görünüyor demektir. None = ölçülmedi (0.0 ile karıştırılmamalı).
    server_stop_minus_local_end_ms: float | None = None
    # Metin katmanının durumu (2026-08-25 saklama kararı): "" = metin yerinde,
    # "not_persisted" = politika gereği hiç yazılmadı (sıfır saklama),
    # "expired" = süresi doldu, silindi. Boşken jsonl satırına HİÇ yazılmaz
    # (bkz. record_to_dict) — bayt maliyeti yalnız durum varken ödenir.
    text_state: str = ""

    def __post_init__(self) -> None:
        # Yuvarlama KAYIT ÜRETİLİRKEN yapılır (bkz. TIMING_DECIMALS): aşama
        # süreleri tam hassasiyetle hesaplanır, yalnız kayda geçerken kısalır.
        # Hesap sırasında yuvarlansaydı stt+translate+tts toplamı e2e'den
        # sapardı; burada her alan kendi tam değerinden bir kez yuvarlanır.
        for name in TIMING_FIELDS:
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, round(float(value), TIMING_DECIMALS))


# Kurucu kararı (2026-08-24, kalem 4): kayıttaki zamanlama değerleri TEK
# ONDALIĞA yuvarlanır. Gerçek prova dosyasında süre alanları satırın %44'ünü
# tutuyor ve `"latency_ms": 9983.732249998866` gibi yazılıyordu — milisaniye
# altı basamaklar ölçülen bir şey DEĞİL, monotonic saatin artığıdır. Ölçülen
# tasarruf %12, bilgi kaybı yok.
TIMING_DECIMALS = 1

# Liste elle tutulmaz: alanın kendisinden TÜRETİLİR. Elle tutulan bir liste,
# ileride eklenen bir `*_ms` alanının sessizce tam hassasiyette yazılmasına
# yol açardı ve bunu kimse fark etmezdi (tests/test_representative_pipeline.py
# içindeki türetme testi iki yönde de kilitler).
TIMING_FIELDS = tuple(f.name for f in fields(UtteranceRecord) if f.name.endswith("_ms")) + (
    "recorded_at",
)

# Diagnostic (süreli) katman: kaynak ve çeviri metni. Zamanlama listesi gibi
# bu da elle tutulmaz, kayıttan TÜRETİLİR — ileride eklenen bir `*_text` alanı
# sessizce süresiz yaşamasın.
TEXT_FIELDS = tuple(f.name for f in fields(UtteranceRecord) if f.name.endswith("_text"))

TEXT_STATE_NOT_PERSISTED = "not_persisted"
TEXT_STATE_EXPIRED = "expired"


@dataclass(frozen=True)
class TextLayer:
    """Metin katmanının bu oturumda diske/loga yazılıp yazılamayacağı.

    Kurucu kararı (2026-08-25): `zero` saklama YEREL metni de kapsar. Karar TEK
    yerde verilir ve hem KAYIT hem EKRAN aynı nesneden geçer — birini redakte
    edip diğerini unutma yolu kapalıdır.

    Sıfır saklamada GARANTİ EDİLEN:
    - kaynak/çeviri düz metni KALICI HÂLE GETİRİLMEZ (jsonl'e yazılmaz),
    - düz metin konsol/log/markdown çıktısına BASILMAZ,
    - jsonl satırında metin alanları boş kalır + `text_state="not_persisted"`,
    - sebep, teslim durumu, yön ve zamanlama olduğu gibi kalır.

    GARANTİNİN DIŞINDA: işlem sırasında bellekte GEÇİCİ olarak bulunan düz
    metin. STT çıktısı, çeviri istemi ve çeviri sonucu süreç belleğinde düz
    metindir; sağlayıcıya da düz metin gider. Bu katman kalıcılığı ve çıktıyı
    yönetir, belleği değil.
    """

    persists: bool

    # Ekranda boşluk bırakmak "hiçbir şey duyulmadı" gibi okunurdu; yerine
    # neyin ve NEDEN olmadığı yazılır.
    redacted_label = "«metin saklanmıyor (sıfır saklama)»"

    def store(self, text: str) -> str:
        """Kalıcı hâle gelecek metin; sıfır saklamada boş döner.

        "Metin hiç var olmadı" DEMEK DEĞİLDİR — çağıran taraf metni elinde
        tutar (çeviri/TTS onunla çalışır); burada kesilen şey kalıcılıktır.
        """
        return text if self.persists else ""

    def show(self, text: str) -> str:
        """Konsola basılacak metin (stdout kalıcı bir loga yönlenmiş olabilir)."""
        return text if self.persists else self.redacted_label

    @property
    def state(self) -> str:
        return "" if self.persists else TEXT_STATE_NOT_PERSISTED


PERSISTING_TEXT_LAYER = TextLayer(persists=True)


def record_to_dict(record: UtteranceRecord) -> dict:
    """jsonl satırının sözlük hali; boş `text_state` satıra hiç yazılmaz."""
    data = asdict(record)
    if not data.get("text_state"):
        data.pop("text_state", None)
    return data


# Kurucu kararı (2026-08-17, seçenek C): eşik altı çeviri SESLENDİRİLİR ama
# transkript/panelde düşük güven olarak İŞARETLENİR. Gerekçe: susmak
# (seçenek B) toplantıda boşluk yaratır; işaretsiz teslim (seçenek A) şüpheli
# çeviriyi normalmiş gibi sunar. Kullanıcı kalite sinyalini görebilmeli.
#
# Kod tarafında teslim zaten yapılıyordu; eksik olan İŞARETİN OKUNABİLİRLİĞİYDİ:
# transkript "işaretli ama duyuldu" ile "hiç seslendirilmedi"yi aynı gösteriyordu.
_FLAG_LABELS = {
    "ok": "",
    "below_threshold": "⚠ düşük güven (seslendirilmedi, tekrar istendi)",
    "no_confidence_signal": "⚠ güven sinyali yok (seslendirilmedi, tekrar istendi)",
    "undetected_language": "✕ dil belirlenemedi (tekrar istendi)",
    "empty_translation": "✕ boş çeviri",
    "meta_output": "✕ iç etiket (sesli okunmadı)",
    "non_translation_output": "✕ tercüman dışı çıktı",
    "wrong_output_language": "✕ yanlış dil",
    # Seslendirilmeyen erken çıkışlar (2026-08-24). Bunlar düşük güven DEĞİL;
    # söz hiç çeviriye girmedi. Karşı tarafa giden ses davranışı değişmedi,
    # yalnız görünürlük eklendi.
    "held_partial_hold_timeout": "✕ yarım söz (bekleme doldu)",
    "held_partial_incomplete_drop": "✕ yarım söz (tamamlanmadı)",
    "suppressed_duplicate": "✕ tekrar bastırıldı",
    "fallback_unknown": "✕ yön belirlenemedi (çevrilmedi)",
}


_TEXT_STATE_LABELS = {
    TEXT_STATE_NOT_PERSISTED: "«saklanmadı (sıfır saklama)»",
    TEXT_STATE_EXPIRED: "«süresi doldu, silindi»",
}


def _text_cell(text: str, state: str) -> str:
    """Boş hücre "hiçbir şey söylenmedi" gibi okunurdu; sebebi yazılır."""
    return text or _TEXT_STATE_LABELS.get(state, "")


def flag_label(record: "UtteranceRecord") -> str:
    """İşaretin insan tarafından okunur karşılığı (panel/transkript dili)."""
    return _FLAG_LABELS.get(record.flag_reason, f"⚠ {record.flag_reason}")


def undetected_language_record(
    source_text: str, latency_ms: float, recorded_at: float
) -> UtteranceRecord:
    """Dili belirlenemeyen söz için denetim kaydı (kurucu kararı 2026-08-23).

    Eskiden bu sözler sessizce varsayılan yöne (TR) düşüp çevriliyordu; canlı
    provada 41 sözün 3'ü böyleydi ("Translate.", "Hey Hasan, speak English!",
    "네."). Artık çevrilmez, tekrar istenir — ve iz bırakır: kayıt olmadan
    "sessizce düştü" ile "tekrar istendi" ayırt edilemez.

    latency_ms gerçek geçen süredir (söz sonu → tekrar isteği); uydurma 0
    yazılmaz, yoksa gecikme çözümlemesi kendini kandırır.
    """
    return UtteranceRecord(
        source_text=source_text,
        source_lang="unknown",
        translated_text="",
        target_lang="unknown",
        confidence=None,
        flagged=True,
        flag_reason="undetected_language",
        latency_ms=latency_ms,
        recorded_at=recorded_at,
        delivered=False,
        repair_spoken=True,
    )


class BilingualTranscript:
    """Append-only transcript; records are never edited or removed."""

    def __init__(self) -> None:
        self._records: list[UtteranceRecord] = []

    def append(self, record: UtteranceRecord) -> None:
        self._records.append(record)

    @property
    def records(self) -> tuple[UtteranceRecord, ...]:
        return tuple(self._records)

    def to_jsonl(self) -> str:
        """One JSON object per utterance — Aşama C ölçüm kaydı formatı."""
        return "\n".join(json.dumps(record_to_dict(r), ensure_ascii=False) for r in self._records)

    @staticmethod
    def append_jsonl(path: str, record: UtteranceRecord) -> None:
        """Crash-safe incremental log: one line per utterance, flushed at once.

        Prova düzeneği çökse bile o ana kadarki her söz diskte kalır (2026-08-14
        stres testi bulgusu: yalnız çıkışta yazmak çökmede tüm veriyi kaybetti).
        """
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record_to_dict(record), ensure_ascii=False) + "\n")

    def to_markdown(self) -> str:
        lines = [
            "| src | çeviri | güven | teslim | işaret | gecikme (ms) |",
            "|---|---|---|---|---|---|",
        ]
        for r in self._records:
            conf = "-" if r.confidence is None else f"{r.confidence:.2f}"
            delivery = "✓ duyuldu" if r.delivered else "✕ seslendirilmedi"
            lines.append(
                f"| {_text_cell(r.source_text, r.text_state)} | "
                f"{_text_cell(r.translated_text, r.text_state)} | {conf} | {delivery} | "
                f"{flag_label(r)} | {r.latency_ms:.0f} |"
            )
        return "\n".join(lines)


def summarize_latencies_ms(transcript: BilingualTranscript) -> dict[str, float | str | bool]:
    records = transcript.records
    # `analyze()` ile aynı ayrım (2026-08-24 seçenek A): seslendirilmeyen
    # kayıtlar sayımda görünür, gecikme hesabına girmez. record_unspoken()
    # satırları transkripte de eklendiği için bu ikiz yol da kirleniyordu.
    measured = [r for r in records if r.delivered]
    if not measured:
        empty_budget = evaluate_first_audio_budget(0.0, 0.0, count=0)
        return {
            "count": len(records),
            "median_ms": 0.0,
            "max_ms": 0.0,
            "p50_ms": 0.0,
            "p90_ms": 0.0,
            "e2e_first_audio_p50_ms": 0.0,
            "e2e_first_audio_p90_ms": 0.0,
            "stt_p50_ms": 0.0,
            "translate_p50_ms": 0.0,
            "tts_to_first_audio_p50_ms": 0.0,
            "tts_synth_p50_ms": 0.0,
            "tts_gate_wait_p50_ms": 0.0,
            "tts_deliver_p50_ms": 0.0,
            "largest_wait": "",
            "first_audio_budget_pass": False,
            "first_audio_budget_reason": str(empty_budget["reason"]),
        }
    e2e = [r.e2e_first_audio_ms or r.latency_ms for r in measured]
    stt = [r.stt_ms for r in measured]
    translate = [r.translate_ms for r in measured]
    tts0 = [r.tts_to_first_audio_ms for r in measured]
    # Alt-aşamalar da AYNI `measured` örnekleminden. `records` kullanılsaydı
    # seslendirilmeyen satırların 0'ları üçünü birden aşağı çeker, oran
    # bozulmadığı için kırılım "doğru görünürken" mutlak sayılar yalan olurdu.
    tts_synth = [r.tts_synth_ms for r in measured]
    tts_gate = [r.tts_gate_wait_ms for r in measured]
    tts_deliver = [r.tts_deliver_ms for r in measured]
    p50 = percentile_ms(e2e, 50)
    p90 = percentile_ms(e2e, 90)
    stt_p50 = percentile_ms(stt, 50)
    translate_p50 = percentile_ms(translate, 50)
    tts_p50 = percentile_ms(tts0, 50)
    budget = evaluate_first_audio_budget(p50, p90, count=len(measured))
    return {
        "count": len(records),
        "median_ms": statistics.median(e2e),
        "max_ms": max(e2e),
        "p50_ms": p50,
        "p90_ms": p90,
        "e2e_first_audio_p50_ms": p50,
        "e2e_first_audio_p90_ms": p90,
        "stt_p50_ms": stt_p50,
        "translate_p50_ms": translate_p50,
        "tts_to_first_audio_p50_ms": tts_p50,
        "tts_synth_p50_ms": percentile_ms(tts_synth, 50),
        "tts_gate_wait_p50_ms": percentile_ms(tts_gate, 50),
        "tts_deliver_p50_ms": percentile_ms(tts_deliver, 50),
        "largest_wait": largest_wait_stage(stt_p50, translate_p50, tts_p50),
        "first_audio_budget_pass": bool(budget["pass"]),
        "first_audio_budget_reason": str(budget["reason"]),
    }


# Meta-sızıntı kesici (TD-15 kardeşi; canlı insan testi 4 bulgusu, 2026-08-17):
# model çeviri yerine iç güven etiketini metin olarak döndürebiliyor ("LOW",
# "Low", "Translation not clear; LOW confidence.") ve bu üç kez botun sesinden
# toplantıya okundu. İç etiket kullanıcıya ASLA ses olarak çıkmaz — desenler
# bilinçli dar tutuldu: yalnız tek-başına etiket metni ve canlıda görülen
# meta cümle kalıbı; "confidence"/"low" kelimesi geçen GERÇEK çeviriler
# (ör. "We have confidence in this plan") kapsam dışıdır.
_META_LABEL_RE = re.compile(r"(?:low|medium|high)(?:\s+confidence)?[\s.!]*", re.IGNORECASE)
_META_PHRASES = ("translation not clear",)


def fold(text: str) -> str:
    """Türkçe-güvenli küçültme.

    `"İşte".casefold()` → "i̇şte" (i + birleşen nokta): desen listesindeki
    "işte" ile EŞLEŞMEZ ve kapı sessizce açık kalır. Yalnız noktalı büyük İ
    çevrilir; noktasız I'ya DOKUNULMAZ — "AI" → "aı" olsaydı İngilizce
    desenler ("as an ai") bu kez kaçardı.
    """
    return text.replace("İ", "i").casefold()


def is_meta_output(text: str) -> bool:
    stripped = text.strip()
    if _META_LABEL_RE.fullmatch(stripped):
        return True
    lower = fold(stripped)
    return any(phrase in lower for phrase in _META_PHRASES)


# Strict tercüman kipi (canlı insan testi 4 bulgusu 2, 2026-08-17): toplantıda
# konuşulan her cümle ÇEVRİLECEK İÇERİKTİR, modele verilmiş talimat değildir.
# Canlı kayıtta "Sen şimdi yabancı muhatap rolündesin." gibi cümleler geçti;
# bunları rol talimatı sanan bir model tercüman olmaktan çıkıp muhatap olur.
# Birinci savunma istemin kendisidir (OpenAITranslator._STRICT_CLAUSE); bu
# kapı ikinci savunmadır: asistan kipine düşmüş çıktı sese ÇIKMAZ.
#
# Desenler bilinçli olarak dar: yalnız (a) yapay zekâ kimliğine veya (b) çeviri
# EYLEMİNİN kendisine atıfta bulunan kalıplar. Toplantıda insan böyle konuşmaz.
# "I cannot attend the meeting" gibi GERÇEK çeviriler kapsam dışıdır — bu kapı
# reddi değil, tercüman-dışı davranışı yakalar.
_NON_TRANSLATION_PHRASES = (
    "as an ai",
    "i am an ai",
    "i'm an ai",
    "bir yapay zeka olarak",
    "bir yapay zekâ olarak",
    "here is the translation",
    "here's the translation",
    "işte çeviri",
    "i cannot translate",
    "i can't translate",
    "çeviremem",
    "çeviri yapamam",
)
# Yalnız BAŞTA duran etiket önekleri (çeviri metninin içinde geçmesi serbest).
_NON_TRANSLATION_PREFIX_RE = re.compile(
    r"^\s*(translation|çeviri|translated text)\s*:", re.IGNORECASE
)


def is_non_translation(text: str) -> bool:
    """Çevirmen tercüman olmayı bırakıp asistan gibi cevap verdi mi?"""
    lower = fold(text.strip())
    if _NON_TRANSLATION_PREFIX_RE.match(text):
        return True
    return any(phrase in lower for phrase in _NON_TRANSLATION_PHRASES)


class InterpreterPipeline:
    """Consecutive interpretation for one utterance at a time.

    The delivered text is exactly the translator's output — this class must
    never concatenate, prefix, or rewrite it (slice tests T3/T4 pin this).
    """

    def __init__(
        self,
        translator: Translator,
        tts: TextToSpeech,
        gate: ConfidenceGate,
        transcript: BilingualTranscript,
        on_flag: Callable[[UtteranceRecord], None] | None = None,
        on_record: Callable[[UtteranceRecord], None] | None = None,
        clock: Callable[[], float] = time.monotonic,
        text_layer: TextLayer = PERSISTING_TEXT_LAYER,
    ) -> None:
        self._translator = translator
        self._tts = tts
        self._gate = gate
        self._transcript = transcript
        self._on_flag = on_flag
        self._on_record = on_record
        self._clock = clock
        # Rig'ler ekrana basarken de buradan geçer (`pipeline.text_layer.show`);
        # böylece konsol ile kayıt aynı politikayı paylaşır, ayrışamaz.
        self.text_layer = text_layer

    def interrupt_playback(self) -> int:
        """Barge-in: drop queued TTS clips. Current clip finishes (echo-safe)."""
        barge = getattr(self._tts, "barge_in", None)
        if callable(barge):
            return int(barge())
        return 0

    def record_unspoken(
        self,
        text: str,
        *,
        flag_reason: str,
        detected_language: str = "",
        direction_reason: str = "",
    ) -> UtteranceRecord:
        """Seslendirilmeyen sözü ÇEVİRMEDEN kayda geçirir (2026-08-24 kararı).

        `speak_assembled_turns` üç yerde pipeline'a hiç uğramadan `continue`
        ediyordu: yarım söz tutma, tekrar bastırma ve (yeni) yön
        belirlenemeyen söz. Sonuç: turn davranışı — yani PR #797'nin asıl
        iddiası — jsonl'e tek satır bile yazmıyor, yalnız akıp giden konsol
        çıktısı olarak var oluyordu. İz bırakmayan davranış ölçülemez.

        Bu yol çevirmene ve TTS'e DOKUNMAZ: karşı tarafa giden ses davranışı
        aynı kalır, yalnız kayıt eklenir. `on_flag` bilinçli olarak
        çağrılmaz — o kanca "düşük güven" mesajı basıyor, oysa buradaki
        kayıtların güvenle ilgisi yok (söz çeviriye hiç girmedi).
        """
        record = UtteranceRecord(
            source_text=self.text_layer.store(text),
            text_state=self.text_layer.state,
            source_lang="",
            translated_text="",
            target_lang="",
            confidence=None,
            flagged=True,
            flag_reason=flag_reason,
            latency_ms=0.0,
            recorded_at=self._clock(),
            delivered=False,
            detected_language=detected_language,
            direction_reason=direction_reason,
        )
        self._transcript.append(record)
        if self._on_record is not None:
            self._on_record(record)
        return record

    def process(self, utterance: Utterance) -> UtteranceRecord:
        from representative.langcheck import detect_lang

        result = self._translator.translate(utterance)
        postcheck_ms = 0.0
        retried = False
        lang_ok = detect_lang(result.text) in ("unknown", utterance.target_lang)
        if not lang_ok:
            # Kurucu kuralı (2026-08-16): EN FAZLA 1 yeniden çeviri; döngü yok.
            retried = True
            retry_start = self._clock()
            retry_result = self._translator.translate(utterance)
            postcheck_ms = (self._clock() - retry_start) * 1000.0
            if detect_lang(retry_result.text) in ("unknown", utterance.target_lang):
                result = retry_result
                lang_ok = True

        decision = self._gate.evaluate(result)
        repair_spoken = False
        translation_ready = self._clock()
        tts_start = translation_ready
        first_audio = translation_ready
        # Seslendirme hiç olmazsa üçü de 0.0 kalır (fail-closed dallar).
        tts_synth_ms = 0.0
        tts_gate_wait_ms = 0.0
        tts_deliver_ms = 0.0
        if not result.text.strip():
            # Test 7 bug'ı: model boş çeviri döndürebilir — boş metin
            # seslendirilmez, işaretli düşer (fail-closed).
            lang_ok = False
            flagged, reason = True, "empty_translation"
        elif is_meta_output(result.text):
            # Canlı insan testi 4: iç güven etiketi çeviri sanılıp
            # seslendirildi — meta çıktı TTS'e verilmez (fail-closed);
            # metin transkriptte denetim için aynen kalır.
            lang_ok = False
            flagged, reason = True, "meta_output"
        elif is_non_translation(result.text):
            # Strict kip: model tercüman olmayı bırakıp asistan gibi cevap
            # verdiyse (rol talimatı sanılan cümle, "İşte çeviri:" etiketi,
            # yapay zekâ kimliği) çıktı seslendirilmez.
            lang_ok = False
            flagged, reason = True, "non_translation_output"
        elif not decision.deliver:
            # Kurucu kararı 2026-08-23: eşik altı/sinyalsiz çeviri karşı tarafa
            # OKUNMAZ; yerine tekrar istenir. İstek konuşanın dilinde kurulur
            # ama ortak ses kanalından TÜM katılımcılar duyar (özel kanal yok).
            # Çeviri metni transkriptte denetim için kalır, yalnız seslendirilmez.
            self._tts.speak(repair_line(utterance.source_lang), utterance.source_lang)
            repair_spoken = True
            lang_ok = False
            flagged, reason = decision.flagged, decision.reason
        elif lang_ok:
            tts_start = self._clock()
            # Chunked oynatıcı ilk klibin damgasını döndürür: ölçülen şey
            # "tüm paragraf bitti" değil, Meet'te İLK SESİN duyulduğu an.
            playback = self._tts.speak(result.text, utterance.target_lang)
            first_audio = self._clock()
            if isinstance(playback, TtsPlayback):
                tts_start = playback.tts_start_ts
                first_audio = playback.first_audio_ts
                # Damgasız oynatıcı (stub/eski TTS) 0.0 döndürür; toplam
                # `tts_to_first_audio_ms` her hâlükârda eskisi gibi hesaplanır.
                tts_synth_ms = playback.synth_ms
                tts_gate_wait_ms = playback.gate_wait_ms
                tts_deliver_ms = playback.deliver_ms
            flagged, reason = decision.flagged, decision.reason
        else:
            # Fail-closed: ikinci çıktı da yanlış dilde — TTS'e verilmez.
            flagged, reason = True, "wrong_output_language"
        stt_final = (
            utterance.stt_final_ts
            if utterance.stt_final_ts is not None
            else utterance.speech_end_ts
        )
        stt_ms = max(0.0, (stt_final - utterance.speech_end_ts) * 1000.0)
        translate_ms = max(0.0, (translation_ready - stt_final) * 1000.0)
        tts_to_first_ms = max(0.0, (first_audio - tts_start) * 1000.0)
        e2e_ms = max(0.0, (first_audio - utterance.speech_end_ts) * 1000.0)
        latency_ms = (
            e2e_ms
            if lang_ok
            else max(0.0, (translation_ready - utterance.speech_end_ts) * 1000.0)
        )
        record = UtteranceRecord(
            source_text=self.text_layer.store(utterance.text),
            source_lang=utterance.source_lang,
            translated_text=self.text_layer.store(result.text),
            text_state=self.text_layer.state,
            target_lang=utterance.target_lang,
            confidence=result.confidence,
            flagged=flagged,
            flag_reason=reason,
            latency_ms=latency_ms,
            recorded_at=first_audio if lang_ok else translation_ready,
            delivered=lang_ok,
            repair_spoken=repair_spoken,
            parts=utterance.parts,
            postcheck_ms=postcheck_ms,
            retried=retried,
            stt_ms=stt_ms,
            translate_ms=translate_ms,
            tts_to_first_audio_ms=tts_to_first_ms,
            tts_synth_ms=tts_synth_ms,
            tts_gate_wait_ms=tts_gate_wait_ms,
            tts_deliver_ms=tts_deliver_ms,
            e2e_first_audio_ms=e2e_ms if lang_ok else 0.0,
            direction=f"{utterance.source_lang}->{utterance.target_lang}",
            direction_reason=utterance.direction_reason,
            detected_language=utterance.detected_language,
            language_detection_confidence=utterance.language_detection_confidence,
            server_stop_minus_local_end_ms=utterance.server_stop_minus_local_end_ms,
        )
        self._transcript.append(record)
        if self._on_record is not None:
            self._on_record(record)
        if record.flagged and self._on_flag is not None:
            self._on_flag(record)
        return record
