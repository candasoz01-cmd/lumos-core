"""Branch cleanup review — read-only git branch classification."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import subprocess
from typing import Literal

Classification = Literal["guvenli", "belirsiz"]


@dataclass
class BranchInfo:
    name: str
    classification: Classification
    merged: bool
    ahead: int
    is_ancestor: bool
    upstream: str | None
    reasons: list[str] = field(default_factory=list)
    suggested_delete: str | None = None


@dataclass
class ReviewResult:
    base_branch: str
    all_local: list[str]
    merged_into_base: list[str]
    branches: list[BranchInfo]


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _git_lines(args: list[str], cwd: Path) -> list[str]:
    proc = _run_git(args, cwd)
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def list_local_branches(cwd: Path) -> list[str]:
    return _git_lines(["branch", "--format=%(refname:short)"], cwd)


def list_merged_branches(cwd: Path, base_branch: str) -> set[str]:
    lines = _git_lines(["branch", "--merged", base_branch, "--format=%(refname:short)"], cwd)
    return set(lines)


def count_ahead(cwd: Path, base_branch: str, branch: str) -> int:
    proc = _run_git(["rev-list", "--count", f"{base_branch}..{branch}"], cwd)
    if proc.returncode != 0:
        return -1
    try:
        return int(proc.stdout.strip())
    except ValueError:
        return -1


def is_ancestor_of_base(cwd: Path, branch: str, base_branch: str) -> bool:
    proc = _run_git(["merge-base", "--is-ancestor", branch, base_branch], cwd)
    return proc.returncode == 0


def get_upstream(cwd: Path, branch: str) -> str | None:
    proc = _run_git(["rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"], cwd)
    if proc.returncode != 0:
        return None
    upstream = proc.stdout.strip()
    if not upstream:
        return None
    verify = _run_git(["rev-parse", "--verify", f"{upstream}@{{commit}}"], cwd)
    if verify.returncode != 0:
        return "[gone]"
    return upstream


def classify_branch(
    *,
    name: str,
    merged: bool,
    ahead: int,
    is_ancestor: bool,
    upstream: str | None,
) -> BranchInfo:
    reasons: list[str] = []
    classification: Classification = "guvenli"

    if not merged:
        reasons.append("main'e merge edilmemiş (--merged listesinde yok)")
    if ahead > 0:
        reasons.append(f"main'den {ahead} commit ahead")
    elif ahead < 0:
        reasons.append("ahead sayımı alınamadı")
    if is_ancestor and not merged:
        reasons.append("squash/ancestor: tip main'de ama --merged değil")
    if upstream is None:
        reasons.append("upstream takibi yok")
    elif upstream == "[gone]":
        reasons.append("upstream [gone]")

    if not merged or ahead != 0:
        classification = "belirsiz"

    suggested_delete = None
    if classification == "guvenli":
        suggested_delete = f"git branch -d {name}"

    return BranchInfo(
        name=name,
        classification=classification,
        merged=merged,
        ahead=max(ahead, 0),
        is_ancestor=is_ancestor,
        upstream=upstream,
        reasons=reasons,
        suggested_delete=suggested_delete,
    )


def run_review(cwd: Path, base_branch: str = "main") -> ReviewResult:
    all_local = list_local_branches(cwd)
    merged_set = list_merged_branches(cwd, base_branch)
    merged_sorted = sorted(merged_set)

    branches: list[BranchInfo] = []
    for name in sorted(all_local):
        if name == base_branch:
            continue
        merged = name in merged_set
        ahead = count_ahead(cwd, base_branch, name)
        ancestor = is_ancestor_of_base(cwd, name, base_branch)
        upstream = get_upstream(cwd, name)
        branches.append(
            classify_branch(
                name=name,
                merged=merged,
                ahead=ahead,
                is_ancestor=ancestor,
                upstream=upstream,
            )
        )

    return ReviewResult(
        base_branch=base_branch,
        all_local=all_local,
        merged_into_base=merged_sorted,
        branches=branches,
    )


def format_report(result: ReviewResult, *, dry_run: bool = True) -> str:
    lines: list[str] = []
    mode = "DRY-RUN (salt okunur)" if dry_run else "RAPOR"
    lines.append(f"=== Branch Cleanup Review [{mode}] ===")
    lines.append(f"Temel dal: {result.base_branch}")
    lines.append("")

    lines.append("--- git branch (yerel) ---")
    if result.all_local:
        for name in result.all_local:
            marker = "*" if name == result.base_branch else " "
            lines.append(f"  {marker} {name}")
    else:
        lines.append("  (yerel dal yok)")
    lines.append("")

    lines.append(f"--- git branch --merged {result.base_branch} ---")
    if result.merged_into_base:
        for name in result.merged_into_base:
            lines.append(f"  {name}")
    else:
        lines.append("  (merge edilmiş dal yok)")
    lines.append("")

    local_except_base = [b.name for b in result.branches]
    lines.append(f"--- {result.base_branch} dışı yerel dallar ({len(local_except_base)}) ---")
    if local_except_base:
        for name in local_except_base:
            lines.append(f"  {name}")
    else:
        lines.append("  (yok)")
    lines.append("")

    safe = [b for b in result.branches if b.classification == "guvenli"]
    uncertain = [b for b in result.branches if b.classification == "belirsiz"]

    lines.append(f"--- Silinmesi güvenli görünen ({len(safe)}) ---")
    if safe:
        for b in safe:
            lines.append(f"  • {b.name} (merged={b.merged}, ahead={b.ahead})")
            if b.suggested_delete:
                lines.append(f"    öneri (çalıştırılmadı): {b.suggested_delete}")
    else:
        lines.append("  (yok)")
    lines.append("")

    lines.append(f"--- Belirsiz / manuel inceleme ({len(uncertain)}) ---")
    if uncertain:
        for b in uncertain:
            reason_text = "; ".join(b.reasons) if b.reasons else "ek kontrol gerekli"
            lines.append(
                f"  • {b.name} (merged={b.merged}, ahead={b.ahead}, ancestor={b.is_ancestor})"
            )
            lines.append(f"    neden: {reason_text}")
    else:
        lines.append("  (yok)")
    lines.append("")

    lines.append("--- Notlar ---")
    lines.append("  Bu rapor salt okunurdur; hiçbir silme komutu çalıştırılmadı.")
    lines.append("  Önerilen silme komutları yalnızca 'öneri' olarak listelenir.")
    lines.append("  Uzak dal silme veya PR işlemi yapılmaz.")

    return "\n".join(lines)
