"""ADR-028 standing-class classifier — #777 is the control-incident fixture."""

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


def test_cli_exits_two_when_excluded() -> None:
    assert main(["docs/contracts/dashboard-health-v1.md"]) == 2


def test_cli_exits_zero_when_eligible() -> None:
    assert main(["docs/TECHNICAL_DEBT.md"]) == 0
