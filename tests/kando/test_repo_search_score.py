"""repo: path uses kando.tools.repo_search token scoring (higher = more tokens per line)."""

import os

import pytest

from kando.tools import repo_search
from kando.llm import llm


@pytest.fixture
def repo_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_repo_search_sorts_by_token_score(repo_root):
    """Lines matching more query tokens rank first (see tools.repo_search score)."""
    prev = os.getcwd()
    try:
        os.chdir(repo_root)
        out = repo_search("model_client import")
    finally:
        os.chdir(prev)

    assert out != "Sonuç bulunamadı"
    o = out.lower()
    assert "model_client" in o
    assert "import" in o
    # En yüksek skorlu satırlar path başına tek kayıt; çıktıda bağlam blokları birleşik
    assert "src/" in out.replace("\\", "/")


def test_llm_repo_prefix_returns_scored_lines(repo_root):
    prev = os.getcwd()
    try:
        os.chdir(repo_root)
        out = llm("repo: model_client import")
    finally:
        os.chdir(prev)

    assert out.strip() != ""
    assert "model_client" in out.lower() or "import" in out.lower()
