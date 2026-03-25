from kando.llm import llm


def test_changes_intent():
    out = llm("yapılan değişiklikler neler")
    assert "Son değişiklikler:" in out
    assert "intent engine" in out
