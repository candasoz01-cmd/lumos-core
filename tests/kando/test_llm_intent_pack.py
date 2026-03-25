from kando.llm import llm, detect_intent, normalize


def test_normalize():
    assert normalize("YARDIM ÇIĞ") == "yardim cig"


def test_detect_intents():
    assert detect_intent("durum") == "status"
    assert detect_intent("napıyorsun") == "greeting"
    assert detect_intent("neden") == "reason"
    assert detect_intent("yardım") == "help"
    assert detect_intent("son eklenenler") == "recent"
    assert detect_intent("öner") == "suggest"
    assert detect_intent("stabil") == "stable"
    assert detect_intent("devam") == "continue"
    assert detect_intent("repo: llm") == "repo"


def test_llm_pack():
    assert llm("durum") == "Lumos Core aktif. Sistem stabil."
    assert llm("proje durum") == "Lumos Core aktif. Sistem stabil."
    assert llm("napıyorsun") == "Çalışıyorum."
    assert "Bağlama" in llm("neden")
    assert "Komutlar:" in llm("yardım")
    assert llm("son eklenenler") == "Yeni veri yok."
    assert "Repo search" in llm("öner")
    assert "Belirli scope" in llm("stabil")
    assert llm("devam") == "Hazırım, devam ediyorum."
    assert llm("skldjnc") == (
        "Tam anlaşılmadı ama bir şey soruyorsun. 'yardım' yaz veya biraz netleştir."
    )
