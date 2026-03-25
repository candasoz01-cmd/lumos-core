from kando.llm import llm


def test_repeat_followup():
    llm("durum")
    out = llm("aynı")
    assert "Lumos Core aktif" in out


def test_expand_followup():
    llm("durum")
    out = llm("detay")
    assert "detay:" in out
