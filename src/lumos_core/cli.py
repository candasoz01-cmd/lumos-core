import argparse
import json
import sys

from lumos_core import __version__


def run_ask(prompt: str, provider: str = "openai") -> None:
    """Route prompt through AIRouter and print provider, prompt, and response (stub or real)."""
    from lumos_core.ai_router import AIRouter

    router = AIRouter()
    try:
        result = router.route(prompt, provider=provider)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    prefix = "[stub] " if result.is_stub else ""
    print()
    print(f"Provider: {provider}")
    print(f"Prompt: {prompt}")
    print(f"Response: {prefix}{result.text}")
    print()


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
