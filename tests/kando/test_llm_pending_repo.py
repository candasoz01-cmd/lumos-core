from kando.llm import llm


def test_pending_repo_flow():
    out1 = llm("repo:")
    assert "repo arama" in out1.lower()
    assert "hazır değil" in out1.lower()

    out2 = llm("llm")
    assert "src/" in out2
