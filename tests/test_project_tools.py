"""Tests for read-only project structure tool: scan, ignored dirs, output limits, file purpose hints."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from lumos_core.context.context import Context
from lumos_core.policy.pre_route import pre_route
from lumos_core.tools.project_tools import (
    _MAX_DEPTH,
    _MAX_OUTPUT_LEN,
    _TRUNCATE_SUFFIX,
    try_handle_project_structure,
)


def _project_root() -> Path:
    """Project root (repo root) for tests that need a real directory with content."""
    return Path(__file__).resolve().parent.parent


class TestProjectStructureScan:
    """Scanning project structure returns a tree of files and folders."""

    def test_scan_returns_tree_with_dirs_and_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lumos_test_", dir=_project_root()) as tmp:
            cwd = Path(tmp)
            (cwd / "src").mkdir()
            (cwd / "src" / "app.py").write_text("", encoding="utf-8")
            (cwd / "README.md").write_text("# Proj", encoding="utf-8")
            result = try_handle_project_structure("scan project", cwd=cwd)
        assert result is not None
        assert "project structure:" in result
        assert "src/" in result
        assert "app.py" in result
        assert "README.md" in result

    def test_scan_via_pre_route(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lumos_test_", dir=_project_root()) as tmp:
            (Path(tmp) / "cli.py").write_text("cli", encoding="utf-8")
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                ctx = Context(message="projeyi tara")
                r = pre_route(ctx)
                assert r.destination == "tool"
                assert "project structure:" in r.message
                assert "cli.py" in r.message
            finally:
                os.chdir(old_cwd)

    def test_show_project_structure_pattern(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lumos_test_", dir=_project_root()) as tmp:
            cwd = Path(tmp)
            (cwd / "x.txt").write_text("", encoding="utf-8")
            result = try_handle_project_structure("show project structure", cwd=cwd)
        assert result is not None
        assert "project structure:" in result
        assert "x.txt" in result

    def test_repo_yapisi_nedir_pattern(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lumos_test_", dir=_project_root()) as tmp:
            cwd = Path(tmp)
            result = try_handle_project_structure("repo yapısı nedir", cwd=cwd)
        assert result is not None
        assert "project structure:" in result

    def test_scan_real_project_root_has_structure(self) -> None:
        """Scanning the actual repo root yields known dirs/files (smoke test)."""
        root = _project_root()
        result = try_handle_project_structure("scan project", cwd=root)
        assert result is not None
        assert "project structure:" in result
        # Repo has src/, tests/, pyproject.toml or similar
        assert "src/" in result or "lumos_core" in result or "tests/" in result


class TestProjectStructureIgnoredDirs:
    """Excluded folders (.git, __pycache__, .venv, node_modules) are not listed."""

    def test_ignores_git_and_pycache(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lumos_test_", dir=_project_root()) as tmp:
            cwd = Path(tmp)
            (cwd / ".git").mkdir()
            (cwd / "__pycache__").mkdir()
            (cwd / "visible").mkdir()
            (cwd / "visible" / "file.txt").write_text("", encoding="utf-8")
            result = try_handle_project_structure("scan project", cwd=cwd)
        assert result is not None
        assert ".git" not in result
        assert "__pycache__" not in result
        assert "visible/" in result
        assert "file.txt" in result

    def test_ignores_venv_and_node_modules(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lumos_test_", dir=_project_root()) as tmp:
            cwd = Path(tmp)
            (cwd / ".venv").mkdir()
            (cwd / "node_modules").mkdir()
            (cwd / "lib.py").write_text("", encoding="utf-8")
            result = try_handle_project_structure("proje yapısını göster", cwd=cwd)
        assert result is not None
        assert ".venv" not in result
        assert "node_modules" not in result
        assert "lib.py" in result

    def test_omits_binary_files_from_tree(self) -> None:
        """Known binary files (e.g. .png, .pdf) are not listed in the tree."""
        with tempfile.TemporaryDirectory(prefix="lumos_test_", dir=_project_root()) as tmp:
            cwd = Path(tmp)
            (cwd / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (cwd / "doc.pdf").write_bytes(b"%PDF-1.0")
            (cwd / "readme.txt").write_text("text", encoding="utf-8")
            result = try_handle_project_structure("scan project", cwd=cwd)
        assert result is not None
        assert "image.png" not in result
        assert "doc.pdf" not in result
        assert "readme.txt" in result


class TestProjectStructureOutputLimits:
    """Large project output is capped to avoid huge responses."""

    def test_depth_limited(self) -> None:
        """Tree stops at _MAX_DEPTH; deeper dirs are not listed."""
        with tempfile.TemporaryDirectory(prefix="lumos_test_", dir=_project_root()) as tmp:
            cwd = Path(tmp)
            d = cwd
            for i in range(_MAX_DEPTH + 3):
                d = d / f"level_{i}"
                d.mkdir()
            (d / "deep.txt").write_text("x", encoding="utf-8")
            result = try_handle_project_structure("scan project", cwd=cwd)
        assert result is not None
        assert "project structure:" in result
        # Deep file beyond max depth should not appear (tree stops at max depth)
        assert "deep.txt" not in result

    def test_output_capped(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lumos_test_", dir=_project_root()) as tmp:
            cwd = Path(tmp)
            for i in range(200):
                (cwd / f"file_{i:03d}.txt").write_text(f"content {i}", encoding="utf-8")
            result = try_handle_project_structure("scan project", cwd=cwd)
        assert result is not None
        assert len(result) <= _MAX_OUTPUT_LEN + len(_TRUNCATE_SUFFIX) + 50

    def test_truncation_suffix_present_when_capped(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lumos_test_", dir=_project_root()) as tmp:
            cwd = Path(tmp)
            for i in range(300):
                (cwd / f"f_{i}.txt").write_text("x", encoding="utf-8")
            result = try_handle_project_structure("project structure", cwd=cwd)
        assert result is not None
        if len(result) > _MAX_OUTPUT_LEN:
            assert "çıktı kısaltıldı" in result or "..." in result


class TestProjectStructureFilePurposeHint:
    """Small text files get a short purpose hint from docstring or comments."""

    def test_py_docstring_hint(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lumos_test_", dir=_project_root()) as tmp:
            cwd = Path(tmp)
            (cwd / "cli.py").write_text(
                '"""CLI entry point."""\nimport sys\n',
                encoding="utf-8",
            )
            result = try_handle_project_structure("scan project", cwd=cwd)
        assert result is not None
        assert "cli.py" in result
        assert "→" in result
        assert "CLI" in result or "entry" in result

    def test_py_comment_hint(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lumos_test_", dir=_project_root()) as tmp:
            cwd = Path(tmp)
            (cwd / "routing.py").write_text(
                "# routing logic\nfrom x import y\n",
                encoding="utf-8",
            )
            result = try_handle_project_structure("scan project", cwd=cwd)
        assert result is not None
        assert "routing.py" in result
        assert "→" in result
        assert "routing" in result

    def test_md_first_line_hint(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lumos_test_", dir=_project_root()) as tmp:
            cwd = Path(tmp)
            (cwd / "docs").mkdir()
            (cwd / "docs" / "intro.md").write_text(
                "# Architecture review\n\nSome text.",
                encoding="utf-8",
            )
            result = try_handle_project_structure("scan project", cwd=cwd)
        assert result is not None
        assert "intro.md" in result
        assert "→" in result


class TestProjectStructureNoMatch:
    """Unrelated messages do not trigger project scan; return None."""

    def test_unrelated_returns_none(self) -> None:
        assert try_handle_project_structure("evren nedir", cwd=Path.cwd()) is None
        assert try_handle_project_structure("read file x.txt", cwd=Path.cwd()) is None
