"""Classify a PR's paths against ADR-028 standing class.

Three states, in strict precedence:

1. ``excluded``        — hard-exclusion hit (file, prefix, path token),
                         unlisted path, or empty diff. Standing merge is
                         forbidden. Fail-closed.
2. ``semantic_review`` — **the path alone cannot decide.** This is not
                         "a human must approve"; it means the path signal is
                         insufficient and an olgu/norm judgement ("ne
                         doğrudur?" vs "bundan sonra neye izin verilir?") is
                         required before any standing decision.

                         That judgement is carried by a **SHA-bound
                         attestation** (see ``SemanticAttestation``):

                         * ``factual``  → promoted to ``eligible``
                         * ``normative``→ demoted to ``excluded`` (explicit
                           human approval required)
                         * missing, or bound to a different head SHA →
                           stays ``semantic_review`` (fail-closed)

                         An attestation can never promote a hard-exclusion
                         hit: ADR-029 stays ``excluded`` whatever it says.
3. ``eligible``        — only narrow, explicitly machine-safe classes.

Precedence is aggregate: any excluded path makes the whole PR excluded; any
semantic path (with no excluded path) makes it semantic_review.

The generic ``docs/`` allowlist was removed on purpose: a new governance or
data-boundary document (e.g. ``docs/merge-rules.md``) must not become
eligible by escaping a hand-maintained name list. It falls to
semantic_review. Name-based tokens are defence in depth, not the mechanism.

PR body is not authority. Only the changed path list plus a SHA-bound
attestation are.

Exit codes (CLI): 0 eligible, 2 excluded, 3 semantic_review.
``3`` means "not yet decided — attest first", not "forbidden".
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")

SCHEMA = "lumos.standing_merge.verdict.v1"
RULES_PATH = Path(__file__).with_name("excluded_paths.json")
CLASS_ELIGIBLE = "eligible"
CLASS_EXCLUDED = "excluded"
CLASS_SEMANTIC = "semantic_review"

VERDICT_FACTUAL = "factual"
VERDICT_NORMATIVE = "normative"


@dataclass(frozen=True)
class SemanticAttestation:
    """Olgu/norm judgement, bound to one head SHA.

    Stale attestations do not carry over: if ``head_sha`` does not match the
    head being classified, the attestation is ignored and the class stays
    ``semantic_review``. This mirrors ADR-027's SHA-bound approval rule.
    """

    verdict: str
    head_sha: str
    evaluated_by: str = ""
    note: str = ""

    def applies_to(self, head_sha: str | None) -> bool:
        if not head_sha or not self.head_sha:
            return False
        return self.head_sha.strip().lower() == head_sha.strip().lower()

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
    attestation: SemanticAttestation | None = None,
    head_sha: str | None = None,
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

    attestation_state = "absent"
    if not normalized:
        standing_class = CLASS_EXCLUDED
        reasons = ["empty_diff"]
    elif excluded_hits:
        standing_class = CLASS_EXCLUDED
        reasons = [row["reason"] for row in excluded_hits]
        # Hard exclusion is never promotable, whatever the attestation says.
        if attestation is not None:
            attestation_state = "ignored_hard_exclusion"
    elif semantic_hits:
        standing_class, reasons, attestation_state = _resolve_semantic(
            semantic_hits, attestation, head_sha
        )
    else:
        standing_class = CLASS_ELIGIBLE
        reasons = []

    return {
        "schema": SCHEMA,
        "class": standing_class,
        "standing_merge": standing_class == CLASS_ELIGIBLE,
        "human_merge_required": standing_class != CLASS_ELIGIBLE,
        "semantic_review_required": standing_class == CLASS_SEMANTIC,
        "attestation": attestation_state,
        "head_sha": (head_sha or "").strip(),
        "paths": normalized,
        "hits": excluded_hits + semantic_hits,
        "unknown": unknown,
        "reasons": reasons,
    }


def _resolve_semantic(
    semantic_hits: list[dict[str, str]],
    attestation: SemanticAttestation | None,
    head_sha: str | None,
) -> tuple[str, list[str], str]:
    """Promote, demote, or hold a semantic_review verdict.

    This is the step that keeps the ADR-028 §Sınıflandırma ölçütü promise
    executable: a purely factual ADR correction can still reach the standing
    lane, instead of being frozen out forever by its path.
    """
    base = [row["reason"] for row in semantic_hits]
    if attestation is None:
        return CLASS_SEMANTIC, base, "absent"
    if not attestation.applies_to(head_sha):
        # Stale or unbound attestation must not carry over to another head.
        return CLASS_SEMANTIC, [*base, "attestation_sha_mismatch"], "stale"
    if attestation.verdict == VERDICT_FACTUAL:
        return CLASS_ELIGIBLE, [f"promoted:factual:{attestation.head_sha[:7]}"], "factual"
    if attestation.verdict == VERDICT_NORMATIVE:
        return (
            CLASS_EXCLUDED,
            [*base, f"demoted:normative:{attestation.head_sha[:7]}"],
            "normative",
        )
    # Unknown verdict string is not a decision.
    return CLASS_SEMANTIC, [*base, "attestation_verdict_unknown"], "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m standing_merge.classify")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Changed paths. Empty = excluded (fail-closed).",
    )
    parser.add_argument(
        "--head-sha",
        default="",
        help="Head SHA being classified. Required for --attest to apply.",
    )
    parser.add_argument(
        "--attest",
        choices=(VERDICT_FACTUAL, VERDICT_NORMATIVE),
        default=None,
        help=(
            "Olgu/norm judgement for semantic_review paths. "
            "factual promotes to eligible; normative demotes to excluded. "
            "Ignored for hard-exclusion hits. Requires --attest-sha."
        ),
    )
    parser.add_argument(
        "--attest-sha",
        default="",
        help="Head SHA the attestation is bound to. Must equal --head-sha.",
    )
    parser.add_argument(
        "--attest-by",
        default="",
        help="Who or what produced the judgement (recorded, not trusted).",
    )
    args = parser.parse_args(argv)
    attestation = None
    if args.attest is not None:
        attestation = SemanticAttestation(
            verdict=args.attest,
            head_sha=args.attest_sha,
            evaluated_by=args.attest_by,
        )
    verdict = classify_paths(
        args.paths, attestation=attestation, head_sha=args.head_sha
    )
    sys.stdout.write(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n")
    standing_class = str(verdict["class"])
    sys.stderr.write(
        f"standing_class={standing_class} standing_merge={verdict['standing_merge']} "
        f"attestation={verdict['attestation']}\n"
    )
    if standing_class == CLASS_ELIGIBLE:
        return 0
    if standing_class == CLASS_SEMANTIC:
        return 3
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
