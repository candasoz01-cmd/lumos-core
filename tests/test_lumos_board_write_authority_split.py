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
    REASON_IDENTITY_GAP,
    REASON_PROOF_AS_PRODUCTION,
    REASON_SERVICE_CONTEXT,
    REASON_SUBJECT_DENIED,
    SUBJECT_AGENT,
    SUBJECT_FOUNDER,
    SUBJECT_SERVICE,
    SUBJECT_UNKNOWN,
    STAGE_A_OPENS,
    STAGE_B_OPENS,
    STAGE_NEITHER_OPENS,
    assert_production_secret_use,
    classify_subject,
    evaluate_identity_evidence,
    main as split_main,
    public_proof_key,
    simulate_required_check_impact,
    stage_authority_map,
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
    assert classify_subject(owner="claude", founder_ids=("candasoz01-cmd",)) == SUBJECT_AGENT
    assert classify_subject(owner="claude[bot]", founder_ids=("candasoz01-cmd",)) == SUBJECT_AGENT
    assert (
        classify_subject(owner="chatgpt-codex-connector[bot]", founder_ids=("candasoz01-cmd",))
        == SUBJECT_AGENT
    )


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


LIVE_IDENTITY = {
    "verified_at": "2026-10-16T17:19Z",
    "source": "GitHub API",
    "founder": {
        "login": "candasoz01-cmd",
        "id": 260758816,
        "type": "User",
        "role": "admin",
    },
    "apps": [
        {
            "slug": "claude",
            "id": 1236702,
            "name": "Claude",
            "owner": "anthropics",
            "bot_login": "claude[bot]",
            "bot_id": 209825114,
            "bot_type": "Bot",
        },
        {
            "slug": "chatgpt-codex-connector",
            "id": 1144995,
            "name": "ChatGPT Codex Connector",
            "owner": "openai",
            "bot_login": "chatgpt-codex-connector[bot]",
            "bot_id": 199175422,
            "bot_type": "Bot",
        },
        {
            "slug": "cursor",
            "id": 1210556,
            "name": "Cursor",
            "owner": "cursor",
            "bot_login": "cursor[bot]",
            "bot_id": 206951365,
            "bot_type": "Bot",
        },
    ],
    "operating_identities": [
        {
            "login": "claude",
            "id": 81847,
            "type": "User",
            "evidence": "repo commits author.login=claude",
        },
        {
            "login": "claude[bot]",
            "id": 209825114,
            "type": "Bot",
            "evidence": "GitHub App bot for slug claude",
        },
        {
            "login": "chatgpt-codex-connector[bot]",
            "id": 199175422,
            "type": "Bot",
            "evidence": "PR reviews on #930 and #932",
        },
        {
            "login": "cursor[bot]",
            "id": 206951365,
            "type": "Bot",
            "evidence": "PR author app/cursor including #947",
        },
    ],
    "write_gate_environment": {
        "name": "lumos-write-gate",
        "required_reviewers": ["candasoz01-cmd"],
        "deployment_branches": ["main"],
    },
    "agent_process": {
        "lumos_write_gate_secret_present": False,
        "github_token_env_present": False,
        "ssh_dir_present": False,
        "gh_account": "cursor",
    },
}


def test_live_identity_evidence_keeps_apps_and_founder_apart() -> None:
    report = evaluate_identity_evidence(LIVE_IDENTITY)
    assert report["ok"] is True
    assert report["founder"] == "candasoz01-cmd"
    assert report["required_apps"] == ["claude", "chatgpt-codex-connector"]
    assert report["production_secret_in_agent_env"] is False
    assert report["grants_stage_a"] is False
    assert report["grants_stage_b"] is False
    assert report["settings_mutated"] is False


def test_identity_evidence_rejects_missing_codex_app() -> None:
    payload = json.loads(json.dumps(LIVE_IDENTITY))
    payload["apps"] = [item for item in payload["apps"] if item["slug"] != "chatgpt-codex-connector"]
    with pytest.raises(ClaimError, match=REASON_IDENTITY_GAP):
        evaluate_identity_evidence(payload)


def test_identity_evidence_rejects_secret_in_agent_env() -> None:
    payload = json.loads(json.dumps(LIVE_IDENTITY))
    payload["agent_process"]["lumos_write_gate_secret_present"] = True
    with pytest.raises(ClaimError, match=REASON_IDENTITY_GAP):
        evaluate_identity_evidence(payload)


def test_identity_evidence_rejects_bot_as_write_gate_reviewer() -> None:
    payload = json.loads(json.dumps(LIVE_IDENTITY))
    payload["write_gate_environment"]["required_reviewers"] = ["claude[bot]"]
    with pytest.raises(ClaimError, match=REASON_IDENTITY_GAP):
        evaluate_identity_evidence(payload)


def test_cli_identities_reads_file_only(tmp_path: Path) -> None:
    path = tmp_path / "identities.json"
    path.write_text(json.dumps(LIVE_IDENTITY), encoding="utf-8")
    assert split_main(["identities", "--file", str(path)]) == 0


def test_stage_map_does_not_open_a_or_b() -> None:
    report = stage_authority_map()
    assert report["grants_stage_a"] is False
    assert report["grants_stage_b"] is False
    assert report["agent_inherits_founder"] is False
    assert report["merge"] is False
    assert report["dispatch"] is False
    assert "founder_merge_of_signer_workflow_onto_main" in report["stage_a_opens"]
    assert "founder_workflow_dispatch_from_refs_heads_main" in report["stage_b_opens"]
    assert "agent_merge" in report["neither_opens"]
    assert set(STAGE_A_OPENS).isdisjoint(STAGE_B_OPENS)
    assert set(STAGE_A_OPENS).isdisjoint(STAGE_NEITHER_OPENS)
    assert set(STAGE_B_OPENS).isdisjoint(STAGE_NEITHER_OPENS)
    assert split_main(["stages"]) == 0


def test_required_check_impact_records_947_trusted_red() -> None:
    report = simulate_required_check_impact(
        current_required=["test", "rust", "macos-app-build", "ui-smoke", "ui-e2e", "publication-gate"],
        add=[PRODUCTION_CHECK],
        pr_checks={
            PROOF_KEY_CHECK: "SUCCESS",
            PRODUCTION_CHECK: "FAILURE",
            "claim-guard": "SUCCESS",
            "test": "SUCCESS",
        },
        pr_number=947,
        head_sha="6153783055abeea6b9b034efd4c871a1eaa576db",
    )
    assert report["would_block_merge"] is True
    assert report["settings_mutated"] is False
    assert report["grants_stage_a"] is False
