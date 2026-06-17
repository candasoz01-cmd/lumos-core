"""Entry point: lumos (or python -m lumos_core). Subcommands: cli (default), decision."""
from __future__ import annotations

import argparse
import sys


def _run_cli(sandbox_mode: bool | None = None) -> None:
    """Run the interactive CLI (main.main). sandbox_mode: True/False override; None = use env."""
    from main import main as cli_main  # noqa: E402
    result = cli_main(sandbox_mode=sandbox_mode)
    sys.exit(0 if result is None else result)


def main() -> None:
    from lumos_core import __version__
    parser = argparse.ArgumentParser(prog="lumos", description="Lumos core CLI")
    parser.add_argument("--version", action="store_true", help="show version and exit")
    parser.add_argument(
        "--sandbox",
        action="store_true",
        help="run in sandbox mode (no writes to live core paths)",
    )
    sub = parser.add_subparsers(dest="cmd", help="subcommand")
    sub.add_parser("cli", help="run interactive CLI (default)")
    decision_p = sub.add_parser("decision", help="run decision pipeline, show proposal diff (no apply)")
    decision_p.add_argument("--goal", required=True, help="goal description")
    decision_p.add_argument("--paths", required=True, nargs="+", help="target paths")
    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit(0)
    if args.cmd == "decision":
        from pathlib import Path
        from core.decision_pipeline import run_decision_pipeline
        from core.decision_runner import format_result_preview
        paths = [Path(p) for p in args.paths]
        result = run_decision_pipeline(args.goal, paths)
        if result is None:
            print("No result (no options generated).")
            sys.exit(1)
        print(format_result_preview(result))
        sys.exit(0 if result.success else 1)
    else:
        # default or explicit cli; --sandbox overrides env
        sandbox_override = True if args.sandbox else None
        _run_cli(sandbox_mode=sandbox_override)


if __name__ == "__main__":
    main()
