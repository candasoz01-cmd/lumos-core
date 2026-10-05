import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from unittest.mock import patch

from lumos_board.evidence_archive import (
    DEFAULT_REMOTE,
    _worktree_paths,
    archive_dir_for,
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


def expect(root, report_id, extra=("note.txt",), base=None, paths=None):
    commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    # `paths` is the frozen capture snapshot. When a test does not pass one,
    # the trusted extra list is that snapshot and the live status can only add paths.
    frozen = list(extra if paths is None else paths)
    scope = {
        "paths": frozen,
        "worktree": True,
        "extra": [],
        "head": commit,
        "task_id": "KA-1",
        "report_id": report_id,
        "commit": commit,
        "run_attempt": "2",
    }
    if base is not None:
        scope["base"] = base
    return {
        "task_id": "KA-1",
        "report_id": report_id,
        "commit": commit,
        "run_attempt": "2",
        "scope": scope,
    }


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


@pytest.mark.parametrize("body", [
    "token = None\n",
    "api_key = None\n",
    "password = None\n",
    "secret = None\n",
])
def test_content_exclusion_of_normal_file_is_incomplete(tmp_path, body):
    root = repo(tmp_path)
    (root / "plain.txt").write_text(body)
    verdict = archive_report(
        root, tmp_path / "archive", task_id="KA-1", report_id="report-1",
        report_kind="interim", run_attempt="2", extra_paths=["note.txt"],
        now=NOW, policy_days=14, object_expires_at=NOW + timedelta(days=30),
        retry_margin=timedelta(hours=1),
    )
    assert verdict["status"] == "SCOPE_INCOMPLETE"
    assert verdict["verified"] is False
    assert any(
        item.get("path") == "plain.txt" and item.get("reason") == "secret"
        for item in verdict["excluded"]
    )
    payload = tmp_path / "archive" / "report-1" / "payload"
    copied = b"".join(path.read_bytes() for path in payload.iterdir()) if payload.is_dir() else b""
    assert body.encode() not in copied


def test_forged_secret_exclusion_without_payload_is_incomplete(tmp_path):
    root, verdict = archived(tmp_path)
    assert verdict["status"] == "VERIFIED"
    archive = tmp_path / "archive" / "report-1"
    manifest_path = archive / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["excluded"] = [
        *(manifest.get("excluded") or []),
        *[{"path": entry["path"], "reason": "secret"} for entry in manifest["files"]],
    ]
    manifest["files"] = []
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    payload = archive / "payload"
    for path in payload.iterdir():
        path.unlink()
    again = observe_archive(root, archive, expect=expect(root, "report-1"))
    assert again["status"] == "SCOPE_INCOMPLETE"
    assert again["verified"] is False


def test_one_forged_secret_exclusion_keeps_the_archive_incomplete(tmp_path):
    root, verdict = archived(tmp_path)
    assert verdict["status"] == "VERIFIED"
    archive = tmp_path / "archive" / "report-1"
    manifest_path = archive / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    kept = []
    forged = list(manifest.get("excluded") or [])
    payload = archive / "payload"
    for entry in manifest["files"]:
        if entry["path"] == "new.txt":
            forged.append({"path": entry["path"], "reason": "secret"})
            (payload / entry["sha256"]).unlink()
        else:
            kept.append(entry)
    assert kept and len(forged) == 1
    manifest["files"] = kept
    manifest["excluded"] = forged
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    again = observe_archive(root, archive, expect=expect(root, "report-1"))
    assert again["status"] == "SCOPE_INCOMPLETE"
    assert again["verified"] is False


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


def _archive(root, tmp_path, report_id="report-1", **kwargs):
    return archive_report(
        root, tmp_path / "archive", task_id="KA-1", report_id=report_id, report_kind="delivery",
        run_attempt="2", now=NOW, policy_days=14, object_expires_at=NOW + timedelta(days=30),
        retry_margin=timedelta(hours=1), **kwargs,
    )


# --- #912 / Bugbot: deletions must be verifiable, not SCOPE_INCOMPLETE ---------------------


def test_deleted_tracked_file_verifies_and_reappearing_file_stops(tmp_path):
    root = repo(tmp_path)
    (root / "note.txt").unlink()  # worktree deletion, also listed in changed_files
    verdict = _archive(root, tmp_path, extra_paths=["note.txt"])
    assert verdict["status"] == "VERIFIED" and verdict["verified"] is True
    assert {"path": "note.txt", "reason": "deleted"} in verdict["excluded"]
    again = observe_archive(root, tmp_path / "archive" / "report-1", expect=expect(root, "report-1"))
    assert again["status"] == "VERIFIED"
    (root / "note.txt").write_text("it came back\n")  # the exclusion is re-checked, not trusted
    stale = observe_archive(root, tmp_path / "archive" / "report-1", expect=expect(root, "report-1"))
    assert stale["status"] == "SOURCE_CHANGED" and stale["verified"] is False


def test_unverifiable_missing_paths_stay_incomplete(tmp_path):
    root = repo(tmp_path)
    for index, ghost in enumerate(("never-existed.txt", "../outside.txt")):
        verdict = _archive(root, tmp_path, report_id=f"r-{index}", extra_paths=[ghost])
        assert verdict["verified"] is False
        assert verdict["status"] == "SCOPE_INCOMPLETE"


def test_committed_deletion_verifies_and_reappearing_file_stops(tmp_path):
    root = repo(tmp_path)
    git(root, "rm", "note.txt")
    git(root, "commit", "-m", "delete note")
    verdict = _archive(root, tmp_path, extra_paths=["note.txt"])
    assert verdict["status"] == "VERIFIED"
    assert {"path": "note.txt", "reason": "deleted"} in verdict["excluded"]
    archive = tmp_path / "archive" / "report-1"
    assert observe_archive(root, archive, expect=expect(root, "report-1"))["verified"]
    (root / "note.txt").write_text("reappeared\n")
    assert observe_archive(root, archive, expect=expect(root, "report-1"))["status"] == "SOURCE_CHANGED"


def test_bind_report_after_delete_commit_stays_successful(tmp_path, monkeypatch):
    root = repo(tmp_path)
    git(root, "rm", "note.txt")
    git(root, "commit", "-m", "delete note")
    monkeypatch.setenv("LUMOS_WALL_EVIDENCE_DIR", str(tmp_path / "archive"))
    monkeypatch.delenv("LUMOS_WALL_EVIDENCE_REMOTE", raising=False)
    bound = bind_report(
        {"status": "ok", "task": "KA-1", "changed_files": ["note.txt"]},
        repo=root, job_id="committed-delete",
    )
    assert bound["status"] == "ok"
    assert bound["evidence"]["required"] is True
    assert bound["evidence"]["verified"] is True


@pytest.mark.parametrize("relative", ["note.txt", "never-existed.txt", "removed-dir"])
def test_missing_paths_are_not_proved_by_unrelated_history(tmp_path, relative):
    root = repo(tmp_path)
    (root / "removed-dir").mkdir()
    (root / "removed-dir" / "child.txt").write_text("child\n")
    git(root, "add", ".")
    git(root, "commit", "-m", "add directory")
    git(root, "rm", "note.txt")
    git(root, "commit", "-m", "earlier deletion")
    git(root, "rm", "-r", "removed-dir")
    git(root, "commit", "-m", "unrelated directory deletion")
    verdict = _archive(root, tmp_path, extra_paths=[relative])
    assert verdict["status"] == "SCOPE_INCOMPLETE"
    assert verdict["verified"] is False


def test_committed_delete_with_literal_filename_and_later_head_change(tmp_path):
    root = repo(tmp_path)
    relative = "literal [x] ü\nfile.txt"
    (root / relative).write_text("tracked\n")
    git(root, "add", "--", relative)
    git(root, "commit", "-m", "add literal path")
    git(root, "rm", "--", relative)
    git(root, "commit", "-m", "delete literal path")
    wanted = expect(root, "report-1")
    assert _archive(root, tmp_path, extra_paths=[relative])["verified"] is True
    git(root, "commit", "--allow-empty", "-m", "later commit")
    result = observe_archive(root, tmp_path / "archive" / "report-1", expect=wanted)
    assert result["status"] == "SOURCE_CHANGED"


def test_replacement_cannot_reclassify_old_deletion(tmp_path):
    root = repo(tmp_path)
    original = expect(root, "report-1")["commit"]
    git(root, "rm", "note.txt")
    git(root, "commit", "-m", "delete note")
    deleted = expect(root, "report-1")["commit"]
    git(root, "commit", "--allow-empty", "-m", "unrelated later commit")
    current = expect(root, "report-1")["commit"]
    git(root, "replace", "--graft", current, original)
    raw = subprocess.check_output(
        ["git", "-C", str(root), "--no-replace-objects", "cat-file", "-p", current], text=True,
    )
    assert f"parent {deleted}\n" in raw
    verdict = _archive(root, tmp_path, extra_paths=["note.txt"])
    assert verdict["commit"] == current
    assert verdict["status"] == "SCOPE_INCOMPLETE"
    assert verdict["verified"] is False


def test_legacy_graft_cannot_reclassify_old_deletion(tmp_path):
    root = repo(tmp_path)
    original = expect(root, "report-1")["commit"]
    git(root, "rm", "note.txt")
    git(root, "commit", "-m", "delete note")
    deleted = expect(root, "report-1")["commit"]
    git(root, "commit", "--allow-empty", "-m", "unrelated later commit")
    current = expect(root, "report-1")["commit"]
    (root / ".git" / "info" / "grafts").write_text(f"{current} {original}\n")
    raw = subprocess.check_output(
        ["git", "-C", str(root), "--no-replace-objects", "cat-file", "-p", current], text=True,
    )
    assert f"parent {deleted}\n" in raw
    verdict = _archive(root, tmp_path, extra_paths=["note.txt"])
    assert verdict["commit"] == current
    assert verdict["status"] == "SCOPE_INCOMPLETE"
    assert verdict["verified"] is False


def test_unreadable_current_tree_cannot_prove_deletion(tmp_path):
    root = repo(tmp_path)
    # Keep the deletion commit's tree nonempty: Git can synthesize the empty tree.
    (root / "kept.txt").write_text("keep\n")
    git(root, "add", "kept.txt")
    git(root, "commit", "-m", "keep another file")
    git(root, "rm", "note.txt")
    git(root, "commit", "-m", "delete note")
    tree = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD^{tree}"], text=True,
    ).strip()
    # Only corrupt this disposable fixture's loose tree object, never the product repository.
    (root / ".git" / "objects" / tree[:2] / tree[2:]).unlink()
    assert subprocess.run(
        ["git", "-C", str(root), "ls-tree", "HEAD"], capture_output=True,
    ).returncode != 0
    verdict = _archive(root, tmp_path, extra_paths=["note.txt"])
    assert verdict["status"] == "SCOPE_INCOMPLETE"
    assert verdict["verified"] is False


# --- rename records carry a second, un-prefixed path ----------------------------------------


def test_rename_keeps_both_full_paths(tmp_path):
    root = repo(tmp_path)
    (root / "old-name.txt").write_text("renamed content\n")
    git(root, "add", "old-name.txt")
    git(root, "commit", "-m", "old")
    git(root, "mv", "old-name.txt", "new-name.txt")
    paths = _worktree_paths(root)
    assert "new-name.txt" in paths
    assert "old-name.txt" in paths  # not truncated to "name.txt"
    assert not any(path in {"name.txt", "ld-name.txt"} for path in paths)
    verdict = _archive(root, tmp_path)
    assert verdict["status"] == "VERIFIED"
    assert [item["path"] for item in verdict["files"]] == ["new-name.txt"]
    assert {"path": "old-name.txt", "reason": "deleted"} in verdict["excluded"]


# --- symlinks are detected before they are followed ----------------------------------------


def test_symlinks_are_excluded_not_followed(tmp_path):
    root = repo(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("not part of the repo\n")
    (root / "in-repo-link").symlink_to("note.txt")
    (root / "outside-link").symlink_to(outside)
    (root / "sub").mkdir()
    (root / "sub" / "kept.txt").write_text("kept\n")
    (root / "dir-link").symlink_to("sub")
    verdict = _archive(root, tmp_path, extra_paths=["dir-link/kept.txt"])
    assert verdict["status"] == "VERIFIED" and verdict["verified"] is True
    archived_paths = {item["path"] for item in verdict["files"]}
    assert "in-repo-link" not in archived_paths and "outside-link" not in archived_paths
    assert "dir-link/kept.txt" not in archived_paths
    reasons = {item["path"]: item["reason"] for item in verdict["excluded"]}
    assert reasons["in-repo-link"] == "symlink"
    assert reasons["outside-link"] == "symlink"  # was outside_repo -> SCOPE_INCOMPLETE
    assert reasons["dir-link/kept.txt"] == "symlink"
    payload = tmp_path / "archive" / "report-1" / "payload"
    assert b"not part of the repo" not in b"".join(path.read_bytes() for path in payload.iterdir())
    # The symlink exclusion is verified by the observer: a real file in its place is a change.
    (root / "in-repo-link").unlink()
    (root / "in-repo-link").write_text("now a regular file\n")
    changed = observe_archive(
        root, tmp_path / "archive" / "report-1",
        expect=expect(root, "report-1", extra=["dir-link/kept.txt"]),
    )
    assert changed["status"] == "SOURCE_CHANGED"


# --- verify CLI must work with the same --archive that checkpoint used ---------------------


def _cli(*args):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "KANDO_MOCK": "1"}
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verified_handoff.py"), *args],
        capture_output=True, text=True, env=env, timeout=60,
    )


def test_verify_cli_accepts_the_checkpoint_archive_directory(tmp_path):
    root = repo(tmp_path)
    (root / "new.txt").write_text("uncommitted work\n")
    archive = tmp_path / "archive"
    commit = expect(root, "report-1")["commit"]
    made = _cli("checkpoint", "--repo", str(root), "--archive", str(archive), "--task", "KA-1",
                "--report", "report-1", "--kind", "delivery", "--run-attempt", "2")
    assert made.returncode == 0, made.stderr
    captured = json.loads(made.stdout)
    for target in (archive, archive / "report-1"):  # root and per-report directory both work
        checked = _cli(
            "verify", "--repo", str(root), "--archive", str(target), "--task", "KA-1",
            "--report", "report-1", "--commit", commit, "--run-attempt", "2",
            "--expect-path", *captured["frozen_paths"],
        )
        assert checked.returncode == 0, checked.stderr
        assert json.loads(checked.stdout)["status"] == "VERIFIED"
    empty = _cli("verify", "--repo", str(root), "--archive", str(tmp_path / "nowhere"), "--task", "KA-1",
                 "--report", "report-1", "--commit", commit, "--run-attempt", "2")
    assert empty.returncode == 2
    assert json.loads(empty.stdout)["status"] == "ARCHIVE_MISSING"
    assert archive_dir_for(archive, "report-1") == archive / "report-1"


# --- the verified outcome must exist before any "saved" artifact is written -----------------


def _run_job(tmp_path, monkeypatch, report):
    from core.evidence_continuity import evidence_continuity_path
    from kando.agent_runner import start_agent_job

    work = repo(tmp_path / "work")
    outbox = tmp_path / "outbox"
    outbox.mkdir()
    (tmp_path / "evidence").mkdir()
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("LUMOS_WALL_EVIDENCE_DIR", str(tmp_path / "evidence"))
    with patch("kando.agent_runner.run_agent_pipeline", return_value=report), patch(
        "kando.agent_runner._copy_cursor_bridge_snapshots_to_outbox"
    ):
        job_id = start_agent_job("goal", False, repo_root=work, outbox_dir=outbox)
        status_path = outbox / f"agent_status_{job_id}.json"
        deadline = time.monotonic() + 20.0
        status = {}
        while time.monotonic() < deadline:
            if status_path.is_file():
                status = json.loads(status_path.read_text(encoding="utf-8"))
                if status.get("phase") == "done":
                    break
            time.sleep(0.05)
    last = json.loads((outbox / "agent_last.json").read_text(encoding="utf-8"))
    journal = evidence_continuity_path(tmp_path)
    records = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines() if line.strip()]
    return status, last, records


def test_failed_archive_is_never_recorded_as_saved(tmp_path, monkeypatch):
    from core.evidence_continuity import OUTCOME_ERROR, PHASE_RESULT

    report = {"status": "ok", "task": "goal", "changed_files": ["ghost.txt"], "errors": []}
    status, last, records = _run_job(tmp_path, monkeypatch, report)
    assert status["status"] == "failed"
    assert last["status"] == "partial"  # agent_last.json was written from the verified outcome
    assert last["evidence"]["verified"] is False
    assert "evidence_unverified" in last["errors"]
    result = [record for record in records if record["phase"] == PHASE_RESULT]
    assert [record["outcome"] for record in result] == [OUTCOME_ERROR]
    assert result[0]["error"]["code"] == "evidence_unverified"


def _omit(archive, path):
    manifest_path = archive / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    kept_files = []
    for entry in manifest["files"]:
        if entry["path"] == path:
            payload = archive / "payload" / entry["sha256"]
            if payload.exists():
                payload.unlink()
        else:
            kept_files.append(entry)
    manifest["files"] = kept_files
    manifest["excluded"] = [entry for entry in manifest["excluded"] if entry["path"] != path]
    manifest["expected_paths"] = [entry["path"] for entry in kept_files]
    manifest["scope_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def _members(verdict):
    return {item["path"] for item in verdict["files"]} | {item["path"] for item in verdict["excluded"]}


def test_verified_archive_is_still_recorded_as_saved(tmp_path, monkeypatch):
    from core.evidence_continuity import OUTCOME_OK, PHASE_RESULT

    report = {"status": "ok", "task": "goal", "changed_files": [], "errors": []}
    status, last, records = _run_job(tmp_path, monkeypatch, report)
    assert status["status"] == "completed"
    assert last["status"] == "ok" and last["evidence"]["verified"] is True
    assert [record["outcome"] for record in records if record["phase"] == PHASE_RESULT] == [OUTCOME_OK]


# --- scope omission: E comes from the caller, M must equal E -----------------------------


def _omitted(tmp_path, root, path, extra=("note.txt",)):
    verdict = _archive(root, tmp_path, extra_paths=list(extra))
    assert verdict["status"] == "VERIFIED", verdict
    assert path in _members(verdict)
    archive = tmp_path / "archive" / "report-1"
    _omit(archive, path)
    again = observe_archive(root, archive, expect=expect(root, "report-1", extra=extra))
    assert again["status"] == "SCOPE_INCOMPLETE" and again["verified"] is False
    stored = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
    assert path not in {item["path"] for item in stored["files"]} | {
        item["path"] for item in stored["excluded"]
    }
    assert stored["scope_sha256"] == "0" * 64  # writable manifest metadata is not the expectation


def test_unstaged_modification_omission_is_incomplete(tmp_path):
    root = repo(tmp_path)
    (root / "note.txt").write_text("changed\n")
    _omitted(tmp_path, root, "note.txt")


def test_staged_modification_omission_is_incomplete(tmp_path):
    root = repo(tmp_path)
    (root / "note.txt").write_text("changed\n")
    git(root, "add", "note.txt")
    _omitted(tmp_path, root, "note.txt")


def test_untracked_addition_omission_is_incomplete(tmp_path):
    root = repo(tmp_path)
    (root / "added.txt").write_text("new\n")
    _omitted(tmp_path, root, "added.txt")


def test_staged_addition_omission_is_incomplete(tmp_path):
    root = repo(tmp_path)
    (root / "added.txt").write_text("new\n")
    git(root, "add", "--", "added.txt")
    _omitted(tmp_path, root, "added.txt")


def test_unstaged_deletion_omission_is_incomplete(tmp_path):
    root = repo(tmp_path)
    (root / "note.txt").unlink()
    _omitted(tmp_path, root, "note.txt")


def test_staged_deletion_omission_is_incomplete(tmp_path):
    root = repo(tmp_path)
    git(root, "rm", "note.txt")
    _omitted(tmp_path, root, "note.txt")


def _rename(root):
    (root / "old-name.txt").write_text("renamed content\n")
    git(root, "add", "old-name.txt")
    git(root, "commit", "-m", "old")
    git(root, "mv", "old-name.txt", "new-name.txt")


def test_rename_old_end_omission_is_incomplete(tmp_path):
    root = repo(tmp_path)
    _rename(root)
    _omitted(tmp_path, root, "old-name.txt", extra=())


def test_rename_new_end_omission_is_incomplete(tmp_path):
    root = repo(tmp_path)
    _rename(root)
    _omitted(tmp_path, root, "new-name.txt", extra=())


def test_content_secret_omission_is_incomplete(tmp_path):
    root = repo(tmp_path)
    (root / "plain.txt").write_text("token = None\n")
    verdict = _archive(root, tmp_path, extra_paths=["note.txt"])
    assert verdict["verified"] is False  # listed content exclusion is still not success
    archive = tmp_path / "archive" / "report-1"
    _omit(archive, "plain.txt")
    again = observe_archive(root, archive, expect=expect(root, "report-1"))
    assert again["status"] == "SCOPE_INCOMPLETE" and again["verified"] is False


def test_filename_secret_omission_is_incomplete(tmp_path):
    root = repo(tmp_path)
    (root / ".env").write_text("api_key=fixture-value\n")
    _omitted(tmp_path, root, ".env")
    payload = tmp_path / "archive" / "report-1" / "payload"
    blob = b"".join(path.read_bytes() for path in payload.iterdir()) if payload.is_dir() else b""
    assert b"fixture-value" not in blob


def test_symlink_omission_is_incomplete(tmp_path):
    root = repo(tmp_path)
    (root / "in-repo-link").symlink_to("note.txt")
    _omitted(tmp_path, root, "in-repo-link")


def test_clean_extra_omission_is_incomplete(tmp_path):
    root = repo(tmp_path)
    (root / "added.txt").write_text("dirty\n")
    _omitted(tmp_path, root, "note.txt")


def test_committed_modification_omission_is_incomplete(tmp_path):
    root = repo(tmp_path)
    base = expect(root, "report-1", extra=())["commit"]
    (root / "note.txt").write_text("committed change\n")
    git(root, "add", "note.txt")
    git(root, "commit", "-m", "change note")
    verdict = _archive(root, tmp_path, extra_paths=[])
    assert verdict["status"] == "VERIFIED" and verdict["files"] == []
    again = observe_archive(root, tmp_path / "archive" / "report-1", expect=expect(root, "report-1", extra=(), base=base))
    assert again["status"] == "SCOPE_INCOMPLETE" and again["verified"] is False


def test_committed_deletion_omission_is_incomplete(tmp_path):
    root = repo(tmp_path)
    base = expect(root, "report-1", extra=())["commit"]
    git(root, "rm", "note.txt")
    git(root, "commit", "-m", "delete note")
    verdict = _archive(root, tmp_path, extra_paths=[])
    assert verdict["status"] == "VERIFIED" and verdict["excluded"] == []
    again = observe_archive(root, tmp_path / "archive" / "report-1", expect=expect(root, "report-1", extra=(), base=base))
    assert again["status"] == "SCOPE_INCOMPLETE" and again["verified"] is False


def test_partial_manifest_subset_is_incomplete(tmp_path):
    root = repo(tmp_path)
    (root / "added.txt").write_text("one\n")
    (root / "other.txt").write_text("two\n")
    _omitted(tmp_path, root, "other.txt", extra=())


def test_untracked_file_arriving_during_observe_is_incomplete(tmp_path, monkeypatch):
    import lumos_board.evidence_archive as archive_mod

    root = repo(tmp_path)
    (root / "added.txt").write_text("one\n")
    verdict = _archive(root, tmp_path, extra_paths=[])
    assert verdict["status"] == "VERIFIED"
    real = archive_mod._caller_scope
    state = {"n": 0}

    def wrapped(repo_path, scope):
        state["n"] += 1
        if state["n"] == 2:
            (root / "later.txt").write_text("later\n")
        return real(repo_path, scope)

    monkeypatch.setattr(archive_mod, "_caller_scope", wrapped)
    again = observe_archive(root, tmp_path / "archive" / "report-1", expect=expect(root, "report-1", extra=()))
    assert again["status"] == "SCOPE_INCOMPLETE" and again["verified"] is False


def test_git_status_error_is_not_an_empty_verified_scope(tmp_path, monkeypatch):
    import lumos_board.evidence_archive as archive_mod

    root = repo(tmp_path)
    verdict = _archive(root, tmp_path, extra_paths=[])
    assert verdict["status"] == "VERIFIED" and verdict["files"] == [] and verdict["excluded"] == []
    monkeypatch.setattr(archive_mod, "_worktree_paths", lambda _repo: (_ for _ in ()).throw(archive_mod._ScopeError("status")))
    again = observe_archive(root, tmp_path / "archive" / "report-1", expect=expect(root, "report-1", extra=()))
    assert again["status"] == "SCOPE_INCOMPLETE" and again["verified"] is False


def test_literal_backslash_path_is_not_collapsed_into_a_slash_path(tmp_path):
    root = repo(tmp_path)
    (root / "dir").mkdir()
    (root / "dir" / "file.txt").write_text("slash\n")
    (root / "dir\\file.txt").write_text("backslash\n")
    verdict = _archive(root, tmp_path, extra_paths=[])
    assert verdict["status"] == "VERIFIED"
    assert {"dir/file.txt", "dir\\file.txt"} <= _members(verdict)
    archive = tmp_path / "archive" / "report-1"
    _omit(archive, "dir\\file.txt")
    again = observe_archive(root, archive, expect=expect(root, "report-1", extra=()))
    assert again["status"] == "SCOPE_INCOMPLETE" and again["verified"] is False


def test_empty_scope_verifies(tmp_path):
    root = repo(tmp_path)
    verdict = _archive(root, tmp_path, extra_paths=[])
    assert verdict["status"] == "VERIFIED" and verdict["verified"] is True
    assert verdict["files"] == [] and verdict["excluded"] == []


def test_rename_and_untracked_file_verify_together(tmp_path):
    root = repo(tmp_path)
    _rename(root)
    (root / "added.txt").write_text("untracked\n")
    verdict = _archive(root, tmp_path, extra_paths=[])
    assert verdict["status"] == "VERIFIED" and verdict["verified"] is True
    assert {"old-name.txt", "new-name.txt", "added.txt"} <= _members(verdict)


def test_manifest_scope_metadata_cannot_authorize_a_smaller_set(tmp_path):
    root = repo(tmp_path)
    (root / "added.txt").write_text("one\n")
    (root / "other.txt").write_text("two\n")
    _omitted(tmp_path, root, "other.txt", extra=())


def test_duplicate_manifest_path_is_corrupt(tmp_path):
    root = repo(tmp_path)
    (root / "added.txt").write_text("one\n")
    verdict = _archive(root, tmp_path, extra_paths=[])
    assert verdict["status"] == "VERIFIED"
    archive = tmp_path / "archive" / "report-1"
    manifest_path = archive / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"].append(dict(manifest["files"][0]))
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    again = observe_archive(root, archive, expect=expect(root, "report-1", extra=()))
    assert again["status"] == "ARCHIVE_CORRUPT" and again["verified"] is False


def test_overlapping_file_and_exclusion_is_corrupt(tmp_path):
    root = repo(tmp_path)
    (root / "added.txt").write_text("one\n")
    verdict = _archive(root, tmp_path, extra_paths=[])
    archive = tmp_path / "archive" / "report-1"
    manifest_path = archive / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["excluded"].append({"path": manifest["files"][0]["path"], "reason": "deleted"})
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    again = observe_archive(root, archive, expect=expect(root, "report-1", extra=()))
    assert again["status"] == "ARCHIVE_CORRUPT" and again["verified"] is False
    assert verdict["status"] == "VERIFIED"


def test_mismatched_base_is_incomplete(tmp_path):
    root = repo(tmp_path)
    tree = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD^{tree}"], text=True).strip()
    unrelated = subprocess.check_output(
        ["git", "-C", str(root), "commit-tree", tree, "-m", "unrelated"], text=True,
    ).strip()
    verdict = _archive(root, tmp_path, extra_paths=[])
    assert verdict["verified"] is True
    missing = observe_archive(
        root, tmp_path / "archive" / "report-1",
        expect=expect(root, "report-1", extra=(), base="0" * 40),
    )
    assert missing["status"] == "SCOPE_INCOMPLETE" and missing["verified"] is False
    foreign = observe_archive(
        root, tmp_path / "archive" / "report-1",
        expect=expect(root, "report-1", extra=(), base=unrelated),
    )
    assert foreign["status"] == "SCOPE_INCOMPLETE" and foreign["verified"] is False


def test_multi_commit_range_is_not_replaced_by_head_parent(tmp_path):
    root = repo(tmp_path)
    base = expect(root, "full", extra=())["commit"]
    (root / "first.txt").write_text("first\n")
    git(root, "add", "first.txt")
    git(root, "commit", "-m", "first")
    (root / "second.txt").write_text("second\n")
    git(root, "add", "second.txt")
    git(root, "commit", "-m", "second")
    partial = _archive(root, tmp_path, report_id="partial", extra_paths=["second.txt"])
    assert partial["status"] == "VERIFIED"
    assert "first.txt" not in _members(partial)
    again = observe_archive(
        root, tmp_path / "archive" / "partial",
        expect=expect(root, "partial", extra=(), base=base),
    )
    assert again["status"] == "SCOPE_INCOMPLETE" and again["verified"] is False
    full = _archive(root, tmp_path, report_id="full", extra_paths=[], scope_base=base)
    assert full["status"] == "VERIFIED"
    assert {"first.txt", "second.txt"} <= _members(full)


def test_literal_newline_and_leading_dash_paths_stay_distinct(tmp_path):
    root = repo(tmp_path)
    newline = "line\nname.txt"
    dash = "-leading.txt"
    (root / newline).write_text("newline\n")
    (root / dash).write_text("dash\n")
    verdict = _archive(root, tmp_path, extra_paths=[])
    assert verdict["status"] == "VERIFIED"
    assert {newline, dash} <= _members(verdict)
    archive = tmp_path / "archive" / "report-1"
    _omit(archive, newline)
    again = observe_archive(root, archive, expect=expect(root, "report-1", extra=()))
    assert again["status"] == "SCOPE_INCOMPLETE" and again["verified"] is False


def test_head_change_during_observe_is_not_verified(tmp_path, monkeypatch):
    import lumos_board.evidence_archive as archive_mod

    root = repo(tmp_path)
    (root / "added.txt").write_text("one\n")
    assert _archive(root, tmp_path, extra_paths=[])["status"] == "VERIFIED"
    real = archive_mod.head_commit
    state = {"n": 0}

    def wrapped(repo_path):
        state["n"] += 1
        value = real(repo_path)
        if state["n"] >= 3:
            return "f" * 40
        return value

    monkeypatch.setattr(archive_mod, "head_commit", wrapped)
    again = observe_archive(root, tmp_path / "archive" / "report-1", expect=expect(root, "report-1", extra=()))
    assert again["verified"] is False
    assert again["status"] in {"SOURCE_CHANGED", "SCOPE_INCOMPLETE"}


def test_scope_query_error_during_observe_is_not_verified(tmp_path, monkeypatch):
    import lumos_board.evidence_archive as archive_mod

    root = repo(tmp_path)
    (root / "added.txt").write_text("one\n")
    assert _archive(root, tmp_path, extra_paths=[])["status"] == "VERIFIED"
    real = archive_mod._worktree_paths
    state = {"n": 0}

    def wrapped(repo_path):
        state["n"] += 1
        if state["n"] >= 2:
            raise archive_mod._ScopeError("status failed")
        return real(repo_path)

    monkeypatch.setattr(archive_mod, "_worktree_paths", wrapped)
    again = observe_archive(root, tmp_path / "archive" / "report-1", expect=expect(root, "report-1", extra=()))
    assert again["status"] == "SCOPE_INCOMPLETE" and again["verified"] is False


def test_observe_without_authorized_scope_is_incomplete(tmp_path):
    root = repo(tmp_path)
    verdict = _archive(root, tmp_path, extra_paths=[])
    assert verdict["verified"] is True
    bare = expect(root, "report-1", extra=())
    del bare["scope"]
    again = observe_archive(root, tmp_path / "archive" / "report-1", expect=bare)
    assert again["status"] == "SCOPE_INCOMPLETE" and again["verified"] is False


# --- frozen capture snapshot: live status cannot drop the original members --------


def _checkpoint(root, archive, commit, *, base=""):
    args = ["checkpoint", "--repo", str(root), "--archive", str(archive), "--task", "KA-1",
            "--report", "report-1", "--kind", "delivery", "--run-attempt", "2"]
    if base:
        args.extend(["--base", base])
    made = _cli(*args)
    assert made.returncode == 0, made.stderr
    body = json.loads(made.stdout)
    assert body["commit"] == commit
    return body


def _verify(root, archive, commit, *, base="", paths=None, empty=False):
    args = ["verify", "--repo", str(root), "--archive", str(archive), "--task", "KA-1",
            "--report", "report-1", "--commit", commit, "--run-attempt", "2"]
    if empty:
        args.append("--expect-empty")
    if paths is not None:
        for item in paths:
            args.extend(["--expect-path", item])
    if base:
        args.extend(["--base", base])
    return _cli(*args)


def _forge_sidecar(archive, commit, paths, base):
    (Path(archive) / "caller-scope.json").write_text(json.dumps({
        "schema": "lumos.caller_scope.v1",
        "entries": [{
            "task_id": "KA-1", "report_id": "report-1", "commit": commit,
            "run_attempt": "2", "paths": list(paths), "base": base,
        }],
    }), encoding="utf-8")


def _wipe_members(archive_dir):
    manifest_path = archive_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = []
    manifest["excluded"] = []
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    payload = archive_dir / "payload"
    if payload.is_dir():
        for child in list(payload.iterdir()):
            if child.is_file():
                child.unlink()


def _assert_not_verified(checked):
    assert checked.returncode == 2
    body = json.loads(checked.stdout)
    assert body["status"] == "SCOPE_INCOMPLETE" and body["verified"] is False
    assert body["files"] == [] and body["excluded"] == []


def test_cli_empty_snapshot_verifies(tmp_path):
    root = repo(tmp_path)
    archive = tmp_path / "archive"
    commit = expect(root, "report-1", extra=())["commit"]
    made = _checkpoint(root, archive, commit)
    assert made["verified"] is True and made["files"] == [] and made["frozen_paths"] == []
    assert made["scope_base"] is None
    stored = json.loads((archive / "report-1" / "manifest.json").read_text(encoding="utf-8"))
    assert "frozen_paths" not in stored and "paths" not in stored and "scope_base" not in stored
    assert not (archive / "caller-scope.json").exists()
    checked = _verify(root, archive, commit, empty=True)
    assert checked.returncode == 0, checked.stderr
    assert json.loads(checked.stdout)["status"] == "VERIFIED"


def test_cli_untracked_shrink_with_forged_sidecar_is_not_verified(tmp_path):
    root = repo(tmp_path)
    (root / "new.txt").write_text("uncommitted work\n")
    archive = tmp_path / "archive"
    commit = expect(root, "report-1", extra=())["commit"]
    made = _checkpoint(root, archive, commit)
    assert made["frozen_paths"] == ["new.txt"]
    intact = _verify(root, archive, commit, paths=made["frozen_paths"])
    assert intact.returncode == 0 and json.loads(intact.stdout)["status"] == "VERIFIED"
    (root / "new.txt").unlink()
    _omit(archive / "report-1", "new.txt")
    _forge_sidecar(archive, commit, [], None)
    _assert_not_verified(_verify(root, archive, commit))


def test_cli_tracked_revert_with_forged_sidecar_is_not_verified(tmp_path):
    root = repo(tmp_path)
    (root / "note.txt").write_text("changed for the archive\n")
    archive = tmp_path / "archive"
    commit = expect(root, "report-1", extra=())["commit"]
    made = _checkpoint(root, archive, commit)
    assert made["frozen_paths"] == ["note.txt"]
    intact = _verify(root, archive, commit, paths=made["frozen_paths"])
    assert intact.returncode == 0
    git(root, "checkout", "--", "note.txt")
    _omit(archive / "report-1", "note.txt")
    _forge_sidecar(archive, commit, [], None)
    _assert_not_verified(_verify(root, archive, commit))


def test_cli_restored_deletion_with_forged_sidecar_is_not_verified(tmp_path):
    root = repo(tmp_path)
    (root / "note.txt").unlink()
    archive = tmp_path / "archive"
    commit = expect(root, "report-1", extra=())["commit"]
    made = _checkpoint(root, archive, commit)
    assert {"path": "note.txt", "reason": "deleted"} in made["excluded"]
    intact = _verify(root, archive, commit, paths=made["frozen_paths"])
    assert intact.returncode == 0
    git(root, "checkout", "--", "note.txt")
    _omit(archive / "report-1", "note.txt")
    _forge_sidecar(archive, commit, [], None)
    _assert_not_verified(_verify(root, archive, commit))


def test_cli_caller_untracked_contract_rejects_the_shrink(tmp_path):
    root = repo(tmp_path)
    (root / "new.txt").write_text("uncommitted work\n")
    archive = tmp_path / "archive"
    commit = expect(root, "report-1", extra=())["commit"]
    made = _checkpoint(root, archive, commit)
    (root / "new.txt").unlink()
    _omit(archive / "report-1", "new.txt")
    _forge_sidecar(archive, commit, [], None)
    _assert_not_verified(_verify(root, archive, commit, paths=made["frozen_paths"]))


def test_cli_caller_tracked_contract_rejects_the_revert(tmp_path):
    root = repo(tmp_path)
    (root / "note.txt").write_text("changed for the archive\n")
    archive = tmp_path / "archive"
    commit = expect(root, "report-1", extra=())["commit"]
    made = _checkpoint(root, archive, commit)
    git(root, "checkout", "--", "note.txt")
    _omit(archive / "report-1", "note.txt")
    _forge_sidecar(archive, commit, made["frozen_paths"], None)
    _assert_not_verified(_verify(root, archive, commit, paths=["note.txt"]))


def test_cli_caller_deletion_contract_rejects_the_restore(tmp_path):
    root = repo(tmp_path)
    (root / "note.txt").unlink()
    archive = tmp_path / "archive"
    commit = expect(root, "report-1", extra=())["commit"]
    made = _checkpoint(root, archive, commit)
    git(root, "checkout", "--", "note.txt")
    _omit(archive / "report-1", "note.txt")
    _assert_not_verified(_verify(root, archive, commit, paths=made["frozen_paths"]))


def test_frozen_untracked_path_survives_source_and_manifest_shrink(tmp_path):
    root = repo(tmp_path)
    (root / "new.txt").write_text("uncommitted work\n")
    verdict = _archive(root, tmp_path, extra_paths=[])
    assert verdict["status"] == "VERIFIED"
    (root / "new.txt").unlink()
    _omit(tmp_path / "archive" / "report-1", "new.txt")
    again = observe_archive(
        root, tmp_path / "archive" / "report-1",
        expect=expect(root, "report-1", extra=(), paths=["new.txt"]),
    )
    assert again["status"] == "SCOPE_INCOMPLETE" and again["verified"] is False


def test_frozen_tracked_edit_survives_revert_and_manifest_shrink(tmp_path):
    root = repo(tmp_path)
    (root / "note.txt").write_text("changed for the archive\n")
    assert _archive(root, tmp_path, extra_paths=[])["status"] == "VERIFIED"
    git(root, "checkout", "--", "note.txt")
    _omit(tmp_path / "archive" / "report-1", "note.txt")
    again = observe_archive(
        root, tmp_path / "archive" / "report-1",
        expect=expect(root, "report-1", extra=(), paths=["note.txt"]),
    )
    assert again["status"] == "SCOPE_INCOMPLETE" and again["verified"] is False


def test_frozen_deletion_survives_restore_and_manifest_shrink(tmp_path):
    root = repo(tmp_path)
    (root / "note.txt").unlink()
    verdict = _archive(root, tmp_path, extra_paths=[])
    assert {"path": "note.txt", "reason": "deleted"} in verdict["excluded"]
    git(root, "checkout", "--", "note.txt")
    _omit(tmp_path / "archive" / "report-1", "note.txt")
    again = observe_archive(
        root, tmp_path / "archive" / "report-1",
        expect=expect(root, "report-1", extra=(), paths=["note.txt"]),
    )
    assert again["status"] == "SCOPE_INCOMPLETE" and again["verified"] is False


def test_range_deletion_before_head_parent_verifies(tmp_path):
    root = repo(tmp_path)
    base = expect(root, "report-1", extra=())["commit"]
    git(root, "rm", "note.txt")
    git(root, "commit", "-m", "delete note")
    (root / "later.txt").write_text("later\n")
    git(root, "add", "later.txt")
    git(root, "commit", "-m", "add later")
    verdict = _archive(root, tmp_path, extra_paths=[], scope_base=base)
    assert verdict["status"] == "VERIFIED" and verdict["verified"] is True
    assert {"path": "note.txt", "reason": "deleted"} in verdict["excluded"]
    assert "later.txt" in {item["path"] for item in verdict["files"]}
    frozen = ["later.txt", "note.txt"]
    assert observe_archive(
        root, tmp_path / "archive" / "report-1",
        expect=expect(root, "report-1", extra=(), paths=frozen, base=base),
    )["verified"] is True
    (root / "note.txt").write_text("back as a file\n")
    assert observe_archive(
        root, tmp_path / "archive" / "report-1",
        expect=expect(root, "report-1", extra=(), paths=frozen, base=base),
    )["status"] == "SOURCE_CHANGED"
    (root / "note.txt").unlink()
    (root / "note.txt").symlink_to("later.txt")
    assert observe_archive(
        root, tmp_path / "archive" / "report-1",
        expect=expect(root, "report-1", extra=(), paths=frozen, base=base),
    )["status"] == "SOURCE_CHANGED"
    (root / "note.txt").unlink()
    (root / "note.txt").mkdir()
    assert observe_archive(
        root, tmp_path / "archive" / "report-1",
        expect=expect(root, "report-1", extra=(), paths=frozen, base=base),
    )["status"] == "SOURCE_CHANGED"


def test_range_rename_before_head_parent_verifies(tmp_path):
    root = repo(tmp_path)
    base = expect(root, "report-1", extra=())["commit"]
    git(root, "mv", "note.txt", "renamed.txt")
    git(root, "commit", "-m", "rename note")
    (root / "later.txt").write_text("later\n")
    git(root, "add", "later.txt")
    git(root, "commit", "-m", "add later")
    verdict = _archive(root, tmp_path, extra_paths=[], scope_base=base)
    assert verdict["status"] == "VERIFIED" and verdict["verified"] is True
    assert {"path": "note.txt", "reason": "deleted"} in verdict["excluded"]
    assert {"later.txt", "renamed.txt"} <= {item["path"] for item in verdict["files"]}


def test_deletion_before_pinned_base_is_not_range_evidence(tmp_path):
    root = repo(tmp_path)
    git(root, "rm", "note.txt")
    git(root, "commit", "-m", "delete before the pinned base")
    base = expect(root, "report-1", extra=())["commit"]
    (root / "later.txt").write_text("later\n")
    git(root, "add", "later.txt")
    git(root, "commit", "-m", "add later")
    verdict = _archive(root, tmp_path, extra_paths=["note.txt"], scope_base=base)
    assert verdict["status"] == "SCOPE_INCOMPLETE" and verdict["verified"] is False


def test_cli_range_deletion_readback_uses_the_caller_contract(tmp_path):
    root = repo(tmp_path)
    (root / "kept.txt").write_text("original\n")
    git(root, "add", "kept.txt")
    git(root, "commit", "-m", "base files")
    base = expect(root, "report-1", extra=())["commit"]
    git(root, "rm", "note.txt")
    git(root, "commit", "-m", "delete note")
    (root / "kept.txt").write_text("changed\n")
    git(root, "add", "kept.txt")
    git(root, "commit", "-m", "change kept")
    archive = tmp_path / "archive"
    head = expect(root, "report-1", extra=())["commit"]
    made = _checkpoint(root, archive, head, base=base)
    assert made["status"] == "VERIFIED" and made["scope_base"] == base
    assert {"path": "note.txt", "reason": "deleted"} in made["excluded"]
    assert "kept.txt" in {item["path"] for item in made["files"]}
    intact = _verify(root, archive, head, paths=made["frozen_paths"], base=base)
    assert intact.returncode == 0, intact.stderr
    _wipe_members(archive / "report-1")
    _forge_sidecar(archive, head, [], head)
    # Same task/report/commit. The forged sidecar is not a contract.
    _assert_not_verified(_verify(root, archive, head))
    # The caller's real base still rejects the emptied archive.
    _assert_not_verified(_verify(root, archive, head, base=base))
    _assert_not_verified(_verify(root, archive, head, paths=made["frozen_paths"], base=base))
