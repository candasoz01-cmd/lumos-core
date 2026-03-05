from lumos_social.core import Event, EventBus


def test_event_bus_emits_and_handles():
    bus = EventBus()
    called = {"value": False}

    def handler(event: Event) -> None:
        called["value"] = True

    bus.subscribe("incoming_message", handler)
    bus.emit(Event(type="incoming_message", payload={}))

    assert called["value"] is True
