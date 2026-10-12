"""Approval must cover the exact PC command, canonical arguments and device."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from kando_bridge.pc_remote_tools import (
    CMD_OPEN_URL,
    CMD_SUGGEST_CLICK,
    CMD_TYPE_TEXT,
    approve_pc_remote_pending,
    handle_tools_execute_body,
)
from kando_bridge.pending_approvals import (
    find_pending_by_approval_id,
    stored_approval_token,
    write_pending_approval,
)
from kando_bridge.pc_remote_audit import EVENT_STUB_EXECUTED, read_audit_events


def _approved(root: Path, *, command: str = CMD_OPEN_URL,
              arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = {"url": "https://example.invalid/a"} if arguments is None else arguments
    status, pending = handle_tools_execute_body(
        {"command": command, "arguments": args, "target_device": "fixture-device"},
        repo_root=root,
    )
    assert status == 200 and pending["status"] == "pending_approval"
    found = find_pending_by_approval_id(root, pending["approval_id"])
    assert found is not None
    ok, reason, _ = approve_pc_remote_pending(
        found[0], found[1], approved=True, repo_root=root,
    )
    assert ok, reason
    return {
        "command": command, "arguments": args, "target_device": "fixture-device",
        "approval_id": pending["approval_id"],
        "approval_token": stored_approval_token(root, pending["approval_id"]),
    }


def _execute(root: Path, body: dict[str, Any], receipts: list[dict[str, Any]]) -> dict[str, Any]:
    _, result = handle_tools_execute_body(body, repo_root=root)
    if result.get("ok") and result.get("status") == "stub":
        receipts.append(result["simulated"])
    return result


def test_changed_url_revokes_the_original_approval(tmp_path: Path) -> None:
    body = _approved(tmp_path)
    receipts: list[dict[str, Any]] = []
    rejected = _execute(tmp_path, {**body, "arguments": {"url": "https://example.invalid/b"}}, receipts)
    assert receipts == [], "changed URL must not reach the stub effect"
    assert not any(row["event"] == EVENT_STUB_EXECUTED for row in read_audit_events(tmp_path))
    assert rejected["error"] == "approval_request_mismatch"
    found = find_pending_by_approval_id(tmp_path, body["approval_id"])
    assert found is not None
    assert found[1]["status"] == "revoked"
    assert found[1]["revoked_reason"] == "scope_change"
    assert found[1]["used"] is True
    original = _execute(tmp_path, body, receipts)
    assert original["error"] == "approval_revoked_scope_change"
    assert receipts == []
    assert not any(row["event"] == EVENT_STUB_EXECUTED for row in read_audit_events(tmp_path))


@pytest.mark.parametrize("change", [
    {"command": CMD_TYPE_TEXT, "arguments": {"text": "benign text"}},
    {"target_device": "other-fixture-device"},
    {"approval_id": "pc_remote_nonexistent_id"},
    {"arguments": {"url": "https://example.invalid/a", "extra": "value"}},
])
def test_request_scope_changes_are_rejected(tmp_path: Path, change: dict[str, Any]) -> None:
    body = _approved(tmp_path)
    receipts: list[dict[str, Any]] = []
    out = _execute(tmp_path, {**body, **change}, receipts)
    assert out["error"] == "approval_request_mismatch" and receipts == []
    again = _execute(tmp_path, body, receipts)
    assert again["error"] == "approval_revoked_scope_change"
    assert receipts == []


@pytest.mark.parametrize("text", ["different", "shorter", "same-prefix-" + "x" * 500 + "B"])
def test_full_text_arguments_are_bound_beyond_preview(tmp_path: Path, text: str) -> None:
    body = _approved(tmp_path, command=CMD_TYPE_TEXT,
                     arguments={"text": "same-prefix-" + "x" * 500 + "A"})
    receipts: list[dict[str, Any]] = []
    out = _execute(tmp_path, {**body, "arguments": {"text": text}}, receipts)
    assert out["error"] == "approval_request_mismatch" and receipts == []


def test_canonical_object_key_order_preserves_matching_control(tmp_path: Path) -> None:
    arguments = {"target_description": "benign fixture", "x": 1, "y": 2}
    body = _approved(tmp_path, command=CMD_SUGGEST_CLICK, arguments=arguments)
    receipts: list[dict[str, Any]] = []
    reordered = {"y": 2, "x": 1, "target_description": "benign fixture"}
    out = _execute(tmp_path, {**body, "arguments": reordered}, receipts)
    assert out["status"] == "stub" and len(receipts) == 1
    assert receipts[0]["auto_click"] is False


@pytest.mark.parametrize("arguments", [
    {"target_description": "benign fixture", "x": True, "y": 2},
    {"target_description": "benign fixture", "x": "1", "y": 2},
    {"target_description": "benign fixture", "x": float("nan"), "y": 2},
    {"target_description": "benign fixture", "x": float("inf"), "y": 2},
    {"target_description": "benign fixture", "x": 1},
])
def test_changed_types_nonfinite_and_removed_arguments_fail_closed(
    tmp_path: Path, arguments: dict[str, Any],
) -> None:
    body = _approved(tmp_path, command=CMD_SUGGEST_CLICK,
                     arguments={"target_description": "benign fixture", "x": 1, "y": 2})
    receipts: list[dict[str, Any]] = []
    out = _execute(tmp_path, {**body, "arguments": arguments}, receipts)
    assert out["error"] == "approval_request_mismatch" and receipts == []


@pytest.mark.parametrize("field", ["command", "arguments", "target_device"])
def test_incomplete_approved_record_fails_closed(tmp_path: Path, field: str) -> None:
    body = _approved(tmp_path)
    found = find_pending_by_approval_id(tmp_path, body["approval_id"])
    assert found is not None
    found[1].pop(field)
    write_pending_approval(found[1], tmp_path)
    receipts: list[dict[str, Any]] = []
    out = _execute(tmp_path, body, receipts)
    assert out["error"] == "approval_request_mismatch" and receipts == []


def test_token_only_lookup_still_binds_resolved_approval(tmp_path: Path) -> None:
    body = _approved(tmp_path)
    body.pop("approval_id")
    receipts: list[dict[str, Any]] = []
    out = _execute(tmp_path, body, receipts)
    assert out["status"] == "stub" and len(receipts) == 1


def test_binding_uses_fresh_record_at_consumption(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import kando_bridge.pc_remote_tools as pc

    body = _approved(tmp_path)
    original = pc.check_approval_gate

    def change_after_precheck(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        found = find_pending_by_approval_id(tmp_path, body["approval_id"])
        assert found is not None
        found[1]["arguments"] = {"url": "https://example.invalid/changed-record"}
        write_pending_approval(found[1], tmp_path)
        return result

    monkeypatch.setattr(pc, "check_approval_gate", change_after_precheck)
    receipts: list[dict[str, Any]] = []
    out = _execute(tmp_path, body, receipts)
    assert out["error"] == "approval_request_mismatch" and receipts == []
    found = find_pending_by_approval_id(tmp_path, body["approval_id"])
    assert found is not None
    assert found[1]["status"] == "revoked"
    assert found[1]["used"] is True


def test_concurrent_matching_and_changed_requests_never_execute_changed(tmp_path: Path) -> None:
    body = _approved(tmp_path)
    changed = {**body, "arguments": {"url": "https://example.invalid/b"}}
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(handle_tools_execute_body, request, repo_root=tmp_path)
                for request in (body, changed)]
        matching, mismatch = [job.result()[1] for job in jobs]
    assert mismatch.get("status") != "stub"
    assert mismatch["error"] in {
        "approval_request_mismatch",
        "approval_already_used",
        "approval_revoked_scope_change",
    }
    events = [row for row in read_audit_events(tmp_path) if row["event"] == EVENT_STUB_EXECUTED]
    if mismatch["error"] == "approval_request_mismatch" and matching.get("status") != "stub":
        assert matching["error"] == "approval_revoked_scope_change"
        assert events == []
    else:
        assert matching["status"] == "stub"
        assert len(events) == 1
        assert events[0].get("command") == CMD_OPEN_URL


def test_nested_keys_are_canonical_but_array_order_is_bound(tmp_path: Path) -> None:
    arguments = {
        "url": "https://example.invalid/a", "metadata": {"b": [1, 2], "a": "fixture"},
    }
    revoked = _approved(tmp_path, arguments=arguments)
    receipts: list[dict[str, Any]] = []
    changed = {"url": "https://example.invalid/a", "metadata": {"a": "fixture", "b": [2, 1]}}
    assert _execute(tmp_path, {**revoked, "arguments": changed}, receipts)["error"] == "approval_request_mismatch"
    assert receipts == []
    assert _execute(tmp_path, revoked, receipts)["error"] == "approval_revoked_scope_change"
    fresh = _approved(tmp_path, arguments=arguments)
    reordered = {"metadata": {"a": "fixture", "b": [1, 2]}, "url": "https://example.invalid/a"}
    assert _execute(tmp_path, {**fresh, "arguments": reordered}, receipts)["status"] == "stub"
    assert len(receipts) == 1


def test_binding_also_checked_without_fcntl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    body = _approved(tmp_path)
    monkeypatch.setitem(sys.modules, "fcntl", None)
    receipts: list[dict[str, Any]] = []
    out = _execute(tmp_path, {**body, "arguments": {"url": "https://example.invalid/b"}}, receipts)
    assert out["error"] == "approval_request_mismatch" and receipts == []
    assert _execute(tmp_path, body, receipts)["error"] == "approval_revoked_scope_change"
    assert receipts == []
