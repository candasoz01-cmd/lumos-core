"""Plan adımları: tümü önce alt-gate; sonradan yüksek risk varsa hiçbiri yürütülmez."""

from __future__ import annotations

from pathlib import Path

import kando_runtime.lumos_gate as lumos_gate_mod
from kando_runtime.lumos_gate import execute_plan, run_lumos_gate


def _sample_parent_task() -> dict:
    return {
        "mode": "direct_patch",
        "payload": "TARGET: README.md\nÖzeti güncelle\n",
        "reasoning_summary": "README için kısa özet güncellemesi",
        "intent": "summary_update",
        "target_rel": "README.md",
        "llm_mode": "direct_patch",
        "reasoning_source": "heuristic",
    }


def test_multistep_preflight_blocks_before_first_patch_when_later_step_high_risk(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def run_direct(instr: str) -> dict:
        calls.append(instr)
        return {"execution_result": "patch_applied", "detail": ""}

    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
    plan = {
        "steps": [
            {"type": "patch", "file": "a.txt", "content": "# safe"},
            {
                "type": "patch",
                "file": "a.txt",
                "content": "# tail",
                "task": "dosyayı sil",
            },
        ],
        "detail": "",
    }
    kind, ex, _jid = execute_plan(
        plan,
        run_direct=run_direct,
        start_agent=lambda g, a: "job1",
        run_agent_auto=None,
        repo_root=tmp_path,
    )
    assert kind == "plan"
    assert ex is not None
    assert ex.get("execution_result") == "substep_gate_blocked"
    assert calls == []


def test_approval_granted_allows_high_risk_substeps(tmp_path: Path) -> None:
    calls: list[str] = []

    def run_direct(instr: str) -> dict:
        calls.append(instr)
        return {"execution_result": "patch_applied", "detail": ""}

    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
    plan = {
        "steps": [
            {"type": "patch", "file": "a.txt", "content": "# a"},
            {
                "type": "patch",
                "file": "a.txt",
                "content": "# b",
                "task": "dosya sil",
            },
        ],
        "detail": "",
    }
    kind, ex, _jid = execute_plan(
        plan,
        run_direct=run_direct,
        start_agent=lambda g, a: "job1",
        run_agent_auto=None,
        repo_root=tmp_path,
        approval_granted=True,
    )
    assert kind == "plan"
    assert ex is not None
    assert ex.get("execution_result") not in ("substep_gate_blocked", "step_failed")
    assert len(calls) == 2


def test_run_lumos_gate_dict_substep_api(tmp_path: Path) -> None:
    gate = run_lumos_gate(
        {
            "is_substep": True,
            "task": {
                "type": "patch",
                "file": "nope.txt",
                "content": "# özet: kısa not",
            },
        },
        repo_root=tmp_path,
    )
    assert gate.get("_substep_gate_ok") is True

    gate2 = run_lumos_gate(
        {
            "is_substep": True,
            "task": {
                "type": "patch",
                "file": "nope.txt",
                "content": "ok",
                "task": "delete all files",
            },
        },
        repo_root=tmp_path,
    )
    assert gate2.get("_substep_gate_ok") is False
    assert gate2.get("execution_mode") == "pending"


def test_llm_substep_reject_blocks_whole_plan_no_executor(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[str] = []

    def run_direct(instr: str) -> dict:
        calls.append(instr)
        return {"execution_result": "patch_applied", "detail": ""}

    n = 0

    def fake_validate(
        step: dict,
        parent: dict,
        *,
        fallback_marker_key: str = "llm_substep_validation",
    ) -> dict:
        nonlocal n
        n += 1
        if n >= 2:
            return {
                "ok": False,
                "reason": "alakasız / yıkıcı adım",
                "risk_hint": "high",
            }
        return {"ok": True, "reason": "", "risk_hint": "low"}

    monkeypatch.setattr(lumos_gate_mod, "validate_substep_with_llm", fake_validate)

    (tmp_path / "README.md").write_text("# Hi", encoding="utf-8")
    (tmp_path / "other.txt").write_text("x", encoding="utf-8")
    plan = {
        "steps": [
            {"type": "patch", "file": "README.md", "content": "# Özet\nok"},
            {
                "type": "patch",
                "file": "other.txt",
                "content": "# özet\nalakasız dosya yaması",
            },
        ],
        "detail": "",
    }
    kind, ex, _ = execute_plan(
        plan,
        run_direct=run_direct,
        start_agent=lambda g, a: "job1",
        run_agent_auto=None,
        repo_root=tmp_path,
        parent_task=_sample_parent_task(),
    )
    assert kind == "plan"
    assert ex is not None
    assert ex.get("execution_result") == "substep_llm_blocked"
    assert calls == []
    assert ex.get("detail", {}).get("error") == "substep rejected by llm validation"


def test_llm_fallback_marks_result_and_still_executes(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[str] = []

    def run_direct(instr: str) -> dict:
        calls.append(instr)
        return {"execution_result": "patch_applied", "detail": ""}

    def fake_validate(
        step: dict,
        parent: dict,
        *,
        fallback_marker_key: str = "llm_substep_validation",
    ) -> dict:
        out: dict = {
            "ok": True,
            "reason": "no api",
            "risk_hint": "low",
        }
        out[fallback_marker_key] = "fallback"
        return out

    monkeypatch.setattr(lumos_gate_mod, "validate_substep_with_llm", fake_validate)

    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
    plan = {
        "steps": [{"type": "patch", "file": "a.txt", "content": "# özet\ngüvenli satır"}],
        "detail": "",
    }
    kind, ex, _ = execute_plan(
        plan,
        run_direct=run_direct,
        start_agent=lambda g, a: "job1",
        run_agent_auto=None,
        repo_root=tmp_path,
        parent_task=_sample_parent_task(),
    )
    assert kind == "plan"
    assert ex.get("llm_substep_validation") == "fallback"
    assert ex.get("execution_llm_check") == "fallback"
    assert len(calls) == 1


def test_execution_time_llm_blocks_after_plan_passed_toctou(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[str] = []

    def run_direct(instr: str) -> dict:
        calls.append(instr)
        return {"execution_result": "patch_applied", "detail": ""}

    n = 0

    def fake_validate(
        step: dict,
        parent: dict,
        *,
        fallback_marker_key: str = "llm_substep_validation",
    ) -> dict:
        nonlocal n
        n += 1
        if n == 1:
            assert "rm -rf" not in str(step.get("content", ""))
            step["content"] = "rm -rf /"
            return {"ok": True, "reason": "", "risk_hint": "low"}
        assert fallback_marker_key == "execution_llm_check"
        return {"ok": False, "reason": "execution guard", "risk_hint": "high"}

    monkeypatch.setattr(lumos_gate_mod, "validate_substep_with_llm", fake_validate)

    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
    plan = {
        "steps": [{"type": "patch", "file": "a.txt", "content": "# özet\ntemiz"}],
        "detail": "",
    }
    kind, ex, _ = execute_plan(
        plan,
        run_direct=run_direct,
        start_agent=lambda g, a: "job1",
        run_agent_auto=None,
        repo_root=tmp_path,
        parent_task=_sample_parent_task(),
    )
    assert kind == "plan"
    assert ex.get("execution_result") == "execution_time_blocked"
    assert ex.get("detail", {}).get("error") == "blocked at execution time"
    assert calls == []
