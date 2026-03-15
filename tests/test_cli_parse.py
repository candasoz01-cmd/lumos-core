"""CLI komut parse testleri: verilen komut dizisinin doğru route/args üretmesi.
Komut toleransı ve fallback mesajı testleri dahil.
cli.cli_parse import edilir (pytest.ini pythonpath=src ile çalışır).
"""
import tempfile
from pathlib import Path

import pytest


def _norm(cmd: str, aliases: dict | None = None):
    try:
        from cli.cli_parse import normalize_command
    except Exception:
        pytest.skip("cli_parse import failed (need PYTHONPATH=src)")
    base = Path(tempfile.gettempdir()) / "lumos_parse_test"
    base.mkdir(parents=True, exist_ok=True)
    return normalize_command(cmd, base, aliases)


def _fallback(raw: str, last_route: str | None = None):
    try:
        from cli.cli_parse import get_fallback_message
    except Exception:
        pytest.skip("cli_parse import failed (need PYTHONPATH=src)")
    return get_fallback_message(raw, last_route)


def test_yetki_profili_commands():
    r, a = _norm("yetki profili")
    assert r == "yetki_profili"
    assert a == []

    r, a = _norm("yetki profili rapor")
    assert r == "yetki_profili"
    assert a == ["rapor"]

    r, a = _norm("yetki profili guvenli_yurut")
    assert r == "yetki_profili"
    assert a == ["guvenli_yurut"]


def test_gorev_commands():
    r, a = _norm("görev oluştur not sistemini kontrol et ve kısa özet ver")
    assert r == "gorev_olustur"
    assert "not" in " ".join(a) and "özet" in " ".join(a) or "ozet" in " ".join(a).lower()

    r, a = _norm("görevler")
    assert r == "gorevler"
    assert a == []

    r, a = _norm("görev durumu 1")
    assert r == "gorev_durumu"
    assert a == ["1"]

    r, a = _norm("görev özeti 1")
    assert r == "gorev_ozeti"
    assert a == ["1"]

    r, a = _norm("görev adımları 2")
    assert r == "gorev_adimlari"
    assert a == ["2"]

    r, a = _norm("görev özeti 2")
    assert r == "gorev_ozeti"
    assert a == ["2"]


def test_genel_onay_and_exit():
    r, a = _norm("genel onay aç")
    assert r == "genel_onay_ac"
    assert a == []

    r, a = _norm("genel onay kapat")
    assert r == "genel_onay_kapat"
    assert a == []

    r, a = _norm("çık")
    assert r == "exit"
    assert a == []


def test_durum_ozet_not_gorev_durumu():
    """durum özet → durum (sistem özeti); görev durumu 1 → gorev_durumu (görev id)."""
    r, a = _norm("durum özet")
    assert r == "durum"
    # args ["özet"] veya [] olabilir (parser sırasına göre); handler args'ta özet varsa "Durum özeti:" basar
    assert r == "durum"

    r, a = _norm("görev durumu 1")
    assert r == "gorev_durumu"
    assert a == ["1"]


def test_durum_ozet_args_trigger_header():
    """durum özet yazıldığında args özet içeriyorsa main handler 'Durum özeti:' basar (sahada görünür)."""
    r, a = _norm("durum özet")
    assert r == "durum"
    has_ozet = bool(a and ("özet" in (a[0] or "") or "ozet" in (a[0].lower().replace("ö", "o") or "")))
    assert has_ozet, "durum özet komutu args ile özet geçmeli ki sahada başlık çıksın"


def test_command_tolerance_typos():
    """Eksik harf / yakın yazım: görev durmu -> görev durumu, görev özti -> görev özeti, yetki profil -> yetki profili."""
    r, a = _norm("görev durmu 2")
    assert r == "gorev_durumu", f"görev durmu 2 -> gorev_durumu, got {r}"
    assert a == ["2"]

    r, a = _norm("görev özti 1")
    assert r == "gorev_ozeti", f"görev özti 1 -> gorev_ozeti, got {r}"
    assert a == ["1"]

    r, a = _norm("yetki profil rapor")
    assert r == "yetki_profili"
    assert a == ["rapor"]


def test_command_tolerance_genel_onaykapat():
    """Küçük boşluk/yazım: genel onaykapat -> genel onay kapat."""
    r, a = _norm("genel onaykapat")
    assert r == "genel_onay_kapat"
    assert a == []


def test_fallback_neden_anlamadin():
    """'neden anlamadın' / 'neyi anlamadın' / 'neye takıldın' -> açıklayıcı fallback."""
    msg = _fallback("neden anlamadın")
    assert "yeterince yakın değildi" in msg or "güvenli" in msg
    assert "görev durumu" in msg or "örnek" in msg.lower()

    msg = _fallback("neye takıldın")
    assert "yeterince yakın" in msg or "güvenli" in msg or "Örnek" in msg


def test_ambiguous_or_risky_stays_unknown():
    """Belirsiz/riskli ifadeler komut olarak tanınmamalı (saat, serbest sohbet)."""
    r, _ = _norm("saat")
    assert r == "unknown"

    r, _ = _norm("sanırım bitti bu aşamada bakalım ne çıktı")
    assert r == "unknown"

    r, _ = _norm("sanırım bitti bu aşamada bakalım ne çıkacak")
    assert r == "unknown"


def test_fallback_neutral_for_casual_and_no_anchor():
    """saat, sanırım bitti... gibi belirsiz/sohbet ifadeler -> nötr fallback (aileye zorla bağlanmasın)."""
    msg_saat = _fallback("saat")
    assert "yeterince yakın bulmadım" in msg_saat or "işlem yapmadım" in msg_saat
    assert "Görev ailesine" not in msg_saat and "Yetki ailesine" not in msg_saat

    msg_sanirim = _fallback("sanırım bitti bu aşamada bakalım ne çıkacak")
    assert "yeterince yakın bulmadım" in msg_sanirim or "işlem yapmadım" in msg_sanirim
    assert "Görev ailesine" not in msg_sanirim and "Yetki ailesine" not in msg_sanirim

    msg_tamam = _fallback("tamam")
    assert "Görev ailesine" not in msg_tamam and "Yetki ailesine" not in msg_tamam


def test_fallback_family_when_anchor_present():
    """Anchor varken (görev, yetki vb.) bilinmeyen alt komut -> ilgili aile fallback."""
    msg_gorev = _fallback("görev xyz 2")
    assert "görev" in msg_gorev.lower() and ("görev durumu" in msg_gorev or "Görev ailesine" in msg_gorev)

    msg_yetki = _fallback("yetki abc rapor")
    assert "yetki" in msg_yetki.lower() and ("yetki profili" in msg_yetki or "Yetki ailesine" in msg_yetki)


def test_tolerance_and_fallback_priority():
    """Toleranslı yazım doğru route; anchor yoksa nötr fallback."""
    r, a = _norm("görev durmu 2")
    assert r == "gorev_durumu", "görev durmu 2 -> görev ailesi (gorev_durumu)"
    assert a == ["2"]

    r, a = _norm("görev özti 1")
    assert r == "gorev_ozeti", "görev özti 1 -> görev ailesi (gorev_ozeti)"
    assert a == ["1"]

    r, a = _norm("yetki profil rapor")
    assert r == "yetki_profili", "yetki profil rapor -> yetki ailesi"
    assert a == ["rapor"]

    # Anchor yok -> nötr (last_route ile aile tahmini yapılmaz)
    msg = _fallback("saat", last_route="gorev_durumu")
    assert "Görev ailesine" not in msg


def test_full_sequence_routes():
    """Verdiğin tam komut dizisinin hedef route'ları."""
    sequence = [
        ("yetki profili", "yetki_profili", []),
        ("yetki profili rapor", "yetki_profili", ["rapor"]),
        ("görev oluştur not sistemini kontrol et ve kısa özet ver", "gorev_olustur", None),
        ("görevler", "gorevler", []),
        ("görev durumu 1", "gorev_durumu", ["1"]),
        ("görev özeti 1", "gorev_ozeti", ["1"]),
        ("yetki profili guvenli_yurut", "yetki_profili", ["guvenli_yurut"]),
        ("genel onay aç", "genel_onay_ac", []),
        ("görev oluştur not sistemini kontrol et ve kısa özet ver", "gorev_olustur", None),
        ("görevler", "gorevler", []),
        ("görev durumu 2", "gorev_durumu", ["2"]),
        ("görev adımları 2", "gorev_adimlari", ["2"]),
        ("görev özeti 2", "gorev_ozeti", ["2"]),
        ("görev temizle tamamlananlar", "gorev_temizle_tamamlananlar", []),
        ("görev temizle simulasyonlar", "gorev_temizle_simulasyonlar", []),
        ("görev arşivle 1", "gorev_arsivle", ["1"]),
        ("görev arşivle 2", "gorev_arsivle", ["2"]),
        ("görev sil 1", "gorev_sil", ["1"]),
        ("görev sayaç", "gorev_sayac", []),
        ("durum özet", "durum", None),
        ("çık", "exit", []),
    ]
    for cmd, expected_route, expected_args in sequence:
        r, a = _norm(cmd)
        assert r == expected_route, f"cmd={cmd!r} -> route {r!r} expected {expected_route!r}"
        if expected_args is not None:
            assert a == expected_args, f"cmd={cmd!r} -> args {a!r} expected {expected_args!r}"
