from kando.llm import llm

from tests.kando.repo_test_helpers import assert_repo_search_output_or_degrade

_REPO_COLON_EMPTY = (
    "repo: <arama> yaz.",
    "Pending geçici olarak kapalı. repo: <arama> yaz.",
    "Repo arama geçici olarak hazır değil.",
)


def test_pending_repo_flow():
    out1 = llm("repo:")
    assert out1 in _REPO_COLON_EMPTY

    out2 = llm("llm")
    if out1 == "Repo arama geçici olarak hazır değil.":
        assert_repo_search_output_or_degrade(out2)
    else:
        assert "tam anlaşılmadı" in out2.lower()
