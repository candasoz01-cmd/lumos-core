"""ADR-028 standing-class classifier — fail-closed; #777 is the fixture."""

from __future__ import annotations

from standing_merge.classify import (
    CLASS_ELIGIBLE,
    CLASS_EXCLUDED,
    PR777_PATHS,
    classify_paths,
    main,
)


def test_pr777_fixture_is_excluded() -> None:
    verdict = classify_paths(PR777_PATHS)
    assert verdict["class"] == CLASS_EXCLUDED
    assert verdict["standing_merge"] is False
    assert verdict["human_merge_required"] is True
    assert any(hit["reason"].startswith("prefix:docs/contracts/") for hit in verdict["hits"])


def test_debt_register_only_is_eligible() -> None:
    verdict = classify_paths(["docs/TECHNICAL_DEBT.md"])
    assert verdict["class"] == CLASS_ELIGIBLE
    assert verdict["standing_merge"] is True
    assert verdict["human_merge_required"] is False
    assert verdict["unknown"] == []


def test_docs_getting_started_is_eligible() -> None:
    verdict = classify_paths(["docs/getting-started.md"])
    assert verdict["class"] == CLASS_ELIGIBLE


def test_empty_diff_is_excluded() -> None:
    verdict = classify_paths([])
    assert verdict["class"] == CLASS_EXCLUDED
    assert "empty_diff" in verdict["reasons"]


def test_adr028_itself_is_excluded() -> None:
    verdict = classify_paths(
        ["docs/decisions/ADR-028-standing-low-risk-merge-approval.md"]
    )
    assert verdict["class"] == CLASS_EXCLUDED
    assert verdict["standing_merge"] is False


def test_constitution_is_excluded() -> None:
    verdict = classify_paths(["docs/CONSTITUTION.md"])
    assert verdict["class"] == CLASS_EXCLUDED


def test_security_code_is_hard_excluded() -> None:
    verdict = classify_paths(["src/security/permissions.py"])
    assert verdict["class"] == CLASS_EXCLUDED
    assert verdict["standing_merge"] is False
    assert any("src/security/" in hit["reason"] for hit in verdict["hits"])


def test_unlisted_code_is_fail_closed() -> None:
    verdict = classify_paths(["src/dashboard_health/watch.py"])
    assert verdict["class"] == CLASS_EXCLUDED
    assert verdict["unknown"] == ["src/dashboard_health/watch.py"]
    assert any(hit["reason"] == "unlisted:src/dashboard_health/watch.py" for hit in verdict["hits"])


def test_hard_exclude_wins_over_docs_allowlist() -> None:
    verdict = classify_paths(
        ["docs/TECHNICAL_DEBT.md", "docs/contracts/dashboard-health-v1.md"]
    )
    assert verdict["class"] == CLASS_EXCLUDED
    assert any("docs/contracts/" in hit["reason"] for hit in verdict["hits"])


def test_cli_exits_two_when_excluded() -> None:
    assert main(["src/security/identity.py"]) == 2


def test_cli_exits_zero_when_eligible() -> None:
    assert main(["docs/TECHNICAL_DEBT.md"]) == 0
