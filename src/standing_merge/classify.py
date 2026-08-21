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

Path inputs are hostile by default: a repository file may be named ``--help``
or ``--attest=factual`` and may contain newlines. Callers must pass paths
after an ``--`` option terminator and transport them NUL-delimited; this
module additionally rejects any path starting with ``-`` (fail-closed).

The classifier that decides a PR must not come from that PR. See the
``standing-class`` workflow: it extracts this module from the pull request's
fixed ``base.sha`` and refuses to run (fail-closed) when the base commit has
no classifier. It never falls back to the PR tree.

Exit codes (CLI): 0 eligible, 2 excluded, 3 semantic_review.
``3`` means "not yet decided — attest first", not "forbidden".
"""

from __future__ import annotations

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

_VALUE_FLAGS = {
    "--head-sha": "head_sha",
    "--attest": "attest",
    "--attest-sha": "attest_sha",
    "--attest-by": "attest_by",
    "--paths-nul": "paths_nul",
}


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
        # 0. A repo path must never look like a CLI option. Git allows file
        #    names starting with "-" (and newlines); argparse would otherwise
        #    read them as flags. Fail-closed before any other rule.
        if item.startswith("-"):
            excluded_hits.append({"path": item, "reason": f"dash_prefixed:{item}"})
            continue
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


def read_nul_paths(data: bytes) -> list[str]:
    """Split a ``git diff -z --name-only`` payload. Newlines stay inside names."""
    if not data:
        return []
    paths: list[str] = []
    for part in data.split(b"\0"):
        if not part:
            continue
        paths.append(part.decode("utf-8", errors="surrogateescape"))
    return paths


def read_nul_paths_from(source: str) -> list[str]:
    raw = sys.stdin.buffer.read() if source == "-" else Path(source).read_bytes()
    return read_nul_paths(raw)


def parse_classify_argv(argv: list[str]) -> dict[str, Any]:
    """Parse flags without argparse so dashed filenames cannot exit 0.

    ``-h`` / ``--help`` are usage only when they are the entire argv.
    After ``--``, every token is a path. Known value flags are accepted
    only before ``--``.
    """
    parsed: dict[str, Any] = {
        "paths": [],
        "head_sha": "",
        "attest": None,
        "attest_sha": "",
        "attest_by": "",
        "paths_nul": None,
        "help": False,
    }
    if argv == ["--help"] or argv == ["-h"]:
        parsed["help"] = True
        return parsed

    if "--" in argv:
        idx = argv.index("--")
        option_tokens = argv[:idx]
        path_tokens = list(argv[idx + 1 :])
    else:
        option_tokens = argv
        path_tokens = []

    i = 0
    leftover: list[str] = []
    while i < len(option_tokens):
        tok = option_tokens[i]
        if _flag_name(tok) in _VALUE_FLAGS:
            key = _VALUE_FLAGS[_flag_name(tok)]
            value, i = _flag_value(option_tokens, i)
            parsed[key] = value
            continue
        leftover.append(tok)
        i += 1
    parsed["paths"] = leftover + path_tokens
    return parsed


def _flag_name(token: str) -> str:
    if token.startswith("--") and "=" in token:
        return token.split("=", 1)[0]
    return token


def _flag_value(tokens: list[str], index: int) -> tuple[str, int]:
    token = tokens[index]
    if token.startswith("--") and "=" in token:
        return token.split("=", 1)[1], index + 1
    if index + 1 >= len(tokens):
        return "", index + 1
    return tokens[index + 1], index + 2


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parsed = parse_classify_argv(argv)
    if parsed["help"]:
        sys.stderr.write(
            "usage: python -m standing_merge.classify [--paths-nul FILE] -- [PATH ...]\n"
            "Dashed path names are excluded. Help is not an eligible verdict.\n"
        )
        return 2
    paths = list(parsed["paths"])
    if parsed["paths_nul"]:
        paths.extend(read_nul_paths_from(str(parsed["paths_nul"])))
    attestation = None
    if parsed["attest"] is not None:
        attestation = SemanticAttestation(
            verdict=str(parsed["attest"]),
            head_sha=str(parsed["attest_sha"] or ""),
            evaluated_by=str(parsed["attest_by"] or ""),
        )
    verdict = classify_paths(
        paths, attestation=attestation, head_sha=str(parsed["head_sha"] or "")
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
