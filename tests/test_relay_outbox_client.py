"""Offline outbox fixtures: no server, model, watcher or clipboard process."""
from __future__ import annotations

import json
import os

import pytest

from kando import relay_outbox_client as client
from kando.cursor_packet import SCHEMA_EXECUTION, SCHEMA_RESULT

GOAL = "README dosyasını özetle [relay:fixture-request]"


def packets(goal=GOAL, task_id=17):
    expected = client.expected_goal_inbox(goal)
    return (
        {"schema_version": SCHEMA_EXECUTION, "goal": expected, "task_id": task_id},
        {"schema_version": SCHEMA_RESULT, "goal_preview": expected[:500],
         "task_id": task_id, "outcome": "applied", "task_status": "tamamlandi",
         "brain_success": True},
    )


def write_pair(root, exe, res):
    paths = client.outbox_paths(root)
    paths[0].parent.mkdir(parents=True, exist_ok=True)
    for path, value in zip(paths, (exe, res)):
        path.write_text(json.dumps(value), encoding="utf-8")
    return paths


@pytest.fixture(autouse=True)
def fast_poll(monkeypatch):
    # Deterministic virtual clock: exercise multiple polls without waiting.
    clock = [0.0]
    monkeypatch.setattr(client.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(client.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))


def wait(root, prev=(None, None)):
    return client.wait_for_new_outbox(*prev, GOAL, 1.0, root=root)


def test_accepts_matching_packets_and_keeps_the_snapshot(tmp_path, capsys):
    exe, res = packets()
    write_pair(tmp_path, exe, res)
    snapshot = wait(tmp_path)
    assert snapshot
    # A later request must not replace the result we display or classify.
    write_pair(tmp_path, *packets("different request", 18))
    client.print_summary(snapshot=snapshot)
    assert GOAL in capsys.readouterr().out
    assert snapshot.succeeded is True


@pytest.mark.parametrize("task_id", [18, None, 0, -1, True, "17", 17.0])
def test_rejects_wrong_or_invalid_result_task_id(tmp_path, task_id):
    exe, res = packets()
    res["task_id"] = task_id
    write_pair(tmp_path, exe, res)
    assert not wait(tmp_path)


@pytest.mark.parametrize("task_id", [None, 0, -1, True, "17", 17.0])
def test_rejects_matching_but_invalid_ids(tmp_path, task_id):
    write_pair(tmp_path, *packets(task_id=task_id))
    assert not wait(tmp_path)


def test_rejects_goal_that_only_contains_the_request(tmp_path):
    exe, res = packets()
    exe["goal"] += " unrelated suffix"
    res["goal_preview"] = exe["goal"][:500]
    write_pair(tmp_path, exe, res)
    assert not wait(tmp_path)


def test_rejects_wrong_result_preview_even_when_task_id_matches(tmp_path):
    exe, res = packets()
    res["goal_preview"] = "görev: earlier request"
    write_pair(tmp_path, exe, res)
    assert not wait(tmp_path)


@pytest.mark.parametrize("bad", ["{", "null", "[]", "\"text\""])
def test_rejects_partial_or_non_object_result(tmp_path, bad):
    paths = write_pair(tmp_path, *packets())
    paths[1].write_text(bad, encoding="utf-8")
    assert not wait(tmp_path)


def test_rejects_missing_result(tmp_path):
    paths = write_pair(tmp_path, *packets())
    paths[1].unlink()
    assert not wait(tmp_path)


@pytest.mark.parametrize("stale_index", [0, 1])
def test_rejects_stale_file_even_if_other_file_is_fresh(tmp_path, stale_index):
    paths = write_pair(tmp_path, *packets())
    for path in paths:
        os.utime(path, (100, 100))
    os.utime(paths[1 - stale_index], (200, 200))
    assert not wait(tmp_path, (100, 100))


def test_rejects_receipt_only_snapshot(tmp_path):
    exe, res = packets()
    res = {"accepted": True, "ok": True, "http_status": 200, "task_id": 17}
    write_pair(tmp_path, exe, res)
    assert not wait(tmp_path)


def test_waits_for_correct_result_after_a_mixed_pair(tmp_path, monkeypatch):
    exe, res = packets()
    write_pair(tmp_path, exe, {**res, "task_id": 16})
    sleep = client.time.sleep

    def publish_result(seconds):
        write_pair(tmp_path, exe, res)
        sleep(seconds)

    monkeypatch.setattr(client.time, "sleep", publish_result)
    snapshot = wait(tmp_path)
    assert snapshot and snapshot.result["task_id"] == 17


def test_rejects_a_file_replaced_during_read(tmp_path, monkeypatch):
    exe, res = packets()
    paths = write_pair(tmp_path, exe, res)
    original = client.load_json

    def race(path):
        value = original(path)
        if path == paths[1]:
            changed = paths[0].with_suffix(".new")
            changed.write_text(json.dumps({**exe, "task_id": 18}))
            changed.replace(paths[0])
        return value

    monkeypatch.setattr(client, "load_json", race)
    assert not wait(tmp_path)


def test_post_timeout_is_reported_without_retry(monkeypatch):
    calls = []

    def fail(request, **kwargs):
        calls.append(request)
        raise TimeoutError("fixture timeout after possible delivery")

    monkeypatch.setattr(client.urllib.request, "urlopen", fail)
    with pytest.raises(RuntimeError, match="otomatik.*gönder"):
        client.post_relay("http://relay.invalid", GOAL)
    assert len(calls) == 1


@pytest.mark.parametrize("goal", [GOAL, "uzun görev " * 80 + "[relay:long-request]"])
def test_existing_cursor_packet_writer_and_outbox_mirror(tmp_path, monkeypatch, goal):
    from types import SimpleNamespace

    from kando.agent_runner import _copy_cursor_bridge_snapshots_to_outbox
    from kando.cursor_bridge import build_result_packet, persist_cursor_bridge
    from kando.cursor_packet import CursorExecutionPacketV1

    expected = client.expected_goal_inbox(goal)
    task = SimpleNamespace(task_id=23, status="tamamlandi")
    execution = CursorExecutionPacketV1(
        schema_version=SCHEMA_EXECUTION, goal=expected, task_id=task.task_id,
        permission_profile="limited", general_approval=False, steps=[], patch=None,
    )
    result = build_result_packet(goal=expected, brain_success=True, task=task)
    base = tmp_path / ".lumos"
    monkeypatch.setenv("LUMOS_BASE_DIR", str(base))
    persist_cursor_bridge(base, execution, result)
    _copy_cursor_bridge_snapshots_to_outbox(tmp_path, base / "outbox")
    snapshot = client.wait_for_new_outbox(None, None, goal, 1, root=tmp_path)
    assert snapshot and snapshot.succeeded
    assert snapshot.result["goal_preview"] == expected[:500]


def test_current_bridge_http_receipt_is_not_completion(tmp_path, monkeypatch):
    from kando_bridge import server

    paths = client.outbox_paths(tmp_path)
    monkeypatch.setattr(server, "OUTBOX_DIR", paths[0].parent)
    monkeypatch.setattr(server, "LAST_EXECUTION_FILE", paths[0])
    monkeypatch.setattr(server, "LAST_RESULT_FILE", paths[1])
    server.persist_post_task_outbox_snapshots(
        {"raw": json.dumps({"goal": GOAL}).encode(), "route": "agent"},
        {"http_status": 200, "response": {"accepted": True, "ok": True}},
    )
    assert not wait(tmp_path)
