"""Core: event bus + pipeline. Publish → handler runs."""

from lumos_social.core.bus import EventBus
from lumos_social.core.events import Event, incoming_message_event
from lumos_social.core.pipeline import Pipeline, log_handler


def test_publish_incoming_message_handler_runs() -> None:
    """Publish 'incoming_message' → pipeline handler is invoked."""
    bus = EventBus()
    pipeline = Pipeline()
    seen: list[Event] = []

    def capture(e: Event) -> None:
        seen.append(e)

    pipeline.add_handler(capture)
    pipeline.add_handler(log_handler)
    bus.subscribe(pipeline.process)

    event = incoming_message_event(payload={"text": "hello"}, source="test")
    bus.publish(event)

    assert len(seen) == 1
    assert seen[0].kind == "incoming_message"
    assert seen[0].payload["text"] == "hello"
    assert seen[0].source == "test"


def test_bus_stats() -> None:
    bus = EventBus()
    pipeline = Pipeline()
    pipeline.add_handler(log_handler)
    bus.subscribe(pipeline.process)
    bus.publish(incoming_message_event(payload={}))
    bus.publish(incoming_message_event(payload={}))
    assert bus.stats()["events_seen"] == 2
    assert bus.stats()["handlers"] == 1


def test_pipeline_process_runs_handlers_in_order() -> None:
    order: list[str] = []
    pipeline = Pipeline()
    pipeline.add_handler(lambda e: order.append("first"))
    pipeline.add_handler(lambda e: order.append("second"))
    pipeline.process(incoming_message_event(payload={}))
    assert order == ["first", "second"]
