from kando.llm import llm


def test_pending_repo_flow():
    out1 = llm("repo:")
    assert "Ne arıyorsun" in out1

    out2 = llm("llm")
    assert "src/" in out2
