"""Telegram user connector skeleton: PRIMARY'de aktif, DEGRADED'da sadece oku + açıklama."""

from lumos_social.connectors.base import BaseConnector
from lumos_social.core.bus import EventBus
from lumos_social.core.events import Event
from lumos_social.runtime.mode import Mode, ModeReason, describe_mode


class TelegramUserConnector(BaseConnector):
    """PRIMARY: mesaj okuyup gönderir. DEGRADED: sadece okur, göndermez, açıklama üretir."""

    def __init__(self, mode: Mode = Mode.PRIMARY, reason: ModeReason | None = None) -> None:
        self._mode = mode
        self._reason = reason
        self._bus: EventBus | None = None
        self._stopped = False

    @property
    def name(self) -> str:
        return "telegram_user"

    def start(self, bus: EventBus) -> None:
        self._bus = bus
        self._stopped = False
        if self._mode == Mode.DEGRADED:
            desc = describe_mode(self._mode, self._reason)
            ev = Event(
                kind="mode_description",
                payload={"description": desc, "send_allowed": False},
                source=self.name,
            )
            bus.publish(ev)

    def stop(self) -> None:
        self._stopped = True
        self._bus = None

    def can_send(self) -> bool:
        """Sadece PRIMARY modda gönderim aktif."""
        return self._mode == Mode.PRIMARY

    def describe_for_user(self) -> str:
        """DEGRADED için kullanıcıya açıklama."""
        return describe_mode(self._mode, self._reason)
