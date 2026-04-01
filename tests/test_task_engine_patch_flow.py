"""patch: hedefi → planner (SAFE_LOCAL) → propose + pending; onay → apply + VERIFY."""

from core.patch_registry import clear_registry
from core.brain import run as brain_run
from kando.patch_pending import apply_pending_after_approval
from task_engine import TaskStore, PROFILE_GUVENLI_YURUT
from task_engine.observation import ObservationEngine


def test_brain_patch_goal_applies_and_verify(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    monkeypatch.setenv("LUMOS_BASE_DIR", str(lumos))
    tasks_dir = lumos / "tasks"
    tasks_dir.mkdir()

    target_rel = "patch_flow_test.py"
    f = tmp_path / target_rel
    f.write_text("x = 0\n", encoding="utf-8")

    clear_registry()
    try:
        store = TaskStore(tasks_dir)
        obs = ObservationEngine()
        goal = (
            f"patch: {target_rel}\n"
            "x = 1\n"
            "\n"
            "VERIFY:\n"
            f'{__import__("sys").executable} -c "print(\'test_sonucu: ok\')"'
        )
        result = brain_run(
            goal,
            store,
            tasks_dir,
            PROFILE_GUVENLI_YURUT,
            True,
            observation_engine=obs,
        )
        assert result.success is True
        assert "x = 1" in f.read_text(encoding="utf-8")
        msg = (result.message or "") + (result.human_readable_summary or "")
        assert "patch_auto_applied" in msg
        assert "patch_result=patch_applied" in msg
        assert "test_sonucu: ok" in msg
    finally:
        clear_registry()


def test_brain_single_file_large_diff_auto_applies(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    monkeypatch.setenv("LUMOS_BASE_DIR", str(lumos))
    tasks_dir = lumos / "tasks"
    tasks_dir.mkdir()

    target_rel = "big_patch.py"
    f = tmp_path / target_rel
    f.write_text("a = 0\n", encoding="utf-8")
    huge = "\n".join([f"# line {i}" for i in range(9000)])

    clear_registry()
    try:
        store = TaskStore(tasks_dir)
        obs = ObservationEngine()
        goal = f"patch: {target_rel}\na = 1\n{huge}\n"
        result = brain_run(
            goal,
            store,
            tasks_dir,
            PROFILE_GUVENLI_YURUT,
            True,
            observation_engine=obs,
        )
        assert result.success is True
        text = f.read_text(encoding="utf-8")
        assert "a = 1" in text
        assert "# line" in text
        msg = (result.message or "") + (result.human_readable_summary or "")
        assert "patch_auto_applied" in msg
        assert "patch_result=patch_applied" in msg
    finally:
        clear_registry()


def test_brain_patch_blocked_too_many_files(tmp_path, monkeypatch):
    from kando.patch_scope import MAX_PATHS_IN_SCOPE

    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    monkeypatch.setenv("LUMOS_BASE_DIR", str(lumos))
    tasks_dir = lumos / "tasks"
    tasks_dir.mkdir()

    paths = [f"x{i}.txt" for i in range(MAX_PATHS_IN_SCOPE + 1)]
    sections = "\n".join(f"--- {p} ---\n{n}" for p, n in zip(paths, paths))
    goal = f"patch: {','.join(paths)}\n{sections}"

    from core.patch_registry import clear_registry
    from core.brain import run as brain_run

    clear_registry()
    try:
        store = TaskStore(tasks_dir)
        obs = ObservationEngine()
        result = brain_run(
            goal,
            store,
            tasks_dir,
            PROFILE_GUVENLI_YURUT,
            True,
            observation_engine=obs,
        )
        assert result.success is False
    finally:
        clear_registry()


def test_parse_patch_goal_verify_inline():
    from task_engine.executors.patch_apply_executor import parse_patch_goal

    rel, body, v = parse_patch_goal("patch: foo/bar.txt\nx\nVERIFY: python -c \"1\"")
    assert rel == "foo/bar.txt"
    assert body == "x"
    assert "python" in (v or "")


def test_brain_patch_goal_insert_at_top_prepends_comment_not_literal(tmp_path, monkeypatch):
    """patch: gövdesi INSERT_AT_TOP:# ... → TaskEngine patch_apply_executor propose öncesi genişle."""
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    monkeypatch.setenv("LUMOS_BASE_DIR", str(lumos))
    tasks_dir = lumos / "tasks"
    tasks_dir.mkdir()

    target_rel = "patch_insert_top.py"
    f = tmp_path / target_rel
    f.write_text("x = 0\n", encoding="utf-8")

    clear_registry()
    try:
        store = TaskStore(tasks_dir)
        obs = ObservationEngine()
        exe = __import__("sys").executable
        goal = (
            f"patch: {target_rel}\n"
            "INSERT_AT_TOP:# TEST_OK\n"
            "\n"
            f"VERIFY:\n{exe} -c \"print('ok')\""
        )
        result = brain_run(
            goal,
            store,
            tasks_dir,
            PROFILE_GUVENLI_YURUT,
            True,
            observation_engine=obs,
        )
        assert result.success is True
        text = f.read_text(encoding="utf-8")
        assert text.startswith("# TEST_OK\n")
        assert "INSERT_AT_TOP" not in text
        assert "x = 0" in text
    finally:
        clear_registry()


def test_brain_multi_file_patch_pending_then_apply(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    lumos = tmp_path / ".lumos"
    lumos.mkdir()
    monkeypatch.setenv("LUMOS_BASE_DIR", str(lumos))
    tasks_dir = lumos / "tasks"
    tasks_dir.mkdir()

    a = tmp_path / "ma.py"
    b = tmp_path / "mb.py"
    a.write_text("va = 0\n", encoding="utf-8")
    b.write_text("vb = 0\n", encoding="utf-8")

    from core.patch_registry import clear_registry
    from core.brain import run as brain_run

    clear_registry()
    try:
        store = TaskStore(tasks_dir)
        obs = ObservationEngine()
        goal = (
            "patch: ma.py,mb.py\n"
            "--- ma.py ---\n"
            "va = 1\n"
            "--- mb.py ---\n"
            "vb = 1\n"
            "\n"
            "VERIFY:\n"
            f'{__import__("sys").executable} -c "assert 1"'
        )
        result = brain_run(
            goal,
            store,
            tasks_dir,
            PROFILE_GUVENLI_YURUT,
            True,
            observation_engine=obs,
        )
        assert result.success is True
        assert "va = 0" in a.read_text(encoding="utf-8")
        assert "vb = 0" in b.read_text(encoding="utf-8")
        assert "patch_multi_pending" in (result.message or "")

        ok, msg = apply_pending_after_approval()
        assert ok is True
        assert "va = 1" in a.read_text(encoding="utf-8")
        assert "vb = 1" in b.read_text(encoding="utf-8")
        assert "verify: ok" in msg.lower()
    finally:
        clear_registry()
