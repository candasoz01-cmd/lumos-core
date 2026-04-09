"""Video önbelleği: yalnızca task_dispatch (_VIDEO_MEMORY_CACHE + disk)."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

import kando_runtime.task_dispatch as td


def test_apply_video_cache_meta_sets_top_and_output() -> None:
    r = {"output": {"type": "video", "url": "https://x"}}
    td._apply_video_cache_meta(r, True)
    assert r["meta"] == {"cache_hit": True}
    assert r["output"]["meta"]["cache_hit"] is True
    td._apply_video_cache_meta(r, False)
    assert r["meta"] == {"cache_hit": False}
    assert r["output"]["meta"]["cache_hit"] is False


def test_memory_cache_hit_sets_meta_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    td._VIDEO_MEMORY_CACHE.clear()
    ck = json.dumps({"prompt": "hello"}, sort_keys=True, ensure_ascii=False)
    td._VIDEO_MEMORY_CACHE[ck] = {
        "stored_at": time.time(),
        "result": td._video_done_payload("https://cached"),
    }
    out = td.run_video_executor({"prompt": "hello"})
    assert out["meta"]["cache_hit"] is True
    assert out["output"]["meta"]["cache_hit"] is True


def test_same_input_twice_equals_and_cache_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    td._VIDEO_MEMORY_CACHE.clear()
    ck = json.dumps({"prompt": "same_input"}, sort_keys=True, ensure_ascii=False)
    td._VIDEO_MEMORY_CACHE[ck] = {
        "stored_at": time.time(),
        "result": td._video_done_payload("https://same"),
    }
    first = td.run_video_executor({"prompt": "same_input"})
    second = td.run_video_executor({"prompt": "same_input"})
    assert first == second
    assert first["meta"]["cache_hit"] is True
    assert first["output"]["meta"]["cache_hit"] is True


def test_disk_cache_returns_cache_hit_true(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    td._VIDEO_MEMORY_CACHE.clear()
    norm = td._video_normalize_prompt("disk prompt")
    ph = td._video_disk_prompt_hash(norm)
    td._save_video_disk_cache(ph, "https://disk")
    out = td.run_video_executor({"prompt": "disk prompt"})
    assert out["status"] == "done"
    assert out["meta"]["cache_hit"] is True
    assert out["output"]["meta"]["cache_hit"] is True
