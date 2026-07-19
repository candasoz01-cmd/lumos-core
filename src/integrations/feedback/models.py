from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FeedbackRecord:
    feedback_id: str
    source_provider: str
    source_workspace: str
    source_channel_id: str
    source_channel: str
    source_message_id: str
    source_url: str
    author_display: str
    received_at: str
    feedback_type: str
    priority: str
    status: str
    summary: str
    original_text: str

    @property
    def deduplication_key(self) -> tuple[str, str, str, str]:
        return (
            self.source_provider,
            self.source_workspace,
            self.source_channel_id,
            self.source_message_id,
        )

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class FeedbackIngestResult:
    accepted: bool
    status: str
    duplicate: bool = False
    record: FeedbackRecord | None = None
    error: str = ""
