"""Classify a PR's paths against ADR-028 standing class.

Three states, in strict precedence:

1. ``excluded``        — hard-exclusion hit (file, prefix, path token),
                         unlisted path, or empty diff. Standing merge is
                         forbidden. Fail-closed.
2. ``semantic_review`` — the path alone cannot decide. Olgu/norm ("ne
                         doğrudur?" vs "bundan sonra neye izin verilir?")
                         must be judged by a human against the current head
                         SHA. No automatic standing authority.
3. ``eligible``        — only narrow, explicitly machine-safe classes.

Precedence is aggregate: any excluded path makes the whole PR excluded; any
semantic path (with no excluded path) makes it semantic_review.

The generic ``docs/`` allowlist was removed on purpose: a new governance or
data-boundary document (e.g. ``docs/merge-rules.md``) must not become
eligible by escaping a hand-maintained name list. It falls to
semantic_review. Name-based tokens are defence in depth, not the mechanism.

PR body is not authority. Only the changed path list is.

Exit codes (CLI): 0 eligible, 2 excluded, 3 semantic_review.
Both 2 and 3 mean: no automatic standing merge.
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
CLASS_SEMANTIC = "semantic_review"

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
    semantic_prefixes = list(loaded.get("semantic_prefixes") or [])
    allow_files = list(loaded.get("allow_files") or [])
    allow_prefixes = list(loaded.get("allow_prefixes") or [])

    normalized = [normalize_path(item) for item in paths if normalize_path(item)]
    excluded_hits: list[dict[str, str]] = []
    semantic_hits: list[dict[str, str]] = []
    unknown: list[str] = []

    for item in normalized:
        # 1. Hard exclusion wins over everything.
        excluded = _matches(item, exclude_files, exclude_prefixes, exclude_tokens)
        if excluded:
            excluded_hits.append({"path": item, "reason": excluded})
            continue
        # 2. Narrow, explicitly safe classes.
        if _matches(item, allow_files, allow_prefixes, []) is not None:
            continue
        # 3. Path alone cannot decide → human semantic review.
        semantic = _matches(item, [], semantic_prefixes, [])
        if semantic:
            semantic_hits.append({"path": item, "reason": f"semantic:{semantic}"})
            continue
        # 4. Anything else is unlisted → fail-closed.
        unknown.append(item)
        excluded_hits.append({"path": item, "reason": f"unlisted:{item}"})

    if not normalized:
        standing_class = CLASS_EXCLUDED
        reasons = ["empty_diff"]
    elif excluded_hits:
        standing_class = CLASS_EXCLUDED
        reasons = [row["reason"] for row in excluded_hits]
    elif semantic_hits:
        standing_class = CLASS_SEMANTIC
        reasons = [row["reason"] for row in semantic_hits]
    else:
        standing_class = CLASS_ELIGIBLE
        reasons = []

    return {
        "schema": SCHEMA,
        "class": standing_class,
        "standing_merge": standing_class == CLASS_ELIGIBLE,
        "human_merge_required": standing_class != CLASS_ELIGIBLE,
        "semantic_review_required": standing_class == CLASS_SEMANTIC,
        "paths": normalized,
        "hits": excluded_hits + semantic_hits,
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
    if standing_class == CLASS_ELIGIBLE:
        return 0
    if standing_class == CLASS_SEMANTIC:
        return 3
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
