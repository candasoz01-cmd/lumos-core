from kando.llm import llm


def test_repo_prev_flow():
    out1 = llm("repo: intent score")
    assert out1.strip() != ""

    out2 = llm("sonraki")
    assert out2.strip() != ""

    out3 = llm("önceki")
    assert out3.strip() != ""
