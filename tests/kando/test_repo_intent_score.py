"""repo: intent — prefix wins before INTENTS token/prefix/fuzzy scoring (intent_engine)."""

from kando.intent_engine import engine
from kando.llm import detect_intent


def test_engine_match_repo_prefix_returns_repo_string():
    """Normalized text must start with repo:; return is str 'repo', not a scored list."""
    assert engine.match("repo: model_client") == "repo"
    assert engine.match("REPO: foo") == "repo"


def test_engine_match_repo_prefix_short_circuits_before_intent_scores():
    """Query part can contain words that match other INTENTS; repo still wins."""
    assert engine.match("repo: durum lumos") == "repo"
    assert engine.match("repo: yardım komut") == "repo"


def test_detect_intent_repo_flattens_to_string():
    assert detect_intent("repo: llm") == "repo"


def test_engine_mid_sentence_repo_not_repo_intent():
    """Only leading repo: triggers repo intent; embedded repo: goes through scoring."""
    r = engine.match("bak repo: llm")
    assert r != "repo"
    assert isinstance(r, list) or r == "unknown"
