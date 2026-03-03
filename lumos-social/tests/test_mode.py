"""Runtime mode: describe_mode, reasons."""

from lumos_social.runtime.mode import Mode, ModeReason, describe_mode


def test_describe_mode_primary() -> None:
    s = describe_mode(Mode.PRIMARY, None)
    assert "Tam yetki" in s or "primary" in s.lower()


def test_describe_mode_degraded_with_reason() -> None:
    s = describe_mode(Mode.DEGRADED, ModeReason.POLICY_LOCK)
    assert "İlke" in s or "policy" in s.lower() or "Sebep" in s


def test_mode_reason_values() -> None:
    assert ModeReason.NO_PRIMARY_ACCESS.value == "no_primary_access"
    assert ModeReason.NO_SESSION.value == "no_session"
