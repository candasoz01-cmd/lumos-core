"""ADR-032 Shadow Watch kernel: ledger, recall-before-watch, re-entry bind."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from security.shadow_watch import (
    ACTION_OBSERVE,
    CORRELATE,
    NO_INHERIT,
    REASON_CHASE_FORBIDDEN,
    REASON_CORRELATED_JOB,
    REASON_CORRELATED_LEASE,
    REASON_CORRELATED_SESSION,
    REASON_IDENTITY_UNVERIFIED,
    REASON_INTENT_FORBIDDEN,
    REASON_MANIFEST_MISSING,
    REASON_OBSERVE_GRANT_MISSING,
    REASON_RECALL_REQUIRED,
    REASON_SCOPE_VIOLATION,
    REASON_SESSION_CONFLICT,
    REASON_SINK_UNAVAILABLE,
    REASON_WATCHER_WRITE,
    STATE_FAIL_CLOSED_BLOCK,
    STATE_IN_SCOPE,
    STATE_RECALL_ISSUED,
    STATE_RETURNED,
    STATE_SURFACE_EXIT,
    STATE_WATCHING,
    ObservedAction,
    ScopeManifest,
    WorkloadIdentity,
    arm_watch,
    chase_after_exit,
    correlate_reentry,
    evaluate_observed,
    handling_tag_effects,
    latest_incident_state,
    load_ledger_entries,
    manifest_sha256,
    note_returned,
    on_scope_violation,
    open_incident,
    record_telemetry,
    score_behavior,
    surface_exit,
    telemetry_record,
    verify_ledger_chain,
    watcher_may,
)


def _manifest() -> ScopeManifest:
    return ScopeManifest(
        tools=("lumos-list-tasks",),
        path_prefixes=("notes",),
        network_classes=("none",),
        action_keys=("file_read",),
        task_id="G-12841",
        profile="rapor",
    )


def _identity(**overrides: object) -> WorkloadIdentity:
    data: dict[str, object] = {
        "subject_id": "user:X",
        "agent_id": "agent:cursor",
        "session_id": "session:s1",
        "claim_id": "claim-aaaa",
        "lease_lineage": ("claim-root",),
        "job_id": "job-1",
    }
    data.update(overrides)
    lineage = data["lease_lineage"]
    if isinstance(lineage, list):
        data["lease_lineage"] = tuple(lineage)
    return WorkloadIdentity(**data)  # type: ignore[arg-type]


def test_w1_missing_manifest_denies() -> None:
    decision = evaluate_observed(None, ObservedAction(tool="lumos-list-tasks"))
    assert decision.allow is False
    assert decision.reason == REASON_MANIFEST_MISSING


def test_w2_in_scope_does_not_open_watch(tmp_path: Path) -> None:
    decision = on_scope_violation(
        _identity(),
        _manifest(),
        ObservedAction(tool="lumos-list-tasks", action_key="file_read", path="notes/a.md"),
        base_dir=tmp_path,
    )
    assert decision.allow is True
    assert decision.state == STATE_IN_SCOPE
    assert load_ledger_entries(tmp_path) == []


@pytest.mark.parametrize(
    "path",
    (
        "notes/../secrets/x",
        "notes/foo/../../.ssh/id_rsa",
        r"notes\..\secrets\x",
    ),
)
def test_path_traversal_fails_closed(path: str) -> None:
    decision = evaluate_observed(_manifest(), ObservedAction(path=path))
    assert decision.allow is False
    assert decision.reason == REASON_SCOPE_VIOLATION


def test_path_with_empty_allowlist_fails_closed() -> None:
    decision = evaluate_observed(ScopeManifest(), ObservedAction(path="notes/a.md"))
    assert decision.allow is False
    assert decision.reason == REASON_SCOPE_VIOLATION


def test_w3_scope_violation_opens_incident_and_recall(tmp_path: Path) -> None:
    decision = on_scope_violation(
        _identity(),
        _manifest(),
        ObservedAction(tool="shell", action_key="file_read"),
        base_dir=tmp_path,
    )
    assert decision.allow is False
    assert decision.reason == REASON_SCOPE_VIOLATION
    assert decision.state == STATE_RECALL_ISSUED
    assert decision.incident_id
    assert latest_incident_state(decision.incident_id, tmp_path) == STATE_RECALL_ISSUED
    assert verify_ledger_chain(tmp_path) is True
    assert len(load_ledger_entries(tmp_path)) == 2


def test_w4_return_after_recall_does_not_arm_watch(tmp_path: Path) -> None:
    opened = on_scope_violation(
        _identity(),
        _manifest(),
        ObservedAction(tool="shell"),
        base_dir=tmp_path,
    )
    returned = note_returned(opened.incident_id, base_dir=tmp_path)
    assert returned.state == STATE_RETURNED
    skipped = arm_watch(opened.incident_id, observe_granted=True, base_dir=tmp_path)
    assert skipped.allow is False
    assert skipped.reason == REASON_RECALL_REQUIRED


def test_w5_and_w7_watch_after_recall_requires_observe_grant(tmp_path: Path) -> None:
    opened = on_scope_violation(
        _identity(),
        _manifest(),
        ObservedAction(tool="shell"),
        base_dir=tmp_path,
    )
    denied = arm_watch(opened.incident_id, observe_granted=False, base_dir=tmp_path)
    assert denied.state == STATE_FAIL_CLOSED_BLOCK
    assert denied.reason == REASON_OBSERVE_GRANT_MISSING

    opened2 = on_scope_violation(
        _identity(session_id="session:s2"),
        _manifest(),
        ObservedAction(path="secrets/x"),
        base_dir=tmp_path,
    )
    watching = arm_watch(opened2.incident_id, observe_granted=True, base_dir=tmp_path)
    assert watching.state == STATE_WATCHING
    assert watching.reason == ACTION_OBSERVE


def test_w6_watch_cannot_skip_recall(tmp_path: Path) -> None:
    opened = open_incident(
        _identity(),
        _manifest(),
        ObservedAction(tool="shell"),
        base_dir=tmp_path,
    )
    skipped = arm_watch(opened.incident_id, observe_granted=True, base_dir=tmp_path)
    assert skipped.allow is False
    assert skipped.reason == REASON_RECALL_REQUIRED
    assert skipped.state == STATE_FAIL_CLOSED_BLOCK


def test_w8_watcher_cannot_write() -> None:
    assert watcher_may(ACTION_OBSERVE).allow is True
    denied = watcher_may("write_local")
    assert denied.allow is False
    assert denied.reason == REASON_WATCHER_WRITE
    assert watcher_may("mail_send").allow is False


def test_w9_telemetry_strips_content_and_tokens() -> None:
    record = telemetry_record(
        ObservedAction(tool="read", path="notes/secret.md"),
        {"content": "TOP SECRET", "token": "teg1.abc", "byte_size": 12},
    )
    assert "content" not in record
    assert "token" not in record
    assert record["byte_size"] == 12
    assert record["path_basename"] == "secret.md"
    assert record["path_hash"]
    dumped = json.dumps(record)
    assert "TOP SECRET" not in dumped
    assert "teg1.abc" not in dumped


def test_w10_surface_exit_forbids_chase(tmp_path: Path) -> None:
    opened = on_scope_violation(
        _identity(),
        _manifest(),
        ObservedAction(tool="shell"),
        base_dir=tmp_path,
    )
    arm_watch(opened.incident_id, observe_granted=True, base_dir=tmp_path)
    exited = surface_exit(opened.incident_id, base_dir=tmp_path)
    assert exited.state == STATE_SURFACE_EXIT
    chase = chase_after_exit("https://evil.example")
    assert chase.allow is False
    assert chase.reason == REASON_CHASE_FORBIDDEN
    assert chase.state == STATE_SURFACE_EXIT


def test_w11_subject_and_agent_alone_do_not_inherit() -> None:
    prior = _identity(session_id="", claim_id="", lease_lineage=(), job_id="")
    incoming = _identity(session_id="", claim_id="", lease_lineage=(), job_id="")
    decision = correlate_reentry(prior, incoming)
    assert decision.decision == NO_INHERIT
    assert decision.inherit_incident is False
    assert decision.reason == REASON_IDENTITY_UNVERIFIED


def test_w11b_same_session_correlates() -> None:
    prior = _identity(claim_id="", lease_lineage=(), job_id="")
    incoming = _identity(claim_id="", lease_lineage=(), job_id="", session_id="session:s1")
    decision = correlate_reentry(prior, incoming)
    assert decision.decision == CORRELATE
    assert decision.reason == REASON_CORRELATED_SESSION
    assert decision.inherit_incident is True


def test_w11c_lease_lineage_correlates_across_sessions() -> None:
    prior = WorkloadIdentity(
        subject_id="user:X",
        agent_id="agent:cursor",
        session_id="session:old",
        claim_id="claim-root",
        lease_lineage=(),
    )
    incoming = WorkloadIdentity(
        subject_id="user:X",
        agent_id="agent:cursor",
        session_id="session:new",
        claim_id="claim-child",
        lease_lineage=("claim-root",),
    )
    decision = correlate_reentry(prior, incoming)
    assert decision.decision == CORRELATE
    assert decision.reason == REASON_CORRELATED_LEASE


def test_w11d_job_id_correlates() -> None:
    prior = WorkloadIdentity(
        subject_id="user:X",
        agent_id="agent:cursor",
        job_id="job-keep",
    )
    incoming = WorkloadIdentity(
        subject_id="user:X",
        agent_id="agent:cursor",
        job_id="job-keep",
    )
    decision = correlate_reentry(prior, incoming)
    assert decision.decision == CORRELATE
    assert decision.reason == REASON_CORRELATED_JOB


def test_w12_placeholder_session_is_unverified() -> None:
    prior = _identity(session_id="session:unspecified", claim_id="", lease_lineage=(), job_id="")
    incoming = _identity(session_id="session:unspecified", claim_id="", lease_lineage=(), job_id="")
    decision = correlate_reentry(prior, incoming)
    assert decision.inherit_incident is False
    assert decision.reason == REASON_IDENTITY_UNVERIFIED


def test_w12b_conflicting_sessions_without_lease_do_not_inherit() -> None:
    prior = WorkloadIdentity(
        subject_id="user:X",
        agent_id="agent:cursor",
        session_id="session:a",
    )
    incoming = WorkloadIdentity(
        subject_id="user:X",
        agent_id="agent:cursor",
        session_id="session:b",
    )
    decision = correlate_reentry(prior, incoming)
    assert decision.decision == NO_INHERIT
    assert decision.reason == REASON_SESSION_CONFLICT


def test_w13_handling_tag_does_not_open_never_auto_or_chase() -> None:
    effects = handling_tag_effects("malicious_behavior_suspected")
    assert "quarantine" in effects["may"]
    assert effects["chase"] is False
    assert effects["never_auto"] is False
    assert effects["standing_merge"] is False
    assert "chase" in effects["must_not"]
    assert "never_auto" in effects["must_not"]


def test_w19_unwritable_sink_fail_closed(tmp_path: Path) -> None:
    blocked = tmp_path / "not-a-dir"
    blocked.write_text("file", encoding="utf-8")
    decision = on_scope_violation(
        _identity(),
        _manifest(),
        ObservedAction(tool="shell"),
        base_dir=blocked,
    )
    assert decision.allow is False
    assert decision.state == STATE_FAIL_CLOSED_BLOCK
    assert decision.reason == REASON_SINK_UNAVAILABLE


def test_w20_intent_field_rejected() -> None:
    with pytest.raises(ValueError, match=REASON_INTENT_FORBIDDEN):
        telemetry_record(ObservedAction(tool="read"), {"intent": "malicious"})
    with pytest.raises(ValueError, match=REASON_INTENT_FORBIDDEN):
        score_behavior({"intent": "accidental"})


def test_record_telemetry_drops_payload(tmp_path: Path) -> None:
    opened = on_scope_violation(
        _identity(),
        _manifest(),
        ObservedAction(tool="shell"),
        base_dir=tmp_path,
    )
    arm_watch(opened.incident_id, observe_granted=True, base_dir=tmp_path)
    recorded = record_telemetry(
        opened.incident_id,
        ObservedAction(path="notes/a.md"),
        {"content": "hello", "title": "secret task"},
        base_dir=tmp_path,
    )
    assert recorded.allow is True
    blob = (tmp_path / "ledgers" / "shadow_watch.jsonl").read_text(encoding="utf-8")
    assert "hello" not in blob
    assert "secret task" not in blob
    assert verify_ledger_chain(tmp_path) is True


def test_manifest_checksum_is_full_sha256_not_cu4_truncation() -> None:
    digest = manifest_sha256(_manifest())
    assert len(digest) == 64
    assert digest != manifest_sha256(ScopeManifest(tools=("other",)))


def test_ledger_tamper_fails_verify(tmp_path: Path) -> None:
    on_scope_violation(
        _identity(),
        _manifest(),
        ObservedAction(tool="shell"),
        base_dir=tmp_path,
    )
    path = tmp_path / "ledgers" / "shadow_watch.jsonl"
    path.write_text(path.read_text(encoding="utf-8") + "{not json\n", encoding="utf-8")
    assert verify_ledger_chain(tmp_path) is False


@pytest.mark.parametrize("row", ("[]", '"not-an-object"', "null"))
def test_non_object_ledger_row_fails_verify(tmp_path: Path, row: str) -> None:
    path = tmp_path / "ledgers" / "shadow_watch.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(row + "\n", encoding="utf-8")
    assert verify_ledger_chain(tmp_path) is False


def test_score_behavior_has_no_intent_key() -> None:
    scored = score_behavior({"scope_distance": 2, "persistence_after_recall": True})
    assert scored["classification"] == "unclassified"
    assert "intent" not in scored
    assert scored["band"] == 2
