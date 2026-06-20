"""Regression: test_api.sh feed path and rate cooldown retry."""

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


def test_test_api_sh_has_rate_post_retry_for_cooldown() -> None:
    text = TEST_API.read_text(encoding="utf-8")
    assert "rate_post()" in text
    assert "429" in text
    assert re.search(r'rate_post\s+"\$POST_A"\s+"\$USER1_TOKEN"\s+4', text)
    assert re.search(r'rate_post\s+"\$POST_A"\s+"\$USER2_TOKEN"\s+4', text)
    assert re.search(r'rate_post\s+"\$POST_P"\s+"\$USER2_TOKEN"\s+5', text)
