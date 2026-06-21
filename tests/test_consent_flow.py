"""Regression: consent vs general_approval separation (ADR-010).

consent_ok reflects consent.json or session_consent — NOT general_approval (genel onay).
"""
import tempfile
from pathlib import Path


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


def test_genel_onay_does_not_set_consent_ok():
    """general_approval (genel onay) alone does not imply consent_ok."""
    from core.startup_health import get_durum_parts, get_startup_summary

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        pl = _mock_presence()
        parts = get_durum_parts(base, False, pl, session_consent=False)
        assert parts["consent_ok"] is False
        summary = get_startup_summary(base, False, pl, session_consent=False)
        assert "Consent alınmadı" in summary or "consent alınmadı" in summary.lower()


def test_durum_parts_and_hazir_follow_session_consent():
    """get_durum_parts and get_startup_summary use session_consent, not general_approval."""
    from core.startup_health import get_durum_parts, get_startup_summary

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        pl = _mock_presence()
        keystore_ok = False

        session_consent: list = [False]

        parts = get_durum_parts(base, keystore_ok, pl, session_consent=session_consent[0])
        assert parts["consent_ok"] is False
        assert "consent alınmadı" in parts.get("not_line", "")
        summary = get_startup_summary(base, keystore_ok, pl, session_consent=session_consent[0])
        assert "Consent alınmadı" in summary or "consent alınmadı" in summary.lower()

        session_consent[0] = True
        parts = get_durum_parts(base, keystore_ok, pl, session_consent=session_consent[0])
        assert parts["consent_ok"] is True
        assert "consent alınmadı" not in (parts.get("not_line") or "")
        summary = get_startup_summary(base, keystore_ok, pl, session_consent=session_consent[0])
        assert "Consent alınmadı" not in summary and "consent alınmadı" not in summary.lower()

        session_consent[0] = False
        parts = get_durum_parts(base, keystore_ok, pl, session_consent=session_consent[0])
        assert parts["consent_ok"] is False
        summary = get_startup_summary(base, keystore_ok, pl, session_consent=session_consent[0])
        assert "Consent alınmadı" in summary or "consent alınmadı" in summary.lower()


def test_session_consent_from_ctx_reflects_session_list_not_ga():
    """ReadOnlyContext.session_consent is separate from general_approval."""
    from cli.cli_readonly import ReadOnlyContext, _session_consent_from_ctx

    session_consent: list = [False]
    general_approval: list = [False]
    ctx = ReadOnlyContext()
    ctx.base_dir = "/tmp"
    ctx.session_consent = session_consent
    ctx.general_approval = general_approval

    assert _session_consent_from_ctx(ctx) is False
    general_approval[0] = True
    assert _session_consent_from_ctx(ctx) is False
    session_consent[0] = True
    assert _session_consent_from_ctx(ctx) is True


def test_task_mutation_policy_consent_from_effective_consent_not_ga():
    """Policy context consent uses effective_consent(session_consent), not general_approval."""
    from cli.cli_tasks_mutation import TaskMutationContext, _task_mutation_policy_context

    with tempfile.TemporaryDirectory() as d:
        ctx = TaskMutationContext()
        ctx.base_dir = d
        ctx.general_approval = [True]
        ctx.session_consent = [False]
        ctx.policy_runtime_mode = "online"
        pol = _task_mutation_policy_context(ctx)
        assert pol["consent"] is False
        assert pol["general_approval"] is True

        ctx.session_consent[0] = True
        pol = _task_mutation_policy_context(ctx)
        assert pol["consent"] is True
