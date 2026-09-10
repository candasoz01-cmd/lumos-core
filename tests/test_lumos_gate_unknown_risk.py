"""F6: unclassified risk is fail-closed (pending + audit), never silent approved."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from kando_runtime.lumos_audit import LumosAuditCollector
from kando_runtime.lumos_gate import (
    _PENDING_APPROVAL_RISKS,
    _risk_gate_execution_mode,
    classify_risk,
    execute_approved_pending_record,
    run_lumos_gate,
    validate_pending_for_approval,
)

UNKNOWN_PAYLOAD = "TARGET: notes.txt\ngünaydın\n"
LOW_PAYLOAD = "TARGET: notes.txt\nözet çıkar\n"
HIGH_PAYLOAD = "TARGET: notes.txt\nbu dosyayı sil\n"


@pytest.fixture(autouse=True)
def _no_live_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def _gate(
    tmp_path: Path,
    payload: str,
    *,
    approval_granted: bool = False,
    audit: LumosAuditCollector | None = None,
) -> dict[str, Any]:
    (tmp_path / ".lumos").mkdir(exist_ok=True)
    (tmp_path / "notes.txt").write_text("x\n", encoding="utf-8")
    return run_lumos_gate(
        "direct_patch",
        payload,
        repo_root=tmp_path,
        approval_granted=approval_granted,
        audit=audit,
    )


def test_classify_risk_keywordless_text_is_unknown() -> None:
    assert classify_risk("günaydın", None) == "unknown"
    assert classify_risk("özet çıkar", None) == "low"
    assert classify_risk("bu dosyayı sil", None) == "high"


def test_unknown_risk_execution_mode_is_pending_approval() -> None:
    assert _risk_gate_execution_mode("unknown") == "pending_approval"
    assert "unknown" in _PENDING_APPROVAL_RISKS


def test_unknown_risk_gate_is_pending_not_approved(tmp_path: Path) -> None:
    out = _gate(tmp_path, UNKNOWN_PAYLOAD)
    assert out.get("status") != "approved"
    assert out.get("_kind") != "run"
    assert out.get("execution_mode") == "pending_approval"
    assert out.get("risk_level") == "unknown"
    assert out.get("final_decision") == "await_user_approval"
    assert out.get("gate_complete") is True
    hb = out.get("http_body") or {}
    assert hb.get("requires_approval") is True
    assert hb.get("risk_level") == "unknown"
    pr = out.get("pending_approval_record")
    assert isinstance(pr, dict)
    assert pr.get("risk_level") == "unknown"
    assert pr.get("execution_mode") == "pending_approval"


def test_unknown_risk_always_attaches_audit_even_without_collector(
    tmp_path: Path,
) -> None:
    out = _gate(tmp_path, UNKNOWN_PAYLOAD, audit=None)
    entry = out.get("lumos_audit_log")
    assert isinstance(entry, dict)
    assert entry.get("schema_version") == "lumos.audit_log.v1"
    assert entry.get("blocked") is True
    assert entry.get("reason") == "unknown_risk"
    assert entry.get("execution_result") == "pending_approval"
    assert entry.get("execution_kind") == "pending_approval"
    assert entry.get("log_id")


def test_unknown_risk_audit_reason_when_collector_passed(tmp_path: Path) -> None:
    audit = LumosAuditCollector(log_id="f6-unknown")
    out = _gate(tmp_path, UNKNOWN_PAYLOAD, audit=audit)
    entry = out.get("lumos_audit_log") or {}
    assert entry.get("log_id") == "f6-unknown"
    assert entry.get("reason") == "unknown_risk"
    assert entry.get("blocked") is True


def test_high_risk_still_pending_with_pending_approval_reason(tmp_path: Path) -> None:
    audit = LumosAuditCollector(log_id="f6-high")
    out = _gate(tmp_path, HIGH_PAYLOAD, audit=audit)
    assert out.get("execution_mode") == "pending_approval"
    assert out.get("risk_level") == "high"
    entry = out.get("lumos_audit_log") or {}
    assert entry.get("reason") == "pending_approval"


def test_low_risk_still_reaches_execute_bundle(tmp_path: Path) -> None:
    out = _gate(tmp_path, LOW_PAYLOAD)
    assert out.get("_kind") == "run"
    assert out.get("risk") == "low"
    assert out.get("execution_mode") != "pending_approval"


def test_unknown_risk_with_prior_approval_is_not_pending(tmp_path: Path) -> None:
    out = _gate(tmp_path, UNKNOWN_PAYLOAD, approval_granted=True)
    assert out.get("_kind") == "run"
    assert out.get("risk") == "unknown"
    assert out.get("execution_mode") != "pending_approval"


def test_validate_pending_accepts_unknown_and_rejects_medium() -> None:
    base = {
        "schema_version": "lumos.pending_approval.v1",
        "final_decision": "await_user_approval",
        "policy_ok": True,
        "execution_mode": "pending_approval",
        "execution_plan": {"steps": [{"type": "patch", "file": "a.txt", "content": "hi"}]},
        "reasoning_snapshot": {"source": "test"},
        "normalized_task": {"target_rel": "a.txt"},
    }
    validate_pending_for_approval({**base, "risk_level": "unknown"})
    validate_pending_for_approval({**base, "risk_level": "high"})
    with pytest.raises(ValueError, match="high veya unknown"):
        validate_pending_for_approval({**base, "risk_level": "medium"})


def test_execute_approved_unknown_pending_runs_recorded_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _allow(
        step: dict,
        parent: dict,
        *,
        fallback_marker_key: str = "llm_substep_validation",
    ) -> dict:
        return {"ok": True, "reason": "", "risk_hint": "low"}

    monkeypatch.setattr("kando_runtime.lumos_gate.validate_substep_with_llm", _allow)
    (tmp_path / "notes").mkdir()
    target = tmp_path / "notes" / "hello.txt"
    target.write_text("old\n", encoding="utf-8")
    calls: list[str] = []

    def _run_direct(instr: str) -> dict:
        calls.append(instr)
        return {"execution_result": "patch_applied", "detail": ""}

    out = execute_approved_pending_record(
        {
            "schema_version": "lumos.pending_approval.v1",
            "policy_ok": True,
            "final_decision": "await_user_approval",
            "risk_level": "unknown",
            "execution_mode": "pending_approval",
            "mode": "direct_patch",
            "original_payload": UNKNOWN_PAYLOAD,
            "execution_plan": {
                "steps": [
                    {
                        "type": "patch",
                        "file": "notes/hello.txt",
                        "content": "günaydın\n",
                    }
                ]
            },
            "reasoning_snapshot": {"source": "test"},
            "normalized_task": {"target_rel": "notes/hello.txt"},
        },
        run_direct=_run_direct,
        start_agent=lambda _g, _a: "job-unused",
        repo_root=tmp_path,
    )
    assert calls
    assert out.get("blocked") is not True
    assert out.get("execution_mode") != "pending_approval"
    hb = out.get("http_body") or {}
    assert hb.get("risk_level") == "unknown"
