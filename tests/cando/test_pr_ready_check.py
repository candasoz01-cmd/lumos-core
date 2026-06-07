"""cando.pr_ready_check: gh mock ve rapor."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from cando.pr_ready_check import (
    _classify_rollup,
    _parse_checks_output,
    format_report,
    run_check,
)


def test_classify_rollup_all_pass():
    rollup = [
        {
            "__typename": "CheckRun",
            "name": "test",
            "status": "COMPLETED",
            "conclusion": "SUCCESS",
        },
        {
            "__typename": "StatusContext",
            "context": "Vercel",
            "state": "SUCCESS",
        },
    ]
    passed, pending, failed = _classify_rollup(rollup)
    assert len(passed) == 2
    assert not pending
    assert not failed


def test_classify_rollup_pending_and_failed():
    rollup = [
        {
            "__typename": "CheckRun",
            "name": "ci",
            "status": "IN_PROGRESS",
            "conclusion": "",
        },
        {
            "__typename": "CheckRun",
            "name": "lint",
            "status": "COMPLETED",
            "conclusion": "FAILURE",
        },
    ]
    passed, pending, failed = _classify_rollup(rollup)
    assert not passed
    assert len(pending) == 1
    assert len(failed) == 1
    assert failed[0].name == "lint"


def test_parse_checks_output():
    stdout = "test\tpass\t28s\thttps://example.com/job\t\nlint\tfail\t1m\thttps://example.com/lint\timport error\n"
    passed, pending, failed = _parse_checks_output(stdout)
    assert len(passed) == 1
    assert passed[0].name == "test"
    assert len(failed) == 1
    assert failed[0].summary == "import error"


def test_run_check_ready(tmp_path: Path):
    pr_json = {
        "state": "OPEN",
        "closed": False,
        "title": "feat: example",
        "url": "https://github.com/org/repo/pull/1",
        "mergedAt": None,
        "mergeable": "MERGEABLE",
        "statusCheckRollup": [
            {
                "__typename": "CheckRun",
                "name": "test",
                "status": "COMPLETED",
                "conclusion": "SUCCESS",
            }
        ],
    }

    def fake_gh(args, cwd):
        import subprocess

        return subprocess.CompletedProcess(args, 0, json.dumps(pr_json), "")

    with patch("cando.pr_ready_check._run_gh", side_effect=fake_gh):
        result = run_check(tmp_path, 1)

    assert result.readiness == "hazir"
    report = format_report(result, dry_run=True)
    assert "merge için hazır" in report
    assert "gh pr merge 1" in report


def test_run_check_merged():
    pr_json = {
        "state": "MERGED",
        "closed": True,
        "title": "docs: done",
        "url": "https://github.com/org/repo/pull/98",
        "mergedAt": "2026-06-07T06:51:44Z",
        "mergeable": "UNKNOWN",
        "statusCheckRollup": [],
    }

    def fake_gh(args, cwd):
        import subprocess

        return subprocess.CompletedProcess(args, 0, json.dumps(pr_json), "")

    with patch("cando.pr_ready_check._run_gh", side_effect=fake_gh):
        result = run_check(Path("/tmp"), 98)

    assert result.readiness == "birlestirilmis"
    report = format_report(result, dry_run=True)
    assert "zaten merge edilmiş" in report
