from kando.llm import llm


def test_repo_context_reuse():
    out1 = llm("repo: llm")
    assert "src/" in out1

    out2 = llm("repo")
    assert "src/" in out2
