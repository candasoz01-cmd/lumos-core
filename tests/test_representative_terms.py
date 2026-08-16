"""TermCorrector tests — gerçek saha bozulmaları (test 3 + bench, 2026-08-14)."""

from __future__ import annotations

import pytest

from representative.terms import TermCorrector


@pytest.fixture
def corrector() -> TermCorrector:
    return TermCorrector()


@pytest.mark.parametrize(
    ("garbled", "expected"),
    [
        (
            "fukuki sorumluluğu ve ilocikali olarak biz üstleniyoruz.",
            "We Lock AI",
        ),
        ("Hukuki sorumluluğu WeLogica'a olarak biz üstleniyoruz.", "We Lock AI"),
        ("Plumostem silcisi toplantıya katılıp çevirecek.", "Lumos temsilcisi"),
        ("Luma ostem silcisi toplantıya katıldı.", "Lumos temsilcisi"),
    ],
)
def test_real_field_garbles_are_corrected(corrector, garbled, expected):
    assert expected in corrector.correct(garbled)


def test_correct_text_stays_untouched(corrector):
    text = "Hukuki sorumluluğu We Lock AI olarak biz üstleniyoruz."
    assert corrector.correct(text) == text


@pytest.mark.parametrize(
    "control",
    [
        "Bilgisayar başında birlikte çalışalım.",
        "Kalanı teslimatta ödenecek ve kilit teslim edilecek.",
        "Lokanta rezervasyonunu yarın yapacağım.",  # 0.53 benzerlik: ilk-harf koruması keser
        "Villa projesini konuşacağız.",
    ],
)
def test_no_false_positives_on_ordinary_turkish(corrector, control):
    assert corrector.correct(control) == control


def test_viluk_is_honestly_out_of_scope(corrector):
    # 0.31 benzerlik — düzeltmeye kalkmak yanlış pozitif riskine değmez;
    # bu vaka STT tarafında (bulut model + istem) çözülmeli.
    text = "Okuk sorunluluğu, viluk olarak biz üstleniyoruz."
    assert "We Lock AI" not in corrector.correct(text)
