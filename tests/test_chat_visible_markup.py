"""Regression: raw TextReference markup must not stay in user-visible chat text."""

from __future__ import annotations

from pathlib import Path

from core.chat_visible_markup import strip_unsupported_chat_markup
from tests.test_panel_component_split import read_panel_source

_REPO = Path(__file__).resolve().parents[1]
_DEVICE_LEAK = (
    'artifacts/voice-stabilize-2026-09-18.log" start={1} end={20} '
    'alt="Voice stabilization test summary"></TextReference>'
)
_FULL_TAG = (
    "<TextReference\n"
    ' path="/opt/cursor/artifacts/voice-stabilize-2026-09-18.log"\n'
    " start={1}\n"
    " end={20}\n"
    ' alt="Voice stabilization test summary"></TextReference>'
)


def test_device_leak_tag_keeps_alt_and_drops_markup() -> None:
    payload = "Özet:\n" + _FULL_TAG + "\nDevam."
    out = strip_unsupported_chat_markup(payload)
    assert "TextReference" not in out
    assert "voice-stabilize-2026-09-18.log" not in out
    assert "start={1}" not in out
    assert "Voice stabilization test summary" in out
    assert out.startswith("Özet:")
    assert out.endswith("Devam.")
    assert _DEVICE_LEAK.split("alt=")[0] not in out


def test_inner_text_kept_when_alt_missing() -> None:
    raw = "A <TextReference path=\"x.log\">iç özet</TextReference> B"
    assert strip_unsupported_chat_markup(raw) == "A iç özet B"


def test_self_closing_alt() -> None:
    raw = 'Ön <TextReference alt="kısa özet" /> son'
    assert strip_unsupported_chat_markup(raw) == "Ön kısa özet son"


def test_html_escaped_tag_keeps_alt() -> None:
    raw = (
        "Not: &lt;TextReference path=\"a.log\" "
        'alt="Voice stabilization test summary"&gt;&lt;/TextReference&gt;.'
    )
    out = strip_unsupported_chat_markup(raw)
    assert "TextReference" not in out
    assert "Voice stabilization test summary" in out
    assert out.startswith("Not:")


def test_plain_prose_mention_is_unchanged() -> None:
    raw = "TextReference bir ajan etiketidir."
    assert strip_unsupported_chat_markup(raw) == raw


def test_none_and_empty() -> None:
    assert strip_unsupported_chat_markup(None) == ""
    assert strip_unsupported_chat_markup("") == ""


def test_panel_runtime_strips_markup_before_bubble_paint() -> None:
    text = read_panel_source()
    assert "function stripUnsupportedChatMarkup(" in text
    assert "stripUnsupportedChatMarkup(text)" in text
    assert "stripPanelTechnicalLeak(maskBridgeSensitive(stripUnsupportedChatMarkup(text)))" in text
    assert 'body.textContent = stripUnsupportedChatMarkup(text);' in text
    assert "textEl.textContent = stripUnsupportedChatMarkup(trimmed);" in text


def test_js_module_matches_python_device_leak() -> None:
    import json
    import subprocess

    payload = "Özet:\n" + _FULL_TAG + "\nDevam."
    module_uri = (_REPO / "api" / "_lib" / "chat_visible_markup.js").resolve().as_uri()
    script = (
        f"import {{ stripUnsupportedChatMarkup }} from {json.dumps(module_uri)};\n"
        f"const payload = {json.dumps(payload)};\n"
        "process.stdout.write(stripUnsupportedChatMarkup(payload));\n"
    )
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    assert proc.stdout == strip_unsupported_chat_markup(payload)


def test_hosted_reply_extractors_format_for_display() -> None:
    hosted = (_REPO / "api" / "_lib" / "hosted_lumos.js").read_text(encoding="utf-8")
    markup = (_REPO / "api" / "_lib" / "chat_visible_markup.js").read_text(encoding="utf-8")
    assert "export function stripUnsupportedChatMarkup(" in markup
    assert 'from "./chat_visible_markup.js"' in hosted
    assert "stripUnsupportedChatMarkup(" in hosted
