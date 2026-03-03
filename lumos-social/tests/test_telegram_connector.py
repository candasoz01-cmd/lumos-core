"""TelegramUserConnector: PRIMARY vs DEGRADED."""

from lumos_social.connectors.telegram_user import TelegramUserConnector
from lumos_social.core.bus import EventBus
from lumos_social.core.events import Event
from lumos_social.runtime.mode import Mode, ModeReason


def test_primary_can_send() -> None:
    c = TelegramUserConnector(mode=Mode.PRIMARY)
    assert c.can_send() is True


def test_degraded_cannot_send() -> None:
    c = TelegramUserConnector(mode=Mode.DEGRADED, reason=ModeReason.POLICY_LOCK)
    assert c.can_send() is False


def test_degraded_emits_mode_description() -> None:
    bus = EventBus()
    seen: list[Event] = []
    bus.subscribe(seen.append)
    c = TelegramUserConnector(mode=Mode.DEGRADED, reason=ModeReason.NO_SESSION)
    c.start(bus)
    assert len(seen) == 1
    assert seen[0].kind == "mode_description"
    assert seen[0].payload.get("send_allowed") is False
    c.stop()
