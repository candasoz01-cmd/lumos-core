"""kando.patch_scope: ayrıştırma, sınıflandırma, minimum kapsam."""
from kando.patch_scope import (
    MAX_PATHS_IN_SCOPE,
    analyze_patch_scope,
    extract_file_task,
    extract_instruction_target_path,
    extract_instruction_paths_ordered,
    instruction_path_allowed_for_multi,
    parse_patch_goal_extended,
    parse_patch_goal_legacy,
    select_instruction_multi_pair,
)


def test_extract_file_task_lines():
    f, t = extract_file_task(
        "file: src/core/x.py\ntask: remove unused imports\n",
    )
    assert f == "src/core/x.py"
    assert t == "remove unused imports"
    assert extract_file_task("plain text") == (None, None)


def test_extract_instruction_target_path_prefers_existing(tmp_path):
    root = tmp_path
    p = root / "src" / "a.py"
    p.parent.mkdir(parents=True)
    p.write_text("x=1\n", encoding="utf-8")
    got = extract_instruction_target_path(
        "önce tests/b.py sonra src/a.py",
        root,
    )
    assert got == "src/a.py"


def test_instruction_path_allowed_for_multi():
    assert instruction_path_allowed_for_multi("src/core/x.py")
    assert not instruction_path_allowed_for_multi("tests/t.py")
    assert not instruction_path_allowed_for_multi("src/core/tests/x.py")
    assert not instruction_path_allowed_for_multi("src/foo.py")


def test_select_instruction_multi_pair_order(tmp_path):
    root = tmp_path
    for rel in ("src/core/m1.py", "src/core/m2.py"):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# m\n", encoding="utf-8")
    ordered = extract_instruction_paths_ordered(
        "bak src/core/m1.py ve src/core/m2.py",
        root,
    )
    pair = select_instruction_multi_pair(ordered, root)
    assert pair == ["src/core/m1.py", "src/core/m2.py"]


def test_legacy_single_file_verify_block():
    rel, body, v = parse_patch_goal_legacy(
        "patch: foo/bar.txt\nx\nVERIFY:\npython -c \"1\""
    )
    assert rel == "foo/bar.txt"
    assert body == "x"
    assert v is not None


def test_extended_multi_sections():
    g = (
        "patch: a.txt,b.txt\n"
        "--- a.txt ---\n"
        "one\n"
        "--- b.txt ---\n"
        "two\n"
    )
    ext = parse_patch_goal_extended(g)
    assert ext.error is None
    assert ext.paths_ordered == ["a.txt", "b.txt"]
    assert ext.bodies["a.txt"] == "one"
    assert ext.bodies["b.txt"] == "two"
    an = analyze_patch_scope(ext)
    assert an.kind == "multi_file_required"
    assert len(an.apply_order) == 2


def test_files_block_and_primary():
    g = (
        "patch: src/x.py\n"
        "FILES:\n"
        "tests/test_x.py\n"
        "--- src/x.py ---\n"
        "a\n"
        "--- tests/test_x.py ---\n"
        "b\n"
    )
    ext = parse_patch_goal_extended(g)
    assert ext.error is None
    assert "src/x.py" in ext.paths_ordered
    assert "tests/test_x.py" in ext.paths_ordered
    an = analyze_patch_scope(ext)
    assert an.kind == "multi_file_required"
    assert "tests/test_x.py" in an.support_files or an.support_files


def test_blocked_glob():
    ext = parse_patch_goal_extended("patch: **/*.py\n--- **/*.py ---\nx\n")
    an = analyze_patch_scope(ext)
    assert an.kind == "blocked_scope_too_wide"


def test_blocked_too_many_paths():
    paths = [f"f{i}.txt" for i in range(MAX_PATHS_IN_SCOPE + 1)]
    first = ",".join(paths)
    sections = "\n".join(f"--- {p} ---\n{x}" for p, x in zip(paths, paths))
    g = f"patch: {first}\n{sections}"
    ext = parse_patch_goal_extended(g)
    assert ext.error is None
    an = analyze_patch_scope(ext)
    assert an.kind == "blocked_scope_too_wide"


def test_single_file_safe_classification():
    ext = parse_patch_goal_extended("patch: only.txt\nhello\n")
    an = analyze_patch_scope(ext)
    assert an.kind == "single_file_safe"


def test_legacy_returns_empty_for_multi():
    g = (
        "patch: a.txt,b.txt\n"
        "--- a.txt ---\n"
        "1\n"
        "--- b.txt ---\n"
        "2\n"
    )
    rel, body, v = parse_patch_goal_legacy(g)
    assert rel == "" and body == "" and v is None
