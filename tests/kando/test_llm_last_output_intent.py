from kando.llm import llm


def test_last_output_intent():
    llm("durum")
    out = llm("ne diyor")
    assert "Lumos Core aktif" in out
