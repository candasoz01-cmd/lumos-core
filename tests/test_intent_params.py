"""Tests for core.intent_params: extract_intent_params for deterministic intents."""
from __future__ import annotations

from core.intent_params import extract_intent_params


def test_list_files_extract_folder_klasorunu():
    """WORK_2026 klasörünü listele -> folder = WORK_2026."""
    out = extract_intent_params("list_files", "WORK_2026 klasörünü listele")
    assert out == {"folder": "WORK_2026"}


def test_list_files_extract_folder_listele():
    """work_2026 listele -> folder = work_2026."""
    out = extract_intent_params("list_files", "work_2026 listele")
    assert out == {"folder": "work_2026"}


def test_list_files_extract_folder_dosyalari():
    """lumos-core dosyaları listele -> folder = lumos-core."""
    out = extract_intent_params("list_files", "lumos-core dosyaları listele")
    assert out == {"folder": "lumos-core"}


def test_list_files_no_folder_dosyalari_listele():
    """dosyaları listele (no folder) -> empty params."""
    out = extract_intent_params("list_files", "dosyaları listele")
    assert out == {}


def test_list_files_no_folder_klasordeki():
    """klasördeki dosyaları listele (no folder name) -> empty params."""
    out = extract_intent_params("list_files", "klasördeki dosyaları listele")
    assert out == {}


def test_unlock_lock_exit_no_params():
    """unlock, lock, exit -> no params."""
    assert extract_intent_params("unlock", "kilit aç") == {}
    assert extract_intent_params("lock", "kilit kapat") == {}
    assert extract_intent_params("exit", "çık") == {}
