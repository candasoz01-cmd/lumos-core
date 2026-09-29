#!/usr/bin/env python3
"""PreToolUse guard: bind GitHub MCP calls to this repository (#906, risk 2).

Permission rules cannot look at tool parameters, so an allowed tool such as
``mcp__github__pull_request_read`` would otherwise read any repository the
token can see. This hook reads the call from stdin and blocks it (exit 2)
when it names another repository. Unreadable input is blocked too.
"""

from __future__ import annotations

import json
import re
import sys

ALLOWED_OWNER = "candasoz01-cmd"
ALLOWED_REPO = "lumos-core"
ALLOWED_FULL = f"{ALLOWED_OWNER}/{ALLOWED_REPO}"

# Pairs of (owner key, repo key) that a GitHub MCP tool may carry.
REPO_KEY_PAIRS = (("owner", "repo"), ("parent_owner", "parent_repo"))
# Search qualifiers that name a scope, with an optional negation prefix.
SCOPE_QUALIFIER = re.compile(r"(?<![\w-])(-?)(repo|org|user|owner):(\S+)", re.IGNORECASE)
# Boolean operators and grouping can combine the repo qualifier with an
# unscoped term (`repo:x OR secret`), so they are not accepted at all.
BOOLEAN_OPERATOR = re.compile(r"(?<!\S)(?:NOT|OR)(?!\S)|[()]")


def _same(value: object, expected: str) -> bool:
    return isinstance(value, str) and value.strip().lower() == expected.lower()


def violation(tool_name: str, tool_input: dict) -> str | None:
    """Return a reason to block the call, or None to let permissions decide."""
    for owner_key, repo_key in REPO_KEY_PAIRS:
        has_owner = owner_key in tool_input
        has_repo = repo_key in tool_input
        if not (has_owner or has_repo):
            continue
        if not (_same(tool_input.get(owner_key), ALLOWED_OWNER) and _same(tool_input.get(repo_key), ALLOWED_REPO)):
            got = f"{tool_input.get(owner_key)}/{tool_input.get(repo_key)}"
            return f"{tool_name}: {owner_key}/{repo_key}={got} is outside {ALLOWED_FULL}"

    if tool_name.startswith("mcp__github__search_"):
        query = tool_input.get("query")
        if not isinstance(query, str):
            return f"{tool_name}: search without a query string"
        if BOOLEAN_OPERATOR.search(query):
            return f"{tool_name}: boolean operators or grouping are not allowed in a guarded search"
        scopes = SCOPE_QUALIFIER.findall(query)
        if not scopes:
            return f"{tool_name}: query must include repo:{ALLOWED_FULL}"
        for negated, kind, target in scopes:
            if negated:
                return f"{tool_name}: negated qualifier -{kind}:{target} widens the search"
            if kind.lower() != "repo" or not _same(target, ALLOWED_FULL):
                return f"{tool_name}: qualifier {kind}:{target} is outside {ALLOWED_FULL}"
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
        tool_name = event["tool_name"]
        tool_input = event.get("tool_input", {})
        if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
            raise TypeError("unexpected hook payload shape")
    except Exception as exc:  # fail closed on anything unreadable
        print(f"github_repo_guard: unreadable hook input ({exc}); call blocked", file=sys.stderr)
        return 2

    reason = violation(tool_name, tool_input)
    if reason:
        print(f"github_repo_guard: {reason}; call blocked", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
