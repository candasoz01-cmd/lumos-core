"""Sıfır saklama YEREL metni de kapsar (kurucu şartı 2026-08-25, şart 2).

Denetimin çıkış noktası: `REAL_MEETING_RETENTION` (zero) yalnız Recall'a giden
bot yüküne yazılıyordu — yani SAĞLAYICI tarafındaki medyayı yönetiyordu. Metni
taşıyan yerel yüzeyler (kendi ürettiğimiz `prova*.jsonl` ve `nohup ... >
prova.log` ile kalıcılaşan konsol çıktısı) politikanın DIŞINDAYDI.

Burada kilitlenen: sıfır saklamada metin hiç ÜRETİLMEZ (sonradan silinmez),
ama sebep/teslim/yön/zamanlama olduğu gibi kalır.
"""

from __future__ import annotations

import ast
import json
import pathlib

import pytest

from representative.meeting_ingress import REAL_MEETING_RETENTION, REHEARSAL_RETENTION
from representative.pipeline import (
    TEXT_FIELDS,
    TEXT_STATE_NOT_PERSISTED,
    BilingualTranscript,
    ConfidenceGate,
    InterpreterPipeline,
    TranslationResult,
    Utterance,
)
from representative.retention import POLICIES, text_layer_for


class _Echo:
    def translate(self, utterance):
        return TranslationResult(text="see you tomorrow", confidence=0.95, provider="stub")


class _Tts:
    def speak(self, text, lang):
        return None


def read_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run_pipeline_with(policy, path: str | None = None):
    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=_Echo(),
        tts=_Tts(),
        gate=ConfidenceGate(0.8),
        transcript=transcript,
        on_record=((lambda r: BilingualTranscript.append_jsonl(path, r)) if path else None),
        text_layer=text_layer_for(policy),
    )
    pipeline.process(
        Utterance(text="yarın görüşürüz", source_lang="tr", target_lang="en", speech_end_ts=0.0)
    )
    pipeline.record_unspoken("What?", flag_reason="fallback_unknown")
    return pipeline, transcript


# --- Kayıt yüzeyi ------------------------------------------------------------


def test_zero_retention_never_writes_text_to_the_transcript(tmp_path):
    path = str(tmp_path / "prova.jsonl")
    run_pipeline_with(REAL_MEETING_RETENTION, path)

    for record in read_jsonl(path):
        assert record["source_text"] == "" and record["translated_text"] == ""
        assert record["text_state"] == TEXT_STATE_NOT_PERSISTED
    raw = pathlib.Path(path).read_text(encoding="utf-8")
    assert "yarın görüşürüz" not in raw and "see you tomorrow" not in raw


def test_zero_retention_keeps_operational_metadata(tmp_path):
    """Silinen yalnız metin: sebep, teslim durumu, yön ve zamanlama kalır."""
    path = str(tmp_path / "prova.jsonl")
    run_pipeline_with(REAL_MEETING_RETENTION, path)
    spoken, unspoken = read_jsonl(path)

    assert spoken["delivered"] is True and spoken["direction"] == "tr->en"
    assert spoken["flag_reason"] == "ok" and spoken["e2e_first_audio_ms"] >= 0.0
    assert unspoken["delivered"] is False
    assert unspoken["flag_reason"] == "fallback_unknown"


def test_transient_in_memory_plaintext_is_outside_the_guarantee():
    """Garantinin sınırı açıkça test edilir: kesilen KALICILIK, bellek değil.

    Çeviri hattı düz metinle çalışır — STT çıktısı, çeviri istemi ve çeviri
    sonucu süreç belleğinde düz metindir ve sağlayıcıya düz metin gider.
    "Metin hiç var olmadı" DENMİYOR; denen şey, o metnin kalıcı bir yüzeye
    (kayıt/konsol/markdown) geçmediğidir.
    """
    seen = {}

    class _Spy:
        def translate(self, utterance):
            seen["source"] = utterance.text  # çevirmen düz metni GÖRÜR
            return TranslationResult(text="see you tomorrow", confidence=0.95, provider="spy")

    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=_Spy(),
        tts=_Tts(),
        gate=ConfidenceGate(0.8),
        transcript=transcript,
        text_layer=text_layer_for(REAL_MEETING_RETENTION),
    )
    pipeline.process(
        Utterance(text="yarın görüşürüz", source_lang="tr", target_lang="en", speech_end_ts=0.0)
    )

    assert seen["source"] == "yarın görüşürüz", "hat düz metinle çalışmaya devam eder"
    assert pipeline.text_layer.store("yarın görüşürüz") == ""
    assert all(r.source_text == "" and r.translated_text == "" for r in transcript.records)


# --- Sentinel: bilinen bir metin hiçbir kalıcı yüzeye sızmamalı ---------------

SENTINEL_SOURCE = "SIZINTI-KAYNAK-7f3a yarın öğleden sonra görüşelim"
SENTINEL_TRANSLATION = "LEAK-TRANSLATION-7f3a let us meet tomorrow afternoon"


class _SentinelTranslator:
    def translate(self, utterance):
        return TranslationResult(text=SENTINEL_TRANSLATION, confidence=0.95, provider="stub")


def drive_bot_rig_console(policy, jsonl_path: str):
    """Gerçek rig konsol yolunu koşturur (bot_rig.speak_assembled_turns).

    Üç dal birden: seslendirilen söz, yarım söz ve tekrar bastırma — üçü de
    kaynak metni ekrana basan kod yollarıdır.
    """
    from collections import deque

    from representative.audio import RepeatSuppressor
    from representative.bot_rig import speak_assembled_turns
    from representative.routing import Direction, DirectionRouter
    from representative.turns import AssembledTurn

    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=_SentinelTranslator(),
        tts=_Tts(),
        gate=ConfidenceGate(0.8),
        transcript=transcript,
        on_record=lambda r: BilingualTranscript.append_jsonl(jsonl_path, r),
        text_layer=text_layer_for(policy),
    )
    turns = [
        AssembledTurn(text=SENTINEL_SOURCE, speech_end_ts=1.0, speakable=True, reason="complete"),
        AssembledTurn(
            text=SENTINEL_SOURCE + " ve", speech_end_ts=1.5, speakable=False,
            reason="incomplete_drop",
        ),
        AssembledTurn(text=SENTINEL_SOURCE, speech_end_ts=2.0, speakable=True, reason="complete"),
    ]
    speak_assembled_turns(
        turns,
        pipeline=pipeline,
        router=DirectionRouter(Direction("tr", "en"), bidirectional=False),
        suppressor=RepeatSuppressor(),
        recent=deque(maxlen=4),
        now=2.0,
    )
    return transcript


def test_sentinel_plaintext_reaches_no_persistent_surface_under_zero_retention(tmp_path, capsys):
    """Üç yüzey birden: jsonl, yakalanan stdout/stderr ve üretilen markdown."""
    path = str(tmp_path / "prova.jsonl")
    transcript = drive_bot_rig_console(REAL_MEETING_RETENTION, path)

    captured = capsys.readouterr()
    console = captured.out + captured.err
    persisted = pathlib.Path(path).read_text(encoding="utf-8")
    markdown = transcript.to_markdown()

    for sentinel in (SENTINEL_SOURCE, SENTINEL_TRANSLATION):
        assert sentinel not in persisted, "kalıcı kayda sızdı"
        assert sentinel not in console, "konsola/loga sızdı"
        assert sentinel not in markdown, "markdown çıktısına sızdı"

    # Test boşa dönmesin: kayıtlar GERÇEKTEN üretildi, yalnız metinsiz.
    records = read_jsonl(path)
    assert len(records) >= 2
    assert all(r["text_state"] == TEXT_STATE_NOT_PERSISTED for r in records)
    assert console.strip(), "konsol yolu hiç koşmadıysa test bir şey kanıtlamaz"


def test_the_sentinel_detector_actually_catches_a_leak(tmp_path, capsys):
    """Yakalayamayan bir sızıntı testi işe yaramaz: aynı kurulum `rehearsal`da
    üç yüzeyde de sentinel'i BULMALI. Bulmazsa üstteki test sahte güven verir.
    """
    path = str(tmp_path / "prova.jsonl")
    transcript = drive_bot_rig_console(REHEARSAL_RETENTION, path)

    captured = capsys.readouterr()
    console = captured.out + captured.err
    persisted = pathlib.Path(path).read_text(encoding="utf-8")
    markdown = transcript.to_markdown()

    assert SENTINEL_SOURCE in persisted and SENTINEL_TRANSLATION in persisted
    assert SENTINEL_SOURCE in console and SENTINEL_TRANSLATION in console
    assert SENTINEL_SOURCE in markdown and SENTINEL_TRANSLATION in markdown


# --- Konsol yüzeyi (nohup ile kalıcılaşır) -----------------------------------


def test_zero_retention_redacts_the_console_surface():
    pipeline, transcript = run_pipeline_with(REAL_MEETING_RETENTION)
    layer = pipeline.text_layer

    assert layer.persists is False
    assert layer.show("yarın görüşürüz") == layer.redacted_label
    assert "yarın görüşürüz" not in transcript.to_markdown()
    assert "«saklanmadı" in transcript.to_markdown(), "boş hücre değil, sebep yazılmalı"


# --- Konsol kilidi: biçimden bağımsız AST denetimi ---------------------------
# PR #805 Bugbot bulgusu (Medium, doğrulandı): önceki denetleyici yalnız
# f-string `{...}` gruplarını tarıyordu. `print(turn.text)`, `print("TR>",
# turn.text)`, `%` biçimlendirme, `.format()` ve `logging.info(...)` hiç
# eşleşmiyordu — yani koruma yeşilken düz metin `prova.log`'a ulaşabilirdi.
# İddia da kapsamdan genişti ("çıplak print eklenirse test kırılır" — kırılmazdı).
#
# Yeni denetim kaynağı AST üzerinden okur, dolayısıyla YAZIM BİÇİMİNDEN
# BAĞIMSIZDIR: bir çıktı çağrısının argüman ağacında toplantı metni taşıyan
# bir ifade varsa ve `show(...)` içinden geçmiyorsa bulgu üretir.

TEXT_ATTRS = frozenset({"text", "translated_text", "source_text"})

# Fail-closed: `.text` taşıyan HER nesne toplantı metni sayılır. İstisna tek ve
# gerekçeli: `warm`, çevirmen ısıtmasının sabit "Merhaba." çıktısıdır —
# toplantıdan gelen bir söz değildir (bot_rig ön uçuş satırı).
NON_MEETING_OBJECTS = frozenset({"warm"})

# Dönüşüm çağrısından doğduğu için türetilemeyen, metin taşıyan yerel adlar
# (bkz. _alias_names bilinen sınırı). Yeni bir tane eklenirse buraya yazılır.
TEXT_LOCALS = frozenset({"heard_text"})

OUTPUT_FUNCS = frozenset({"print"})
OUTPUT_METHODS = frozenset({"write", "info", "warning", "error", "debug", "exception"})


def _is_show_call(node: ast.AST) -> bool:
    func = getattr(node, "func", None)
    if isinstance(func, ast.Name):
        return func.id == "show"
    if isinstance(func, ast.Attribute):
        return func.attr == "show"
    return False


def _is_output_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Name):
        return node.func.id in OUTPUT_FUNCS
    if isinstance(node.func, ast.Attribute):
        return node.func.attr in OUTPUT_METHODS
    return False


def _is_text_expr(node: ast.AST, alias_names: set[str]) -> bool:
    if isinstance(node, ast.Attribute) and node.attr in TEXT_ATTRS:
        base = node.value
        return not (isinstance(base, ast.Name) and base.id in NON_MEETING_OBJECTS)
    return isinstance(node, ast.Name) and node.id in alias_names


def _unredacted(node: ast.AST, alias_names: set[str]) -> list[str]:
    """`show(...)` altına inmeden, ağaçtaki redakte edilmemiş metin ifadeleri."""
    if isinstance(node, ast.Call) and _is_show_call(node):
        return []  # show() altındaki her şey politikadan geçmiş sayılır
    if _is_text_expr(node, alias_names):
        return [ast.unparse(node)]
    found: list[str] = []
    for child in ast.iter_child_nodes(node):
        found.extend(_unredacted(child, alias_names))
    return found


def _yields_text(node: ast.AST, names: set[str]) -> bool:
    """Bu ifadenin DEĞERİ metnin kendisi mi? (atama zinciri takibi için)

    Keyfi bir çağrının dönüşü bilinemez: `decision = router.route(turn.text)`
    metin ALMASINA rağmen metin DÖNDÜRMEZ. Bu yüzden çağrılar zinciri keser —
    aksi hâlde `record`, `decision`, `marker` gibi adlar metin sayılıp
    yanlış pozitif üretirdi.
    """
    if isinstance(node, ast.Call):
        return False
    if _is_text_expr(node, names):
        return True
    if isinstance(node, (ast.Subscript, ast.BinOp, ast.JoinedStr, ast.IfExp, ast.FormattedValue)):
        return any(_yields_text(child, names) for child in ast.iter_child_nodes(node))
    return False


def _alias_names(tree: ast.AST) -> set[str]:
    """Metin taşıyan yerel adlar kaynaktan türetilir; zincir sabit noktaya kadar.

    `first = turn.text` → `second = first` → `print(second)` yakalanır.

    BİLİNEN SINIR: bir dönüşüm ÇAĞRISINDAN doğan adlar türetilemez
    (`heard_text = corrector.correct(heard.text)` metin döndürür ama
    `router.route(turn.text)` döndürmez; ikisi de aynı şekle sahip). Bu yüzden
    o adlar TEXT_LOCALS'ta açıkça sayılır — sayının kendisi kısa tutulur ve
    gerekçesi budur.
    """
    names: set[str] = set(TEXT_LOCALS)
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not _yields_text(node.value, names):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id not in names:
                    names.add(target.id)
                    changed = True
    return names


def unredacted_text_output(source: str) -> list[str]:
    """Çıktı çağrılarında redakte edilmemiş toplantı metni ifadeleri."""
    tree = ast.parse(source)
    aliases = _alias_names(tree)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not _is_output_call(node):
            continue
        for argument in list(node.args) + [kw.value for kw in node.keywords]:
            offenders.extend(_unredacted(argument, aliases))
    return offenders


def test_no_rig_prints_meeting_text_without_the_text_layer():
    """Yalnız jsonl'i redakte etmek yetmez: `nohup ... > prova.log` konsolu da
    kalıcı bir düz metin kopyasına çevirir. Bu yüzden rig'lerdeki HER çıktı
    çağrısı (print / logging / write) AST üzerinden denetlenir: toplantı metni
    taşıyan bir ifade `show()` içinden geçmiyorsa test kırılır — yazım biçimi
    ne olursa olsun.
    """
    import representative

    package = pathlib.Path(representative.__file__).parent
    offenders = []
    for module in sorted(package.glob("*_rig.py")):
        for expression in unredacted_text_output(module.read_text(encoding="utf-8")):
            offenders.append(f"{module.name}: {expression}")
    assert not offenders, "redakte edilmemiş metin basımı: " + "; ".join(offenders)


@pytest.mark.parametrize(
    "snippet",
    [
        'print(f"TR> {turn.text}")',
        "print(turn.text)",
        'print("TR>", turn.text)',
        'print("TR> %s" % record.translated_text)',
        'print("TR> {}".format(utt.text))',
        "logging.info(turn.text)",
        "sys.stdout.write(turn.text)",
        'print(f"TR> {heard.text[:40]}")',
        "heard_text = corrector.correct(heard.text)\nprint(heard_text)",
        "first = turn.text\nsecond = first\nprint(second)",
    ],
)
def test_the_console_lock_catches_every_output_shape(snippet):
    """Denetleyicinin KENDİ testi (PR #805 Medium bulgusunun kapanışı).

    Yakalayamayan bir koruma, korumasızlıktan daha kötüdür: yeşil görünür.
    Eski regex bu satırların yalnız f-string olanlarını yakalıyordu; listedeki
    her biçim artık bulgu üretmek ZORUNDA.
    """
    assert unredacted_text_output(snippet), f"kaçırıldı: {snippet}"


@pytest.mark.parametrize(
    "snippet",
    [
        'print(f"TR> {show(turn.text)}")',
        "print(show(turn.text))",
        'print("TR>", pipeline.text_layer.show(record.translated_text))',
        'print(f"  (yarım söz seslendirilmedi: {turn.reason})")',
        'print(f"çevirmen: GEÇTİ (örnek çıktı: {warm.text[:40]!r})")',
        "print(f'{record.latency_ms:.0f} ms')",
    ],
)
def test_the_console_lock_does_not_cry_wolf(snippet):
    """Yanlış pozitif üreten bir koruma da işe yaramaz: susturulur.

    `show()` içinden geçen metin, metin olmayan alanlar (`reason`, süreler) ve
    toplantıdan gelmeyen ısıtma çıktısı (`warm.text`) bulgu ÜRETMEZ.
    """
    assert not unredacted_text_output(snippet), f"yanlış pozitif: {snippet}"


# --- Politika tek kaynaktan gelir -------------------------------------------


def test_the_same_policy_object_governs_provider_media_and_local_text():
    """İkinci bir politika tanımlamak ikinci bir saklama yolu demek olurdu."""
    from representative.meeting_ingress import build_recall_bot_payload

    payload = build_recall_bot_payload(
        "https://meet.google.com/abc-defg-hij", REAL_MEETING_RETENTION, internal_ref="ref"
    )
    assert payload["recording_config"]["retention"] is None  # sıfır saklama
    assert POLICIES["real-meeting"] is REAL_MEETING_RETENTION
    assert POLICIES["rehearsal"] is REHEARSAL_RETENTION
    assert text_layer_for(POLICIES["real-meeting"]).persists is False


def test_text_layer_follows_the_policy_kind():
    assert text_layer_for(REHEARSAL_RETENTION).persists is True
    assert text_layer_for(REAL_MEETING_RETENTION).persists is False
    with pytest.raises(ValueError):
        text_layer_for("timed/24h")  # type: ignore[arg-type]


def test_rehearsal_retention_still_keeps_text(tmp_path):
    """Varsayılan davranış değişmedi: kapalı provada metin yazılmaya devam eder."""
    path = str(tmp_path / "prova.jsonl")
    pipeline, _ = run_pipeline_with(REHEARSAL_RETENTION, path)

    assert pipeline.text_layer.persists is True
    assert pipeline.text_layer.show("yarın görüşürüz") == "yarın görüşürüz"
    records = read_jsonl(path)
    assert records[0]["source_text"] == "yarın görüşürüz"
    assert "text_state" not in records[0], "boş durum satıra yazılmamalı (bayt)"


def test_text_layer_fields_are_derived_from_the_record():
    """Türetme testi: metin alanları elle sayılmaz, kayıttan çıkarılır."""
    import dataclasses

    from representative.pipeline import UtteranceRecord

    names = {f.name for f in dataclasses.fields(UtteranceRecord)}
    assert set(TEXT_FIELDS) == {n for n in names if n.endswith("_text")}
    assert "flag_reason" not in TEXT_FIELDS and "detected_language" not in TEXT_FIELDS
