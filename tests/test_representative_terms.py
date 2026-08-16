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


@pytest.mark.parametrize(
    "garbled",
    [
        "Okuk sorunluluğu, viluk olarak biz üstleniyoruz.",  # 0.31
        "Hukuki sorumluluğu WeLogica'a olarak biz üstleniyoruz.",  # 0.59
    ],
)
def test_far_garbles_are_honestly_out_of_scope(corrector, garbled):
    # 0.70 bandının altı: düzeltmeye kalkmak yanlış pozitif riskine değmez;
    # bu vakalar STT tarafında (bulut model + istem) çözülmeli.
    assert "We Lock AI" not in corrector.correct(garbled)


def test_t4_regression_real_speech_is_never_rewritten(corrector):
    # Test 4 gerçek yanlış pozitifi: "Lumos projesini" (0.62) "Lumos
    # temsilcisi"ne çevrilmişti — anlam bozan düzeltme yasak.
    text = "Merhaba, ben Candaş. Bugün Lumos projesini konuşmak istiyorum."
    assert corrector.correct(text) == text


def test_t4_prompt_echo_is_detected():
    from representative.stt import LUMOS_TERMS_PROMPT
    from representative.terms import is_prompt_echo

    echoes = [
        "Lumos, ChatLumos, We Lock AI, Lumos temsilcisi, toplantı, sözleşme, teklif.",
        "Lumos ChatLumos WeLock AI Lumos temsilcisi toplantı sözleşme teklif",
        "ChatLumos, We Lock AI, Lumos temsilcisi, toplantı, sözleşme, teklif.",
    ]
    for echo in echoes:
        assert is_prompt_echo(echo, LUMOS_TERMS_PROMPT) is True
    real = [
        "Merhaba, ben Candaş. Bugün Lumos projesini konuşmak istiyorum.",
        "Sözleşmeyi elli bin dolara imzalayacağız ve teslimat bir Ekim'de olacak.",
        "ChatLumos tüm yapay zeka araçlarını tek yerden yönetmesini sağlar.",
    ]
    for text in real:
        assert is_prompt_echo(text, LUMOS_TERMS_PROMPT) is False
