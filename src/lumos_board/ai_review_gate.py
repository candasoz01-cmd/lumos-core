"""AI review evidence gate (ADR-036, draft).

Runs from the PR **base** SHA via ``pull_request_target``. Counts SHA-bound
review evidence produced by GitHub App identities only (``cursor`` check run,
``chatgpt-codex-connector`` review-state comment). GitHub authenticates the
App; the verifier pins the exact 40-hex head SHA. At least two distinct
providers must pass; critical paths are stricter.

AI evidence is never human approval and never founder merge authority
(``human_approval`` is always ``False``). Founder authority is the ADR-035
merge-authority signature bound to repo + PR + head SHA + action.

Fail-closed: missing data, unknown values or API errors deny.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

VERDICT_SCHEMA = "lumos.ai_review_gate.verdict.v1"
POLICY_SCHEMA = "lumos.ai_review_policy.v1"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
AI_NOT_HUMAN = "AI review evidence — not human approval"

Fetch = Callable[[str], Any]


class GateError(RuntimeError):
    """Fail-closed configuration or input error."""


# ---------------------------------------------------------------- policy


def load_policy(path: Path) -> dict[str, Any]:
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GateError(f"policy unreadable: {path}: {exc}") from exc
    if policy.get("schema") != POLICY_SCHEMA:
        raise GateError(f"policy schema mismatch: {policy.get('schema')!r}")
    if int(policy.get("min_distinct_providers", 0)) < 2:
        raise GateError("policy must require at least 2 distinct providers")
    return policy


def is_critical(paths: list[str], policy: dict[str, Any]) -> list[str]:
    crit = policy.get("critical_paths", {})
    prefixes = tuple(crit.get("prefixes", []))
    files = set(crit.get("files", []))
    hits = []
    for path in paths:
        # Leading dash or traversal is treated as critical (fail-closed).
        hostile = path.startswith("-") or ".." in path.split("/")
        if hostile or path in files or (prefixes and path.startswith(prefixes)):
            hits.append(path)
    return hits


# -------------------------------------------------------- provider checks


def _app_slug(obj: dict[str, Any]) -> str:
    app = obj.get("app") or obj.get("performed_via_github_app") or {}
    return str(app.get("slug") or "")


def _is_bot(user: dict[str, Any] | None, login: str) -> bool:
    user = user or {}
    return user.get("type") == "Bot" and user.get("login") == login


def eval_cursor(
    cfg: dict[str, Any],
    head_sha: str,
    check_runs: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    critical: bool,
    critical_cfg: dict[str, Any],
) -> dict[str, Any]:
    runs = [
        c
        for c in check_runs
        if c.get("name") == cfg["check_name"]
        and _app_slug(c) == cfg["app_slug"]
        and c.get("head_sha") == head_sha
    ]
    if not runs:
        return {"pass": False, "reason": "cursor check run missing on head SHA"}
    latest = max(runs, key=lambda c: (c.get("completed_at") or "", c.get("id") or 0))
    if latest.get("status") != "completed":
        return {"pass": False, "reason": f"cursor check {latest.get('status')}"}
    if latest.get("conclusion") not in cfg.get("pass_conclusions", []):
        return {"pass": False, "reason": f"cursor conclusion {latest.get('conclusion')}"}
    evidence = {"check_run_id": latest.get("id"), "conclusion": latest.get("conclusion")}
    if critical and critical_cfg.get("require_cursor_review_on_head"):
        on_head = [
            r
            for r in reviews
            if _is_bot(r.get("user"), cfg["review_login"]) and r.get("commit_id") == head_sha
        ]
        if not on_head:
            return {"pass": False, "reason": "critical: cursor review missing on head SHA"}
        evidence["review_id"] = on_head[-1].get("id")
    return {"pass": True, "evidence": evidence}


_CODEX_STATE = re.compile(r"codex-review-state:v1\s+(\{.*?\})\s*-->", re.DOTALL)


def eval_codex(
    cfg: dict[str, Any],
    head_sha: str,
    issue_comments: list[dict[str, Any]],
    critical: bool,
    critical_cfg: dict[str, Any],
) -> dict[str, Any]:
    pass_status = cfg.get("pass_status") or []
    if not pass_status:
        return {
            "pass": False,
            "permanent": True,
            "reason": "codex pass status not yet verified in policy",
        }
    states = []
    for c in issue_comments:
        if not _is_bot(c.get("user"), cfg["login"]) or _app_slug(c) != cfg["app_slug"]:
            continue
        m = _CODEX_STATE.search(c.get("body") or "")
        if not m:
            continue
        try:
            state = json.loads(m.group(1))
        except ValueError:
            continue
        states.append((c.get("updated_at") or "", c.get("id") or 0, state))
    if not states:
        return {"pass": False, "reason": "codex review state comment missing"}
    _, cid, state = max(states, key=lambda s: (s[0], s[1]))
    review = state.get("code_review") or {}
    if review.get("commit_sha") != head_sha:
        return {"pass": False, "reason": "codex review not on head SHA"}
    if review.get("status") not in pass_status:
        return {"pass": False, "reason": f"codex status {review.get('status')}"}
    if review.get("has_unresolved_findings") is not False:
        return {"pass": False, "reason": "codex unresolved findings"}
    strict = critical and critical_cfg.get("codex_require_no_findings")
    if strict and review.get("has_any_findings") is not False:
        return {"pass": False, "reason": "critical: codex reported findings"}
    return {"pass": True, "evidence": {"comment_id": cid, "status": review.get("status")}}


def evaluate_ai_gate(
    *,
    pr: int,
    head_sha: str,
    paths: list[str],
    check_runs: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    review_comments: list[dict[str, Any]],
    issue_comments: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    if not SHA_RE.match(head_sha or ""):
        raise GateError("head SHA must be a full 40-hex SHA")
    hits = is_critical(paths, policy) if paths else ["<no-paths>"]
    critical = bool(hits)
    ccfg = policy.get("critical", {})
    providers = policy["providers"]
    results: dict[str, Any] = {}
    for name, cfg in providers.items():
        if cfg["kind"] == "check_run":
            results[name] = eval_cursor(cfg, head_sha, check_runs, reviews, critical, ccfg)
        elif cfg["kind"] == "codex_state_comment":
            results[name] = eval_codex(cfg, head_sha, issue_comments, critical, ccfg)
        else:
            results[name] = {"pass": False, "reason": f"unknown provider kind {cfg['kind']}"}
    passed = sorted(n for n, r in results.items() if r["pass"])
    reasons = []
    if len(passed) < int(policy["min_distinct_providers"]):
        reasons.append(f"distinct providers passed {len(passed)} < {policy['min_distinct_providers']}")
    if critical and ccfg.get("require_all_providers") and len(passed) != len(providers):
        reasons.append("critical: all providers must pass")
    if critical and ccfg.get("forbid_ai_inline_findings_on_head"):
        bot_logins = {c.get("review_login") or c.get("login") for c in providers.values()}
        inline = [
            c.get("id")
            for c in review_comments
            if (c.get("user") or {}).get("type") == "Bot"
            and (c.get("user") or {}).get("login") in bot_logins
            and c.get("commit_id") == head_sha
        ]
        if inline:
            reasons.append(f"critical: {len(inline)} AI inline finding(s) on head SHA")
    # Waiting cannot help if a provider can never pass under this policy.
    blocked = [n for n, r in results.items() if r.get("permanent")]
    reachable = len(providers) - len(blocked)
    final = bool(blocked) and (
        reachable < int(policy["min_distinct_providers"])
        or (critical and bool(ccfg.get("require_all_providers")))
    )
    return {
        "schema": VERDICT_SCHEMA,
        "retryable": not final and bool(reasons),
        "pr": pr,
        "head_sha": head_sha,
        "pass": not reasons,
        "critical": critical,
        "critical_paths": hits,
        "providers": results,
        "providers_passed": passed,
        "reasons": reasons,
        "human_approval": False,
        "note": AI_NOT_HUMAN,
    }


# ------------------------------------------------------------- GitHub I/O


@dataclass
class GitHub:
    repo: str
    token: str = ""
    api: str = "https://api.github.com"
    calls: list[str] = field(default_factory=list)

    def get(self, path: str) -> Any:
        url = path if path.startswith("http") else f"{self.api}/repos/{self.repo}{path}"
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        self.calls.append(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            link = resp.headers.get("Link") or ""
        return body, link

    def all(self, path: str, key: str | None = None) -> list[Any]:
        items: list[Any] = []
        sep = "&" if "?" in path else "?"
        url: str | None = f"{path}{sep}per_page=100"
        for _ in range(30):
            if not url:
                break
            body, link = self.get(url)
            items += body[key] if key else body
            m = re.search(r'<([^>]+)>;\s*rel="next"', link)
            url = m.group(1) if m else None
        return items


def changed_paths(files: list[dict[str, Any]]) -> list[str]:
    """Both sides of a rename count: moving a critical file out of a critical
    path must still be judged by the critical rules."""
    paths: list[str] = []
    for f in files:
        for key in ("filename", "previous_filename"):
            if f.get(key) and f[key] not in paths:
                paths.append(f[key])
    return paths


def _ai_inputs(gh: GitHub, pr: int, head: str) -> dict[str, Any]:
    return {
        "paths": changed_paths(gh.all(f"/pulls/{pr}/files")),
        "check_runs": gh.all(f"/commits/{head}/check-runs", key="check_runs"),
        "reviews": gh.all(f"/pulls/{pr}/reviews"),
        "review_comments": gh.all(f"/pulls/{pr}/comments"),
        "issue_comments": gh.all(f"/issues/{pr}/comments"),
    }


def _summary(verdict: dict[str, Any], title: str) -> None:
    out = os.environ.get("GITHUB_STEP_SUMMARY")
    text = f"## {title}\n\n```json\n{json.dumps(verdict, indent=2, ensure_ascii=False)}\n```\n"
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(text)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m lumos_board.ai_review_gate")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ai-gate")
    p.add_argument("--repo", required=True)
    p.add_argument("--pr", type=int, required=True)
    p.add_argument("--head", required=True)
    p.add_argument("--policy", required=True, type=Path)
    p.add_argument("--wait-seconds", type=int, default=0)
    p.add_argument("--interval", type=int, default=60)
    args = ap.parse_args(argv)
    title = f"ai-review-gate — {AI_NOT_HUMAN}"
    try:
        policy = load_policy(args.policy)
        gh = GitHub(repo=args.repo, token=os.environ.get("GITHUB_TOKEN", ""))
        deadline = time.monotonic() + max(args.wait_seconds, 0)
        while True:
            verdict = evaluate_ai_gate(
                pr=args.pr, head_sha=args.head, policy=policy, **_ai_inputs(gh, args.pr, args.head)
            )
            if verdict["pass"] or time.monotonic() >= deadline:
                break
            time.sleep(max(args.interval, 5))
    except (GateError, urllib.error.URLError, KeyError, ValueError) as exc:
        verdict = {"pass": False, "human_approval": False,
                   "reasons": [f"fail-closed: {type(exc).__name__}: {exc}"]}
        title = "ai-review-gate error (fail-closed)"
    print(json.dumps(verdict, ensure_ascii=False, sort_keys=True))
    _summary(verdict, title)
    return 0 if verdict.get("pass") else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
