"""Regression: consent (genel onay aç/kapat) is a single source of truth for durum, hazır, and policy.

After 'genel onay aç', durum and hazır must reflect consent active; after 'genel onay kapat' they revert.
"""
import tempfile
from pathlib import Path

import pytest


def _mock_presence():
    """Minimal presence module: load_presence_cfg returns enabled=False so we don't touch camera."""
    class Cfg:
        enabled = False

    class Mod:
        def load_presence_cfg(self, base_dir: Path):
            return Cfg()

    return Mod()


def test_effective_consent_session_overrides_when_no_file():
    """Without consent.json, effective_consent is True only when session_consent is True."""
    from core.startup_health import effective_consent

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        assert effective_consent(base, False) is False
        assert effective_consent(base, True) is True


def test_effective_consent_file_implies_true():
    """With consent.json, effective_consent is True regardless of session_consent."""
    from core.startup_health import effective_consent

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        (base / "consent.json").write_text("{}")
        assert effective_consent(base, False) is True
        assert effective_consent(base, True) is True


def test_durum_parts_and_hazir_follow_session_consent():
    """get_durum_parts and get_startup_summary use session consent; genel onay aç/kapat flow is consistent."""
    from core.startup_health import get_durum_parts, get_startup_summary

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        pl = _mock_presence()
        keystore_ok = False  # lock not required for consent_ok to reflect

        # Same ref as router: genel onay aç sets [0]=True, genel onay kapat sets [0]=False
        general_approval: list = [False]

        # No file consent; session closed -> consent_ok False, hazır says consent alınmadı
        parts = get_durum_parts(base, keystore_ok, pl, session_consent=general_approval[0])
        assert parts["consent_ok"] is False
        assert "consent alınmadı" in parts.get("not_line", "")
        summary = get_startup_summary(base, keystore_ok, pl, session_consent=general_approval[0])
        assert "Consent alınmadı" in summary or "consent alınmadı" in summary.lower()

        # Genel onay aç
        general_approval[0] = True
        parts = get_durum_parts(base, keystore_ok, pl, session_consent=general_approval[0])
        assert parts["consent_ok"] is True
        assert "consent alınmadı" not in (parts.get("not_line") or "")
        summary = get_startup_summary(base, keystore_ok, pl, session_consent=general_approval[0])
        assert "Consent alınmadı" not in summary and "consent alınmadı" not in summary.lower()

        # Genel onay kapat
        general_approval[0] = False
        parts = get_durum_parts(base, keystore_ok, pl, session_consent=general_approval[0])
        assert parts["consent_ok"] is False
        assert "consent alınmadı" in (parts.get("not_line") or "")
        summary = get_startup_summary(base, keystore_ok, pl, session_consent=general_approval[0])
        assert "Consent alınmadı" in summary or "consent alınmadı" in summary.lower()


def test_session_consent_from_ctx_reflects_same_list():
    """ReadOnlyContext.general_approval same ref as mut_ctx; _session_consent_from_ctx reflects it."""
    from cli.cli_readonly import ReadOnlyContext, _session_consent_from_ctx

    general_approval: list = [False]
    ctx = ReadOnlyContext()
    ctx.base_dir = "/tmp"
    ctx.general_approval = general_approval

    assert _session_consent_from_ctx(ctx) is False
    general_approval[0] = True
    assert _session_consent_from_ctx(ctx) is True
    general_approval[0] = False
    assert _session_consent_from_ctx(ctx) is False
