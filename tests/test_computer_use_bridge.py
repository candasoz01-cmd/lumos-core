"""Exercise the existing adapter through an explicitly offline transport."""

import builtins
import importlib
import json
import os
import socket
import subprocess
import urllib.request
import webbrowser

import pytest

from kando_bridge import computer_use_bridge as bridge
from kando_bridge import openai_tool_adapter as adapter
from kando_bridge.pc_remote_tools import openai_tool_definitions


MAPPED = (
    ("pc_open_url", {"url": "https://example.invalid"}, "navigate"),
    ("pc_read_screen_state", {"scope": "active_window"}, "observe"),
    ("pc_type_text", {"text": "synthetic text"}, "type"),
    ("pc_suggest_click", {"target_description": "synthetic target"}, "suggest"),
)


def assert_unexecuted(result):
    for key in ("ok", "completed", "real", "success", "real_execution", "live_ready"):
        assert result[key] is False
    assert result["result_kind"] == "unexecuted"
    assert result["status"] in ("disabled", "rejected")
    assert result["stub_only"] is True
    assert result["transport"] == "offline"


@pytest.fixture
def no_external_calls(monkeypatch):
    calls = []

    def blocked(*args, **kwargs):
        calls.append(True)
        raise AssertionError("offline transport attempted an external operation")

    # Real collaborators must not run even if an implementation catches their
    # exceptions. The call list below catches swallowed attempts as well.
    for module, names in (
        (adapter, ("http_json", "approve_pending", "fetch_live_openai_response")),
        (socket, ("socket", "create_connection", "getaddrinfo")),
        (urllib.request, ("urlopen",)),
        (subprocess, ("run", "Popen")),
        (os, ("system", "popen")),
        (webbrowser, ("open",)),
        (builtins, ("open",)),
    ):
        for name in names:
            monkeypatch.setattr(module, name, blocked)
    yield calls
    assert calls == []


@pytest.mark.parametrize("command,arguments,category", MAPPED)
def test_existing_response_adapter_reaches_disabled_contract(
    command, arguments, category, no_external_calls, monkeypatch,
):
    monkeypatch.setenv("LUMOS_DEV_AUTO_APPROVE", "1")
    seen = []

    def transport(method, path, **kwargs):
        seen.append((method, path))
        return bridge.offline_computer_use_transport(method, path, **kwargs)

    response = {"output": [{
        "type": "function_call", "call_id": "synthetic-call",
        "name": command, "arguments": json.dumps(arguments),
    }]}
    results = adapter.run_openai_response_loop(
        response, http_fn=transport, auto_approve=True,
    )
    assert seen == [("POST", "/tools/execute")]
    assert len(results) == 1
    result = results[0]
    assert result["ok"] is False
    assert result["stage"] == "error"
    assert result["error"] == "computer_use_disabled"
    assert result["execute"]["category"] == category
    assert_unexecuted(result["execute"])
    model_result = adapter.tool_result_for_model(result["execute"])
    assert model_result["ok"] is False
    assert model_result["status"] == "disabled"
    assert model_result["simulated"] is None


def test_supported_command_names_match_existing_schema():
    schemas = {item["name"]: item for item in openai_tool_definitions()}
    for command, arguments, _ in MAPPED:
        schema = schemas[command]["parameters"]
        assert set(arguments) <= set(schema["properties"])
        assert set(schema["required"]) <= set(arguments)


@pytest.mark.parametrize("command", [
    "pc_open_app", "pc_request_file_picker", "pc_request_user_approval",
    "computer_use", "shell", "", None, [],
])
def test_unmapped_commands_never_guess_an_action(command, no_external_calls):
    status, result = bridge.offline_computer_use_transport(
        "POST", "/tools/execute", body={"command": command, "arguments": {}},
    )
    assert status == 400
    assert result["category"] == "unknown"
    assert result["status"] == "rejected"
    assert_unexecuted(result)


@pytest.mark.parametrize("body", [None, {}, [], "bad", {
    "command": "pc_open_url", "arguments": "not-a-dictionary",
}])
def test_bad_envelope_fails_closed(body, no_external_calls):
    status, result = bridge.offline_computer_use_transport(
        "POST", "/tools/execute", body=body,
    )
    assert status == 400
    assert_unexecuted(result)


@pytest.mark.parametrize("method,path,query,status", [
    ("GET", "/tools/execute", None, 405),
    ("POST", "/approve", None, 404),
    ("POST", "/task", None, 404),
    ("POST", "/tools/execute", {"enable": "true"}, 400),
])
def test_other_routes_cannot_approve_or_dispatch(method, path, query, status, no_external_calls):
    code, result = bridge.offline_computer_use_transport(
        method, path, query=query, body={"command": "pc_type_text", "arguments": {}},
    )
    assert code == status
    assert_unexecuted(result)


def test_payload_and_approval_metadata_are_not_forwarded_or_echoed(no_external_calls, monkeypatch):
    secret = "SYNTHETIC-PRIVATE-PAYLOAD-683"
    received = []
    original = bridge.ComputerUseAction

    def action(**kwargs):
        received.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(bridge, "ComputerUseAction", action)
    body = {
        "command": "pc_type_text", "arguments": {"text": secret, "approved": True},
        "approval_token": secret, "approval_id": secret,
        "requested_by": secret, "target_device": secret,
        "ok": True, "status": "completed", "result_kind": "real",
    }
    snapshot = json.dumps(body)
    code, result = bridge.offline_computer_use_transport("POST", "/tools/execute", body=body)
    assert code == 200
    assert received == [{"category": bridge.ComputerUseCategory.TYPE}]
    assert_unexecuted(result)
    assert secret not in json.dumps(result)
    assert json.dumps(body) == snapshot


def test_module_import_does_not_activate_any_transport(no_external_calls):
    default_http = adapter.http_json
    importlib.reload(bridge)
    assert adapter.http_json is default_http
    assert_unexecuted(bridge.offline_computer_use_transport(
        "POST", "/tools/execute", body={"command": "pc_read_screen_state", "arguments": {}},
    )[1])
