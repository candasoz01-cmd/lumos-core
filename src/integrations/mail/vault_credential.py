from __future__ import annotations

from dataclasses import dataclass

# Amaç kodları — tam liste private; public yalnızca iskelet referansı.
VAULT_PURPOSE_MAIL_READ = "integration.mail.read"
VAULT_PURPOSE_MAIL_NOTIFY = "integration.mail.notify"

MAIL_VAULT_PROVIDER = "gmail_oauth"


@dataclass(frozen=True)
class VaultCredentialRef:
    """Opak vault referansı — secret/token içermez."""

    purpose_code: str
    ref_id: str
    account_id: str


class DemoVaultCredentialBridge:
    """Demo-safe stub — gerçek vault/Infisical bağlantısı private katmanda."""

    def is_configured(self, ref: VaultCredentialRef) -> bool:
        return False

    def connection_hint(self, ref: VaultCredentialRef) -> dict[str, str | bool]:
        return {
            "configured": False,
            "provider": MAIL_VAULT_PROVIDER,
            "purpose_code": ref.purpose_code,
            "boundary": "private_vault_impl_required",
        }


_default_bridge = DemoVaultCredentialBridge()


def get_vault_credential_bridge() -> DemoVaultCredentialBridge:
    return _default_bridge


def mail_read_credential_ref(account_id: str) -> VaultCredentialRef:
    return VaultCredentialRef(
        purpose_code=VAULT_PURPOSE_MAIL_READ,
        ref_id=f"mail-read:{account_id}",
        account_id=account_id,
    )
