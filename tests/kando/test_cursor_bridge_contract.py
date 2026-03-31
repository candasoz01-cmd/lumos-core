"""Cursor bridge packet + persist."""
import json
import os
import threading
import time
import uuid
from typing import Any

import core.patch_pipeline as patch_pipeline
from kando import cursor_bridge
from kando.cursor_bridge import (
    build_execution_packet,
    build_result_packet,
    get_patch_memory_entry,
    persist_cursor_bridge,
    read_filtered_patch_apply_history,
    read_recent_patch_apply_history,
    run_brain_and_persist_bridge,
    try_instruction_patch_apply,
)
from task_engine import PROFILE_GUVENLI_YURUT
from task_engine.engine import TaskRecord, TaskStep
from task_engine.profiles import STEP_TYPE_ANALYZE


def test_execution_packet_guard_flags():
    t = TaskRecord(
        task_id=1,
        title="t",
        description="x",
        created_at="2025-01-01T00:00:00",
        permission_profile=PROFILE_GUVENLI_YURUT,
        steps=[
            TaskStep("a", kind=STEP_TYPE_ANALYZE),
        ],
    )
    p = build_execution_packet(
        "x",
        t,
        permission_profile=PROFILE_GUVENLI_YURUT,
        general_approval=True,
    )
    assert p.schema_version == "kando.cursor.execution.v1"
    assert len(p.steps) == 1
    assert p.steps[0].guard_allowed is True


def test_persist_roundtrip(tmp_path):
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    t = TaskRecord(
        task_id=2,
        title="t",
        description="patch: f.txt\ny\n",
        created_at="2025-01-01T00:00:00",
        permission_profile=PROFILE_GUVENLI_YURUT,
        steps=[TaskStep("p", kind="safe_local")],
    )
    exe = build_execution_packet(
        "patch: f.txt\ny\n",
        t,
        permission_profile=PROFILE_GUVENLI_YURUT,
        general_approval=True,
    )
    t.status = "tamamlandi"
    t.verified_count = 1
    res = build_result_packet(
        goal="patch: f.txt\ny\n",
        brain_success=True,
        task=t,
        execution={"execution_result": "pending_approval", "plan": "x"},
    )
    pe, pr = persist_cursor_bridge(lumos, exe, res)
    assert pe.is_file() and pr.is_file()
    d = json.loads(pr.read_text(encoding="utf-8"))
    assert d["outcome"] == "partial"
    assert "verification_summary" in d
    assert "execution" in d
    assert d["execution"]["execution_result"] == "pending_approval"

    ex = json.loads(pe.read_text(encoding="utf-8"))
    assert ex.get("target_file") == "f.txt"
    assert ex.get("instruction", "").startswith("patch:")
    assert "verify" in ex


def test_execution_has_audit_id(monkeypatch, tmp_path):
    """Patch apply sonuçlarında audit_id execution ve patch_apply.jsonl içinde UUID olarak bulunur."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()

    from core.patch_registry import clear_registry

    executions: list[dict[str, Any]] = []

    fp1 = tmp_path / "bridge_audit.py"
    fp1.write_text("x = 1", encoding="utf-8")
    goal_no_change = "TARGET: bridge_audit.py\nx = 1\n"

    def _apply_must_not_run(*args, **kwargs):
        raise AssertionError("apply_patch must not run when disk already matches proposed_text")

    monkeypatch.setattr(patch_pipeline, "apply_patch", _apply_must_not_run)
    clear_registry()
    try:
        _, _, _, exe1, _ = run_brain_and_persist_bridge(
            goal_no_change,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        executions.append(exe1.constraints["execution"])
    finally:
        clear_registry()

    fp2 = tmp_path / "bridge_audit_w.py"
    fp2.write_text("x = 0\n", encoding="utf-8")
    goal_write_fail = "TARGET: bridge_audit_w.py\nx = 1\n"

    def _apply_leave_wrong(proposal, **kwargs):
        fp2.write_text("partial", encoding="utf-8")

    monkeypatch.setattr(patch_pipeline, "apply_patch", _apply_leave_wrong)

    def _replace_always_fail(a, b, *args, **kwargs):
        raise OSError("simulated atomic replace failure")

    monkeypatch.setattr(os, "replace", _replace_always_fail)

    clear_registry()
    try:
        _, _, _, exe2, _ = run_brain_and_persist_bridge(
            goal_write_fail,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        executions.append(exe2.constraints["execution"])
    finally:
        clear_registry()

    audit_ids: list[str] = []
    for ex in executions:
        aid = ex.get("audit_id")
        assert isinstance(aid, str) and aid
        uuid.UUID(aid)
        audit_ids.append(aid)
    assert audit_ids[0] != audit_ids[1]

    log_path = tmp_path / ".lumos" / "logs" / "patch_apply.jsonl"
    assert log_path.is_file()
    log_audit_ids: list[str] = []
    for ln in log_path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        row = json.loads(ln)
        la = row.get("audit_id")
        assert isinstance(la, str) and la
        uuid.UUID(la)
        log_audit_ids.append(la)
    assert set(audit_ids).issubset(set(log_audit_ids))


def test_patch_already_applied_returns_no_change(monkeypatch, tmp_path):
    """Dosya zaten hedef içerikteyse tekrar patch no-op; execution_result=no_change, apply_patch çağrılmaz."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "bridge_idem.py"
    # Instruction gövdesi strip("\n") ile bittiği için proposed_text tam olarak "x = 1" (EOF newline yok).
    fp.write_text("x = 1", encoding="utf-8")
    goal = "TARGET: bridge_idem.py\nx = 1\n"

    def _apply_must_not_run(*args, **kwargs):
        raise AssertionError("apply_patch must not run when disk already matches proposed_text")

    monkeypatch.setattr(patch_pipeline, "apply_patch", _apply_must_not_run)

    from core.patch_registry import clear_registry

    clear_registry()
    try:
        _, _, _, exe, _ = run_brain_and_persist_bridge(
            goal,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert exe.constraints["execution"]["execution_result"] == "no_change"
        assert exe.constraints["execution"]["detail"] == "patch already applied"
        assert fp.read_text(encoding="utf-8") == "x = 1"
    finally:
        clear_registry()


def test_atomic_write_no_partial_file(monkeypatch, tmp_path):
    """Atomic yazım hata verirse hedef bozulmaz, .tmp kalıntısı olmaz, execution_result=write_failed."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "bridge_atomic.py"
    original = "x = 0\n"
    fp.write_text(original, encoding="utf-8")
    goal = "TARGET: bridge_atomic.py\nx = 1\n"

    def _apply_leave_wrong(proposal, **kwargs):
        fp.write_text("partial", encoding="utf-8")

    monkeypatch.setattr(patch_pipeline, "apply_patch", _apply_leave_wrong)

    def _replace_always_fail(a, b, *args, **kwargs):
        raise OSError("simulated atomic replace failure")

    monkeypatch.setattr(os, "replace", _replace_always_fail)

    from core.patch_registry import clear_registry

    clear_registry()
    try:
        _, _, _, exe, _ = run_brain_and_persist_bridge(
            goal,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert exe.constraints["execution"]["execution_result"] == "write_failed"
        assert exe.constraints["execution"]["detail"] == "atomic write failed"
        assert fp.read_text(encoding="utf-8") == original
        assert not (fp.parent / "bridge_atomic.py.tmp").exists()
    finally:
        clear_registry()


def test_file_lock_prevents_parallel_write(monkeypatch, tmp_path):
    """Önceden oluşturulmuş .lock varken patch yazmaz; execution_result=locked."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "bridge_lock.py"
    original = "x = 0\n"
    fp.write_text(original, encoding="utf-8")
    lock_path = tmp_path / "bridge_lock.py.lock"
    lock_path.write_text("", encoding="utf-8")
    goal = "TARGET: bridge_lock.py\nx = 1\n"

    from core.patch_registry import clear_registry

    clear_registry()
    try:
        _, _, _, exe, _ = run_brain_and_persist_bridge(
            goal,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert exe.constraints["execution"]["execution_result"] == "locked"
        assert exe.constraints["execution"]["detail"] == "file is locked"
        assert fp.read_text(encoding="utf-8") == original
        assert lock_path.is_file()
    finally:
        clear_registry()


def test_file_lock_cleanup_on_failure(monkeypatch, tmp_path):
    """Kilit alındıktan sonra patch hata verirse .lock dosyası silinir (stale kalmaz)."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "bridge_lock_fail.py"
    fp.write_text("x = 0\n", encoding="utf-8")
    goal = "TARGET: bridge_lock_fail.py\nx = 1\n"
    lock_path = tmp_path / "bridge_lock_fail.py.lock"

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated patch failure")

    monkeypatch.setattr(patch_pipeline, "propose_text_patch", _boom)

    from core.patch_registry import clear_registry

    clear_registry()
    try:
        _, _, _, exe, _ = run_brain_and_persist_bridge(
            goal,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert exe.constraints["execution"]["execution_result"] == "patch_failed"
        assert not lock_path.exists()
    finally:
        clear_registry()


def test_instruction_target_line_patch_applies(monkeypatch, tmp_path):
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "bridge_tgt.py"
    fp.write_text("x = 0\n", encoding="utf-8")
    goal = "TARGET: bridge_tgt.py\nx = 1\n"
    from core.patch_registry import clear_registry

    clear_registry()
    try:
        _, _, _, exe, _ = run_brain_and_persist_bridge(
            goal,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert exe.constraints["execution"]["execution_result"] == "patch_applied"
        assert "x = 1" in fp.read_text(encoding="utf-8")
    finally:
        clear_registry()


def test_patch_memory_records_previous_content(monkeypatch, tmp_path):
    """Patch sonrası bellekte repo göreli yol için önceki içerik tutulur (rollback zemini)."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "bridge_mem.py"
    previous = "x = 0\n"
    fp.write_text(previous, encoding="utf-8")
    goal = "TARGET: bridge_mem.py\nx = 1\n"
    from core.patch_registry import clear_registry

    clear_registry()
    try:
        _, _, _, exe, _ = run_brain_and_persist_bridge(
            goal,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert exe.constraints["execution"]["execution_result"] == "patch_applied"
        assert exe.constraints["execution"].get("had_previous") is True
        entry = get_patch_memory_entry("bridge_mem.py")
        assert entry is not None
        assert entry["previous_content"] == previous
        assert isinstance(entry["timestamp"], float)
    finally:
        clear_registry()


def test_rollback_restores_previous_content(monkeypatch, tmp_path):
    """Patch uygula, ROLLBACK_LAST ile bellekten tek adım geri al; dosya önceki içeriğe döner."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "bridge_rollback.py"
    previous = "x = 0\n"
    fp.write_text(previous, encoding="utf-8")
    goal_patch = "TARGET: bridge_rollback.py\nx = 1\n"
    goal_rollback = "ROLLBACK_LAST"
    from core.patch_registry import clear_registry

    clear_registry()
    try:
        cursor_bridge._PATCH_MEMORY.clear()
        _, _, _, exe1, _ = run_brain_and_persist_bridge(
            goal_patch,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert exe1.constraints["execution"]["execution_result"] == "patch_applied"
        assert "x = 1" in fp.read_text(encoding="utf-8")

        _, _, _, exe2, _ = run_brain_and_persist_bridge(
            goal_rollback,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert exe2.constraints["execution"]["execution_result"] == "rollback_applied"
        assert fp.read_text(encoding="utf-8") == previous
        assert cursor_bridge.get_patch_memory_entry("bridge_rollback.py") is None
    finally:
        clear_registry()


def test_rollback_preview_does_not_modify_file(monkeypatch, tmp_path):
    """Patch sonrası ROLLBACK_PREVIEW yalnızca diff üretir; dosyaya yazmaz, bellek silinmez."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "bridge_rb_preview.py"
    fp.write_text("x = 0\n", encoding="utf-8")
    goal_patch = "TARGET: bridge_rb_preview.py\nx = 1\n"
    goal_preview = "ROLLBACK_PREVIEW"
    from core.patch_registry import clear_registry

    clear_registry()
    try:
        cursor_bridge._PATCH_MEMORY.clear()
        _, _, _, exe1, _ = run_brain_and_persist_bridge(
            goal_patch,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert exe1.constraints["execution"]["execution_result"] == "patch_applied"
        after_patch = fp.read_text(encoding="utf-8")
        assert "x = 1" in after_patch

        _, _, _, exe2, _ = run_brain_and_persist_bridge(
            goal_preview,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        ex2 = exe2.constraints["execution"]
        assert ex2["execution_result"] == "rollback_preview"
        dp = str(ex2.get("diff_preview") or "").strip()
        assert len(dp) > 0
        assert "x = 1" in dp or "x = 0" in dp or "---" in dp
        assert fp.read_text(encoding="utf-8") == after_patch
        assert cursor_bridge.get_patch_memory_entry("bridge_rb_preview.py") is not None
    finally:
        clear_registry()


def test_rollback_preview_risk_level(monkeypatch, tmp_path):
    """rollback_preview: değişen satır sayısına göre risk_level low / medium / high."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    goal_preview = "ROLLBACK_PREVIEW"
    from core.patch_registry import clear_registry

    clear_registry()
    try:
        # low: tek satırlık fark (birkaç +/- satırı, toplam < 5)
        cursor_bridge._PATCH_MEMORY.clear()
        fp_lo = tmp_path / "rl_low.py"
        fp_lo.write_text("x = 0\n", encoding="utf-8")
        _, _, _, ex_lo1, _ = run_brain_and_persist_bridge(
            "TARGET: rl_low.py\nx = 1\n",
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert ex_lo1.constraints["execution"]["execution_result"] == "patch_applied"
        _, _, _, ex_lo2, _ = run_brain_and_persist_bridge(
            goal_preview,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert ex_lo2.constraints["execution"]["risk_level"] == "low"

        # medium: 5 satır tamamen değişir → 10 +/- satırı (5–20)
        cursor_bridge._PATCH_MEMORY.clear()
        before_m = "\n".join([f"line{i}" for i in range(5)]) + "\n"
        after_m = "\n".join([f"new{i}" for i in range(5)]) + "\n"
        fp_m = tmp_path / "rl_med.py"
        fp_m.write_text(before_m, encoding="utf-8")
        _, _, _, ex_m1, _ = run_brain_and_persist_bridge(
            f"TARGET: rl_med.py\n{after_m}\n",
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert ex_m1.constraints["execution"]["execution_result"] == "patch_applied"
        _, _, _, ex_m2, _ = run_brain_and_persist_bridge(
            goal_preview,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert ex_m2.constraints["execution"]["risk_level"] == "medium"

        # high: 11 satır tamamen değişir → 22 +/- satırı (>20)
        cursor_bridge._PATCH_MEMORY.clear()
        before_h = "\n".join([f"h{i}" for i in range(11)]) + "\n"
        after_h = "\n".join([f"z{i}" for i in range(11)]) + "\n"
        fp_h = tmp_path / "rl_high.py"
        fp_h.write_text(before_h, encoding="utf-8")
        _, _, _, ex_h1, _ = run_brain_and_persist_bridge(
            f"TARGET: rl_high.py\n{after_h}\n",
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert ex_h1.constraints["execution"]["execution_result"] == "blocked"
        fp_h.write_text(after_h, encoding="utf-8")
        _, _, _, ex_h2, _ = run_brain_and_persist_bridge(
            goal_preview,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert ex_h2.constraints["execution"]["risk_level"] == "high"
    finally:
        clear_registry()


def test_high_risk_patch_blocked(monkeypatch, tmp_path):
    """Apply: yüksek risk engellenir; low/medium patch_applied; dry_run önizlemesi engellenmez."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    from core.patch_registry import clear_registry

    clear_registry()
    try:
        before_h = "\n".join([f"h{i}" for i in range(11)]) + "\n"
        after_h = "\n".join([f"z{i}" for i in range(11)]) + "\n"
        fp_h = tmp_path / "hr_block.py"
        fp_h.write_text(before_h, encoding="utf-8")
        _, _, _, ex_high, _ = run_brain_and_persist_bridge(
            f"TARGET: hr_block.py\n{after_h}\n",
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert ex_high.constraints["execution"]["execution_result"] == "blocked"
        assert ex_high.constraints["execution"]["error_type"] == "high_risk_blocked"
        assert ex_high.constraints["execution"]["risk_level"] == "high"
        assert ex_high.constraints["execution"]["forced"] is False
        assert fp_h.read_text(encoding="utf-8") == before_h

        fp_lo = tmp_path / "hr_low.py"
        fp_lo.write_text("x = 0\n", encoding="utf-8")
        _, _, _, ex_lo, _ = run_brain_and_persist_bridge(
            "TARGET: hr_low.py\nx = 1\n",
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert ex_lo.constraints["execution"]["execution_result"] == "patch_applied"
        assert "x = 1" in fp_lo.read_text(encoding="utf-8")

        before_m = "\n".join([f"line{i}" for i in range(5)]) + "\n"
        after_m = "\n".join([f"new{i}" for i in range(5)]) + "\n"
        fp_m = tmp_path / "hr_med.py"
        fp_m.write_text(before_m, encoding="utf-8")
        _, _, _, ex_m, _ = run_brain_and_persist_bridge(
            f"TARGET: hr_med.py\n{after_m}\n",
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert ex_m.constraints["execution"]["execution_result"] == "patch_applied"
        assert ex_m.constraints["execution"]["forced"] is False

        fp_dry = tmp_path / "hr_dry.py"
        fp_dry.write_text(before_h, encoding="utf-8")
        goal_dry = f"TARGET: hr_dry.py\n{after_h}\n"
        t_dry = TaskRecord(
            task_id=902,
            title="dry",
            description=goal_dry,
            created_at="2025-01-01T00:00:00",
            permission_profile=PROFILE_GUVENLI_YURUT,
            steps=[],
        )
        exe_dry = build_execution_packet(
            goal_dry,
            t_dry,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        exe_dry.constraints["lumos_base_resolved"] = str((tmp_path / ".lumos").resolve())
        exe_dry.constraints["dry_run"] = True
        try_instruction_patch_apply(goal_dry, exe_dry)
        assert exe_dry.constraints["execution"]["execution_result"] == "dry_run_success"
        assert fp_dry.read_text(encoding="utf-8") == before_h
    finally:
        clear_registry()


def test_high_risk_requires_force(monkeypatch, tmp_path):
    """Yüksek risk: force yoksa block; execution.force veya constraints.force ile apply + forced=True."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    from core.patch_registry import clear_registry

    clear_registry()
    try:
        before_h = "\n".join([f"h{i}" for i in range(11)]) + "\n"
        after_h = "\n".join([f"z{i}" for i in range(11)]) + "\n"
        goal = f"TARGET: hr_force.py\n{after_h}\n"
        fp = tmp_path / "hr_force.py"
        fp.write_text(before_h, encoding="utf-8")
        t = TaskRecord(
            task_id=903,
            title="t",
            description=goal,
            created_at="2025-01-01T00:00:00",
            permission_profile=PROFILE_GUVENLI_YURUT,
            steps=[],
        )
        lumos_resolved = str((tmp_path / ".lumos").resolve())

        exe_no = build_execution_packet(
            goal,
            t,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        exe_no.constraints["lumos_base_resolved"] = lumos_resolved
        try_instruction_patch_apply(goal, exe_no)
        assert exe_no.constraints["execution"]["execution_result"] == "blocked"
        assert exe_no.constraints["execution"]["forced"] is False
        assert fp.read_text(encoding="utf-8") == before_h

        exe_in = build_execution_packet(
            goal,
            t,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        exe_in.constraints["lumos_base_resolved"] = lumos_resolved
        exe_in.constraints["execution"] = {"force": True}
        try_instruction_patch_apply(goal, exe_in)
        assert exe_in.constraints["execution"]["execution_result"] == "patch_applied"
        assert exe_in.constraints["execution"]["forced"] is True
        assert fp.read_text(encoding="utf-8").rstrip("\n") == after_h.rstrip("\n")

        fp_b = tmp_path / "hr_force_b.py"
        fp_b.write_text(before_h, encoding="utf-8")
        goal_b = f"TARGET: hr_force_b.py\n{after_h}\n"
        exe_top = build_execution_packet(
            goal_b,
            t,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        exe_top.constraints["lumos_base_resolved"] = lumos_resolved
        exe_top.constraints["force"] = True
        try_instruction_patch_apply(goal_b, exe_top)
        assert exe_top.constraints["execution"]["execution_result"] == "patch_applied"
        assert exe_top.constraints["execution"]["forced"] is True
        assert fp_b.read_text(encoding="utf-8").rstrip("\n") == after_h.rstrip("\n")
    finally:
        clear_registry()


def test_high_risk_blocked_without_force(monkeypatch, tmp_path):
    """Karar katmanı: risk_level=high iken policy gate → pending_approval (direkt block değil)."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "policy_gate_hr.py"
    fp.write_text("x = 0\n", encoding="utf-8")
    goal = "TARGET: policy_gate_hr.py\nx = 1\n"
    t = TaskRecord(
        task_id=880,
        title="t",
        description=goal,
        created_at="2025-01-01T00:00:00",
        permission_profile=PROFILE_GUVENLI_YURUT,
        steps=[],
    )
    lumos_resolved = str((tmp_path / ".lumos").resolve())
    from core.patch_registry import clear_registry

    clear_registry()
    try:
        cursor_bridge._PATCH_MEMORY.clear()
        cursor_bridge._PENDING_APPROVALS.clear()
        exe = build_execution_packet(
            goal,
            t,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        exe.constraints["lumos_base_resolved"] = lumos_resolved
        exe.constraints["execution"] = {"risk_level": "high"}
        try_instruction_patch_apply(goal, exe)
        assert exe.constraints["execution"]["execution_result"] == "pending_approval"
        assert exe.constraints["execution"]["error_type"] == "approval_required"
        assert "yüksek risk" in exe.constraints["execution"].get("detail", "").lower()
        assert exe.constraints["execution"].get("policy_gate", {}).get("assessment") == "high_risk_approval_required"
        assert fp.read_text(encoding="utf-8") == "x = 0\n"
    finally:
        clear_registry()


def test_high_risk_goes_to_pending(monkeypatch, tmp_path):
    """Üst policy gate: risk_level=high → pending_approval + bekleyen kayıt (audit_id)."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "policy_block_hr.py"
    fp.write_text("a = 1\n", encoding="utf-8")
    goal = "TARGET: policy_block_hr.py\na = 2\n"
    t = TaskRecord(
        task_id=882,
        title="t",
        description=goal,
        created_at="2025-01-01T00:00:00",
        permission_profile=PROFILE_GUVENLI_YURUT,
        steps=[],
    )
    lumos_resolved = str((tmp_path / ".lumos").resolve())
    from core.patch_registry import clear_registry

    clear_registry()
    try:
        cursor_bridge._PATCH_MEMORY.clear()
        cursor_bridge._PENDING_APPROVALS.clear()
        exe = build_execution_packet(
            goal,
            t,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        exe.constraints["lumos_base_resolved"] = lumos_resolved
        exe.constraints["execution"] = {"risk_level": "high"}
        try_instruction_patch_apply(goal, exe)
        ex = exe.constraints["execution"]
        assert ex["execution_result"] == "pending_approval"
        assert ex["error_type"] == "approval_required"
        assert ex.get("policy_gate", {}).get("result") == "pending"
        aid = ex.get("audit_id")
        assert aid and aid in cursor_bridge._PENDING_APPROVALS
        assert cursor_bridge._PENDING_APPROVALS[aid]["goal"] == goal
        assert fp.read_text(encoding="utf-8") == "a = 1\n"
    finally:
        clear_registry()


def test_approve_executes_patch(monkeypatch, tmp_path):
    """APPROVE <audit_id> bekleyen hedefi force ile uygular → approved_and_executed."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "approve_exec.py"
    fp.write_text("x = 0\n", encoding="utf-8")
    goal = "TARGET: approve_exec.py\nx = 1\n"
    t = TaskRecord(
        task_id=885,
        title="t",
        description=goal,
        created_at="2025-01-01T00:00:00",
        permission_profile=PROFILE_GUVENLI_YURUT,
        steps=[],
    )
    lumos_resolved = str((tmp_path / ".lumos").resolve())
    from core.patch_registry import clear_registry

    clear_registry()
    try:
        cursor_bridge._PATCH_MEMORY.clear()
        cursor_bridge._PENDING_APPROVALS.clear()
        exe1 = build_execution_packet(
            goal,
            t,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        exe1.constraints["lumos_base_resolved"] = lumos_resolved
        exe1.constraints["execution"] = {"risk_level": "high"}
        try_instruction_patch_apply(goal, exe1)
        aid = exe1.constraints["execution"]["audit_id"]
        assert exe1.constraints["execution"]["execution_result"] == "pending_approval"

        exe2 = build_execution_packet(
            f"APPROVE {aid}",
            t,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        exe2.constraints["lumos_base_resolved"] = lumos_resolved
        try_instruction_patch_apply(f"APPROVE {aid}", exe2)
        assert exe2.constraints["execution"]["execution_result"] == "approved_and_executed"
        assert "x = 1" in fp.read_text(encoding="utf-8")
        assert aid not in cursor_bridge._PENDING_APPROVALS
    finally:
        clear_registry()


def test_reject_blocks_execution(monkeypatch, tmp_path):
    """REJECT <audit_id> bekleyen kaydı siler ve rejected döner."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "reject_t.py"
    fp.write_text("z = 1\n", encoding="utf-8")
    goal = "TARGET: reject_t.py\nz = 2\n"
    t = TaskRecord(
        task_id=886,
        title="t",
        description=goal,
        created_at="2025-01-01T00:00:00",
        permission_profile=PROFILE_GUVENLI_YURUT,
        steps=[],
    )
    lumos_resolved = str((tmp_path / ".lumos").resolve())
    from core.patch_registry import clear_registry

    clear_registry()
    try:
        cursor_bridge._PATCH_MEMORY.clear()
        cursor_bridge._PENDING_APPROVALS.clear()
        exe1 = build_execution_packet(
            goal,
            t,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        exe1.constraints["lumos_base_resolved"] = lumos_resolved
        exe1.constraints["execution"] = {"risk_level": "high"}
        try_instruction_patch_apply(goal, exe1)
        aid = exe1.constraints["execution"]["audit_id"]

        exe2 = build_execution_packet(
            f"REJECT {aid}",
            t,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        exe2.constraints["lumos_base_resolved"] = lumos_resolved
        try_instruction_patch_apply(f"REJECT {aid}", exe2)
        assert exe2.constraints["execution"]["execution_result"] == "rejected"
        assert exe2.constraints["execution"]["error_type"] == "approval_rejected"
        assert aid not in cursor_bridge._PENDING_APPROVALS
        assert fp.read_text(encoding="utf-8") == "z = 1\n"
    finally:
        clear_registry()


def test_policy_allows_safe_patch(monkeypatch, tmp_path):
    """Üst policy gate: low/medium risk veya bilinmeyen → patch; policy_gate_audit işaretli."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "policy_safe.py"
    fp.write_text("x = 0\n", encoding="utf-8")
    goal = "TARGET: policy_safe.py\nx = 1\n"
    t = TaskRecord(
        task_id=883,
        title="t",
        description=goal,
        created_at="2025-01-01T00:00:00",
        permission_profile=PROFILE_GUVENLI_YURUT,
        steps=[],
    )
    lumos_resolved = str((tmp_path / ".lumos").resolve())
    from core.patch_registry import clear_registry

    clear_registry()
    try:
        cursor_bridge._PATCH_MEMORY.clear()
        exe = build_execution_packet(
            goal,
            t,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        exe.constraints["lumos_base_resolved"] = lumos_resolved
        exe.constraints["execution"] = {"risk_level": "low"}
        try_instruction_patch_apply(goal, exe)
        assert exe.constraints["execution"]["execution_result"] == "patch_applied"
        assert exe.constraints["execution"].get("policy_gate", {}).get("result") == "allow"
        assert exe.constraints["execution"].get("policy_gate", {}).get("assessment") == "known_risk"
        assert "x = 1" in fp.read_text(encoding="utf-8")
    finally:
        clear_registry()


def test_force_override_bypasses_policy(monkeypatch, tmp_path):
    """force=True: üst policy gate yüksek riski bypass eder (decision gate dahil)."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "policy_force_bypass.py"
    fp.write_text("x = 0\n", encoding="utf-8")
    goal = "TARGET: policy_force_bypass.py\nx = 1\n"
    t = TaskRecord(
        task_id=884,
        title="t",
        description=goal,
        created_at="2025-01-01T00:00:00",
        permission_profile=PROFILE_GUVENLI_YURUT,
        steps=[],
    )
    lumos_resolved = str((tmp_path / ".lumos").resolve())
    from core.patch_registry import clear_registry

    clear_registry()
    try:
        cursor_bridge._PATCH_MEMORY.clear()
        exe = build_execution_packet(
            goal,
            t,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        exe.constraints["lumos_base_resolved"] = lumos_resolved
        exe.constraints["force"] = True
        exe.constraints["execution"] = {"risk_level": "high", "force": True}
        try_instruction_patch_apply(goal, exe)
        assert exe.constraints["execution"]["execution_result"] == "patch_applied"
        assert exe.constraints.get("policy_gate_audit", {}).get("result") == "bypass"
        assert "x = 1" in fp.read_text(encoding="utf-8")
    finally:
        clear_registry()


def test_force_override_allows_execution(monkeypatch, tmp_path):
    """Karar katmanı: force True iken risk_level=high önceden gelse bile patch uygulanır."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "policy_gate_force.py"
    fp.write_text("x = 0\n", encoding="utf-8")
    goal = "TARGET: policy_gate_force.py\nx = 1\n"
    t = TaskRecord(
        task_id=881,
        title="t",
        description=goal,
        created_at="2025-01-01T00:00:00",
        permission_profile=PROFILE_GUVENLI_YURUT,
        steps=[],
    )
    lumos_resolved = str((tmp_path / ".lumos").resolve())
    from core.patch_registry import clear_registry

    clear_registry()
    try:
        cursor_bridge._PATCH_MEMORY.clear()
        exe = build_execution_packet(
            goal,
            t,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        exe.constraints["lumos_base_resolved"] = lumos_resolved
        exe.constraints["force"] = True
        exe.constraints["execution"] = {"risk_level": "high", "force": True}
        try_instruction_patch_apply(goal, exe)
        assert exe.constraints["execution"]["execution_result"] == "patch_applied"
        assert "x = 1" in fp.read_text(encoding="utf-8")
    finally:
        clear_registry()


def test_no_patch_during_rollback(monkeypatch, tmp_path):
    """Rollback sürerken başka bir iş parçacığı patch denerse uygulanmaz (blocked_by_rollback)."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "bridge_rb_guard.py"
    fp.write_text("x = 0\n", encoding="utf-8")
    goal_patch = "TARGET: bridge_rb_guard.py\nx = 1\n"
    goal_rollback = "ROLLBACK_LAST"
    from core.patch_registry import clear_registry

    clear_registry()
    try:
        cursor_bridge._PATCH_MEMORY.clear()
        _, _, _, exe_patch, _ = run_brain_and_persist_bridge(
            goal_patch,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert exe_patch.constraints["execution"]["execution_result"] == "patch_applied"
        assert "x = 1" in fp.read_text(encoding="utf-8")

        rollback_entered = threading.Event()
        patch_can_continue = threading.Event()
        patch_out: dict[str, Any] = {}

        orig_rb = cursor_bridge.rollback_patch_file

        def _hold_rollback(*args, **kwargs):
            rollback_entered.set()
            assert patch_can_continue.wait(timeout=10.0)
            return orig_rb(*args, **kwargs)

        monkeypatch.setattr(cursor_bridge, "rollback_patch_file", _hold_rollback)

        t = TaskRecord(
            task_id=501,
            title="t",
            description="d",
            created_at="2025-01-01T00:00:00",
            permission_profile=PROFILE_GUVENLI_YURUT,
            steps=[],
        )
        lumos_resolved = str((tmp_path / ".lumos").resolve())

        def _try_patch_while_rollback():
            rollback_entered.wait(timeout=10.0)
            exe2 = build_execution_packet(
                goal_patch,
                t,
                permission_profile=PROFILE_GUVENLI_YURUT,
                general_approval=True,
            )
            exe2.constraints["lumos_base_resolved"] = lumos_resolved
            try_instruction_patch_apply(goal_patch, exe2)
            patch_out["execution"] = dict(exe2.constraints.get("execution") or {})
            patch_can_continue.set()

        th = threading.Thread(target=_try_patch_while_rollback)
        th.start()

        exe_rb = build_execution_packet(
            goal_rollback,
            t,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        exe_rb.constraints["lumos_base_resolved"] = lumos_resolved
        try_instruction_patch_apply(goal_rollback, exe_rb)

        th.join(timeout=5.0)
        assert not th.is_alive()

        assert patch_out["execution"].get("execution_result") == "blocked_by_rollback"
        assert exe_rb.constraints["execution"]["execution_result"] == "rollback_applied"
        assert fp.read_text(encoding="utf-8") == "x = 0\n"
    finally:
        clear_registry()


def test_instruction_without_target_target_required(monkeypatch, tmp_path):
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    (tmp_path / ".lumos").mkdir()
    _, _, _, exe, _ = run_brain_and_persist_bridge(
        "genel analiz metni",
        permission_profile=PROFILE_GUVENLI_YURUT,
        general_approval=True,
    )
    assert exe.constraints["execution"]["execution_result"] == "target_required"
    assert "TARGET ZORUNLU" in exe.constraints["execution"]["detail"]


def test_build_execution_packet_multi_targets(monkeypatch, tmp_path):
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / "src" / "core").mkdir(parents=True)
    (tmp_path / "src" / "core" / "ma.py").write_text("x\n", encoding="utf-8")
    (tmp_path / "src" / "core" / "mb.py").write_text("y\n", encoding="utf-8")
    t = TaskRecord(
        task_id=9,
        title="t",
        description="d",
        created_at="2025-01-01T00:00:00",
        permission_profile=PROFILE_GUVENLI_YURUT,
        steps=[],
    )
    p = build_execution_packet(
        "src/core/ma.py ve src/core/mb.py",
        t,
        permission_profile=PROFILE_GUVENLI_YURUT,
        general_approval=True,
    )
    assert p.target_files == ["src/core/ma.py", "src/core/mb.py"]
    assert p.target_file == "src/core/ma.py"


def test_instruction_multi_two_files_applied(monkeypatch, tmp_path):
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    a = tmp_path / "src" / "core" / "ma.py"
    b = tmp_path / "src" / "core" / "mb.py"
    a.parent.mkdir(parents=True)
    a.write_text("a=1\n", encoding="utf-8")
    b.write_text("b=1\n", encoding="utf-8")
    from core.patch_registry import clear_registry

    clear_registry()
    try:
        _, _, _, exe, _ = run_brain_and_persist_bridge(
            "görev: src/core/ma.py ve src/core/mb.py güvenlik dokunuşu",
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert exe.constraints["execution"]["execution_result"] == "patch_applied"
        assert exe.constraints["execution"].get("multi_file") is True
        assert len(exe.constraints["execution"].get("file_results", [])) == 2
        assert "lumos:instruction-pipeline safe touch" in a.read_text(encoding="utf-8")
        assert "lumos:instruction-pipeline safe touch" in b.read_text(encoding="utf-8")
    finally:
        clear_registry()


def test_file_task_lines_requires_target_body(monkeypatch, tmp_path):
    """file: + task ile hedef yolu çıkar; tek dosya deterministic instruction_path_fallback."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "vendor" / "pkg" / "mod.py"
    fp.parent.mkdir(parents=True)
    fp.write_text("x = 1\n", encoding="utf-8")
    from core.patch_registry import clear_registry

    clear_registry()
    try:
        goal = "file: vendor/pkg/mod.py\ntask: remove unused imports\n"
        _, _, _, exe, _ = run_brain_and_persist_bridge(
            goal,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert exe.constraints["execution"]["execution_result"] == "patch_applied"
        assert "instruction_path_fallback" in exe.constraints["execution"].get("detail", "")
    finally:
        clear_registry()


def test_patch_timeout_returns_timeout(monkeypatch, tmp_path):
    """Ağır patch adımı süreyi aşınca execution_result=timeout."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "timeout_tgt.py"
    fp.write_text("a = 1\n", encoding="utf-8")
    goal = "TARGET: timeout_tgt.py\na = 2\n"

    _orig_propose = patch_pipeline.propose_text_patch

    def _slow_propose(*args, **kwargs):
        time.sleep(0.15)
        return _orig_propose(*args, **kwargs)

    monkeypatch.setattr(cursor_bridge, "MAX_PATCH_SECONDS", 0.05)
    monkeypatch.setattr(patch_pipeline, "propose_text_patch", _slow_propose)

    from core.patch_registry import clear_registry

    clear_registry()
    try:
        _, _, _, exe, _ = run_brain_and_persist_bridge(
            goal,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert exe.constraints["execution"]["execution_result"] == "timeout"
        assert exe.constraints["execution"]["detail"] == "patch timeout"
    finally:
        clear_registry()


def test_patch_total_timeout(monkeypatch, tmp_path):
    """Çoklu patch akışında toplam süre aşılınca execution_result=timeout_total."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    a = tmp_path / "src" / "core" / "ma.py"
    b = tmp_path / "src" / "core" / "mb.py"
    a.parent.mkdir(parents=True)
    a.write_text("a=1\n", encoding="utf-8")
    b.write_text("b=1\n", encoding="utf-8")

    _orig_propose = patch_pipeline.propose_text_patch

    def _slow_propose(*args, **kwargs):
        time.sleep(0.06)
        return _orig_propose(*args, **kwargs)

    monkeypatch.setattr(cursor_bridge, "MAX_TOTAL_PATCH_SECONDS", 0.1)
    monkeypatch.setattr(cursor_bridge, "MAX_PATCH_SECONDS", 30.0)
    monkeypatch.setattr(patch_pipeline, "propose_text_patch", _slow_propose)

    from core.patch_registry import clear_registry

    clear_registry()
    try:
        _, _, _, exe, _ = run_brain_and_persist_bridge(
            "görev: src/core/ma.py ve src/core/mb.py güvenlik dokunuşu",
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert exe.constraints["execution"]["execution_result"] == "timeout_total"
        assert exe.constraints["execution"]["detail"] == "total patch timeout"
    finally:
        clear_registry()


def test_show_history_returns_recent_entries(monkeypatch, tmp_path):
    """SHOW_HISTORY: patch_apply.jsonl son kayıtlarını execution.history içinde döndürür."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    log_dir = tmp_path / ".lumos" / "logs"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "patch_apply.jsonl"
    rows = [
        {"time": "2026-01-01T00:00:00Z", "audit_id": "a1", "file": "f1.py", "result": "patch_applied", "detail": "x"},
        {"time": "2026-01-02T00:00:00Z", "audit_id": "a2", "file": "f2.py", "result": "no_change", "detail": "y", "risk_level": "low"},
    ]
    log_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    t = TaskRecord(
        task_id=700,
        title="h",
        description="SHOW_HISTORY",
        created_at="2026-01-01T00:00:00Z",
        permission_profile=PROFILE_GUVENLI_YURUT,
        steps=[],
    )
    lumos_resolved = str((tmp_path / ".lumos").resolve())
    exe = build_execution_packet(
        "SHOW_HISTORY",
        t,
        permission_profile=PROFILE_GUVENLI_YURUT,
        general_approval=True,
    )
    exe.constraints["lumos_base_resolved"] = lumos_resolved
    try_instruction_patch_apply("SHOW_HISTORY", exe)
    ex = exe.constraints["execution"]
    assert ex["execution_result"] == "history_listed"
    assert "history" in ex
    hist = ex["history"]
    assert len(hist) == 2
    assert hist[0]["audit_id"] == "a1"
    assert hist[0]["execution_result"] == "patch_applied"
    assert hist[0]["target_file"] == "f1.py"
    assert hist[0]["risk_level"] == "unknown"
    assert hist[0]["timestamp"] == "2026-01-01T00:00:00Z"
    assert hist[1]["audit_id"] == "a2"
    assert hist[1]["risk_level"] == "low"

    assert read_recent_patch_apply_history(tmp_path / ".lumos", limit=1) == [hist[1]]

    exe_empty = build_execution_packet(
        "SHOW_HISTORY",
        t,
        permission_profile=PROFILE_GUVENLI_YURUT,
        general_approval=True,
    )
    exe_empty.constraints["lumos_base_resolved"] = str((tmp_path / ".lumos_empty").resolve())
    try_instruction_patch_apply("SHOW_HISTORY", exe_empty)
    assert exe_empty.constraints["execution"]["execution_result"] == "history_empty"
    assert exe_empty.constraints["execution"]["history"] == []


def test_show_history_filters_results(monkeypatch, tmp_path):
    """SHOW_HISTORY: result/risk/file filtreleri birlikte; eşleşme yoksa history_empty."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    log_dir = tmp_path / ".lumos" / "logs"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "patch_apply.jsonl"
    rows = [
        {"time": "2026-01-01T00:00:00Z", "audit_id": "a1", "file": "src/a.py", "result": "patch_applied", "detail": ""},
        {"time": "2026-01-02T00:00:00Z", "audit_id": "a2", "file": "src/b.py", "result": "blocked", "detail": ""},
        {"time": "2026-01-03T00:00:00Z", "audit_id": "a3", "file": "src/c.py", "result": "patch_failed", "detail": ""},
        {
            "time": "2026-01-04T00:00:00Z",
            "audit_id": "a4",
            "file": "src/d.py",
            "result": "patch_applied",
            "detail": "",
            "risk_level": "high",
        },
    ]
    log_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    t = TaskRecord(
        task_id=701,
        title="h",
        description="SHOW_HISTORY",
        created_at="2026-01-01T00:00:00Z",
        permission_profile=PROFILE_GUVENLI_YURUT,
        steps=[],
    )
    lumos_resolved = str((tmp_path / ".lumos").resolve())

    def _exe(goal: str):
        exe = build_execution_packet(
            goal,
            t,
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        exe.constraints["lumos_base_resolved"] = lumos_resolved
        try_instruction_patch_apply(goal, exe)
        return exe

    ex_blocked = _exe("SHOW_HISTORY result=blocked")
    assert ex_blocked.constraints["execution"]["execution_result"] == "history_listed"
    assert len(ex_blocked.constraints["execution"]["history"]) == 1
    assert ex_blocked.constraints["execution"]["history"][0]["audit_id"] == "a2"

    ex_failed = _exe("SHOW_HISTORY result=failed")
    assert len(ex_failed.constraints["execution"]["history"]) == 1
    assert ex_failed.constraints["execution"]["history"][0]["execution_result"] == "patch_failed"

    ex_risk = _exe("SHOW_HISTORY risk=high")
    assert len(ex_risk.constraints["execution"]["history"]) == 1
    assert ex_risk.constraints["execution"]["history"][0]["audit_id"] == "a4"

    ex_file = _exe("SHOW_HISTORY file=src/b.py")
    assert len(ex_file.constraints["execution"]["history"]) == 1
    assert ex_file.constraints["execution"]["history"][0]["target_file"] == "src/b.py"

    ex_and = _exe("SHOW_HISTORY result=failed file=src/c.py")
    assert len(ex_and.constraints["execution"]["history"]) == 1
    assert ex_and.constraints["execution"]["history"][0]["audit_id"] == "a3"

    ex_or_result = _exe("SHOW_HISTORY result=failed result=blocked")
    ids = {h["audit_id"] for h in ex_or_result.constraints["execution"]["history"]}
    assert ids == {"a2", "a3"}

    ex_none = _exe("SHOW_HISTORY result=failed risk=high")
    assert ex_none.constraints["execution"]["execution_result"] == "history_empty"
    assert ex_none.constraints["execution"]["history"] == []

    base = tmp_path / ".lumos"
    f_or = {"result": ["failed", "blocked"], "risk": [], "file": []}
    assert len(read_filtered_patch_apply_history(base, f_or, limit=10)) == 2


def test_instruction_embedded_path_requires_target_body(monkeypatch, tmp_path):
    """Metinde gömülü repo yolu → tek hedef; deterministic patch_applied."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir()
    fp = tmp_path / "src" / "core" / "embedded.py"
    fp.parent.mkdir(parents=True)
    fp.write_text('print("hi")\n', encoding="utf-8")
    from core.patch_registry import clear_registry

    clear_registry()
    try:
        _, _, _, exe, _ = run_brain_and_persist_bridge(
            f"incele ve küçük düzelt: {fp.relative_to(tmp_path).as_posix()}",
            permission_profile=PROFILE_GUVENLI_YURUT,
            general_approval=True,
        )
        assert exe.constraints["execution"]["execution_result"] == "patch_applied"
        assert "instruction_path_fallback" in exe.constraints["execution"].get("detail", "")
    finally:
        clear_registry()
