from __future__ import annotations

from integrations.mail.connector import MAIL_PROVIDER_GMAIL_OAUTH, StubMailConnector
from integrations.mail.models import MailMessageSummary
from integrations.mail.vault_credential import (
    DemoVaultCredentialBridge,
    VaultCredentialRef,
    mail_read_credential_ref,
)
from integrations.vault.purpose_codes import PURPOSE_MAIL_READ

# Gmail OAuth read-only scope — public-safe sabit; client secret repo'da yok.
GMAIL_OAUTH_SCOPE_READONLY = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_OAUTH_SCOPES_DAR_V1 = frozenset({GMAIL_OAUTH_SCOPE_READONLY})


class GmailOAuthConnector:
    """Gmail OAuth read-only connector — vault credential ile read path; yoksa stub."""

    provider = MAIL_PROVIDER_GMAIL_OAUTH

    def __init__(
        self,
        *,
        vault_bridge: DemoVaultCredentialBridge | None = None,
        account_id: str = "",
    ) -> None:
        self._vault = vault_bridge
        self._account_id = account_id
        self._stub = StubMailConnector()

    def list_unread_summaries(self, *, account_id: str, limit: int = 10) -> list[MailMessageSummary]:
        cap = max(1, min(limit, 20))
        vault = self._vault
        if vault is None:
            return self._stub.list_unread_summaries(account_id=account_id, limit=cap)

        ref = mail_read_credential_ref(account_id)
        if not vault.is_configured(ref):
            return self._stub.list_unread_summaries(account_id=account_id, limit=cap)

        resolution = vault.resolve_credential(ref)
        if not resolution.ok:
            return self._stub.list_unread_summaries(account_id=account_id, limit=cap)

        return self._vault_backed_summaries(account_id=account_id, cap=cap, ref=ref)

    def _vault_backed_summaries(
        self,
        *,
        account_id: str,
        cap: int,
        ref: VaultCredentialRef,
    ) -> list[MailMessageSummary]:
        """Vault-backed read path — public repo'da canlı Gmail API yok; mock-friendly özet."""
        samples = [
            MailMessageSummary(
                message_id=f"vault-{ref.ref_id}-001",
                subject_preview="[vault-backed] Okunmamış özet",
                from_preview="inbox@example.invalid",
                received_at="2026-06-20T14:00:00Z",
            ),
            MailMessageSummary(
                message_id=f"vault-{ref.ref_id}-002",
                subject_preview="[vault-backed] Bildirim adayı",
                from_preview="alerts@example.invalid",
                received_at="2026-06-20T13:45:00Z",
            ),
        ]
        _ = account_id  # account scope reserved for private Gmail API impl
        _ = PURPOSE_MAIL_READ
        return samples[:cap]
