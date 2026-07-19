from __future__ import annotations

from .models import FeedbackRecord


class InMemoryFeedbackStore:
    """Small event sink; durable storage can implement the same add contract later."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str, str], FeedbackRecord] = {}

    def add(self, record: FeedbackRecord) -> bool:
        key = record.deduplication_key
        if key in self._records:
            return False
        self._records[key] = record
        return True

    def records(self) -> tuple[FeedbackRecord, ...]:
        return tuple(self._records.values())
