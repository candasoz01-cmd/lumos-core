from lumos_social.runtime.mode import Mode, ModeReason, describe_mode


def test_primary_mode():
    text = describe_mode(Mode.PRIMARY)
    assert "tam kapasite" in text


def test_degraded_reason():
    text = describe_mode(Mode.DEGRADED, ModeReason.NO_SESSION)
    assert "Telegram oturumu" in text
