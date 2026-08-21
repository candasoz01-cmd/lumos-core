"""Classify a PR's paths against ADR-028 standing class.

Hard-exclusion first (files, prefixes, path tokens). Remaining paths
must all match the allow list. Unlisted paths are excluded (fail-closed).
PR body is not authority. Olgu/norm is not classified here.

Exit codes (CLI): 0 eligible, 2 excluded.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")

SCHEMA = "lumos.standing_merge.verdict.v1"
RULES_PATH = Path(__file__).with_name("excluded_paths.json")
CLASS_ELIGIBLE = "eligible"
CLASS_EXCLUDED = "excluded"

# candasoz01-cmd/lumos-core#777 · MERGED · c50127b6 — fixture, not a second history.
PR777_PATHS = (
    "docs/contracts/dashboard-health-v1.md",
    "docs/decisions/ADR-029-dashboard-health-earned-responsibility.md",
)


def load_rules(path: Path = RULES_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_path(raw: str) -> str:
    text = raw.strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text.lstrip("/")


def path_tokens(normalized: str) -> set[str]:
    return {part for part in _TOKEN_SPLIT.split(normalized.lower()) if part}


def _matches(
    normalized: str,
    files: list[str],
    prefixes: list[str],
    tokens: list[str],
) -> str | None:
    for exact in files:
        if normalized == exact:
            return f"file:{exact}"
    for prefix in prefixes:
        if normalized.startswith(prefix):
            return f"prefix:{prefix}"
    parts = path_tokens(normalized)
    for token in tokens:
        lowered = token.lower()
        if lowered in parts:
            return f"token:{lowered}"
    return None


def classify_paths(
    paths: list[str] | tuple[str, ...],
    *,
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    loaded = rules if rules is not None else load_rules()
    exclude_files = list(loaded.get("exclude_files") or loaded.get("files") or [])
    exclude_prefixes = list(loaded.get("exclude_prefixes") or loaded.get("prefixes") or [])
    exclude_tokens = list(loaded.get("exclude_tokens") or [])
    allow_files = list(loaded.get("allow_files") or [])
    allow_prefixes = list(loaded.get("allow_prefixes") or [])
    normalized = [normalize_path(item) for item in paths if normalize_path(item)]
    hits: list[dict[str, str]] = []
    unknown: list[str] = []
    for item in normalized:
        excluded = _matches(item, exclude_files, exclude_prefixes, exclude_tokens)
        if excluded:
            hits.append({"path": item, "reason": excluded})
            continue
        allowed = _matches(item, allow_files, allow_prefixes, [])
        if allowed is None:
            unknown.append(item)
            hits.append({"path": item, "reason": f"unlisted:{item}"})
    if not normalized:
        standing_class = CLASS_EXCLUDED
        reasons = ["empty_diff"]
    elif hits:
        standing_class = CLASS_EXCLUDED
        reasons = [row["reason"] for row in hits]
    else:
        standing_class = CLASS_ELIGIBLE
        reasons = []
    return {
        "schema": SCHEMA,
        "class": standing_class,
        "standing_merge": standing_class == CLASS_ELIGIBLE,
        "human_merge_required": standing_class != CLASS_ELIGIBLE,
        "paths": normalized,
        "hits": hits,
        "unknown": unknown,
        "reasons": reasons,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m standing_merge.classify")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Changed paths. Empty = excluded (fail-closed).",
    )
    args = parser.parse_args(argv)
    verdict = classify_paths(args.paths)
    sys.stdout.write(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n")
    standing_class = str(verdict["class"])
    sys.stderr.write(
        f"standing_class={standing_class} standing_merge={verdict['standing_merge']}\n"
    )
    return 0 if standing_class == CLASS_ELIGIBLE else 2


if __name__ == "__main__":
    raise SystemExit(main())
