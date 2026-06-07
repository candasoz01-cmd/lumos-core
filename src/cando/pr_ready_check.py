"""PR ready check — read-only gh pr view + checks report."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import subprocess
from typing import Literal

Readiness = Literal["hazir", "beklemede", "basarisiz", "birlestirilmis", "kapali", "bilinmiyor"]


@dataclass
class CheckInfo:
    name: str
    status: str
    summary: str | None = None
    url: str | None = None


@dataclass
class PrReadyResult:
    pr_number: int
    title: str
    url: str
    state: str
    closed: bool
    merged_at: str | None
    mergeable: str | None
    readiness: Readiness
    passed: list[CheckInfo] = field(default_factory=list)
    pending: list[CheckInfo] = field(default_factory=list)
    failed: list[CheckInfo] = field(default_factory=list)
    suggested_next: str = ""
    error: str | None = None


def _run_gh(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _parse_rollup_item(item: dict) -> CheckInfo:
    typename = item.get("__typename", "")
    if typename == "CheckRun":
        name = str(item.get("name") or item.get("workflowName") or "check")
        status = str(item.get("status") or "")
        conclusion = str(item.get("conclusion") or "")
        if status in ("IN_PROGRESS", "QUEUED", "PENDING", "WAITING"):
            display = "pending"
        elif conclusion in ("SUCCESS", "NEUTRAL", "SKIPPED"):
            display = "pass"
        elif conclusion:
            display = "fail"
        else:
            display = status.lower() or "unknown"
        return CheckInfo(
            name=name,
            status=display,
            url=item.get("detailsUrl"),
        )
    if typename == "StatusContext":
        name = str(item.get("context") or "status")
        state = str(item.get("state") or "").upper()
        if state in ("PENDING", "EXPECTED"):
            display = "pending"
        elif state == "SUCCESS":
            display = "pass"
        elif state in ("FAILURE", "ERROR"):
            display = "fail"
        else:
            display = state.lower() or "unknown"
        return CheckInfo(
            name=name,
            status=display,
            url=item.get("targetUrl"),
        )
    return CheckInfo(name="unknown", status="unknown")


def _classify_rollup(rollup: list[dict]) -> tuple[list[CheckInfo], list[CheckInfo], list[CheckInfo]]:
    passed: list[CheckInfo] = []
    pending: list[CheckInfo] = []
    failed: list[CheckInfo] = []
    for item in rollup:
        info = _parse_rollup_item(item)
        if info.status == "pass":
            passed.append(info)
        elif info.status == "pending":
            pending.append(info)
        elif info.status == "fail":
            failed.append(info)
        else:
            pending.append(info)
    return passed, pending, failed


def _parse_checks_output(stdout: str) -> tuple[list[CheckInfo], list[CheckInfo], list[CheckInfo]]:
    passed: list[CheckInfo] = []
    pending: list[CheckInfo] = []
    failed: list[CheckInfo] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        name = parts[0]
        raw_status = parts[1].lower()
        url = parts[3] if len(parts) > 3 else None
        summary = parts[4] if len(parts) > 4 else None
        info = CheckInfo(name=name, status=raw_status, url=url, summary=summary)
        if raw_status in ("pass", "success", "skipping"):
            passed.append(info)
        elif raw_status in ("pending", "in_progress", "queued", "waiting"):
            pending.append(info)
        elif raw_status in ("fail", "failure", "error", "cancel"):
            failed.append(info)
        else:
            pending.append(info)
    return passed, pending, failed


def _determine_readiness(
    *,
    state: str,
    closed: bool,
    passed: list[CheckInfo],
    pending: list[CheckInfo],
    failed: list[CheckInfo],
) -> Readiness:
    upper = state.upper()
    if upper == "MERGED":
        return "birlestirilmis"
    if closed:
        return "kapali"
    if failed:
        return "basarisiz"
    if pending:
        return "beklemede"
    if passed:
        return "hazir"
    return "bilinmiyor"


def _suggest_next(readiness: Readiness, pr_number: int) -> str:
    if readiness == "hazir":
        return f"gh pr merge {pr_number} --merge"
    if readiness == "beklemede":
        return f"python scripts/cando_local.py recipe pr-ready-check --pr {pr_number} --dry-run"
    if readiness == "basarisiz":
        return "Başarısız check loglarını incele; düzeltme sonrası tekrar kontrol et."
    if readiness == "birlestirilmis":
        return "PR zaten merge edilmiş; ek işlem gerekmez."
    if readiness == "kapali":
        return "PR kapalı; merge işlemi uygulanamaz."
    return "PR durumunu manuel kontrol et."


def fetch_pr_view(cwd: Path, pr_number: int) -> dict:
    proc = _run_gh(
        [
            "pr",
            "view",
            str(pr_number),
            "--json",
            "state,mergeable,title,url,mergedAt,closed,statusCheckRollup",
        ],
        cwd,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "gh pr view başarısız")
    return json.loads(proc.stdout)


def fetch_pr_checks(cwd: Path, pr_number: int) -> str:
    proc = _run_gh(["pr", "checks", str(pr_number)], cwd)
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr.strip() or "gh pr checks başarısız")
    return proc.stdout


def run_check(cwd: Path, pr_number: int) -> PrReadyResult:
    try:
        data = fetch_pr_view(cwd, pr_number)
    except (RuntimeError, json.JSONDecodeError) as exc:
        return PrReadyResult(
            pr_number=pr_number,
            title="",
            url="",
            state="",
            closed=False,
            merged_at=None,
            mergeable=None,
            readiness="bilinmiyor",
            error=str(exc),
            suggested_next="PR numarasını ve gh oturumunu kontrol et.",
        )

    rollup = data.get("statusCheckRollup") or []
    passed, pending, failed = _classify_rollup(rollup)

    if not passed and not pending and not failed:
        try:
            checks_out = fetch_pr_checks(cwd, pr_number)
            passed, pending, failed = _parse_checks_output(checks_out)
        except RuntimeError:
            pass

    state = str(data.get("state") or "")
    closed = bool(data.get("closed"))
    readiness = _determine_readiness(
        state=state,
        closed=closed,
        passed=passed,
        pending=pending,
        failed=failed,
    )

    return PrReadyResult(
        pr_number=pr_number,
        title=str(data.get("title") or ""),
        url=str(data.get("url") or ""),
        state=state,
        closed=closed,
        merged_at=data.get("mergedAt"),
        mergeable=data.get("mergeable"),
        readiness=readiness,
        passed=passed,
        pending=pending,
        failed=failed,
        suggested_next=_suggest_next(readiness, pr_number),
    )


def format_report(result: PrReadyResult, *, dry_run: bool = True) -> str:
    lines: list[str] = []
    mode = "DRY-RUN (salt okunur)" if dry_run else "RAPOR"
    lines.append(f"=== PR Ready Check [{mode}] ===")
    lines.append(f"PR: #{result.pr_number}")
    lines.append("")

    if result.error:
        lines.append("--- Hata ---")
        lines.append(f"  {result.error}")
        lines.append("")
        lines.append(f"Önerilen adım: {result.suggested_next}")
        lines.append("")
        lines.append("--- Notlar ---")
        lines.append("  Bu rapor salt okunurdur; merge veya dal işlemi yapılmaz.")
        return "\n".join(lines)

    lines.append("--- PR bilgisi ---")
    lines.append(f"  Başlık: {result.title}")
    lines.append(f"  URL: {result.url}")
    lines.append(f"  Durum: {result.state}")
    if result.merged_at:
        lines.append(f"  Merge zamanı: {result.merged_at}")
    if result.mergeable:
        lines.append(f"  Mergeable: {result.mergeable}")
    lines.append("")

    if result.readiness == "birlestirilmis":
        lines.append("--- Sonuç ---")
        lines.append("  PR zaten merge edilmiş.")
    elif result.readiness == "kapali":
        lines.append("--- Sonuç ---")
        lines.append("  PR kapalı (merge edilmemiş).")
    elif result.readiness == "hazir":
        lines.append("--- Sonuç ---")
        lines.append("  merge için hazır")
    elif result.readiness == "beklemede":
        lines.append("--- Sonuç ---")
        lines.append("  Bekleyen check'ler var")
        for c in result.pending:
            lines.append(f"    • {c.name} ({c.status})")
    elif result.readiness == "basarisiz":
        lines.append("--- Sonuç ---")
        lines.append("  Başarısız check'ler var")
        for c in result.failed:
            summary = f" — {c.summary}" if c.summary else ""
            lines.append(f"    • {c.name}{summary}")
    else:
        lines.append("--- Sonuç ---")
        lines.append("  Check durumu belirlenemedi.")

    if result.passed:
        lines.append("")
        lines.append(f"--- Geçen check'ler ({len(result.passed)}) ---")
        for c in result.passed:
            lines.append(f"  • {c.name}")

    lines.append("")
    lines.append("--- Önerilen sonraki adım ---")
    lines.append(f"  {result.suggested_next}")
    lines.append("")
    lines.append("--- Notlar ---")
    lines.append("  Bu rapor salt okunurdur; merge veya dal işlemi yapılmaz.")

    return "\n".join(lines)
