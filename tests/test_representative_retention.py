"""Prova kaydının metin katmanı saklama süresi (kurucu kararları 08-24/08-25).

Denetimin çıkış noktası: `REHEARSAL_RETENTION` yalnız Recall'a giden bot
yüküne yazılıyordu, yani SAĞLAYICI tarafındaki medyayı kapsıyordu. Metin ise
bizim ürettiğimiz yerel `prova*.jsonl` dosyasında (ve `nohup` konsol logunda)
duruyor, hiçbir süreye tabi değildi.

08-25 şartı: temizlik "bir sonraki rig koşusunda" olamaz — rig bir daha hiç
koşmayabilir. Bu dosya, makine açıkken periyodik koşan temizliği ve onun
doğrulanmasını kilitler. DUVAR-SAATİ GARANTİSİ İDDİA EDİLMEZ: uykudaki/kapalı
makinede tur koşmaz ve dosyaya yeni satır eklenince damga tazelendiği için eski
satırlar 24 saati aşabilir (satır-başına süre semantiği uygulanmadı).
"""

from __future__ import annotations

import json
import os
import pathlib
import plistlib

import pytest

from representative.meeting_ingress import REAL_MEETING_RETENTION, REHEARSAL_RETENTION
from representative.pipeline import TEXT_STATE_EXPIRED
from representative.retention import (
    SWEEP_INTERVAL_S,
    SWEEP_MARGIN_HOURS,
    SWEEP_STAMP_MAX_AGE_S,
    SWEEP_STAMP_NAME,
    SWEEPER_LABEL,
    TEXT_FIELDS,
    enforce,
    expire_log,
    expire_text_layer,
    file_age_hours,
    is_expired,
    prune_jsonl,
    require_sweeper,
    sweep,
    sweeper_status,
)

# Fail-closed susturmanın ürettiği dört sebep (bot_rig.speak_assembled_turns).
FAIL_CLOSED_REASONS = (
    "fallback_unknown",
    "held_partial_hold_timeout",
    "held_partial_incomplete_drop",
    "suppressed_duplicate",
)

HOUR = 3600.0


def unspoken_record(text: str, flag_reason: str) -> dict:
    return {
        "source_text": text,
        "source_lang": "",
        "translated_text": "",
        "target_lang": "",
        "confidence": None,
        "flagged": True,
        "flag_reason": flag_reason,
        "latency_ms": 0.0,
        "recorded_at": 4322.0,
        "delivered": False,
        "detected_language": "unknown",
        "direction_reason": "fallback_unknown",
    }


def spoken_record(text: str = "yarın görüşürüz") -> dict:
    return {
        "source_text": text,
        "source_lang": "tr",
        "translated_text": "see you tomorrow",
        "target_lang": "en",
        "confidence": 0.91,
        "flagged": False,
        "flag_reason": "ok",
        "latency_ms": 2130.4,
        "recorded_at": 1234.6,
        "delivered": True,
        "stt_ms": 400.0,
        "translate_ms": 730.4,
        "tts_to_first_audio_ms": 1000.0,
        "e2e_first_audio_ms": 2130.4,
        "direction": "tr->en",
        "direction_reason": "detected",
        "detected_language": "tr",
    }


def aged(path: pathlib.Path, age_hours: float) -> str:
    stamp = os.stat(path).st_mtime - age_hours * HOUR
    os.utime(path, (stamp, stamp))
    return str(path)


def write_jsonl(path: pathlib.Path, records: list[dict], age_hours: float) -> str:
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
    )
    return aged(path, age_hours)


def read_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# --- Doğrulama: mevcut mekanizma bu kayıtları kapsıyor muydu? ----------------


def test_recall_retention_governs_provider_media_not_our_transcript():
    """Denetimin kayda geçmiş hali: iki saklama YERİ var, biri kapsanmıyordu."""
    from representative.meeting_ingress import build_recall_bot_payload
    from representative.retention import POLICIES

    payload = build_recall_bot_payload(
        "https://meet.google.com/abc-defg-hij", REHEARSAL_RETENTION, internal_ref="ref"
    )
    assert payload["recording_config"]["retention"] == {"type": "timed", "hours": 24}
    # Yerel metin katmanı AYNI politika nesnesini kullanır; burada ikinci bir
    # "24" sayısı tanımlanmaz (ayrı politika = ayrı saklama yolu demektir).
    assert POLICIES["rehearsal"] is REHEARSAL_RETENTION
    assert POLICIES["real-meeting"] is REAL_MEETING_RETENTION


@pytest.mark.parametrize("flag_reason", FAIL_CLOSED_REASONS)
def test_fail_closed_source_text_expires_with_the_same_24h_window(tmp_path, flag_reason):
    path = write_jsonl(tmp_path / "prova.jsonl", [unspoken_record("What?", flag_reason)], 24.5)

    result = prune_jsonl(path)

    assert result.expired is True and result.cleared == 1
    (record,) = read_jsonl(path)
    assert record["source_text"] == ""
    assert record["text_state"] == TEXT_STATE_EXPIRED


@pytest.mark.parametrize("flag_reason", FAIL_CLOSED_REASONS)
def test_reason_and_status_fields_survive_expiry(tmp_path, flag_reason):
    """Kalem 1: sebep/durum alanları SÜREKLİ. Silinen yalnız metin katmanı."""
    original = unspoken_record("What?", flag_reason)
    path = write_jsonl(tmp_path / "prova.jsonl", [original], 30.0)

    prune_jsonl(path)

    (record,) = read_jsonl(path)
    for field, value in original.items():
        if field in TEXT_FIELDS:
            continue
        assert record[field] == value, f"{field} korunmalıydı"


def test_spoken_and_unspoken_records_expire_the_same_way(tmp_path):
    """Ayrı yol YOK: seslendirilen ve susturulan satır aynı işleme girer."""
    path = write_jsonl(
        tmp_path / "prova.jsonl",
        [spoken_record(), unspoken_record("What?", "fallback_unknown")],
        25.0,
    )

    result = prune_jsonl(path)

    assert result.cleared == 2
    for record in read_jsonl(path):
        assert record["source_text"] == "" and record["translated_text"] == ""
        assert record["text_state"] == TEXT_STATE_EXPIRED


def test_expire_text_layer_never_looks_at_flag_reason():
    """Süre kararı sebebe bakmaz — bakan bir uygulama muafiyet kapısı açardı."""
    baseline = expire_text_layer(spoken_record())
    for reason in FAIL_CLOSED_REASONS + ("ok", "below_threshold", "uydurma_sebep"):
        pruned = expire_text_layer({**spoken_record(), "flag_reason": reason})
        assert {k: v for k, v in pruned.items() if k != "flag_reason"} == {
            k: v for k, v in baseline.items() if k != "flag_reason"
        }


# --- Süre dolmadan hiçbir şeye dokunulmaz ------------------------------------


@pytest.mark.parametrize("age_hours", [0.0, 1.0, 23.0])
def test_fresh_file_is_left_byte_identical(tmp_path, age_hours):
    """Süre dolmadan yazma YOK: yazmak damgayı tazeleyip süreyi uzatırdı."""
    records = [spoken_record(), unspoken_record("What?", "fallback_unknown")]
    path = write_jsonl(tmp_path / "prova.jsonl", records, age_hours)
    before = pathlib.Path(path).read_bytes()
    mtime_before = os.stat(path).st_mtime

    result = prune_jsonl(path)

    assert result.expired is False and result.cleared == 0
    assert pathlib.Path(path).read_bytes() == before
    assert os.stat(path).st_mtime == mtime_before


def test_expiry_boundary_is_exactly_the_policy_window():
    assert is_expired(23.99, REHEARSAL_RETENTION) is False
    assert is_expired(24.0, REHEARSAL_RETENTION) is True
    assert is_expired(1000.0, REHEARSAL_RETENTION) is True
    # zero saklama = metin hiç yaşamaz (gerçek dış toplantı politikası)
    assert is_expired(0.0, REAL_MEETING_RETENTION) is True


def test_file_without_text_is_not_rewritten(tmp_path):
    """Sıfır saklamayla üretilmiş dosyada silinecek metin yok → damga tazelenmez."""
    textless = {**spoken_record(), "source_text": "", "translated_text": ""}
    path = write_jsonl(tmp_path / "prova.jsonl", [textless], 48.0)
    mtime_before = os.stat(path).st_mtime

    result = prune_jsonl(path)

    assert result.expired is True and result.cleared == 0 and result.written is False
    assert os.stat(path).st_mtime == mtime_before


def test_dry_run_changes_nothing(tmp_path):
    path = write_jsonl(tmp_path / "prova.jsonl", [spoken_record()], 48.0)
    before = pathlib.Path(path).read_bytes()

    result = prune_jsonl(path, dry_run=True)

    assert result.cleared == 1 and result.written is False
    assert pathlib.Path(path).read_bytes() == before


# --- Periyodik temizlik: makine açıkken koşar, garanti değildir --------------


def test_sweeper_margin_removes_a_whole_interval_of_delay():
    """Güvenlik payı silmenin bir tur GECİKMESİNİ önler — garanti üretmez.

    Süpürücü 15 dakikada bir koşuyor; tam 24.0 saatte silmeye kalksaydı, 23.99
    saatlik bir dosya bu turda atlanır ve bir sonraki tura kadar beklerdi. Pay
    bunu kapatır. KAPATMADIĞI şeyler (test edilemez, bu yüzden iddia da
    edilmez): makine uykuda/kapalıysa hiçbir tur koşmaz; dosyaya yeni satır
    eklenince damga tazelendiği için eski satırlar 24 saati aşabilir.
    """
    assert SWEEP_MARGIN_HOURS == pytest.approx(SWEEP_INTERVAL_S / 3600.0)
    just_under = 24.0 - SWEEP_MARGIN_HOURS

    # Düz budama (elle koşu) tam pencereyi uygular: henüz dolmadı.
    assert is_expired(just_under, REHEARSAL_RETENTION) is False
    # Süpürücü aynı dosyayı ŞİMDİ siler; böylece 24 saati aşan metin kalmaz.
    assert is_expired(just_under, REHEARSAL_RETENTION, margin_hours=SWEEP_MARGIN_HOURS) is True


def test_sweep_covers_transcripts_and_console_logs(tmp_path):
    """Konsol logu da kalıcı düz metin yüzeydir (runbook: nohup > prova.log)."""
    write_jsonl(tmp_path / "prova_bot.jsonl", [spoken_record()], 26.0)
    log = tmp_path / "prova_bot.log"
    log.write_text("TR(duyulan)> yarın görüşürüz\nEN> see you tomorrow\n", encoding="utf-8")
    aged(log, 26.0)
    fresh_log = tmp_path / "prova_taze.log"
    fresh_log.write_text("TR(duyulan)> bugünkü söz\n", encoding="utf-8")

    result = sweep(tmp_path)

    assert read_jsonl(str(tmp_path / "prova_bot.jsonl"))[0]["source_text"] == ""
    assert not log.exists(), "süresi dolmuş konsol logu silinmeli"
    assert fresh_log.exists(), "süresi dolmamış log korunmalı"
    assert "prova_bot.log" in result.describe()


def test_sweep_dry_run_touches_nothing(tmp_path):
    path = write_jsonl(tmp_path / "prova_bot.jsonl", [spoken_record()], 26.0)
    log = tmp_path / "prova_bot.log"
    log.write_text("TR(duyulan)> yarın görüşürüz\n", encoding="utf-8")
    aged(log, 26.0)
    before = pathlib.Path(path).read_bytes()

    sweep(tmp_path, dry_run=True)

    assert pathlib.Path(path).read_bytes() == before
    assert log.exists()


def test_zero_policy_does_not_delete_a_running_sessions_log(tmp_path):
    """Sıfır saklamada metin loga zaten düşmez; buradan silmek koşan oturumu vururdu."""
    log = tmp_path / "prova_bot.log"
    log.write_text("saklama: SIFIR\n", encoding="utf-8")

    result = expire_log(str(log), policy=REAL_MEETING_RETENTION)

    assert result.deleted is False and log.exists()


# --- Zamanlayıcı doğrulaması (fail-closed) ----------------------------------


def write_plist(
    tmp_path,
    *,
    directory,
    interval=SWEEP_INTERVAL_S,
    label=SWEEPER_LABEL,
    program=None,
):
    plist = tmp_path / f"{label}.plist"
    with open(plist, "wb") as f:
        plistlib.dump(
            {
                "Label": label,
                "ProgramArguments": [
                    str(program or pathlib.Path(os.__file__)),  # var olan bir yol
                    "-m",
                    "representative.retention",
                    "--sweep",
                    "--dir",
                    str(directory),
                ],
                "StartInterval": interval,
                "RunAtLoad": True,
            },
            f,
        )
    return plist


def beat(directory, age_s: float = 0.0) -> pathlib.Path:
    """Süpürücünün kalp atışı: son koşunun damgası."""
    stamp = pathlib.Path(directory) / SWEEP_STAMP_NAME
    stamp.write_text("1\n", encoding="utf-8")
    if age_s:
        moment = os.stat(stamp).st_mtime - age_s
        os.utime(stamp, (moment, moment))
    return stamp


def test_sweeper_status_ok(tmp_path):
    plist = write_plist(tmp_path, directory=tmp_path)
    beat(tmp_path)

    status = sweeper_status(
        tmp_path, plist_path=plist, loaded_probe=lambda _label: True, platform_name="darwin"
    )

    assert status.healthy is True and status.reason == "ok"
    assert status.interval_s == SWEEP_INTERVAL_S


def test_sweep_writes_its_heartbeat_last(tmp_path):
    """"Kurulu" değil "koşuyor" kanıtı: damga yalnız gerçek süpürmede tazelenir."""
    stamp = tmp_path / SWEEP_STAMP_NAME
    assert not stamp.exists()

    sweep(tmp_path, dry_run=True)
    assert not stamp.exists(), "kuru çalışma kalp atışı üretmemeli"

    sweep(tmp_path)
    assert stamp.exists()


def test_loaded_but_never_running_sweeper_is_not_healthy(tmp_path):
    """Fail-open deliği: plist yüklü ama iş her turda patlıyorsa temizlik sahtedir."""
    plist = write_plist(tmp_path, directory=tmp_path)

    never = sweeper_status(
        tmp_path, plist_path=plist, loaded_probe=lambda _label: True, platform_name="darwin"
    )
    assert never.healthy is False and never.reason == "never_ran"

    beat(tmp_path, age_s=SWEEP_STAMP_MAX_AGE_S + 60)
    stale = sweeper_status(
        tmp_path, plist_path=plist, loaded_probe=lambda _label: True, platform_name="darwin"
    )
    assert stale.healthy is False and stale.reason == "stale_heartbeat"


def test_sweeper_with_a_missing_interpreter_is_not_healthy(tmp_path):
    """Silinmiş worktree'den kurulmuş ajan: plist sağlam görünür, iş koşamaz."""
    plist = write_plist(tmp_path, directory=tmp_path, program=tmp_path / "yok" / "python")
    beat(tmp_path)

    status = sweeper_status(
        tmp_path, plist_path=plist, loaded_probe=lambda _label: True, platform_name="darwin"
    )

    assert status.healthy is False and status.reason == "program_missing"


@pytest.mark.parametrize(
    "case, expected",
    [
        ("missing", "plist_missing"),
        ("interval", "interval_too_long"),
        ("directory", "wrong_directory"),
        ("unloaded", "not_loaded"),
        ("platform", "unsupported_platform"),
    ],
)
def test_sweeper_status_rejects_every_way_the_cleanup_can_be_fake(tmp_path, case, expected):
    """Soru "plist var mı" değil: yeterince sık mı ve DOĞRU dizini mi süpürüyor?"""
    other = tmp_path / "baska"
    other.mkdir()
    plist = write_plist(
        tmp_path,
        directory=other if case == "directory" else tmp_path,
        interval=SWEEP_INTERVAL_S * 10 if case == "interval" else SWEEP_INTERVAL_S,
    )
    if case == "missing":
        plist.unlink()
    beat(tmp_path)

    status = sweeper_status(
        tmp_path,
        plist_path=plist,
        loaded_probe=lambda _label: case != "unloaded",
        platform_name="linux" if case == "platform" else "darwin",
    )

    assert status.healthy is False
    assert status.reason == expected


def test_require_sweeper_refuses_and_names_both_ways_out(tmp_path):
    with pytest.raises(RuntimeError) as excinfo:
        require_sweeper(
            tmp_path,
            plist_path=tmp_path / "yok.plist",
            loaded_probe=lambda _label: False,
            platform_name="darwin",
        )

    message = str(excinfo.value)
    assert "install-retention-sweeper.sh" in message, "kurulum komutu verilmeli"
    assert "real-meeting" in message, "metni hiç saklamama seçeneği verilmeli"


def test_installer_and_template_exist_and_agree_with_the_code():
    """Kurulum betiği koddaki etiketi/aralığı kullanmalı — iki gerçek olmasın."""
    repo = pathlib.Path(__file__).resolve().parents[1]
    script = repo / "ops" / "retention" / "install-retention-sweeper.sh"
    template = repo / "ops" / "retention" / f"{SWEEPER_LABEL}.plist.template"

    assert script.exists() and template.exists()
    body = script.read_text(encoding="utf-8")
    assert SWEEPER_LABEL in body
    assert "SWEEP_INTERVAL_S" in body, "aralık koddan okunmalı, betikte sabit olmamalı"
    assert "--dry-run" in body, "kurulumdan önce ne silineceği gösterilmeli"


# --- Eski dosyalar + bozuk satırlar -----------------------------------------


def test_legacy_records_without_new_fields_still_prune(tmp_path):
    """`delivered`/aşama alanları olmayan eski prova dosyaları okunmaya devam."""
    legacy = {
        "source_text": "eski söz",
        "source_lang": "tr",
        "translated_text": "old utterance",
        "target_lang": "en",
        "confidence": 0.9,
        "flagged": False,
        "flag_reason": "ok",
        "latency_ms": 3490.0,
        "recorded_at": 12.0,
    }
    path = write_jsonl(tmp_path / "eski.jsonl", [legacy], 48.0)

    result = prune_jsonl(path)

    (record,) = read_jsonl(path)
    assert result.cleared == 1
    assert record["source_text"] == "" and record["translated_text"] == ""
    assert record["latency_ms"] == 3490.0 and record["flag_reason"] == "ok"
    assert "delivered" not in record, "olmayan alan uydurulmaz"


def test_half_written_line_is_dropped_instead_of_leaking_text(tmp_path):
    """Çökmede yarım kalmış satır redakte edilemez → süre dolunca DÜŞÜRÜLÜR."""
    path = tmp_path / "prova.jsonl"
    path.write_text(
        json.dumps(spoken_record(), ensure_ascii=False) + '\n{"source_text": "yarım kalmış giz',
        encoding="utf-8",
    )
    aged(path, 25.0)

    result = prune_jsonl(str(path))

    assert result.dropped == 1
    assert "yarım kalmış giz" not in path.read_text(encoding="utf-8")


def test_pruned_file_is_still_readable_by_the_latency_analyzer(tmp_path):
    """Metin gitse de ölçüm yolu çalışmaya devam eder (sebep/durum sürekli)."""
    from representative.latency import analyze, load_records

    records = [spoken_record() for _ in range(4)] + [unspoken_record("What?", "fallback_unknown")]
    path = write_jsonl(tmp_path / "prova.jsonl", records, 26.0)
    before = analyze(load_records(path))

    prune_jsonl(path)
    after = analyze(load_records(path))

    assert after.count == before.count == 5
    assert after.delivered == before.delivered == 4
    assert after.p50_ms == before.p50_ms
    assert after.by_flag_reason == before.by_flag_reason


# --- Kapsam: metni taşıyan her yüzey süreye tabi -----------------------------


def test_every_rig_that_writes_the_transcript_enforces_retention_and_cleanup():
    """Yeni bir yazma yolu eklenirse bu test kırılır (kural = kod, yorum değil)."""
    import representative

    package = pathlib.Path(representative.__file__).parent
    callers = {
        module.name: module.read_text(encoding="utf-8")
        for module in sorted(package.glob("*.py"))
        if module.name != "pipeline.py" and "append_jsonl(" in module.read_text(encoding="utf-8")
    }

    assert callers, "jsonl yazan modül bulunamadı — test kendini doğrulayamıyor"
    for name, text in callers.items():
        assert "enforce_text_retention" in text, f"{name} saklama süresini uygulamıyor"
        assert "require_sweeper" in text, f"{name} periyodik temizliği doğrulamıyor"


def test_enforce_is_a_noop_when_the_file_does_not_exist(tmp_path):
    assert enforce(str(tmp_path / "yok.jsonl")) is None


def test_file_age_uses_the_oldest_available_stamp(tmp_path):
    path = write_jsonl(tmp_path / "prova.jsonl", [spoken_record()], 10.0)
    now = os.stat(path).st_mtime + 2 * HOUR

    assert file_age_hours(path, now) == pytest.approx(2.0, abs=0.01)


def test_dry_run_says_will_delete_not_deleted(tmp_path):
    """Kurulum betiği bu satırları gösterip onay istiyor: kip karışamaz.

    Kuru çalışma "SİLİNDİ" deseydi kurucu, dosyaların gittiğini sanarak onay
    verirdi; "silinecek metin yok" deseydi tersine, hiçbir şey kaybolmayacağını
    sanarak. İki yön de yanlış bilgiyle onaydır.
    """
    path = write_jsonl(tmp_path / "prova_bot.jsonl", [spoken_record()], 48.0)
    log = tmp_path / "prova_bot.log"
    log.write_text("TR(duyulan)> yarın görüşürüz\n", encoding="utf-8")
    aged(log, 48.0)

    preview = sweep(tmp_path, dry_run=True).describe()

    assert "SİLİNECEK" in preview and "kuru çalışma" in preview
    assert "SİLİNDİ" not in preview
    assert "silinecek metin yok" not in preview
    assert pathlib.Path(path).exists() and log.exists()

    applied = sweep(tmp_path).describe()
    assert "SİLİNDİ" in applied and "kuru çalışma" not in applied
