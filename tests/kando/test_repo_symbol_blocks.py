from kando.tools import repo_search


def test_repo_search_returns_scored_lines_for_query():
    out = repo_search("intent score")
    assert isinstance(out, str)
    assert out.strip() != ""
    assert "intent_engine.py" in out


def test_repo_search_returns_symbol_block_when_symbol_given():
    out = repo_search("intent_engine add_score")
    assert isinstance(out, str)
    assert out.strip() != ""
    assert "def add_score" in out
