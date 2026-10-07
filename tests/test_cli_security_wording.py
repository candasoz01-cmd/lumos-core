"""CLI güvenlik dili: kamera/presence güvenliğin kendisi değildir.

Presence (kamera tabanlı otomatik kilit) isteğe bağlı, varsayılan kapalı ve
kişiyi ayırt etmeyen bir demodur (ADR-007, ADR-010). Kapalı olması güvenlik
cevabını düşürmez; açık olması toplu bir "korumalar aktif" hükmü üretmez.
Aynı gerçek durum için `durum` ile "şu an güvenli miyim" birbirini çürütmez.
"""
from pathlib import Path

import pytest

import core.startup_health as startup_health
from cli.cli_parse import (
    _get_en_onemli_eksik,
    _get_guvenli_cevap,
    _get_mod_cevabi,
    _get_oneri,
    _get_tek_sonraki_adim,
)
from core.startup_health import get_durum_parts
from core.state import format_durum

MISLEADING = (
    "kısmen güvenlisin",
    "Temel korumalar aktif",
    "Şu an güvenlisin",
    "İstersen kamera aç",
    "kamera/presence aç",
    "temel güvenlik durumu tam değil",
    "güvenli offline",
)


def _presence(enabled: bool = False, broken: bool = False):
    class Cfg:
        pass

    Cfg.enabled = enabled

    class Mod:
        def load_presence_cfg(self, base_dir: Path):
            if broken:
                raise OSError("unreadable")
            return Cfg()

    return Mod()


@pytest.fixture(autouse=True)
def _pinned_host(monkeypatch):
    """Host platformu ve kamera izni sabit: macOS'ta da aynı sonuç, gerçek kamera açılmaz.
    Darwin davranışını sınayan test bunları kendi içinde yeniden ayarlar."""
    monkeypatch.setattr(startup_health.platform, "system", lambda: "Linux")
    monkeypatch.setattr(startup_health, "_macos_permissions_ok", lambda: None)


@pytest.fixture
def ready(tmp_path):
    (tmp_path / "consent.json").write_text("{}")
    return tmp_path


def _answers(base, pl):
    return [
        _get_guvenli_cevap(base, True, pl),
        _get_en_onemli_eksik(base, True, pl),
        _get_tek_sonraki_adim(base, True, pl),
        _get_mod_cevabi("offline", base, True, pl),
        *_get_oneri(base, True, pl),
    ]


def _assert_no_misleading(texts):
    for text in texts:
        for phrase in MISLEADING:
            assert phrase not in text, (phrase, text)


def test_presence_off_does_not_lower_security_answer(ready):
    pl = _presence(enabled=False)
    parts = get_durum_parts(ready, True, pl)
    durum = format_durum({"lock_status": "UNLOCKED"}, parts["consent_ok"],
                         parts["keystore_ready"], parts["durum_label"], parts["not_line"])
    answer = _get_guvenli_cevap(ready, True, pl)
    # durum: kritik eksik yok; güvenlik sorusu bunu çürütmez.
    assert "Not: kritik eksik yok" in durum
    assert answer == "Consent kayıtlı, keystore hazır. Kritik eksik görünmüyor."
    assert "kamera" not in answer.lower()
    _assert_no_misleading(_answers(ready, pl))


def test_presence_on_gives_same_answer_as_off(ready):
    off = _get_guvenli_cevap(ready, True, _presence(enabled=False))
    on = _get_guvenli_cevap(ready, True, _presence(enabled=True))
    assert on == off
    _assert_no_misleading(_answers(ready, _presence(enabled=True)))


def test_camera_is_never_suggested_as_a_security_step(ready):
    for pl in (_presence(enabled=False), _presence(enabled=True)):
        assert _get_oneri(ready, True, pl) == [
            "Hazırsın. durum, hazir veya yardım et ile devam edebilirsin."]
        assert _get_tek_sonraki_adim(ready, True, pl) == (
            "Bir sonraki adım: durum veya hazir ile devam et.")


@pytest.mark.parametrize("macos,not_line", [(False, "kamera izni yok"), (None, "kamera izni bilinmiyor")])
def test_enabled_demo_issue_is_reported_as_optional_demo(ready, monkeypatch, macos, not_line):
    monkeypatch.setattr(startup_health.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(startup_health, "_macos_permissions_ok", lambda: macos)
    pl = _presence(enabled=True)
    parts = get_durum_parts(ready, True, pl)
    assert parts["not_line"] == not_line
    demo = f"İsteğe bağlı kamera tabanlı otomatik kilit (demo): {not_line}"
    assert _get_guvenli_cevap(ready, True, pl) == (
        f"Consent kayıtlı, keystore hazır. {demo}.")
    assert _get_en_onemli_eksik(ready, True, pl) == (
        f"Şu an kritik bir eksik görünmüyor. {demo}.")
    assert _get_oneri(ready, True, pl) == [f"{demo}. Ayarı görmek için: kamera"]
    assert _get_tek_sonraki_adim(ready, True, pl) == (
        "Bir sonraki adım: durum veya hazir ile devam et. İsteğe bağlı kamera ayarı için: kamera")
    _assert_no_misleading(_answers(ready, pl))


def test_unreadable_demo_config_is_not_a_security_gap(ready):
    pl = _presence(broken=True)
    assert _get_en_onemli_eksik(ready, True, pl) == (
        "Şu an kritik bir eksik görünmüyor. İsteğe bağlı kamera tabanlı otomatik "
        "kilit (demo): presence yapılandırması yok.")
    _assert_no_misleading(_answers(ready, pl))


def test_offline_mode_answer_carries_no_security_label(ready):
    for pl in (_presence(enabled=False), _presence(enabled=True)):
        assert _get_mod_cevabi("offline", ready, True, pl) == "Şu an offline moddasın."
    assert _get_mod_cevabi("online", ready, True, _presence()) == "Şu an online moddasın."


def test_real_missing_prerequisites_are_still_reported(tmp_path):
    pl = _presence()
    assert _get_guvenli_cevap(tmp_path, True, pl) == "Şu an tam güvenli değilsin. Consent eksik."
    (tmp_path / "consent.json").write_text("{}")
    assert _get_guvenli_cevap(tmp_path, False, pl) == (
        "Şu an tam güvenli değilsin. Keystore hazır değil.")
    assert _get_en_onemli_eksik(tmp_path, False, pl) == "En önemli eksik: keystore hazır değil."
