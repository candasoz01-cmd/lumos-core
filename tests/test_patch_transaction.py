from __future__ import annotations

import threading
from pathlib import Path


from core.patch_model import PatchMetadata, PatchProposal, PatchFingerprint
from core.patch_registry import clear_registry, get_record
from core.patch_transaction import apply_with_transaction


def _make_proposal(target: Path, original: str, proposed: str) -> PatchProposal:
    target.write_text(original, encoding="utf-8")
    meta = PatchMetadata(
        reason="test",
        caller="test_patch_transaction",
        source="test",
        user_initiated=True,
        requires_review=False,
        protected_target=False,
    )
    fp = PatchFingerprint.from_text(original)
    return PatchProposal(
        id="test-proposal",
        target_path=target,
        operation="replace_file",
        original_fingerprint=fp,
        original_text=original,
        proposed_text=proposed,
        metadata=meta,
        diff_text=None,
    )


def test_atomic_write(tmp_path: Path):
    clear_registry()
    target = tmp_path / "file.txt"
    proposal = _make_proposal(target, "v1", "v2")

    apply_with_transaction(proposal)

    assert target.read_text(encoding="utf-8") == "v2"
    rec = get_record(proposal.id)
    assert rec is not None
    assert rec.state == "APPLIED"
    assert rec.apply_result is not None
    assert rec.apply_result.get("status") == "applied"
    assert "apply_started_at" in rec.apply_result
    assert "apply_finished_at" in rec.apply_result
    assert rec.apply_result.get("conflict_detected") is False


def test_fingerprint_conflict_rejected(tmp_path: Path):
    clear_registry()
    target = tmp_path / "file.txt"
    proposal = _make_proposal(target, "v1", "v2")

    # Proposal üretildikten sonra dosya değişsin.
    target.write_text("other", encoding="utf-8")

    apply_with_transaction(proposal)

    rec = get_record(proposal.id)
    assert rec is not None
    assert rec.state == "FAILED_CONFLICT"
    assert rec.apply_result is not None
    assert rec.apply_result.get("conflict_detected") is True
    assert "fingerprint_conflict" in rec.apply_result.get("message", "")


def test_lock_release_allows_sequential_applies(tmp_path: Path):
    clear_registry()
    target = tmp_path / "file.txt"
    p1 = _make_proposal(target, "v1", "v2")

    apply_with_transaction(p1)
    assert target.read_text(encoding="utf-8") == "v2"

    # Yeni proposal v2 -> v3
    from core.patch_model import PatchFingerprint

    fp2 = PatchFingerprint.from_text("v2")
    p2 = PatchProposal(
        id="test-proposal-2",
        target_path=target,
        operation="replace_file",
        original_fingerprint=fp2,
        original_text="v2",
        proposed_text="v3",
        metadata=p1.metadata,
        diff_text=None,
    )

    apply_with_transaction(p2)
    assert target.read_text(encoding="utf-8") == "v3"


def test_concurrent_patch_same_file_conflict(tmp_path: Path):
    clear_registry()
    target = tmp_path / "file.txt"
    target.write_text("base", encoding="utf-8")

    from core.patch_model import PatchFingerprint
    from core.patch_model import PatchMetadata

    fp = PatchFingerprint.from_text("base")
    meta = PatchMetadata(
        reason="test-concurrent",
        caller="test_patch_transaction",
        source="test",
        user_initiated=True,
        requires_review=False,
        protected_target=False,
    )

    p1 = PatchProposal(
        id="p1",
        target_path=target,
        operation="replace_file",
        original_fingerprint=fp,
        original_text="base",
        proposed_text="v1",
        metadata=meta,
        diff_text=None,
    )
    p2 = PatchProposal(
        id="p2",
        target_path=target,
        operation="replace_file",
        original_fingerprint=fp,
        original_text="base",
        proposed_text="v2",
        metadata=meta,
        diff_text=None,
    )

    def t1():
        apply_with_transaction(p1)

    def t2():
        apply_with_transaction(p2)

    th1 = threading.Thread(target=t1)
    th2 = threading.Thread(target=t2)
    th1.start()
    th2.start()
    th1.join()
    th2.join()

    final = target.read_text(encoding="utf-8")
    assert final in ("v1", "v2")

    r1 = get_record("p1")
    r2 = get_record("p2")
    states = {r1.state if r1 else None, r2.state if r2 else None}
    # Bir tanesi APPLIED olmalı, diğeri FAILED_CONFLICT veya FAILED
    assert "APPLIED" in states
    assert "FAILED_CONFLICT" in states or "FAILED" in states

