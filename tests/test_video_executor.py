"""video_executor: cache anahtarı, cache_hit, busy guard (davranış korunur)."""
from __future__ import annotations

from pathlib import Path

import pytest

from kando_runtime.executors import video_executor as ve


def test_normalize_prompt_stable_for_equivalent_strings() -> None:
    assert ve._normalize_prompt("  Hello. ") == ve._normalize_prompt("hello")
    a = ve._normalize_prompt("a  b\nc")
    b = ve._normalize_prompt("A B C")
    assert a == b


def test_make_video_cache_key_stable_for_same_norm() -> None:
    n = ve._normalize_prompt("same prompt")
    k1, h1 = ve._make_video_cache_key(n)
    k2, h2 = ve._make_video_cache_key(n)
    assert k1 == k2 == "video:" + h1
    assert h1 == h2


def test_mark_cache_hit_sets_meta_true() -> None:
    cached = {"output": {"type": "video", "url": "https://x"}}
    out = ve._mark_cache_hit(cached)
    assert out["output"]["meta"]["cache_hit"] is True


def test_memory_cache_hit_sets_meta_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    ve.CACHE.clear()
    ck, _ = ve._make_video_cache_key(ve._normalize_prompt("hello"))
    ve.CACHE[ck] = ve._done_video_payload("https://cached")
    out = ve.run({"prompt": "hello"})
    assert out["output"]["meta"]["cache_hit"] is True


def test_disk_cache_does_not_add_cache_hit_meta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    ve.CACHE.clear()
    norm = ve._normalize_prompt("disk prompt")
    _, ph = ve._make_video_cache_key(norm)
    ve._save_cache(ph, "https://disk")
    out = ve.run({"prompt": "disk prompt"})
    assert out["status"] == "done"
    assert out["output"].get("meta") is None


def test_busy_guard_returns_pending_without_duplicate_shape_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ve, "REPLICATE_API_TOKEN", "test-token", raising=False)
    ve.CACHE.clear()
    ve._VIDEO_BUSY = True
    try:
        r1 = ve.run({"prompt": "first"})
        r2 = ve.run({"prompt": "second"})
    finally:
        ve._VIDEO_BUSY = False
    assert r1["status"] == "pending" == r2["status"]
    assert r1["output"]["message"] == r2["output"]["message"] == "sırada bekliyor"


def test_error_video_payload_shape() -> None:
    e = ve._error_video_payload("oops")
    assert e["status"] == "error"
    assert e["output"]["error"] == "oops"
    assert e["output"]["provider"] == ve.PROVIDER_REPLICATE


def test_done_video_payload_provider_default() -> None:
    d = ve._done_video_payload("https://v")
    assert d["output"]["provider"] == ve.PROVIDER_REPLICATE
