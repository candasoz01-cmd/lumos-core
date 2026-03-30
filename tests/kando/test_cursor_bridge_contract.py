"""Cursor bridge packet + persist."""
import json
import os
import time

import core.patch_pipeline as patch_pipeline
from kando import cursor_bridge
from kando.cursor_bridge import (
    build_execution_packet,
    build_result_packet,
    persist_cursor_bridge,
    run_brain_and_persist_bridge,
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
