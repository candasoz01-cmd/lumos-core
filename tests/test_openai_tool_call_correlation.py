"""Per-call results without weakening approval or enabling external effects."""
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from kando_bridge import openai_tool_adapter as adapter
from kando_bridge.computer_use_bridge import offline_computer_use_transport


def item(call_id="call-A", **updates):
    value = {"type": "function_call", "call_id": call_id, "name": "pc_open_url",
             "arguments": {"url": "https://example.invalid/a"}}
    value.update(updates)
    return value


def test_distinct_ids_get_distinct_disabled_results():
    transport = Mock(side_effect=offline_computer_use_transport)
    approval = Mock()
    out = adapter.run_openai_response_loop(
        {"output": [item(), item("call-B")]}, http_fn=transport, approve_fn=approval,
    )
    assert [row["call_id"] for row in out] == ["call-A", "call-B"]
    assert all(row["execute"]["status"] == "disabled" for row in out)
    assert all(row["execute"]["result_kind"] == "unexecuted" for row in out)
    assert transport.call_count == 2
    approval.assert_not_called()


def test_same_call_multiple_projections_dispatch_once():
    args = {"url": "https://example.invalid/a", "nested": {"a": 1, "b": 2}}
    projections = [item(arguments=args),
                   {"type": "function", "id": "call-A", "function": {
                       "name": "pc_open_url", "arguments": json.dumps(args)}},
                   SimpleNamespace(type="function_call", call_id="call-A",
                                   name="pc_open_url", arguments={
                                       "nested": {"b": 2, "a": 1}, "url": args["url"]})]
    transport = Mock(side_effect=offline_computer_use_transport)
    out = adapter.run_openai_response_loop({"output": projections}, http_fn=transport)
    assert len(out) == 1 and out[0]["call_id"] == "call-A"
    assert transport.call_count == 1


@pytest.mark.parametrize("change", [
    {"name": "pc_type_text"}, {"arguments": {"url": "https://example.invalid/b"}},
])
def test_conflicting_same_id_rejects_batch_before_any_dispatch(change):
    transport, approval = Mock(), Mock()
    with pytest.raises(ValueError, match="^conflicting_tool_call_id$"):
        adapter.run_openai_response_loop(
            {"output": [item("earlier"), item(), item(**change)]},
            http_fn=transport, approve_fn=approval,
        )
    transport.assert_not_called()
    approval.assert_not_called()


def test_anonymous_legacy_dedup_does_not_swallow_identified_call():
    calls = adapter.parse_openai_tool_calls({"output": [item(""), item(""), item()]})
    assert [call.call_id for call in calls] == ["", "call-A"]


def test_call_id_has_priority_over_response_item_id():
    calls = adapter.parse_openai_tool_calls({"output": [
        item(id="fc-A"), item(id="fc-projection"), item("call-B", id="fc-B"),
    ]})
    assert [call.call_id for call in calls] == ["call-A", "call-B"]


@pytest.mark.parametrize("status,response,stage", [
    (200, {"ok": True, "status": "stub"}, "direct"),
    (200, {"status": "pending_approval"}, "pending"),
    (0, {"error": "connection_failed"}, "error"),
    (200, [], "error"),
    (500, {"status": "rejected", "error": "internal_error"}, "error"),
    (200, {"status": "disabled", "call_id": "untrusted-other"}, "error"),
])
def test_loop_outcomes_keep_input_id(status, response, stage):
    out = adapter.run_tool_call_loop(
        adapter.ParsedToolCall("pc_open_url", {}, "call-A"),
        http_fn=Mock(return_value=(status, response)),
    )
    assert out["call_id"] == "call-A" and out["stage"] == stage


def test_unknown_command_keeps_id_without_transport():
    transport = Mock()
    out = adapter.run_tool_call_loop(
        adapter.ParsedToolCall("unknown", {}, "call-A"), http_fn=transport,
    )
    assert out["call_id"] == "call-A" and out["error"] == "unknown_command"
    transport.assert_not_called()


def test_transport_exception_keeps_id():
    out = adapter.run_tool_call_loop(
        adapter.ParsedToolCall("pc_open_url", {}, "call-A"),
        http_fn=Mock(side_effect=RuntimeError("fixture")),
    )
    assert out["call_id"] == "call-A" and out["error"] == "bridge_request_failed"


@pytest.mark.parametrize("pending,accepted,stage", [
    ({}, True, "approve"),
    ({"approval_id": "fixture", "approval_token": "synthetic"}, False, "approve"),
    ({"approval_id": "fixture", "approval_token": "synthetic"}, True, "executed"),
])
def test_manual_approval_results_keep_id(pending, accepted, stage):
    transport = Mock(side_effect=offline_computer_use_transport)
    approval = Mock(return_value={"accepted": accepted})
    _, out = adapter.approve_and_reexecute(
        adapter.ParsedToolCall("pc_open_url", {}, "call-A"), pending,
        http_fn=transport, approve_fn=approval,
    )
    assert out["call_id"] == "call-A" and out["stage"] == stage
    if stage == "executed":
        assert out["ok"] is False and out["execute"]["status"] == "disabled"
    else:
        transport.assert_not_called()


@pytest.mark.parametrize("enabled", [False, True])
def test_dev_auto_approve_outcome_keeps_id(monkeypatch, enabled):
    monkeypatch.setenv("LUMOS_DEV_AUTO_APPROVE", "1" if enabled else "0")
    transport = Mock(side_effect=[
        (200, {"status": "pending_approval", "approval_id": "fixture", "approval_token": "synthetic"}),
        (200, {"status": "disabled", "ok": False}),
    ])
    approval = Mock(return_value={"accepted": True})
    out = adapter.run_tool_call_loop(
        adapter.ParsedToolCall("pc_open_url", {}, "call-A"),
        http_fn=transport, approve_fn=approval, auto_approve=True,
    )
    assert out["call_id"] == "call-A" and not out["ok"]
    assert out["stage"] == ("executed" if enabled else "pending")
    assert approval.call_count == int(enabled)


def test_same_id_across_responses_is_not_a_replay_authorization():
    transport = Mock(side_effect=offline_computer_use_transport)
    for _ in range(2):
        out = adapter.run_openai_response_loop(item(), http_fn=transport)
        assert out[0]["call_id"] == "call-A"
        assert out[0]["execute"]["status"] == "disabled"
    assert transport.call_count == 2  # Dedup is payload-local, not a replay cache.
