"""Landing index.astro — inline tokens; no dead external stylesheet link."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_INDEX_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "index.astro"


def test_index_has_no_dead_lumos_tokens_stylesheet_link() -> None:
    text = _INDEX_ASTRO.read_text(encoding="utf-8")
    assert "/styles/lumos-tokens.css" not in text
    assert "--lumos-land-teal:" in text
