"""Entry point: lumos (or python -m lumos_core). Subcommands: cli (default), web."""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


def _run_web() -> None:
    """Run web/app.py main() by loading the module from repo root."""
    # Editable install: __file__ is .../src/lumos_core/__main__.py -> repo = parent of src
    repo_root = Path(__file__).resolve().parent.parent.parent
    app_py = repo_root / "web" / "app.py"
    if not app_py.exists():
        sys.exit("web/app.py not found")
    spec = importlib.util.spec_from_file_location("web_app", app_py)
    if spec is None or spec.loader is None:
        sys.exit("Could not load web/app.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["web_app"] = module
    spec.loader.exec_module(module)
    if hasattr(module, "main"):
        module.main()
    else:
        sys.exit("web/app.py has no main()")


def _run_cli() -> None:
    """Run the interactive CLI (lumos_core.interactive_cli.main)."""
    from lumos_core.security.consent import has_user_consent

    if not has_user_consent():
        from lumos_core.system.env_scan import build_capability_report, print_onboarding_preview

        env = build_capability_report()
        print_onboarding_preview(env)
        print()

    from lumos_core.interactive_cli import main as cli_main
    result = cli_main()
    sys.exit(0 if result is None else result)


def _run_env() -> None:
    """Run first-run environment scan (lumos_core.cli env)."""
    from lumos_core.cli import _run_env as _env
    _env()


def _run_ask(prompt: str, provider: str) -> None:
    """Run ask command: route prompt through AIRouter and print response (lumos_core.cli)."""
    from lumos_core.cli import run_ask
    run_ask(prompt, provider=provider)


def _run_chat(provider: str) -> None:
    """Run chat command: interactive terminal chat via AIRouter (lumos_core.cli)."""
    from lumos_core.cli import run_chat
    run_chat(provider=provider)


def main() -> int | None:
    from lumos_core import __version__
    parser = argparse.ArgumentParser(prog="lumos", description="Lumos core CLI and web")
    parser.add_argument("--version", action="store_true", help="show version and exit")
    sub = parser.add_subparsers(dest="cmd", help="subcommand")
    sub.add_parser("cli", help="run interactive CLI (default)")
    sub.add_parser("web", help="run Web v1 server")
    sub.add_parser("env", help="first-run environment scan (JSON + summary)")
    ask_p = sub.add_parser("ask", help="send a prompt to the AI router")
    ask_p.add_argument("prompt", help="your prompt (e.g. \"Explain quantum computing\")")
    ask_p.add_argument("--provider", default="openai", help="AI provider: openai, gemini, anthropic (default: openai)")
    chat_p = sub.add_parser("chat", help="interactive terminal chat with AI")
    chat_p.add_argument("--provider", default="openai", help="AI provider (default: openai)")
    tg_p = sub.add_parser("tg", help="telegram: auth, follow, sources, enable, disable, run")
    tg_p.add_argument("sub", nargs="?", choices=["auth", "follow", "sources", "enable", "disable", "run"])
    tg_p.add_argument("peer", nargs="?", default=None)
    tg_p.add_argument("--db", default=None)
    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit(0)
    if args.cmd == "tg":
        from lumos_social.telegram.cli import _tg_cmd

        return _tg_cmd(args)
    if args.cmd == "web":
        _run_web()
    elif args.cmd == "env":
        _run_env()
    elif args.cmd == "ask":
        _run_ask(args.prompt, args.provider)
    elif args.cmd == "chat":
        _run_chat(args.provider)
    else:
        # default or explicit cli
        _run_cli()


if __name__ == "__main__":
    code = main()
    sys.exit(code if code is not None else 0)
