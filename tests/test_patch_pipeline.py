from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.patch_model import compute_unified_diff, PatchMetadata
from core.patch_pipeline import (
    ProtectedApplyForbidden,
    apply_patch,
    propose_text_patch,
    run_sandbox_validation,
    validate_proposal_against_filesystem,
)
from core.patch_registry import (
    clear_registry,
    get_record,
    mark_ready_for_apply,
    rollback_patch,
)


def test_compute_unified_diff_shows_change():
    before = "a\nb\n"
    after = "a\nc\n"
    diff = compute_unified_diff(before, after, from_path="before.txt", to_path="after.txt")
    assert "--- before.txt" in diff
    assert "+++ after.txt" in diff
    assert "-b" in diff
    assert "+c" in diff


def test_propose_text_patch_creates_diff_and_metadata(tmp_path):
    clear_registry()
    target = tmp_path / "example.txt"
    target.write_text("old\n", encoding="utf-8")

    proposal = propose_text_patch(
        target,
        "new\n",
        reason="update example",
        caller="test_propose_text_patch",
        source="test",
        user_initiated=True,
        protected_target=False,
    )

    assert proposal.target_path == target
    assert proposal.operation == "replace_file"
    assert proposal.original_text == "old\n"
    assert proposal.proposed_text == "new\n"
    assert proposal.diff_text is not None
    assert "old" in proposal.diff_text
    assert "new" in proposal.diff_text
    assert isinstance(proposal.metadata, PatchMetadata)
    assert proposal.metadata.reason == "update example"
    assert proposal.metadata.caller == "test_propose_text_patch"
    assert proposal.metadata.source == "test"
    assert proposal.metadata.user_initiated is True
    assert proposal.metadata.protected_target is False
    assert proposal.metadata.requires_review is False


def test_validate_proposal_ok_when_file_unchanged(tmp_path):
    clear_registry()
    target = tmp_path / "file.txt"
    target.write_text("v1\n", encoding="utf-8")

    proposal = propose_text_patch(
        target,
        "v2\n",
        reason="change",
        caller="test_validate_proposal_ok_when_file_unchanged",
    )
    result = validate_proposal_against_filesystem(proposal)
    assert result.status == "ok"
    assert result.protected_target is proposal.metadata.protected_target
    rec = get_record(proposal.id)
    assert rec is not None
    assert rec.state == "VALIDATED"


def test_validate_proposal_fingerprint_mismatch_when_file_changed(tmp_path):
    clear_registry()
    target = tmp_path / "file.txt"
    target.write_text("v1\n", encoding="utf-8")

    proposal = propose_text_patch(
        target,
        "v2\n",
        reason="change",
        caller="test_validate_proposal_fingerprint_mismatch_when_file_changed",
    )

    # Dosya öneri üretildikten sonra değişirse fingerprint uyuşmaz.
    target.write_text("other\n", encoding="utf-8")

    result = validate_proposal_against_filesystem(proposal)
    assert result.status == "fingerprint_mismatch"
    assert result.requires_review is True
    rec = get_record(proposal.id)
    # Drift durumunda lifecycle state PROPOSED olarak kalır.
    assert rec is not None
    assert rec.state == "PROPOSED"


def test_run_sandbox_validation_writes_to_temp_file_without_touching_target(tmp_path):
    clear_registry()
    target = tmp_path / "file.txt"
    target.write_text("v1\n", encoding="utf-8")

    proposal = propose_text_patch(
        target,
        "v2\n",
        reason="change",
        caller="test_run_sandbox_validation_writes_to_temp_file_without_touching_target",
    )

    temp_path = run_sandbox_validation(proposal)
    assert temp_path.is_file()
    assert temp_path.read_text(encoding="utf-8") == "v2\n"
    # Hedef dosya sandbox validation sırasında değişmemiş olmalı.
    assert target.read_text(encoding="utf-8") == "v1\n"
    rec = get_record(proposal.id)
    assert rec is not None
    assert rec.sandbox_result is not None
    assert rec.sandbox_result["status"] == "ok"


def test_apply_patch_allows_non_protected_without_review(tmp_path):
    clear_registry()
    target = tmp_path / "file.txt"
    target.write_text("v1\n", encoding="utf-8")

    proposal = propose_text_patch(
        target,
        "v2\n",
        reason="change",
        caller="test_apply_patch_allows_non_protected_without_review",
        protected_target=False,
    )

    apply_patch(proposal, assume_reviewed=True, allow_protected_apply=False)
    assert target.read_text(encoding="utf-8") == "v2\n"
    rec = get_record(proposal.id)
    assert rec is not None
    assert rec.state == "APPLIED"
    assert rec.apply_result is not None
    assert rec.apply_result["status"] == "applied"


def test_apply_patch_blocks_protected_without_explicit_gate(tmp_path):
    clear_registry()
    target = tmp_path / "core.json"
    target.write_text("v1\n", encoding="utf-8")

    proposal = propose_text_patch(
        target,
        "v2\n",
        reason="change",
        caller="test_apply_patch_blocks_protected_without_explicit_gate",
        protected_target=True,
    )

    with pytest.raises(ProtectedApplyForbidden):
        apply_patch(proposal, assume_reviewed=True, allow_protected_apply=False)


def test_apply_patch_requires_review_when_flagged(tmp_path):
    clear_registry()
    target = tmp_path / "core.json"
    target.write_text("v1\n", encoding="utf-8")

    # protected_target=True → requires_review=True
    proposal = propose_text_patch(
        target,
        "v2\n",
        reason="change",
        caller="test_apply_patch_requires_review_when_flagged",
        protected_target=True,
    )

    # allow_protected_apply=True olsa bile review işareti varsa assume_reviewed=False iken bloklanmalı.
    with pytest.raises(ProtectedApplyForbidden):
        apply_patch(proposal, assume_reviewed=False, allow_protected_apply=True)

    # Review sonrası üst katman assume_reviewed=True ile ve READY_FOR_APPLY state'i ile çağırabilir.
    mark_ready_for_apply(proposal.id)
    apply_patch(proposal, assume_reviewed=True, allow_protected_apply=True)
    assert target.read_text(encoding="utf-8") == "v2\n"
    rec = get_record(proposal.id)
    assert rec is not None
    assert rec.state == "APPLIED"


def test_protected_apply_requires_ready_for_apply_state(tmp_path):
    clear_registry()
    target = tmp_path / "core.json"
    target.write_text("v1\n", encoding="utf-8")

    proposal = propose_text_patch(
        target,
        "v2\n",
        reason="change",
        caller="test_protected_apply_requires_ready_for_apply_state",
        protected_target=True,
    )
    # VALIDATED ama READY_FOR_APPLY değilken apply denemesi engellenir.
    _ = validate_proposal_against_filesystem(proposal)

    with pytest.raises(ProtectedApplyForbidden):
        apply_patch(proposal, assume_reviewed=True, allow_protected_apply=True)


def test_rollback_after_applied_patch(tmp_path):
    clear_registry()
    target = tmp_path / "file.txt"
    target.write_text("v1\n", encoding="utf-8")

    proposal = propose_text_patch(
        target,
        "v2\n",
        reason="change",
        caller="test_rollback_after_applied_patch",
        protected_target=False,
    )

    apply_patch(proposal, assume_reviewed=True, allow_protected_apply=False)
    assert target.read_text(encoding="utf-8") == "v2\n"

    rec_applied = get_record(proposal.id)
    assert rec_applied is not None
    assert rec_applied.state == "APPLIED"

    rec_rolled = rollback_patch(proposal.id)
    assert rec_rolled is not None
    assert rec_rolled.state == "ROLLED_BACK"
    assert target.read_text(encoding="utf-8") == "v1\n"


def test_rollback_aborts_on_content_drift(tmp_path):
    clear_registry()
    target = tmp_path / "file.txt"
    target.write_text("v1\n", encoding="utf-8")

    proposal = propose_text_patch(
        target,
        "v2\n",
        reason="change",
        caller="test_rollback_aborts_on_content_drift",
        protected_target=False,
    )

    apply_patch(proposal, assume_reviewed=True, allow_protected_apply=False)
    assert target.read_text(encoding="utf-8") == "v2\n"

    # Dosya applied içerikten farklı hale gelirse rollback hata ile sonuçlanır.
    target.write_text("other\n", encoding="utf-8")
    rec = rollback_patch(proposal.id)
    assert rec is not None
    assert rec.apply_result is not None
    assert rec.apply_result["status"] == "error"
    assert "drift" in rec.apply_result["message"]

