"""Aşama 0 yetki ayrımı — merge/dispatch/ayar yazmaz."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lumos_board.task_claim import ClaimError
from lumos_board.write_authority_split import (
    PRODUCTION_CHECK,
    PROOF_KEY_CHECK,
    REASON_AGENT_SECRET,
    REASON_ALLOWED,
    REASON_PROOF_AS_PRODUCTION,
    REASON_SERVICE_CONTEXT,
    REASON_SUBJECT_DENIED,
    SUBJECT_AGENT,
    SUBJECT_FOUNDER,
    SUBJECT_SERVICE,
    SUBJECT_UNKNOWN,
    assert_production_secret_use,
    classify_subject,
    main as split_main,
    public_proof_key,
    simulate_required_check_impact,
)

PROOF = "x" * 32
PRODUCTION = "y" * 32
MAIN = "refs/heads/main"
DISPATCH = "workflow_dispatch"


def test_agent_owner_is_never_founder() -> None:
    assert (
        classify_subject(
            owner="cursor-cloud",
            lumos_agent="",
            founder_ids=("candasoz01-cmd",),
        )
        == SUBJECT_AGENT
    )
    assert (
        classify_subject(
            owner="candasoz01-cmd",
            lumos_agent="cursor-cloud",
            founder_ids=("candasoz01-cmd",),
        )
        == SUBJECT_AGENT
    )
    assert classify_subject(owner="cursoragent[bot]") == SUBJECT_AGENT
    assert classify_subject(owner="codex-pr945") == SUBJECT_AGENT
    assert classify_subject(owner="claude-cowork") == SUBJECT_AGENT


def test_founder_requires_allowlist_and_no_agent_env() -> None:
    assert (
        classify_subject(owner="candasoz01-cmd", founder_ids=("candasoz01-cmd",))
        == SUBJECT_FOUNDER
    )
    assert classify_subject(owner="candasoz01-cmd") == SUBJECT_UNKNOWN


def test_service_subject_only_on_main_dispatch() -> None:
    assert (
        classify_subject(
            owner="lumos-write-gate",
            event_name=DISPATCH,
            ref=MAIN,
        )
        == SUBJECT_SERVICE
    )
    assert classify_subject(owner="lumos-write-gate", event_name="pull_request", ref=MAIN) == SUBJECT_UNKNOWN
    assert (
        classify_subject(
            owner="lumos-write-gate",
            lumos_agent="cursor-cloud",
            event_name=DISPATCH,
            ref=MAIN,
        )
        == SUBJECT_UNKNOWN
    )


def test_production_secret_denied_to_agents_and_proof_key() -> None:
    with pytest.raises(ClaimError, match=REASON_AGENT_SECRET):
        assert_production_secret_use(
            subject=SUBJECT_AGENT,
            secret=PRODUCTION,
            proof_key=PROOF,
            event_name=DISPATCH,
            ref=MAIN,
        )
    with pytest.raises(ClaimError, match=REASON_PROOF_AS_PRODUCTION):
        assert_production_secret_use(
            subject=SUBJECT_SERVICE,
            secret=PROOF,
            proof_key=PROOF,
            event_name=DISPATCH,
            ref=MAIN,
        )
    with pytest.raises(ClaimError, match=REASON_SUBJECT_DENIED):
        assert_production_secret_use(
            subject=SUBJECT_FOUNDER,
            secret=PRODUCTION,
            proof_key=PROOF,
            event_name=DISPATCH,
            ref=MAIN,
        )


def test_production_secret_only_for_service_on_main_dispatch() -> None:
    assert (
        assert_production_secret_use(
            subject=SUBJECT_SERVICE,
            secret=PRODUCTION,
            proof_key=PROOF,
            event_name=DISPATCH,
            ref=MAIN,
        )
        == REASON_ALLOWED
    )
    with pytest.raises(ClaimError, match=REASON_SERVICE_CONTEXT):
        assert_production_secret_use(
            subject=SUBJECT_SERVICE,
            secret=PRODUCTION,
            proof_key=PROOF,
            event_name="workflow_dispatch",
            ref="refs/heads/cursor/trusted-sign-path-c95e",
        )


def test_required_check_impact_does_not_mutate_and_blocks_945_fixture() -> None:
    report = simulate_required_check_impact(
        current_required=["test", "rust", "macos-app-build", "ui-smoke", "ui-e2e", "publication-gate"],
        add=[PRODUCTION_CHECK],
        pr_checks={
            PROOF_KEY_CHECK: "SUCCESS",
            PRODUCTION_CHECK: "FAILURE",
            "claim-guard": "SUCCESS",
            "test": "SUCCESS",
        },
        pr_number=945,
        head_sha="8ea3ea1a674e30a1452321e7a1effce0203a1dad",
    )
    assert report["settings_mutated"] is False
    assert report["dispatch"] is False
    assert report["merge"] is False
    assert report["grants_stage_a"] is False
    assert report["grants_stage_b"] is False
    assert report["would_block_merge"] is True
    assert report["blockers"] == [{"check": PRODUCTION_CHECK, "conclusion": "FAILURE"}]
    assert report["proof_key_check"] == "SUCCESS"


def test_adding_already_green_check_would_not_block() -> None:
    report = simulate_required_check_impact(
        current_required=["test"],
        add=["claim-guard"],
        pr_checks={"claim-guard": "SUCCESS"},
        pr_number=945,
    )
    assert report["would_block_merge"] is False
    assert report["settings_mutated"] is False


def test_cli_required_impact_reads_file_only(tmp_path: Path) -> None:
    payload = {
        "current_required": ["test"],
        "add": [PRODUCTION_CHECK],
        "pr_checks": {PRODUCTION_CHECK: "FAILURE"},
        "pr_number": 945,
        "head_sha": "deadbeef",
    }
    path = tmp_path / "impact.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert split_main(["required-impact", "--file", str(path)]) == 0


def test_public_proof_key_reads_claim_guard_workflow() -> None:
    key = public_proof_key()
    assert len(key.encode("utf-8")) >= 32
    assert "secrets." not in key
