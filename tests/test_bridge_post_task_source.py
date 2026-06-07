"""POST /task source görünürlüğü — parse, yanıt zarfı, outbox snapshot."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kando_bridge.server import (
    _normalize_task_source,
    _parse_task_source_from_request_raw,
    _resolve_task_routing,
    merge_post_task_http_envelope,
    persist_post_task_outbox_snapshots,
)


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("panel_chat", "panel_chat"),
        ("  panel_clipboard  ", "panel_clipboard"),
        ("panel_gorevler", "panel_gorevler"),
        ("panel_capability_test", "panel_capability_test"),
        ("direct", "direct"),
        ("", None),
        ("   ", None),
        (None, None),
        (123, None),
    ],
)
def test_normalize_task_source(raw_value: object, expected: str | None) -> None:
    assert _normalize_task_source(raw_value) == expected


def test_parse_task_source_from_text_payload() -> None:
    raw = json.dumps({"text": "README düzelt", "source": "panel_chat"}, ensure_ascii=False).encode()
    assert _parse_task_source_from_request_raw(raw) == "panel_chat"


def test_parse_task_source_from_goal_payload() -> None:
    raw = json.dumps(
        {"goal": "Video üret", "source": "panel_gorevler"},
        ensure_ascii=False,
    ).encode()
    assert _parse_task_source_from_request_raw(raw) == "panel_gorevler"


def test_resolve_task_routing_panel_gorevler_skips_path_inference() -> None:
    raw = json.dumps(
        {"goal": "README.md özetle", "source": "panel_gorevler"},
        ensure_ascii=False,
    ).encode()
    err, mode, _payload, _ = _resolve_task_routing("application/json", raw)
    assert err is None
    assert mode == "agent"


def test_merge_post_task_http_envelope_includes_source_and_route() -> None:
    raw = json.dumps({"text": "selam", "source": "panel_clipboard"}, ensure_ascii=False).encode()
    merged = merge_post_task_http_envelope(
        status=200,
        payload={"accepted": True, "mode": "agent"},
        envelope_meta={"raw": raw, "route": "agent"},
    )
    assert merged["source"] == "panel_clipboard"
    assert merged["route"] == "agent"
    assert merged["ok"] is True


def test_persist_post_task_outbox_snapshots_writes_source(tmp_path: Path, monkeypatch) -> None:
    from kando_bridge import server as srv

    outbox = tmp_path / ".lumos" / "outbox"
    outbox.mkdir(parents=True)
    monkeypatch.setattr(srv, "OUTBOX_DIR", outbox)
    monkeypatch.setattr(srv, "LAST_EXECUTION_FILE", outbox / "last_execution.json")
    monkeypatch.setattr(srv, "LAST_RESULT_FILE", outbox / "last_result.json")

    raw = json.dumps({"goal": "test görev", "source": "panel_capability_test"}, ensure_ascii=False).encode()
    persist_post_task_outbox_snapshots(
        {"raw": raw, "route": "agent"},
        {
            "http_status": 200,
            "response": {"accepted": True, "ok": True, "mode": "agent"},
        },
    )

    last_ex = json.loads((outbox / "last_execution.json").read_text(encoding="utf-8"))
    last_res = json.loads((outbox / "last_result.json").read_text(encoding="utf-8"))
    assert last_ex["source"] == "panel_capability_test"
    assert last_ex["route"] == "agent"
    assert last_res["source"] == "panel_capability_test"
    assert last_res["accepted"] is True
