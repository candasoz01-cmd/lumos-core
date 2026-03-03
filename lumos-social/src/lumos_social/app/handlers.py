"""Register event handlers on the bus."""

from lumos_social.core.bus import EventBus
from lumos_social.core.events import Event


def _on_incoming_message(event: Event) -> None:
    if event.kind != "incoming_message":
        return
    p = event.payload
    platform = p.get("platform", "")
    from_user = p.get("from_user", "")
    text = p.get("text", "")
    print(f"incoming_message platform={platform} from={from_user} text={text}")


def register_handlers(bus: EventBus) -> None:
    """Subscribe incoming_message and other handlers to the bus."""
    bus.subscribe(_on_incoming_message)
