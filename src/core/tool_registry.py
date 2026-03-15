"""Minimal tool registry: map intent names to declared capabilities.

Intents (e.g. list_files) are checked against this registry before execution.
No filesystem or real tool implementation here; only availability and description.
"""
from __future__ import annotations

TOOLS: dict[str, dict[str, bool | str]] = {
    "list_files": {
        "available": False,
        "description": "List files in a folder",
    },
    "read_file": {
        "available": False,
        "description": "Read a file from disk",
    },
    "write_file": {
        "available": False,
        "description": "Write content to a file",
    },
}


def tool_available(name: str) -> bool:
    """Return True if the tool is registered and marked available."""
    if not name or not isinstance(name, str):
        return False
    entry = TOOLS.get(name.strip())
    if entry is None:
        return False
    return bool(entry.get("available") is True)
