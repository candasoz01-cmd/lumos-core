"""Disabled Computer Use contract: no execution, no success, no secret echo."""

from __future__ import annotations

import ast
import builtins
import json
import os
import socket
import subprocess
import sys
import types
import urllib.request
import webbrowser
from pathlib import Path

import pytest

from kando_bridge.computer_use_executor import (
    CATEGORY_UNKNOWN,
    ERROR_DISABLED,
    ERROR_REJECTED,
    EXECUTOR_CONTRACT_VERSION,
    RECOGNIZED_ACTION_CATEGORIES,
    RESULT_KIND_UNEXECUTED,
    STATUS_DISABLED,
    STATUS_REJECTED,
    ComputerUseAction,
    ComputerUseCategory,
    ComputerUseResult,
    DisabledComputerUseExecutor,
    default_executor,
    executor_contract_payload,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    REPO_ROOT
    / "packages"
    / "kando_bridge"
    / "src"
    / "kando_bridge"
    / "computer_use_executor.py"
)

EXPECTED_CATEGORIES = (
    "read",
    "observe",
    "suggest",
    "click",
    "navigate",
    "type",
    "external_write",
    "send",
    "email",
    "file_send",
    "delete",
    "payment",
    "domain",
)

FORBIDDEN_IMPORT_ROOTS = frozenset({
    "os",
    "subprocess",
    "socket",
    "urllib",
    "http",
    "ssl",
    "requests",
    "httpx",
    "webbrowser",
    "playwright",
    "selenium",
    "shutil",
    "ctypes",
    "pty",
    "asyncio",
    "ftplib",
    "smtplib",
    "poplib",
    "imaplib",
    "telnetlib",
    "xmlrpc",
    "multiprocessing",
    "signal",
    "fcntl",
    "termios",
    "openai",
    "kando_bridge",
})
FORBIDDEN_CALLS = frozenset({
    "open",
    "system",
    "popen",
    "urlopen",
    "eval",
    "exec",
    "compile",
    "__import__",
    "Popen",
    "run",
    "call",
    "check_call",
    "check_output",
})
SECRET = "sk-live-DO-NOT-ECHO-683"
FORBIDDEN_OUTCOME_STRINGS = frozenset({
    "completed",
    "real",
    "success",
    "tamamlandi",
})


def _assert_unexecuted(
    result: ComputerUseResult,
    *,
    status: str,
    category: str,
    error: str,
) -> None:
    assert result.ok is False
    assert result.status == status
    assert result.status not in FORBIDDEN_OUTCOME_STRINGS
    assert result.result_kind == RESULT_KIND_UNEXECUTED
    assert result.result_kind not in FORBIDDEN_OUTCOME_STRINGS
    assert result.completed is False
    assert result.real is False
    assert result.success is False
    assert result.real_execution is False
    assert result.category == category
    assert result.error == error
    assert result.contract_version == EXECUTOR_CONTRACT_VERSION
    public = result.public_dict()
    assert public == {
        "ok": False,
        "status": status,
        "result_kind": RESULT_KIND_UNEXECUTED,
        "category": category,
        "error": error,
        "completed": False,
        "real": False,
        "success": False,
        "real_execution": False,
        "contract_version": EXECUTOR_CONTRACT_VERSION,
    }
    blob = repr(result) + json.dumps(public)
    assert SECRET not in blob
    assert "target-" not in blob
    visible = (result.status, result.result_kind, result.category, result.error)
    assert FORBIDDEN_OUTCOME_STRINGS.isdisjoint(visible)


def _approval_action(category: str) -> ComputerUseAction:
    return ComputerUseAction(
        category=ComputerUseCategory(category),
        target=f"target-{SECRET}",
        arguments={
            "approved": True,
            "auto_approve": True,
            "approval_granted": True,
            "confirm": "yes",
            "password": SECRET,
            "api_key": SECRET,
            "token": SECRET,
            "ok": True,
            "status": "completed",
            "result_kind": "real",
            "success": True,
        },
        task_id=f"task-{SECRET}",
        approval_id=f"apr-{SECRET}",
    )


def test_recognized_categories_are_the_closed_contract() -> None:
    assert RECOGNIZED_ACTION_CATEGORIES == EXPECTED_CATEGORIES
    assert len(RECOGNIZED_ACTION_CATEGORIES) == len(set(RECOGNIZED_ACTION_CATEGORIES))
    assert tuple(item.value for item in ComputerUseCategory) == EXPECTED_CATEGORIES


@pytest.mark.parametrize("category", EXPECTED_CATEGORIES)
def test_recognized_category_stays_disabled_with_approval_like_input(
    category: str,
) -> None:
    result = DisabledComputerUseExecutor().execute(_approval_action(category))
    _assert_unexecuted(
        result,
        status=STATUS_DISABLED,
        category=category,
        error=ERROR_DISABLED,
    )
    again = default_executor().execute(_approval_action(category))
    assert again == result


def test_missing_approval_is_still_disabled() -> None:
    action = ComputerUseAction(category=ComputerUseCategory.READ)
    result = default_executor().execute(action)
    _assert_unexecuted(
        result,
        status=STATUS_DISABLED,
        category="read",
        error=ERROR_DISABLED,
    )


@pytest.mark.parametrize(
    "action",
    [
        None,
        "",
        "click",
        "CLICK",
        "shell",
        SECRET,
        0,
        True,
        b"click",
        ["click"],
        {"category": "click", "approved": True, "api_key": SECRET},
        object(),
    ],
)
def test_invalid_and_unknown_inputs_fail_closed(action: object) -> None:
    result = default_executor().execute(action)
    _assert_unexecuted(
        result,
        status=STATUS_REJECTED,
        category=CATEGORY_UNKNOWN,
        error=ERROR_REJECTED,
    )


@pytest.mark.parametrize("category", ["", " ", "CLICK", "shell", "scroll", SECRET])
def test_unknown_category_constructor_does_not_echo_input(category: str) -> None:
    with pytest.raises(ValueError, match="unknown computer-use category") as caught:
        ComputerUseAction(category=category)
    if category.strip():
        assert category not in str(caught.value)
    assert SECRET not in str(caught.value)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"category": 1}, "category must be a recognized computer-use category"),
        ({"category": None}, "category must be a recognized computer-use category"),
        ({"category": "read", "target": None}, "target must be a string"),
        ({"category": "read", "arguments": ["nope"]}, "arguments must be a mapping"),
        ({"category": "read", "arguments": SECRET}, "arguments must be a mapping"),
        ({"category": "read", "task_id": None}, "task_id must be a string"),
        ({"category": "read", "approval_id": 5}, "approval_id must be a string"),
    ],
)
def test_malformed_action_raises_fixed_message_without_payload(
    kwargs: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(TypeError, match=message) as caught:
        ComputerUseAction(**kwargs)  # type: ignore[arg-type]
    assert SECRET not in str(caught.value)


def test_action_and_result_are_immutable() -> None:
    action = _approval_action("click")
    assert SECRET not in repr(action)
    assert "target-" not in repr(action)
    with pytest.raises(TypeError):
        action.arguments["password"] = "changed"  # type: ignore[index]
    with pytest.raises(AttributeError):
        action.target = "elsewhere"  # type: ignore[misc]
    result = default_executor().execute(action)
    with pytest.raises(AttributeError):
        result.ok = True  # type: ignore[misc]
    public = result.public_dict()
    public["ok"] = True
    public["status"] = "completed"
    assert result.ok is False
    assert result.status == STATUS_DISABLED


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ok": True, "status": STATUS_DISABLED, "result_kind": RESULT_KIND_UNEXECUTED,
         "category": "read", "error": ERROR_DISABLED},
        {"ok": False, "status": "completed", "result_kind": RESULT_KIND_UNEXECUTED,
         "category": "read", "error": ERROR_DISABLED},
        {"ok": False, "status": "real", "result_kind": RESULT_KIND_UNEXECUTED,
         "category": "read", "error": ERROR_DISABLED},
        {"ok": False, "status": "success", "result_kind": RESULT_KIND_UNEXECUTED,
         "category": "read", "error": ERROR_DISABLED},
        {"ok": False, "status": STATUS_DISABLED, "result_kind": "completed",
         "category": "read", "error": ERROR_DISABLED},
        {"ok": False, "status": STATUS_DISABLED, "result_kind": "real",
         "category": "read", "error": ERROR_DISABLED},
        {"ok": False, "status": STATUS_REJECTED, "result_kind": RESULT_KIND_UNEXECUTED,
         "category": CATEGORY_UNKNOWN, "error": ERROR_REJECTED, "completed": True},
        {"ok": False, "status": STATUS_REJECTED, "result_kind": RESULT_KIND_UNEXECUTED,
         "category": CATEGORY_UNKNOWN, "error": ERROR_REJECTED, "real": True},
        {"ok": False, "status": STATUS_REJECTED, "result_kind": RESULT_KIND_UNEXECUTED,
         "category": CATEGORY_UNKNOWN, "error": ERROR_REJECTED, "success": True},
        {"ok": False, "status": STATUS_REJECTED, "result_kind": RESULT_KIND_UNEXECUTED,
         "category": CATEGORY_UNKNOWN, "error": ERROR_REJECTED, "real_execution": True},
        {"ok": False, "status": STATUS_DISABLED, "result_kind": RESULT_KIND_UNEXECUTED,
         "category": "read", "error": SECRET},
    ],
)
def test_result_refuses_completed_real_or_success(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        ComputerUseResult(**kwargs)  # type: ignore[arg-type]


def test_contract_payload_is_disabled_and_secret_free() -> None:
    payload = executor_contract_payload()
    assert payload["default"] == "disabled"
    assert payload["real_execution"] is False
    assert payload["completed"] is False
    assert payload["success"] is False
    assert payload["runtime"] == "private_not_in_this_module"
    assert payload["categories"] == list(EXPECTED_CATEGORIES)
    assert payload["contract_version"] == EXECUTOR_CONTRACT_VERSION
    blob = json.dumps(payload)
    assert SECRET not in blob
    assert "http://" not in blob
    assert "https://" not in blob
    assert isinstance(default_executor(), DisabledComputerUseExecutor)


def test_source_has_no_runtime_imports_or_external_calls() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "http://" not in source
    assert "https://" not in source
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name.split(".", 1)[0] for alias in node.names]
            assert FORBIDDEN_IMPORT_ROOTS.isdisjoint(names)
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            assert root not in FORBIDDEN_IMPORT_ROOTS
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                assert func.id not in FORBIDDEN_CALLS
            elif isinstance(func, ast.Attribute):
                assert func.attr not in FORBIDDEN_CALLS
    executor = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "DisabledComputerUseExecutor"
    )
    helper = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_recognized_category"
    )
    leaked_names = {"arguments", "approval_id", "target", "task_id", "password", "token"}
    for scanned in (executor, helper):
        for child in ast.walk(scanned):
            if isinstance(child, ast.Attribute):
                assert child.attr not in leaked_names
            elif isinstance(child, ast.Name):
                assert child.id not in leaked_names
            elif isinstance(child, ast.Constant) and isinstance(child.value, str):
                assert child.value not in leaked_names


def test_import_and_execute_perform_no_external_operations(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def _blocked(label: str):
        def _inner(*_args: object, **_kwargs: object) -> None:
            calls.append(label)
            raise AssertionError(label)

        return _inner

    source = MODULE_PATH.read_text(encoding="utf-8")
    monkeypatch.setattr(subprocess, "run", _blocked("subprocess.run"))
    monkeypatch.setattr(subprocess, "Popen", _blocked("subprocess.Popen"))
    monkeypatch.setattr(subprocess, "call", _blocked("subprocess.call"))
    monkeypatch.setattr(subprocess, "check_call", _blocked("subprocess.check_call"))
    monkeypatch.setattr(subprocess, "check_output", _blocked("subprocess.check_output"))
    monkeypatch.setattr(os, "system", _blocked("os.system"))
    monkeypatch.setattr(os, "popen", _blocked("os.popen"))
    monkeypatch.setattr(socket, "socket", _blocked("socket.socket"))
    monkeypatch.setattr(socket, "create_connection", _blocked("socket.create_connection"))
    monkeypatch.setattr(urllib.request, "urlopen", _blocked("urllib.request.urlopen"))
    monkeypatch.setattr(webbrowser, "open", _blocked("webbrowser.open"))
    monkeypatch.setattr(builtins, "open", _blocked("open"))

    module_name = "computer_use_executor_isolated"
    module = types.ModuleType(module_name)
    module.__file__ = str(MODULE_PATH)
    before = set(sys.modules)
    sys.modules[module_name] = module
    try:
        exec(compile(source, str(MODULE_PATH), "exec"), module.__dict__)  # noqa: S102
    finally:
        sys.modules.pop(module_name, None)
    introduced = set(sys.modules) - before
    assert FORBIDDEN_IMPORT_ROOTS.isdisjoint(
        name.split(".", 1)[0] for name in introduced
    )

    executor = module.DisabledComputerUseExecutor()
    for category in module.RECOGNIZED_ACTION_CATEGORIES:
        action = module.ComputerUseAction(
            category=category,
            target=f"target-{SECRET}",
            arguments={"api_key": SECRET, "approved": True},
            approval_id=f"apr-{SECRET}",
        )
        result = executor.execute(action)
        assert result.ok is False
        assert result.real_execution is False
        assert result.completed is False
        assert SECRET not in repr(result)
    rejected = executor.execute({"api_key": SECRET, "status": "completed"})
    assert rejected.status == module.STATUS_REJECTED
    assert rejected.ok is False
    assert SECRET not in repr(rejected)
    assert calls == []
