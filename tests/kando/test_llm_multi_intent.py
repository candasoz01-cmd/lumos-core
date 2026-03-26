from kando.llm import llm

from tests.kando.repo_test_helpers import assert_repo_search_output_or_degrade


def test_multi_intent_priority_and_merge():
    out = llm("durum ve öneri")
    assert "Lumos Core aktif" in out
    assert "Repo search" in out


def test_multi_intent_repo_priority():
    llm("repo: llm")
    out = llm("repo ve durum")
    # repo önce gelmeli
    first_line = out.splitlines()[0]
    assert_repo_search_output_or_degrade(first_line)
