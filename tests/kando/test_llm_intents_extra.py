from kando.llm import llm


def test_greeting_intents():
    assert llm("napan") == "Çalışıyorum."
    assert llm("ne yapıyorsun") == "Çalışıyorum."
    assert llm("napıyorsun") == "Çalışıyorum."
    assert llm("napiyon") == "Çalışıyorum."
    assert llm("naber") == "Çalışıyorum."


def test_reason_intent():
    assert "Bağlama" in llm("neden")


def test_recent_intent():
    assert llm("son eklenenler") == "Yeni veri yok."


def test_suggestion_intent():
    assert "Repo" in llm("öner")
