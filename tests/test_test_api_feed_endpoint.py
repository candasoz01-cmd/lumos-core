"""Regression: test_api.sh must use GET /posts?order=feed, not deprecated /posts/feed."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_API = REPO_ROOT / "test_api.sh"


def test_test_api_sh_uses_order_feed_not_deprecated_path() -> None:
    text = TEST_API.read_text(encoding="utf-8")
    assert "/posts/feed" not in text, "deprecated /posts/feed must not appear in test_api.sh"
    assert "/posts?order=feed" in text
    feed_fetches = re.findall(r"fetch\([^)]*order=feed[^)]*\)", text)
    assert len(feed_fetches) >= 3, f"expected >=3 feed fetch calls, got {feed_fetches!r}"
