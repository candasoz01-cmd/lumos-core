"""Tests for core.next_step: suggest_next_step for locked, consent_missing, tool_unavailable, clarification_needed."""
from __future__ import annotations

from core.next_step import (
    REASON_CLARIFICATION_NEEDED,
    REASON_CONSENT_MISSING,
    REASON_LOCKED,
    REASON_TOOL_UNAVAILABLE,
    suggest_next_step,
)


def test_next_step_locked():
    """locked -> next_step: kilit aç, message explains block and next step."""
    g = suggest_next_step(None, None, REASON_LOCKED, None)
    assert g["blocked"] is True
    assert g["reason"] == "locked"
    assert g["next_step"] == "kilit aç"
    assert "kilit" in g["message"] and "Sonraki adım" in g["message"]


def test_next_step_consent_missing():
    """consent_missing -> next_step: onaylıyorum."""
    g = suggest_next_step(None, None, REASON_CONSENT_MISSING, None)
    assert g["blocked"] is True
    assert g["reason"] == "consent_missing"
    assert g["next_step"] == "onaylıyorum"
    assert "onay" in g["message"] and "Sonraki adım" in g["message"]


def test_next_step_tool_unavailable():
    """tool_unavailable -> next_step explanatory message."""
    g = suggest_next_step("list_files", None, REASON_TOOL_UNAVAILABLE, None)
    assert g["blocked"] is True
    assert g["reason"] == "tool_unavailable"
    assert "mevcut değil" in g["message"]
    assert "Sonraki adım" in g["message"] or "terminal" in g["message"].lower()


def test_next_step_clarification_needed_folder():
    """clarification_needed + missing_param=folder -> next_step: klasör adını yaz."""
    g = suggest_next_step("list_files", None, REASON_CLARIFICATION_NEEDED, "folder")
    assert g["blocked"] is True
    assert g["reason"] == "clarification_needed"
    assert g["next_step"] == "klasör adını yaz"
    assert "Hangi klasör" in g["message"] or "klasör" in g["message"]


def test_next_step_clarification_needed_other():
    """clarification_needed without folder -> generic next_step."""
    g = suggest_next_step("other", None, REASON_CLARIFICATION_NEEDED, "other_param")
    assert g["blocked"] is True
    assert "eksik" in g["next_step"] or "parametre" in g["next_step"]
