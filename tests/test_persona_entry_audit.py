"""Read-only persona entry audit: structure and regression baseline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.persona_entry_audit import (
    CATEGORIES,
    find_repo_root,
    format_summary,
    report_to_json,
    run_audit,
)

# Known 2026-06-07 baseline from persona/security docs (minimum, not exact snapshot).
MIN_TOTAL_FINDINGS = 12
MIN_BY_CATEGORY = {
    "bridge_gateway": 4,
    "cli_task_engine": 2,
    "cando_recipe": 2,
    "offline_push": 1,
    "secret_signature": 1,
}


@pytest.fixture(scope="module")
def repo_root() -> Path:
    return find_repo_root()


@pytest.fixture(scope="module")
def audit_report(repo_root: Path):
    return run_audit(repo_root)


def test_find_repo_root_points_at_lumos_core(repo_root: Path) -> None:
    assert (repo_root / "pyproject.toml").is_file()
    assert "lumos-core" in (repo_root / "pyproject.toml").read_text(encoding="utf-8")


def test_audit_report_structure(audit_report) -> None:
    assert audit_report.repo_root
    assert isinstance(audit_report.findings, list)
    assert set(audit_report.category_counts.keys()) == set(CATEGORIES)
    assert audit_report.total == len(audit_report.findings)
    assert audit_report.total == sum(audit_report.category_counts.values())


def test_audit_finding_fields(audit_report) -> None:
    for finding in audit_report.findings:
        assert finding.category in CATEGORIES
        assert finding.heuristic
        assert finding.path
        assert finding.detail
        assert finding.line is None or finding.line >= 1


def test_audit_regression_baseline(audit_report) -> None:
    assert audit_report.total >= MIN_TOTAL_FINDINGS
    for category, minimum in MIN_BY_CATEGORY.items():
        assert audit_report.category_counts[category] >= minimum, (
            f"{category} count {audit_report.category_counts[category]} < baseline {minimum}"
        )


def test_format_summary_includes_counts(audit_report, capsys) -> None:
    print(format_summary(audit_report))
    out = capsys.readouterr().out
    assert "category counts:" in out
    for cat in CATEGORIES:
        assert cat in out


def test_json_report_roundtrip(audit_report) -> None:
    payload = json.loads(report_to_json(audit_report))
    assert payload["total"] == audit_report.total
    assert set(payload["category_counts"]) == set(CATEGORIES)
    assert len(payload["findings"]) == audit_report.total


def test_known_bridge_chat_shortcut_detected(audit_report) -> None:
    hits = [
        f
        for f in audit_report.findings
        if f.heuristic == "bridge_chat_simple_task_shortcut"
    ]
    assert hits, "expected POST /chat simple_chat_task shortcut in baseline repo"


def test_known_cando_local_detected(audit_report) -> None:
    hits = [f for f in audit_report.findings if f.heuristic == "cando_local_entry_script"]
    assert hits
