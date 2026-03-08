from __future__ import annotations

import argparse
import json
import sys
from typing import TYPE_CHECKING

from lumos_core import __version__

if TYPE_CHECKING:
    from lumos_core.ai_router import AIRouter


def run_ask(
    prompt: str,
    provider: str = "openai",
    router: AIRouter | None = None,
) -> None:
    """Route prompt through pre_route then AIRouter then response_builder; print response or Lumos message.
    Pass router= for tests (e.g. mock providers)."""
    from lumos_core.ai_router import AIRouter
    from lumos_core.context.context import Context
    from lumos_core.memory.memory_manager import (
        add_approved_preference,
        build_chat_context,
        load_user_profile,
        parse_memory_save_intent,
        preference_key_from_value,
    )
    from lumos_core.policy.pre_route import pre_route
    from lumos_core.response_builder import build_response

    # Explicit memory-save: "bunu hatırla: ..." -> store in user memory only, no provider
    content = parse_memory_save_intent(prompt)
    if content is not None:
        key = preference_key_from_value(content)
        add_approved_preference(key, content)
        print()
        print(f"Lumos > Bunu hatırladım: {content}")
        print()
        return

    ctx = Context(message=prompt)
    route = pre_route(ctx)
    if route.destination != "provider":
        print(route.message)
        return

    if router is None:
        router = AIRouter()
    user, approved_prefs = load_user_profile()
    # Chat context wired only through memory manager (build_chat_context; ask has no session)
    try:
        result = router.route(
            prompt,
            provider=provider,
            user_name=user.name or None,
            chat_context=build_chat_context(user, approved_prefs, session_memory=None),
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    out_text = build_response(result.text, user)
    prefix = "[stub] " if result.is_stub else ""
    print()
    print(f"Provider: {provider}")
    print(f"Prompt: {prompt}")
    print(f"Response: {prefix}{out_text}")
    print()


def run_chat(
    provider: str = "openai",
    router: AIRouter | None = None,
) -> None:
    """
    Interactive terminal chat with session memory. Each user message is sent through
    pre_route then either a read-only tool or the AI router. Conversation history
    (last N messages) is kept in memory for the session and passed to the provider.
    Exits on exit/quit/Ctrl+C/Ctrl+D.
    Pass router= for tests (e.g. mock providers).
    """
    from lumos_core.ai_router import AIRouter
    from lumos_core.context.context import Context
    from lumos_core.memory.memory_manager import (
        build_chat_context,
        create_session_memory,
        load_user_profile,
        parse_memory_save_intent,
        preference_key_from_value,
        add_approved_preference,
    )
    from lumos_core.policy.pre_route import pre_route
    from lumos_core.response_builder import build_response

    if router is None:
        router = AIRouter()
    session_memory = create_session_memory()
    user, approved_prefs = load_user_profile()
    EXIT_WORDS = frozenset({"exit", "quit"})

    while True:
        try:
            line = input("Lumos > ").strip()
        except EOFError:
            break
        except KeyboardInterrupt:
            print()
            break

        if not line:
            continue
        if line.lower() in EXIT_WORDS:
            break

        # Explicit memory-save: "bunu hatırla: ..." -> store in user memory, no provider
        content = parse_memory_save_intent(line)
        if content is not None:
            key = preference_key_from_value(content)
            add_approved_preference(key, content)
            print("Lumos > Bunu hatırladım: " + content)
            continue

        ctx = Context(message=line)
        route = pre_route(ctx)
        if route.destination != "provider":
            print("Lumos > " + route.message)
            session_memory.add_turn(line, route.message)
            continue

        try:
            chat_context = build_chat_context(user, approved_prefs, session_memory)
            result = router.route(
                line,
                provider=provider,
                user_name=user.name or None,
                chat_context=chat_context,
            )
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            continue
        out_text = build_response(result.text, user)
        prefix = "[stub] " if result.is_stub else ""
        print("Lumos > " + prefix + out_text)
        session_memory.add_turn(line, out_text)


def main():
    parser = argparse.ArgumentParser(prog="lumos")
    parser.add_argument("--version", action="store_true")
    sub = parser.add_subparsers(dest="cmd", help="subcommand")
    sub.add_parser("env", help="ilk açılış environment scan (JSON + özet)")
    ask_p = sub.add_parser("ask", help="send a prompt to the AI router")
    ask_p.add_argument("prompt", help="your prompt (e.g. \"Explain quantum computing\")")
    ask_p.add_argument("--provider", default="openai", help="AI provider: openai, gemini, anthropic (default: openai)")
    chat_p = sub.add_parser("chat", help="interactive terminal chat with session memory")
    chat_p.add_argument("--provider", default="openai", help="AI provider (default: openai)")
    tg_p = sub.add_parser("tg", help="telegram: auth, follow, sources, enable, disable, run")
    tg_p.add_argument(
        "sub",
        nargs="?",
        choices=["auth", "follow", "sources", "enable", "disable", "run"],
    )
    tg_p.add_argument("peer", nargs="?", default=None)
    tg_p.add_argument("--db", default=None)
    args = parser.parse_args()

    if args.version:
        print(__version__)
        return

    cmd = args.cmd
    if cmd == "tg":
        from lumos_social.telegram.cli import _tg_cmd

        return _tg_cmd(args)

    if cmd == "env":
        _run_env()
        return

    if cmd == "ask":
        run_ask(args.prompt, provider=args.provider)
        return

    if cmd == "chat":
        run_chat(provider=args.provider)
        return

    print("Lumos core is running")


def _run_env() -> None:
    from lumos_core.device.scan import scan
    from lumos_core.device.capabilities import classify, format_report

    data = scan()
    caps = classify(data)
    data["capabilities"] = caps

    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("\n--- Özet ---")
    for k, v in caps.items():
        print(f"  {k}: {v}")
    print("\n" + format_report(data, caps))
