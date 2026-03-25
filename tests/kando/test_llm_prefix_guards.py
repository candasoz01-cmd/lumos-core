from kando.llm import llm


def test_project_only_hits_prefix_cases():
    assert llm("proje durum").startswith("Lumos Core aktif")
    assert llm("proje") == "Lumos Core aktif. Sistem stabil."
    assert llm("bu proje çok karışık").startswith("Lumos Core aktif")


def test_status_only_hits_prefix_cases():
    assert llm("durum").startswith("Lumos Core aktif")
    assert llm("durum lumos").startswith("Lumos Core aktif")
    assert llm("bana durum anlat").startswith("Lumos Core aktif")


def test_prefix_intents_match_mid_sentence_when_flexible():
    assert "Bağlama" in llm("bugün neden böyle")
    assert llm("şu an napan sen") == "Çalışıyorum."
    assert llm("son eklenen neydi") == "Yeni veri yok."
    assert "Repo search" in llm("bir şey öner bana")
