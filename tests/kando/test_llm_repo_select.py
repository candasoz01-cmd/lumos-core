from kando.llm import llm


def test_repo_select_flow():
    out1 = llm("repo: intent score")
    assert out1.strip() != ""

    out2 = llm("seç 1")
    assert out2.strip() != ""
