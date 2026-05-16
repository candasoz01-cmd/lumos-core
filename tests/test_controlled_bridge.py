"""Kontrollü köprü: dar komut yüzeyi ve workspace sandbox."""
from __future__ import annotations

from pathlib import Path

import pytest

from kando_runtime.controlled_bridge import (
    BRIDGE_MODE_CONTROLLED,
    execute_controlled,
    policy_allows_normalized,
    validate_controlled_body,
)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "workspace").mkdir()
    return tmp_path


def test_ping_ok(repo: Path) -> None:
    out = execute_controlled(
        repo,
        {"permission": "file_rw", "command": "ping"},
    )
    assert out["ok"] is True
    assert out["bridge_mode"] == BRIDGE_MODE_CONTROLLED


def test_write_read_roundtrip(repo: Path) -> None:
    w = execute_controlled(
        repo,
        {
            "permission": "file_rw",
            "command": "write",
            "path": "hello.txt",
            "content": "merhaba lumos",
        },
    )
    assert w["ok"] is True
    r = execute_controlled(
        repo,
        {"permission": "file_rw", "command": "read", "path": "hello.txt"},
    )
    assert r["ok"] is True
    assert r["content"] == "merhaba lumos"


def test_path_traversal_rejected(repo: Path) -> None:
    out = execute_controlled(
        repo,
        {
            "permission": "file_rw",
            "command": "read",
            "path": "../secret.txt",
        },
    )
    assert out["ok"] is False
    assert out["error"] == "path_outside_sandbox"


def test_shell_surface_blocked(repo: Path) -> None:
    req, err = validate_controlled_body(
        {
            "permission": "file_rw",
            "command": "read",
            "path": "x.txt",
            "text": "run bash terminal",
        },
    )
    assert req is None
    assert err == "surface_blocked"


def test_delete_surface_blocked(repo: Path) -> None:
    out = execute_controlled(
        repo,
        {
            "permission": "file_rw",
            "command": "write",
            "path": "delete me.txt",
            "content": "x",
        },
    )
    assert out["ok"] is False


def test_policy_blocks_agent_in_controlled_mode() -> None:
    ok, reason = policy_allows_normalized(
        {
            "bridge_mode": "controlled",
            "controlled_permission": "file_rw",
            "mode": "agent",
            "agent_blob": "do something",
        },
    )
    assert ok is False
    assert reason == "agent_not_allowed_in_controlled_mode"


def test_policy_allows_workspace_patch() -> None:
    ok, reason = policy_allows_normalized(
        {
            "bridge_mode": "controlled",
            "controlled_permission": "file_rw",
            "mode": "direct_patch",
            "target_rel": "workspace/note.txt",
            "target_body": "hello",
        },
    )
    assert ok is True
    assert reason == ""
