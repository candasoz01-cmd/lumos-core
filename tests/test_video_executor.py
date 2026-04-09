"""video_executor: Replicate yolu (önbellek task_dispatch'ta)."""
from __future__ import annotations

from pathlib import Path

import pytest

from kando_runtime.executors import video_executor as ve


def test_normalize_prompt_stable_for_equivalent_strings() -> None:
    assert ve._normalize_prompt("  Hello. ") == ve._normalize_prompt("hello")
    a = ve._normalize_prompt("a  b\nc")
    b = ve._normalize_prompt("A B C")
    assert a == b


def test_run_returns_no_meta_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Saf executor meta/cache_hit eklemez."""
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    out = ve.run({"prompt": "x"})
    assert out.get("meta") is None
    assert (out.get("output") or {}).get("meta") is None


def test_busy_guard_returns_pending_without_duplicate_shape_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ve, "REPLICATE_API_TOKEN", "test-token", raising=False)
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
