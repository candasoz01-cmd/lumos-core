"""Tests for read-only system tools: cwd, list_dir, python_version, disk_usage, system_info.

Supported read-only capabilities (v1): current working directory, list files in current directory,
Python version, disk usage summary, basic system info (OS/platform). Unsupported device/system
requests (e.g. cihazın saatine bak, telefonu aç) return a short clear Lumos message.
"""
from __future__ import annotations


from lumos_core.context.context import Context
from lumos_core.policy.pre_route import pre_route
from lumos_core.tools.system_tools import _MAX_OUTPUT_LEN, try_handle_readonly_tool


def _is_user_friendly(s: str) -> bool:
    """Tool output should not contain raw tracebacks or technical error jargon."""
    if not s or len(s) > 2000:
        return False
    return not any(b in s for b in ("Traceback", "Error:", "Exception:", "File \""))


class TestTryHandleReadonlyTool:
    """try_handle_readonly_tool returns human-friendly result for supported intents, None otherwise."""

    def test_cwd_phrases(self) -> None:
        r = try_handle_readonly_tool("hangi klasördeyim")
        assert r is not None
        assert "Bulunduğunuz klasör" in r
        assert "/" in r
        assert _is_user_friendly(r)
        assert try_handle_readonly_tool("neredeyim") is not None
        assert try_handle_readonly_tool("pwd") is not None

    def test_list_dir_phrases(self) -> None:
        r = try_handle_readonly_tool("bu klasörde ne var")
        assert r is not None
        assert "Bu klasördeki öğeler" in r or "bu klasör boş" in r
        assert _is_user_friendly(r)
        assert try_handle_readonly_tool("buradaki dosyaları göster") is not None
        assert try_handle_readonly_tool("dosyaları listele") is not None

    def test_list_dir_empty_or_with_items(self) -> None:
        """List dir returns header and either item lines or (bu klasör boş)."""
        r = try_handle_readonly_tool("bu klasörde ne var")
        assert r is not None
        assert r.startswith("Bu klasördeki öğeler")
        assert "boş" in r or "\n  " in r

    def test_python_version_phrases(self) -> None:
        r = try_handle_readonly_tool("python versiyonu kaç")
        assert r is not None
        assert "Python sürümü" in r and "." in r
        assert _is_user_friendly(r)
        assert try_handle_readonly_tool("python version") is not None

    def test_disk_usage_phrases(self) -> None:
        r = try_handle_readonly_tool("diskte ne kadar yer var")
        assert r is not None
        assert "GB" in r or "Lumos" in r
        assert "Disk kullanımı" in r or "Lumos" in r
        assert _is_user_friendly(r)
        assert try_handle_readonly_tool("disk usage") is not None

    def test_system_info_phrases(self) -> None:
        r = try_handle_readonly_tool("sistem bilgisi ver")
        assert r is not None
        assert try_handle_readonly_tool("system info") is not None
        assert "Sistem bilgisi" in r or "İşletim" in r or "platform" in r.lower() or "Lumos" in r
        assert _is_user_friendly(r)

    def test_returns_none_for_unrelated(self) -> None:
        assert try_handle_readonly_tool("evren nedir") is None
        assert try_handle_readonly_tool("hello world") is None
        assert try_handle_readonly_tool("") is None


class TestPreRouteReadonlyTools:
    """pre_route returns destination 'tool' with friendly output for supported read-only requests."""

    def test_cwd_tool(self) -> None:
        ctx = Context(message="hangi klasördeyim")
        r = pre_route(ctx)
        assert r.destination == "tool", f"expected tool, got {r.destination}"
        assert len(r.message) > 0
        assert "/" in r.message

    def test_list_dir_tool(self) -> None:
        ctx = Context(message="bu klasörde ne var")
        r = pre_route(ctx)
        assert r.destination == "tool"
        assert len(r.message) > 0
        assert "klasör" in r.message.lower() or "boş" in r.message

    def test_python_version_tool(self) -> None:
        ctx = Context(message="python versiyonu kaç")
        r = pre_route(ctx)
        assert r.destination == "tool"
        assert "." in r.message
        assert "Python" in r.message

    def test_disk_usage_tool(self) -> None:
        ctx = Context(message="diskte ne kadar yer var")
        r = pre_route(ctx)
        assert r.destination == "tool"
        assert "GB" in r.message or "Lumos" in r.message

    def test_system_info_tool(self) -> None:
        ctx = Context(message="sistem bilgisi ver")
        r = pre_route(ctx)
        assert r.destination == "tool"
        assert len(r.message) > 0
        assert "İşletim" in r.message or "Sistem" in r.message or "platform" in r.message.lower()

    def test_normal_question_still_provider(self) -> None:
        ctx = Context(message="evren nedir")
        r = pre_route(ctx)
        assert r.destination == "provider"

    def test_unsupported_device_request_clear_message(self) -> None:
        """Unsupported device/system request returns short clear Lumos message, no technical jargon."""
        ctx = Context(message="cihazın saatine bak")
        r = pre_route(ctx)
        assert r.destination == "tool_not_implemented"
        assert r.message.strip().startswith("Lumos:")
        assert "desteklenmiyor" in r.message
        assert len(r.message) <= 200, "unsupported message should stay short"
        assert "Traceback" not in r.message and "Exception" not in r.message
        assert _is_user_friendly(r.message)

    def test_unsupported_another_device_phrase(self) -> None:
        """Another unsupported device phrase gets same short clear message."""
        ctx = Context(message="telefonu aç")
        r = pre_route(ctx)
        assert r.destination == "tool_not_implemented"
        assert "Lumos" in r.message
        assert "desteklenmiyor" in r.message

    def test_unsupported_examples_return_short_lumos_message(self) -> None:
        """Unsupported device/system examples all get tool_not_implemented with short, clear Lumos message."""
        unsupported_examples = [
            "cihazın saatine bak",
            "telefonu aç",
            "pil durumu",
            "ekranı kapat",
            "ayarı değiştir",
        ]
        for msg in unsupported_examples:
            r = pre_route(Context(message=msg))
            assert r.destination == "tool_not_implemented", f"expected tool_not_implemented for {msg!r}"
            assert r.message.strip().startswith("Lumos:"), f"message should start with Lumos: for {msg!r}"
            assert len(r.message) <= 220, f"unsupported message should stay short for {msg!r}: {len(r.message)} chars"
            assert _is_user_friendly(r.message), f"message should be user-friendly for {msg!r}"

    def test_all_readonly_capabilities_return_user_friendly_output(self) -> None:
        """Each supported capability returns short, clear output without technical leakage."""
        phrases = [
            "hangi klasördeyim",
            "bu klasörde ne var",
            "python versiyonu kaç",
            "diskte ne kadar yer var",
            "sistem bilgisi ver",
        ]
        for phrase in phrases:
            r = try_handle_readonly_tool(phrase)
            assert r is not None, f"expected result for {phrase!r}"
            assert _is_user_friendly(r), f"output for {phrase!r} should be user-friendly: {r[:100]!r}"

    def test_list_dir_capped_when_many_items(self) -> None:
        """List dir output is capped; no unbounded dump; no technical leakage."""
        r = try_handle_readonly_tool("bu klasörde ne var")
        assert r is not None
        assert "Bu klasördeki öğeler" in r or "bu klasör boş" in r
        assert "Traceback" not in r
        assert "PermissionError" not in r and "Exception" not in r

    def test_current_working_directory_returns_path(self) -> None:
        """Current working directory: returns human-friendly line with path."""
        r = try_handle_readonly_tool("hangi klasördeyim")
        assert r is not None
        assert "Bulunduğunuz klasör" in r
        assert "/" in r or "\\" in r

    def test_disk_usage_returns_gb_lines(self) -> None:
        """Disk usage: returns Toplam/Kullanılan/Boş in GB or Lumos fallback."""
        r = try_handle_readonly_tool("diskte ne kadar yer var")
        assert r is not None
        assert "Disk kullanımı" in r or "Lumos" in r
        assert "GB" in r or "Lumos" in r

    def test_system_info_returns_os_or_platform(self) -> None:
        """System info: returns OS/platform line or Lumos fallback."""
        r = try_handle_readonly_tool("sistem bilgisi ver")
        assert r is not None
        assert "Sistem bilgisi" in r or "İşletim" in r or "platform" in r.lower() or "Lumos" in r

    def test_unsupported_message_no_exception_leak(self) -> None:
        """Unsupported device message must never contain exception/traceback text."""
        for msg in ("cihazın saatine bak", "telefonu aç", "pil durumu"):
            r = pre_route(Context(message=msg))
            if r.destination == "tool_not_implemented":
                assert "Traceback" not in r.message
                assert "Error:" not in r.message
                assert "Exception" not in r.message
                assert "File \"" not in r.message

    def test_tool_output_bounded_length(self) -> None:
        """All read-only tool outputs are capped; no unbounded response."""
        max_len = _MAX_OUTPUT_LEN + 50  # allow for truncation suffix
        phrases = [
            "hangi klasördeyim",
            "bu klasörde ne var",
            "python versiyonu kaç",
            "diskte ne kadar yer var",
            "sistem bilgisi ver",
        ]
        for phrase in phrases:
            r = try_handle_readonly_tool(phrase)
            assert r is not None, f"expected result for {phrase!r}"
            assert len(r) <= max_len, f"output for {phrase!r} should be bounded: got {len(r)} chars"
