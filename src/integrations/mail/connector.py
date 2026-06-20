from __future__ import annotations

from typing import Protocol

from integrations.mail.models import MailMessageSummary

MAIL_PROVIDER_GMAIL_OAUTH = "gmail_oauth"


class MailConnector(Protocol):
    """Mail connector arayüzü — gerçek Gmail API private katmanda."""

    provider: str

    def list_unread_summaries(self, *, account_id: str, limit: int = 10) -> list[MailMessageSummary]:
        ...


class StubMailConnector:
    """Demo-safe stub — OAuth/Gmail API yok; sabit örnek özetler."""

    provider = MAIL_PROVIDER_GMAIL_OAUTH

    def list_unread_summaries(self, *, account_id: str, limit: int = 10) -> list[MailMessageSummary]:
        cap = max(1, min(limit, 20))
        samples = [
            MailMessageSummary(
                message_id="demo-msg-001",
                subject_preview="[demo] Bildirim testi",
                from_preview="demo@example.invalid",
                received_at="2026-06-20T12:00:00Z",
            ),
            MailMessageSummary(
                message_id="demo-msg-002",
                subject_preview="[demo] Okuma özeti",
                from_preview="notify@example.invalid",
                received_at="2026-06-20T11:30:00Z",
            ),
        ]
        return samples[:cap]


_default_connector = StubMailConnector()


def get_mail_connector(
    *,
    account_id: str = "",
    vault_configured: bool = False,
    grants_include_read: bool = False,
    vault_bridge=None,
) -> MailConnector:
    """Vault + read grant OK ise GmailOAuthConnector; aksi halde stub."""
    if vault_configured and grants_include_read and account_id.strip():
        from integrations.mail.providers.gmail_oauth import GmailOAuthConnector

        return GmailOAuthConnector(vault_bridge=vault_bridge, account_id=account_id)
    return _default_connector
