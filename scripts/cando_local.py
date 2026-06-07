#!/usr/bin/env python3
"""Cando local recipe runner — dry-run MVP."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

_SRC = Path(__file__).resolve().parents[1] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from cando.branch_cleanup_review import format_report as format_branch_report  # noqa: E402
from cando.branch_cleanup_review import run_review  # noqa: E402
from cando.pr_ready_check import format_report as format_pr_report  # noqa: E402
from cando.pr_ready_check import run_check  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
RECIPES_DIR = REPO_ROOT / "config" / "recipes"


def _load_recipe(name: str) -> dict[str, str]:
    path = RECIPES_DIR / f"{name}.yaml"
    if not path.is_file():
        raise SystemExit(f"Recipe bulunamadı: {path}")
    data: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def _cmd_recipe(args: argparse.Namespace) -> int:
    recipe = _load_recipe(args.recipe_name)
    if args.recipe_name == "branch-cleanup-review":
        if not args.dry_run:
            print("branch-cleanup-review yalnızca --dry-run modunda desteklenir.", file=sys.stderr)
            return 2
        base_branch = str(recipe.get("base_branch") or "main")
        result = run_review(REPO_ROOT, base_branch=base_branch)
        print(format_branch_report(result, dry_run=True))
        return 0

    if args.recipe_name == "pr-ready-check":
        if not args.dry_run:
            print("pr-ready-check yalnızca --dry-run modunda desteklenir.", file=sys.stderr)
            return 2
        if args.pr is None:
            print("pr-ready-check için --pr <N> zorunludur.", file=sys.stderr)
            return 2
        result = run_check(REPO_ROOT, pr_number=args.pr)
        print(format_pr_report(result, dry_run=True))
        return 0

    print(f"Recipe henüz uygulanmadı: {args.recipe_name}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cando local recipe runner")
    sub = parser.add_subparsers(dest="command", required=True)

    recipe_parser = sub.add_parser("recipe", help="Salt okunur recipe çalıştır")
    recipe_parser.add_argument("recipe_name", help="Recipe adı (ör. branch-cleanup-review)")
    recipe_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Salt okunur rapor; yazma/silme yok",
    )
    recipe_parser.add_argument(
        "--pr",
        type=int,
        default=None,
        help="PR numarası (pr-ready-check için zorunlu)",
    )
    recipe_parser.set_defaults(func=_cmd_recipe)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
