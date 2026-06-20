from __future__ import annotations

from dataclasses import dataclass

from integrations.vault.adapter import CredentialResolution, InfisicalVaultAdapter, get_default_vault_adapter
from integrations.vault.purpose_codes import PURPOSE_MAIL_NOTIFY, PURPOSE_MAIL_READ

# Geriye uyumluluk — amaç kodları vault katmanından re-export.
VAULT_PURPOSE_MAIL_READ = PURPOSE_MAIL_READ
VAULT_PURPOSE_MAIL_NOTIFY = PURPOSE_MAIL_NOTIFY

MAIL_VAULT_PROVIDER = "gmail_oauth"


@dataclass(frozen=True)
class VaultCredentialRef:
    """Opak vault referansı — secret/token içermez."""

    purpose_code: str
    ref_id: str
    account_id: str


class MailVaultBridge:
    """Mail vault köprüsü — Infisical adapter env-gated; fails closed when unset."""

    def __init__(self, adapter: InfisicalVaultAdapter | None = None) -> None:
        self._adapter = adapter or get_default_vault_adapter()

    def is_configured(self, ref: VaultCredentialRef) -> bool:
        if not self._adapter.is_configured():
            return False
        resolution = self._adapter.resolve_credential(ref.ref_id, ref.purpose_code)
        return resolution.ok

    def resolve_credential(self, ref: VaultCredentialRef) -> CredentialResolution:
        return self._adapter.resolve_credential(ref.ref_id, ref.purpose_code)

    def connection_hint(self, ref: VaultCredentialRef) -> dict[str, str | bool]:
        configured = self.is_configured(ref)
        resolution = self._adapter.resolve_credential(ref.ref_id, ref.purpose_code)
        hint: dict[str, str | bool] = {
            "configured": configured,
            "provider": MAIL_VAULT_PROVIDER,
            "purpose_code": ref.purpose_code,
        }
        if configured:
            hint["boundary"] = "vault_poc_ready"
            if resolution.token_intent:
                hint["token_intent"] = resolution.token_intent
        elif self._adapter.is_configured():
            hint["boundary"] = "vault_env_set_credential_unresolved"
            if resolution.error:
                hint["error"] = resolution.error
        else:
            hint["boundary"] = "private_vault_impl_required"
        return hint


# Geriye uyumluluk alias — testler ve mevcut importlar.
DemoVaultCredentialBridge = MailVaultBridge

_default_bridge = MailVaultBridge()


def get_vault_credential_bridge() -> MailVaultBridge:
    return _default_bridge


def mail_read_credential_ref(account_id: str) -> VaultCredentialRef:
    return VaultCredentialRef(
        purpose_code=VAULT_PURPOSE_MAIL_READ,
        ref_id=f"mail-read:{account_id}",
        account_id=account_id,
    )
