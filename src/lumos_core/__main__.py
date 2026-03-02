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
    """Run the interactive CLI (main.main)."""
    from main import main as cli_main  # noqa: E402
    result = cli_main()
    sys.exit(0 if result is None else result)


def main() -> None:
    from lumos_core import __version__
    parser = argparse.ArgumentParser(prog="lumos", description="Lumos core CLI and web")
    parser.add_argument("--version", action="store_true", help="show version and exit")
    sub = parser.add_subparsers(dest="cmd", help="subcommand")
    sub.add_parser("cli", help="run interactive CLI (default)")
    sub.add_parser("web", help="run Web v1 server")
    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit(0)
    if args.cmd == "web":
        _run_web()
    else:
        # default or explicit cli
        _run_cli()


if __name__ == "__main__":
    main()
