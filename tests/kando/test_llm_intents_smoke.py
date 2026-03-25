from kando.llm import llm


def test_status_intents():
    assert "Lumos Core aktif" in llm("durum")
    assert "Lumos Core aktif" in llm("durum lumos")
    assert "Lumos Core aktif" in llm("proje durum")


def test_repo_intent_still_routes():
    out = llm("repo: model_client nerede kullanılıyor")
    assert isinstance(out, str)
    assert out.strip() != ""


def test_unknown_input_falls_back():
    msg = (
        "Tam anlaşılmadı ama bir şey soruyorsun. 'yardım' yaz veya biraz netleştir."
    )
    assert llm("şişt") == msg
    assert llm("skldjnc") == msg
