from kando.llm import llm

from tests.kando.repo_test_helpers import assert_repo_search_output_or_degrade


def test_repo_context_reuse():
    out1 = llm("repo: llm")
    assert_repo_search_output_or_degrade(out1)

    out2 = llm("repo")
    assert_repo_search_output_or_degrade(out2)
