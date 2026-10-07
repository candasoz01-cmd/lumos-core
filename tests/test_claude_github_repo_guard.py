"""#906 risk 2: GitHub MCP calls stay bound to candasoz01-cmd/lumos-core."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "github_repo_guard.py"


def run_hook(payload: object) -> subprocess.CompletedProcess[str]:
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run([sys.executable, str(HOOK)], input=stdin, capture_output=True, text=True, check=False)


def call(tool: str, **tool_input: object) -> dict:
    return {"hook_event_name": "PreToolUse", "tool_name": f"mcp__github__{tool}", "tool_input": tool_input}


@pytest.mark.parametrize(
    "payload",
    [
        call("pull_request_read", method="get", owner="candasoz01-cmd", repo="lumos-core", pullNumber=905),
        call("list_commits", owner="Candasoz01-CMD", repo="Lumos-Core"),
        call("get_me"),
        call("search_code", query="guard repo:candasoz01-cmd/lumos-core"),
        call("issue_write", method="create", owner="candasoz01-cmd", repo="lumos-core",
             parent_owner="candasoz01-cmd", parent_repo="lumos-core", parent_issue_number=1),
    ],
)
def test_calls_on_this_repository_pass(payload: dict) -> None:
    result = run_hook(payload)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "payload",
    [
        call("pull_request_read", method="get_diff", owner="someone", repo="private-repo", pullNumber=1),
        call("list_commits", owner="candasoz01-cmd", repo="other-repo"),
        call("get_check_run", owner="candasoz01-cmd"),
        call("get_file_contents", repo="lumos-core"),
        call("issue_write", method="create", owner="candasoz01-cmd", repo="lumos-core",
             parent_owner="someone", parent_repo="else", parent_issue_number=1),
        call("search_code", query="password"),
        call("search_issues", query="repo:candasoz01-cmd/lumos-core repo:someone/else"),
        call("search_pull_requests", query="org:someone is:open"),
        call("search_code", query="-repo:candasoz01-cmd/lumos-core secret"),
        call("search_code", query="secret -repo:candasoz01-cmd/lumos-core"),
        call("search_code", query="repo:candasoz01-cmd/lumos-core OR secret"),
        call("search_code", query="secret NOT repo:candasoz01-cmd/lumos-core"),
        call("search_code", query="(repo:candasoz01-cmd/lumos-core) secret"),
        call("search_code"),
    ],
)
def test_calls_outside_this_repository_are_blocked(payload: dict) -> None:
    result = run_hook(payload)
    assert result.returncode == 2
    assert "call blocked" in result.stderr


@pytest.mark.parametrize("stdin", ["", "not json", json.dumps({"tool_input": {}}), json.dumps({"tool_name": "x", "tool_input": []})])
def test_unreadable_input_fails_closed(stdin: str) -> None:
    result = run_hook(stdin)
    assert result.returncode == 2
