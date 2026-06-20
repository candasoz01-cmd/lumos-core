from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MailMessageSummary:
    """Demo-safe özet — tam gövde, ham token veya PII yok."""

    message_id: str
    subject_preview: str
    from_preview: str
    received_at: str


@dataclass(frozen=True)
class MailConnectionStatus:
    provider: str
    vault_configured: bool
    connector_ready: bool
    account_id: str = ""
