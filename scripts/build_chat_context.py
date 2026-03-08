#!/usr/bin/env python3
"""
Build chat context for Lumos: load user profile, optionally session memory, and print
the context dict (chat_context_suffix, recent_messages) that would be passed to the router.

Usage:
  python scripts/build_chat_context.py [base_dir]

Requires lumos_core to be installed (e.g. pip install -e ".[dev]" or make install).
With no session (ask-style): only user memory in suffix, recent_messages=[].
With session: set LUMOS_SESSION=1 and optionally add messages (this script uses empty session).
"""

from __future__ import annotations

import json
import os
import sys
from lumos_core.memory import build_chat_context, create_session_memory, load_user_profile


def main() -> None:
    base_dir = (sys.argv[1:] and sys.argv[1]) or None
    user, approved_prefs = load_user_profile(base_dir)
    session_memory = None
    if os.environ.get("LUMOS_SESSION"):
        session_memory = create_session_memory()
        # Optionally add messages here for testing; by default empty
    ctx = build_chat_context(user, approved_prefs, session_memory=session_memory)
    # Serialize for output (recent_messages may contain dicts)
    out = {
        "chat_context_suffix": ctx.get("chat_context_suffix"),
        "recent_messages": ctx.get("recent_messages", []),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
