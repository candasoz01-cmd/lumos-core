import argparse
import json
import sys

from lumos_core import __version__


def run_ask(prompt: str, provider: str = "openai") -> None:
    """Route prompt through pre_route then AIRouter then response_builder; print response or Lumos message."""
    from lumos_core.ai_router import AIRouter
    from lumos_core.context.context import Context
    from lumos_core.policy.pre_route import pre_route
    from lumos_core.response_builder import build_response
    from lumos_core.user_identity import load as load_user_identity

    ctx = Context(message=prompt)
    route = pre_route(ctx)
    if route.destination != "provider":
        print(route.message)
        return

    router = AIRouter()
    try:
        result = router.route(prompt, provider=provider)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    user = load_user_identity()
    out_text = build_response(result.text, user)
    prefix = "[stub] " if result.is_stub else ""
    print()
    print(f"Provider: {provider}")
    print(f"Prompt: {prompt}")
    print(f"Response: {prefix}{out_text}")
    print()


def run_chat(provider: str = "openai") -> None:
    """Interactive terminal chat: pre_route then AIRouter then response_builder; Lumos messages for command/tool/unsupported."""
    from lumos_core.ai_router import AIRouter
    from lumos_core.context.context import Context
    from lumos_core.policy.pre_route import pre_route
    from lumos_core.response_builder import build_response
    from lumos_core.user_identity import load as load_user_identity

    router = AIRouter()
    user = load_user_identity()
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

        ctx = Context(message=line)
        route = pre_route(ctx)
        if route.destination != "provider":
            print("Lumos > " + route.message)
            continue

        try:
            result = router.route(line, provider=provider)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            continue
        out_text = build_response(result.text, user)
        prefix = "[stub] " if result.is_stub else ""
        print("Lumos > " + prefix + out_text)


def main():
    parser = argparse.ArgumentParser(prog="lumos")
    parser.add_argument("--version", action="store_true")
    sub = parser.add_subparsers(dest="cmd", help="subcommand")
    sub.add_parser("env", help="ilk açılış environment scan (JSON + özet)")
    ask_p = sub.add_parser("ask", help="send a prompt to the AI router")
    ask_p.add_argument("prompt", help="your prompt (e.g. \"Explain quantum computing\")")
    ask_p.add_argument("--provider", default="openai", help="AI provider: openai, gemini, anthropic (default: openai)")
    args = parser.parse_args()

    if args.version:
        print(__version__)
        return

    if args.cmd == "env":
        _run_env()
        return

    if args.cmd == "ask":
        run_ask(args.prompt, provider=args.provider)
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
