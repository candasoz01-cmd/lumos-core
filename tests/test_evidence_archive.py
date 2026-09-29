import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lumos_board.evidence_archive import (
    DEFAULT_REMOTE,
    archive_report,
    bind_report,
    checkpoint_due,
    execute_source_deletion,
    inventory,
    observe_archive,
    probe_remote,
    publish_and_read_back,
    source_deletion_decision,
    transfer_window,
    workflow_retention_days,
)
from lumos_board.evidence_policy import EvidencePolicy
from lumos_board.founder_approval import FounderApprovalStore, FounderApproverRegistry

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


def git(repo, *args):
    subprocess.check_call(["git", "-C", str(repo), *args], stdout=subprocess.DEVNULL)


def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    git(root, "init")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.invalid")
    (root / "note.txt").write_text("keep this\n")
    git(root, "add", "note.txt")
    git(root, "commit", "-m", "note")
    return root


def expect(root, report_id):
    commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    return {"task_id": "KA-1", "report_id": report_id, "commit": commit, "run_attempt": "2"}


def archived(tmp_path, report_id="report-1", **kwargs):
    root = repo(tmp_path)
    (root / "new.txt").write_text("uncommitted work\n")
    verdict = archive_report(
        root,
        tmp_path / "archive",
        task_id="KA-1",
        report_id=report_id,
        report_kind="interim",
        run_attempt="2",
        extra_paths=["note.txt"],
        now=NOW,
        policy_days=14,
        object_expires_at=NOW + timedelta(days=30),
        retry_margin=timedelta(hours=1),
        **kwargs,
    )
    return root, verdict


def test_uncommitted_file_is_verified_and_secret_is_not_copied(tmp_path):
    root = repo(tmp_path)
    (root / "new.txt").write_text("uncommitted work\n")
    (root / ".env").write_text("api_key=super-secret\n")
    verdict = archive_report(
        root, tmp_path / "archive", task_id="KA-1", report_id="report-1",
        report_kind="delivery", run_attempt="2", extra_paths=["note.txt"],
        now=NOW, policy_days=14, object_expires_at=NOW + timedelta(days=30),
        retry_margin=timedelta(hours=1), report={"task": "api_key=super-secret"},
    )
    assert verdict["verified"] is True
    assert verdict["status"] == "VERIFIED"
    payload = tmp_path / "archive" / "report-1" / "payload"
    blob = b"".join(path.read_bytes() for path in payload.iterdir())
    assert b"uncommitted work" in blob
    assert b"super-secret" not in blob
    report = json.loads((tmp_path / "archive" / "report-1" / "report.json").read_text())
    assert "super-secret" not in json.dumps(report)
    assert any(item["reason"] == "secret" for item in verdict["excluded"])


def test_corrupt_copy_stops_verification(tmp_path):
    root, verdict = archived(tmp_path)
    assert verdict["verified"] is True
    payload = next((tmp_path / "archive" / "report-1" / "payload").iterdir())
    payload.write_bytes(payload.read_bytes() + b"x")
    again = observe_archive(root, tmp_path / "archive" / "report-1", expect=expect(root, "report-1"))
    assert again["verified"] is False
    assert again["status"] == "ARCHIVE_CORRUPT"


def test_missing_payload_stops_verification(tmp_path):
    root, _ = archived(tmp_path)
    payload = tmp_path / "archive" / "report-1" / "payload"
    for child in payload.iterdir():
        child.unlink()
    again = observe_archive(root, tmp_path / "archive" / "report-1", expect=expect(root, "report-1"))
    assert again["status"] == "ARCHIVE_MISSING"
    assert again["verified"] is False


def test_wrong_report_stops_verification(tmp_path):
    root, _ = archived(tmp_path)
    wanted = expect(root, "other-report")
    again = observe_archive(root, tmp_path / "archive" / "report-1", expect=wanted)
    assert again["status"] == "WRONG_REPORT"


def test_changed_source_stops_verification(tmp_path):
    root, _ = archived(tmp_path)
    (root / "new.txt").write_text("changed after archive\n")
    again = observe_archive(root, tmp_path / "archive" / "report-1", expect=expect(root, "report-1"))
    assert again["status"] == "SOURCE_CHANGED"
    assert again["verified"] is False


def test_short_retention_is_not_success_and_not_eighty_days(tmp_path):
    root = repo(tmp_path)
    (root / "new.txt").write_text("work\n")
    verdict = archive_report(
        root, tmp_path / "archive", task_id="KA-1", report_id="short",
        report_kind="interim", run_attempt="2", now=NOW,
        object_expires_at=NOW + timedelta(minutes=10), retry_margin=timedelta(hours=2),
    )
    assert verdict["verified"] is False
    assert verdict["status"] == "RETENTION_TOO_SHORT"
    unknown = transfer_window(now=NOW, policy_days=None, object_expires_at=None)
    assert unknown["status"] == "RETENTION_UNKNOWN"
    assert unknown["fixed_80_90_assumed"] is False
    assert 80 not in (unknown["deadline"], unknown["complete_by"])
    assert 90 not in (unknown["deadline"], unknown["complete_by"])


def test_layer1a_retention_is_fourteen_days():
    assert workflow_retention_days(ROOT / ".github/workflows/layer1a.yml") == 14
    assert workflow_retention_days(ROOT / ".github/workflows/bridge-llm-observe.yml") == 14


def test_remote_failure_is_not_verified(tmp_path):
    root, verdict = archived(tmp_path)
    result = publish_and_read_back(
        root, tmp_path / "archive" / "report-1", str(tmp_path / "missing.git"),
        tmp_path / "readback", report_id="report-1", expect=expect(root, "report-1"),
    )
    assert result["verified"] is False
    assert result["status"] == "REMOTE_UNREACHABLE"
    assert verdict["verified"] is True


def test_local_remote_roundtrip_reads_back_independently(tmp_path):
    root, _ = archived(tmp_path, report_id="remote-1")
    bare = tmp_path / "wall.git"
    subprocess.check_call(["git", "init", "--bare", str(bare)])
    result = publish_and_read_back(
        root, tmp_path / "archive" / "remote-1", bare.as_uri(), tmp_path / "readback",
        report_id="remote-1", expect=expect(root, "remote-1"),
    )
    assert result["status"] == "VERIFIED"
    assert result["verified"] is True
    assert "readback" in result["archive"]


def test_private_github_archive_is_not_claimed_verified():
    result = probe_remote(DEFAULT_REMOTE)
    assert result["verified"] is False
    assert result["status"] in {"REMOTE_UNREACHABLE", "REMOTE_FORBIDDEN"}


def test_observer_does_not_write(tmp_path):
    root, _ = archived(tmp_path)
    target = tmp_path / "archive" / "report-1"
    before = sorted(path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file())
    observe_archive(root, target, expect=expect(root, "report-1"))
    after = sorted(path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file())
    assert before == after


def test_inventory_keeps_lost_separate_from_recovered(tmp_path):
    archived(tmp_path, report_id="held")
    root = repo(tmp_path / "other")
    (root / "new.txt").write_text("soon\n")
    archive_report(
        root, tmp_path / "archive", task_id="KA-1", report_id="soon",
        report_kind="interim", run_attempt="2", now=NOW,
        object_expires_at=NOW + timedelta(days=1), retry_margin=timedelta(0),
    )
    lost_root = repo(tmp_path / "lost")
    (lost_root / "new.txt").write_text("gone\n")
    archive_report(
        lost_root, tmp_path / "archive", task_id="KA-1", report_id="gone",
        report_kind="interim", run_attempt="2", now=NOW,
        object_expires_at=NOW + timedelta(days=30), retry_margin=timedelta(hours=1),
    )
    for child in (tmp_path / "archive" / "gone" / "payload").iterdir():
        child.unlink()
    listed = inventory(tmp_path / "archive", now=NOW, horizon=timedelta(days=7))
    assert "held" in listed["held"]
    assert "soon" in listed["near_expiry"]
    assert listed["lost"] == ["gone"]
    assert listed["recovered_from_lost"] == []


def test_source_deletion_needs_archive_and_founder_gate(tmp_path):
    root, verdict = archived(tmp_path)
    archive = tmp_path / "archive" / "report-1"
    registry = FounderApproverRegistry({"founder": datetime(2099, 1, 1, tzinfo=timezone.utc)})
    store = FounderApprovalStore(tmp_path / "approvals", registry=registry, clock=lambda: NOW)
    head = expect(root, "report-1")["commit"]
    terms = EvidencePolicy().record_terms(datetime(2024, 1, 1, tzinfo=timezone.utc), kind="audit", severity="ordinary")
    blocked = source_deletion_decision(
        store, task="KA-1", head_sha=head, verification=verdict, terms=terms, at=NOW, archive_dir=archive,
    )
    assert blocked["allowed"] is False
    assert "EXPLICIT_SCOPE_APPROVAL_REQUIRED" in blocked["reasons"]
    with pytest.raises(PermissionError):
        execute_source_deletion(root, ["new.txt"], blocked, archive_dir=archive, verification=verdict)
    assert (root / "new.txt").is_file()
    approval = store.request(task="KA-1", gate="evidence_archive", action="delete_source", head_sha=head)
    store.grant(approval.approval_id, approved_by="founder")
    allowed = source_deletion_decision(
        store, task="KA-1", head_sha=head, verification=verdict, terms=terms,
        at=datetime(2026, 6, 1, tzinfo=timezone.utc), archive_dir=archive,
    )
    assert allowed["allowed"] is True
    result = execute_source_deletion(root, ["new.txt"], allowed, archive_dir=archive, verification=verdict)
    assert result["archive_retained"] is True
    assert not (root / "new.txt").exists()
    assert list((archive / "payload").iterdir())


def test_checkpoint_interval_and_unconfigured_report(tmp_path, monkeypatch):
    assert checkpoint_due(tmp_path / "empty", now=NOW) is True
    (tmp_path / "empty").mkdir()
    (tmp_path / "empty" / "last_checkpoint_at").write_text(NOW.isoformat() + "\n")
    assert checkpoint_due(tmp_path / "empty", now=NOW + timedelta(minutes=1)) is False
    monkeypatch.delenv("LUMOS_WALL_EVIDENCE_DIR", raising=False)
    monkeypatch.delenv("LUMOS_WALL_EVIDENCE_REMOTE", raising=False)
    report = bind_report({"status": "ok", "task": "KA-1", "errors": []}, repo=tmp_path, job_id="job")
    assert report["evidence"]["status"] == "ARCHIVE_NOT_CONFIGURED"
    assert report["evidence"]["verified"] is False
    assert report["status"] == "ok"
    monkeypatch.setenv("LUMOS_WALL_EVIDENCE_DIR", str(tmp_path / "missing-parent"))
    os.makedirs(tmp_path / "missing-parent", exist_ok=True)
    bound = bind_report({"status": "ok", "task": "KA-1", "changed_files": []}, repo=repo(tmp_path / "job"), job_id="job")
    assert bound["evidence"]["required"] is True
    assert bound["evidence"]["verified"] is True
    assert bound["status"] == "ok"
