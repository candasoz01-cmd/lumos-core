from kando.llm import llm


def test_fallback_question():
    # "neden" tek başına reason intent ile çakışır; nasıl → fallback soru dalı
    out = llm("bu nasıl böyle")
    assert "Sebep" in out or "analiz" in out


def test_fallback_definition():
    out = llm("bu ne")
    assert "Tanım" in out or "spesifik" in out


def test_fallback_action():
    out = llm("bunu çalıştır")
    assert "Aksiyon" in out or "Komut" in out
