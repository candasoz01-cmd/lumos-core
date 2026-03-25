from kando.llm import llm


def test_project_mid_sentence_matches_flexible():
    assert llm("bu proje karışık").startswith("Lumos Core aktif")


def test_reason_prefix_only():
    assert "Bağlama" in llm("neden")
    assert "Bağlama" in llm("bugün neden böyle")


def test_greeting_prefix_only():
    assert llm("napan") == "Çalışıyorum."
    assert llm("şu an napan sen") == "Çalışıyorum."
