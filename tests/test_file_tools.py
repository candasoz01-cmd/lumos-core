"""Tests for read-only file content tool: small file, large preview, missing file, binary, path traversal."""
from __future__ import annotations

import tempfile
from pathlib import Path

from lumos_core.context.context import Context
from lumos_core.policy.pre_route import pre_route
from lumos_core.tools.file_tools import (
    _MAX_OUTPUT_LEN,
    _MAX_PREVIEW_CHARS,
    try_handle_read_file,
)


class TestReadFileSmallFile:
    """Reading a small text file returns its content."""

    def test_read_small_file_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "hello.txt").write_text("Hello world\nLine two", encoding="utf-8")
            result = try_handle_read_file("read this file hello.txt", cwd=cwd)
            assert result is not None
            assert "Hello world" in result
            assert "Line two" in result
            assert "hello.txt" in result

    def test_read_file_via_pre_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "notes.txt").write_text("Project notes here.", encoding="utf-8")
            # Run from tmp so pre_route uses Path.cwd() = tmp
            import os
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                ctx = Context(message="bu dosyayı oku notes.txt")
                r = pre_route(ctx)
                assert r.destination == "tool"
                assert "Project notes here" in r.message
            finally:
                os.chdir(old_cwd)

    def test_dosya_icerigini_ver_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "x.txt").write_text("icerik", encoding="utf-8")
            result = try_handle_read_file("dosya içeriğini ver x.txt", cwd=cwd)
            assert result is not None
            assert "icerik" in result

    def test_read_this_file_with_current_file(self) -> None:
        """When user says 'read this file' with no path, current_file from context is used."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "README.md").write_text("# Project\nHello from README.", encoding="utf-8")
            result = try_handle_read_file(
                "read this file",
                cwd=cwd,
                current_file="README.md",
            )
            assert result is not None
            assert "Project" in result and "README" in result


class TestReadFileLargePreview:
    """Large file returns bounded preview."""

    def test_large_file_preview_truncated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            content = "x" * (_MAX_PREVIEW_CHARS + 5000)
            (cwd / "big.txt").write_text(content, encoding="utf-8")
            result = try_handle_read_file("read file big.txt", cwd=cwd)
            assert result is not None
            assert "dosya büyük" in result or "önizleme kısaltıldı" in result
            assert len(result) <= _MAX_OUTPUT_LEN + 100

    def test_output_size_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "small.txt").write_text("short", encoding="utf-8")
            result = try_handle_read_file("read file small.txt", cwd=cwd)
            assert result is not None
            assert len(result) <= _MAX_OUTPUT_LEN + 100


class TestReadFileMissing:
    """Missing file returns clear message, no traceback."""

    def test_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = try_handle_read_file("read this file nonexistent.txt", cwd=cwd)
            assert result is not None
            assert "Lumos" in result
            assert "bulunamadı" in result or "Dosya" in result
            assert "Traceback" not in result

    def test_missing_file_via_pre_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            import os
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                ctx = Context(message="şu dosyayı göster no_such_file.txt")
                r = pre_route(ctx)
                assert r.destination == "tool"
                assert "Lumos" in r.message
                assert "Traceback" not in r.message
            finally:
                os.chdir(old_cwd)


class TestReadFileBinary:
    """Binary or unsupported file returns clear message."""

    def test_binary_extension_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            result = try_handle_read_file("read file image.png", cwd=cwd)
            assert result is not None
            assert "Lumos" in result
            assert "ikili" in result or "desteklenmiyor" in result or "metin" in result

    def test_binary_content_null_byte_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "data.bin").write_bytes(b"text\x00more")
            result = try_handle_read_file("read file data.bin", cwd=cwd)
            assert result is not None
            assert "Lumos" in result
            assert "ikili" in result or "desteklenmiyor" in result


class TestReadFilePathTraversal:
    """Path traversal is prevented; only files under cwd are readable."""

    def test_path_traversal_returns_missing_or_safe_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "allowed.txt").write_text("ok", encoding="utf-8")
            # Try to escape with ../ — resolved path is outside cwd, so we get "file not found"
            result = try_handle_read_file("read file ../allowed.txt", cwd=cwd)
            assert result is not None
            assert "Lumos" in result
            assert "ok" not in result  # must not leak content from outside cwd
            assert "Traceback" not in result

    def test_subdir_file_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            sub = cwd / "sub"
            sub.mkdir()
            (sub / "inner.txt").write_text("inner content", encoding="utf-8")
            result = try_handle_read_file("read file sub/inner.txt", cwd=cwd)
            assert result is not None
            assert "inner content" in result


class TestReadFileNoMatch:
    """Unrelated messages do not trigger file read; return None."""

    def test_unrelated_returns_none(self) -> None:
        assert try_handle_read_file("evren nedir", cwd=Path.cwd()) is None
        assert try_handle_read_file("hello world", cwd=Path.cwd()) is None

    def test_matched_but_no_path_returns_which_file_message(self) -> None:
        result = try_handle_read_file("bu dosyayı oku", cwd=Path.cwd(), current_file=None)
        assert result is not None
        assert "Hangi dosyayı" in result or "Lumos" in result
