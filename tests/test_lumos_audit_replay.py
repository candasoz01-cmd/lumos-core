"""Lumos audit JSONL + replay + karşılaştırma."""

from __future__ import annotations

from pathlib import Path

import kando_runtime.lumos_gate as lumos_gate_mod
from kando_runtime.lumos_audit import (
    LumosAuditCollector,
    append_audit_log,
    compare_audit_entries,
    find_audit_entry,
    plan_execution_failed,
)
from kando_runtime.lumos_gate import execute_plan, replay_lumos_task


def test_append_and_find_audit_entry(tmp_path: Path) -> None:
    c = LumosAuditCollector(log_id="e1")
    c.set_input("direct_patch", "TARGET: a.txt\nx\n")
    c.set_plan({"steps": []})
    c.set_step_results([])
    c.set_summary(
        blocked=False,
        reason="",
        execution_result="noop",
        execution_kind="plan",
    )
    ent = c.to_log_entry()
    append_audit_log(tmp_path, ent)
    found = find_audit_entry(tmp_path, "e1")
    assert found is not None
    assert found["log_id"] == "e1"
    assert found["input"]["mode"] == "direct_patch"


def test_compare_dry_run_ignores_execution_result() -> None:
    a = {"blocked": False, "execution_result": "patch_applied", "step_decisions": []}
    b = {"blocked": False, "execution_result": "replay_skipped", "step_decisions": []}
    m, d = compare_audit_entries(a, b, dry_run=True)
    assert m is True
    assert d == []
    m2, d2 = compare_audit_entries(a, b, dry_run=False)
    assert m2 is False
    assert any("execution_result" in x for x in d2)


def test_compare_detects_blocked_mismatch() -> None:
    a = {
        "blocked": True,
        "execution_result": "substep_llm_blocked",
        "step_decisions": [{"decision": "blocked", "source": "llm"}],
    }
    b = {
        "blocked": False,
        "execution_result": "plan_completed",
        "step_decisions": [{"decision": "allowed", "source": "policy"}],
    }
    m, d = compare_audit_entries(a, b, dry_run=True)
    assert m is False
    assert any("blocked" in x for x in d)


def test_execute_plan_fills_audit_single_step(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text("a", encoding="utf-8")
    audit = LumosAuditCollector(log_id="p1")

    def rd(instr: str) -> dict:
        return {"execution_result": "patch_applied", "detail": ""}

    plan = {
        "steps": [{"type": "patch", "file": "f.txt", "content": "# özet\nb"}],
        "detail": "",
    }
    k, ex, _ = execute_plan(
        plan,
        run_direct=rd,
        start_agent=lambda g, a: "j",
        run_agent_auto=None,
        repo_root=tmp_path,
        parent_task=None,
        audit=audit,
    )
    assert k == "plan"
    ent = audit.to_log_entry()
    assert ent["blocked"] is False
    assert plan_execution_failed(str(ex.get("execution_result") or "")) is False
    assert len(ent["step_decisions"]) == 1
    assert ent["step_decisions"][0]["decision"] == "allowed"
    assert ent["llm_checks"]["plan"] == []
    assert ent["llm_checks"]["execution"] == []


def test_replay_skips_real_executor(monkeypatch: object, tmp_path: Path) -> None:
    (tmp_path / "g.txt").write_text("z", encoding="utf-8")

    def rd(instr: str) -> dict:
        raise AssertionError("executor must not run in replay")

    plan = {
        "steps": [{"type": "patch", "file": "g.txt", "content": "# özet\nq"}],
        "detail": "",
    }

    def fake_gate(mode: str, payload: str, **kwargs: object) -> dict:
        audit = kwargs.get("audit")
        replay_mode = kwargs.get("replay_mode")
        assert replay_mode is True
        norm = lumos_gate_mod.normalize_request(mode, payload)
        norm = lumos_gate_mod.enrich_normalized_with_target_file(norm, tmp_path)
        reasoning = {
            "source": "heuristic",
            "summary": "t",
            "llm_mode": "direct_patch",
            "generated_content": "q",
        }
        ctx = lumos_gate_mod.GateContext()
        ctx.policy_ok = True
        ctx.reasoning_summary = "t"
        ctx.execution_mode = "plan"
        return {
            "_kind": "run",
            "policy_ok": True,
            "gate_complete": False,
            "plan": plan,
            "ctx": ctx,
            "norm": norm,
            "reasoning": reasoning,
            "risk": "low",
            "mode": mode,
            "payload": payload,
            "approval_granted": False,
            "repo_root": tmp_path,
            "audit": audit,
            "replay_mode": replay_mode,
        }

    monkeypatch.setattr(lumos_gate_mod, "run_lumos_gate", fake_gate)

    def fake_llm(
        step: dict,
        parent: dict,
        *,
        fallback_marker_key: str = "llm_substep_validation",
    ) -> dict:
        return {"ok": True, "reason": "", "risk_hint": "low"}

    monkeypatch.setattr(lumos_gate_mod, "validate_substep_with_llm", fake_llm)

    orig = LumosAuditCollector(log_id="orig")
    orig.set_input("direct_patch", "TARGET: g.txt\n# özet\nq\n")
    pt = {
        "mode": "direct_patch",
        "payload": "TARGET: g.txt\n# özet\nq\n",
        "reasoning_summary": "t",
        "intent": "patch",
        "target_rel": "g.txt",
        "llm_mode": "direct_patch",
        "reasoning_source": "heuristic",
    }
    execute_plan(
        plan,
        run_direct=lambda i: {"execution_result": "patch_applied", "detail": ""},
        start_agent=lambda g, a: "j",
        run_agent_auto=None,
        repo_root=tmp_path,
        parent_task=pt,
        audit=orig,
    )
    entry = orig.to_log_entry()
    res = replay_lumos_task(entry, repo_root=tmp_path)
    assert res["replay"] is True
    assert res["match"] is True, res.get("differences")
    assert res["differences"] == []
    steps = (res.get("new_log") or {}).get("steps") or []
    assert any(
        isinstance(s, dict) and s.get("execution_result") == "replay_skipped" for s in steps
    )
