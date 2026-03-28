"""kando.agent_runner: hedef seçimi ve güvenlik."""
from kando.agent_runner import (
    MAX_CANDIDATE_FILES,
    _is_risky_goal,
    _list_src_core_py_files,
    select_target_and_task,
)


def test_is_risky_goal():
    assert _is_risky_goal("please rm -rf /") is not None
    assert _is_risky_goal("fix imports in runtime_state") is None


def test_select_target_prefers_scored_file(tmp_path):
    root = tmp_path
    (root / "src" / "core").mkdir(parents=True)
    a = root / "src" / "core" / "aaa.py"
    b = root / "src" / "core" / "bbb.py"
    a.write_text("# aaa\n", encoding="utf-8")
    b.write_text("# runtime_state duplicateword duplicateword duplicateword\n", encoding="utf-8")
    rel, task, meta = select_target_and_task("duplicateword düzelt", root)
    assert rel == "src/core/bbb.py"
    assert "duplicateword" in task
    assert meta.get("top_scores")


def test_list_src_core_respects_limit(tmp_path):
    (tmp_path / "src" / "core").mkdir(parents=True)
    for i in range(5):
        (tmp_path / "src" / "core" / f"f{i}.py").write_text("x\n", encoding="utf-8")
    files = _list_src_core_py_files(tmp_path, limit_scan=3)
    assert len(files) == 3


def test_max_candidate_constant():
    assert MAX_CANDIDATE_FILES == 2
