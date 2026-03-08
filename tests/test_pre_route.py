"""Focused tests for the minimal v1 decision layer (pre_route)."""
from __future__ import annotations

import os
from pathlib import Path

from lumos_core.context.context import Context
from lumos_core.policy.pre_route import pre_route


class TestPreRouteV1:
    """Verify pre_route behavior for main v1 cases."""

    def test_normal_question_goes_to_provider(self) -> None:
        """evren nedir -> provider, normal answer path."""
        ctx = Context(message="evren nedir")
        r = pre_route(ctx)
        assert r.destination == "provider", f"expected provider, got {r}"
        assert r.message == ""

    def test_explicit_device_tool_request_no_provider(self) -> None:
        """cihazın saatine bak -> tool_not_implemented, short clear Lumos message."""
        ctx = Context(message="cihazın saatine bak")
        r = pre_route(ctx)
        assert r.destination == "tool_not_implemented", f"expected tool_not_implemented, got {r}"
        assert "Lumos" in r.message
        assert "desteklenmiyor" in r.message

    def test_natural_command_relay_no_provider(self) -> None:
        """kankime slm söyle -> tool_not_implemented, Lumos limitation message."""
        ctx = Context(message="kankime slm söyle")
        r = pre_route(ctx)
        assert r.destination == "tool_not_implemented", f"expected tool_not_implemented, got {r}"
        assert "Lumos" in r.message
        assert "mesaj" in r.message or "söyleme" in r.message

    def test_empty_unsupported_no_provider(self) -> None:
        """Empty input -> unsupported, short Lumos explanation."""
        ctx = Context(message="")
        r = pre_route(ctx)
        assert r.destination == "unsupported", f"expected unsupported, got {r}"
        assert "Lumos" in r.message
        assert len(r.message) > 0

    def test_too_short_unsupported_no_provider(self) -> None:
        """? or very short -> unsupported."""
        ctx = Context(message="?")
        r = pre_route(ctx)
        assert r.destination == "unsupported", f"expected unsupported, got {r}"
        assert "Lumos" in r.message

    def test_read_this_file_routes_to_file_tool(self) -> None:
        """'read this file <path>' is handled by read-only file tool (destination=tool)."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "readme.txt").write_text("Hello from readme", encoding="utf-8")
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                ctx = Context(message="read this file readme.txt")
                r = pre_route(ctx)
                assert r.destination == "tool", f"expected tool, got {r.destination}"
                assert "Hello from readme" in r.message
            finally:
                os.chdir(old_cwd)

    def test_bu_dosyayi_oku_routes_to_file_tool(self) -> None:
        """'bu dosyayı oku <path>' is handled by read-only file tool (destination=tool)."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "notes.txt").write_text("Project notes here.", encoding="utf-8")
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                ctx = Context(message="bu dosyayı oku notes.txt")
                r = pre_route(ctx)
                assert r.destination == "tool", f"expected tool, got {r.destination}"
                assert "Project notes here" in r.message
            finally:
                os.chdir(old_cwd)

    def test_su_dosyayi_goster_routes_to_file_tool(self) -> None:
        """'şu dosyayı göster <path>' is handled by read-only file tool (destination=tool)."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "x.txt").write_text("icerik", encoding="utf-8")
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                ctx = Context(message="şu dosyayı göster x.txt")
                r = pre_route(ctx)
                assert r.destination == "tool", f"expected tool, got {r.destination}"
                assert "icerik" in r.message
            finally:
                os.chdir(old_cwd)

    def test_read_this_file_uses_current_file_from_context(self) -> None:
        """When message is 'read this file' with no path, pre_route uses ctx.current_file."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "README.md").write_text("# Project\nHello from README.", encoding="utf-8")
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                ctx = Context(message="read this file", current_file="README.md")
                r = pre_route(ctx)
                assert r.destination == "tool", f"expected tool, got {r.destination}"
                assert "Project" in r.message and "README" in r.message
            finally:
                os.chdir(old_cwd)

    def test_dosya_icerigini_ver_routes_to_file_tool(self) -> None:
        """'dosya içeriğini ver <path>' is handled by read-only file tool (destination=tool)."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "config.txt").write_text("config value", encoding="utf-8")
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                ctx = Context(message="dosya içeriğini ver config.txt")
                r = pre_route(ctx)
                assert r.destination == "tool", f"expected tool, got {r.destination}"
                assert "config value" in r.message
            finally:
                os.chdir(old_cwd)
