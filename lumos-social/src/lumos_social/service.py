"""Service: connector → event bus'a event basar."""

from lumos_social.connectors.base import BaseConnector, Update
from lumos_social.core.bus import EventBus
from lumos_social.core.events import Event, incoming_message_event


class SocialService:
    """Connector'dan update çeker, her biri için bus'a event publish eder."""

    def __init__(self, connector: BaseConnector, bus: EventBus) -> None:
        self._connector = connector
        self._bus = bus

    def fetch_and_publish(self) -> int:
        """Update çek → her update için bus'a event bas. Dönen: publish edilen event sayısı."""
        updates = self._connector.fetch_updates()
        for u in updates:
            event = self._update_to_event(u)
            self._bus.publish(event)
        return len(updates)

    def _update_to_event(self, update: Update) -> Event:
        return incoming_message_event(
            payload={"id": update.id, "kind": update.kind, **update.payload},
            source=update.source or self._connector.name,
        )
