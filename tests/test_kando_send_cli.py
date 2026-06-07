"""Minimal tests for scripts/kando_send.py text helpers."""
from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_kando_send():
    path = Path(__file__).resolve().parents[1] / "scripts" / "kando_send.py"
    spec = importlib.util.spec_from_file_location("kando_send", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_resolve_message_text_argv_join():
    ks = _load_kando_send()
    assert ks.resolve_message_text(["a", "b", "c"]) == "a b c"
    assert ks.resolve_message_text(["tek satır"]) == "tek satır"


def test_resolve_message_text_stdin():
    ks = _load_kando_send()
    assert ks.resolve_message_text([], stdin_text="stdin görev") == "stdin görev"
    assert ks.resolve_message_text([], stdin_text="line1\nline2\n") == "line1\nline2"
    assert ks.resolve_message_text([], stdin_text="metin\n  \n") == "metin"


def test_resolve_message_text_empty_raises():
    ks = _load_kando_send()
    import pytest

    with pytest.raises(ValueError, match="boş"):
        ks.resolve_message_text([], stdin_text="   ")
    with pytest.raises(ValueError, match="boş"):
        ks.resolve_message_text([], stdin_text="")
