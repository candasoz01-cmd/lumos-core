from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from integrations.vault.purpose_codes import is_known_purpose_code, token_intent_for_purpose

ENV_VAULT_URL = "LUMOS_VAULT_URL"
ENV_VAULT_TOKEN = "LUMOS_VAULT_TOKEN"


@dataclass(frozen=True)
class CredentialResolution:
    """Vault çözümleme sonucu — secret_value yalnızca operatör PoC'ta dolu olabilir."""

    ok: bool
    purpose_code: str
    ref: str
    token_intent: str | None = None
    secret_value: str | None = None
    error: str | None = None


class VaultAdapter(Protocol):
    """Vault kasa geçidi — Lumos yüzeyinde secret taşınmaz."""

    def is_configured(self) -> bool:
        ...

    def resolve_credential(self, ref: str, purpose_code: str) -> CredentialResolution:
        ...


class InfisicalVaultAdapter:
    """Infisical self-host PoC adapter — env-gated, fails closed when unset."""

    def __init__(
        self,
        *,
        vault_url: str | None = None,
        vault_token: str | None = None,
    ) -> None:
        self._vault_url = (vault_url if vault_url is not None else os.environ.get(ENV_VAULT_URL, "")).strip()
        self._vault_token = (
            vault_token if vault_token is not None else os.environ.get(ENV_VAULT_TOKEN, "")
        ).strip()

    def is_configured(self) -> bool:
        return bool(self._vault_url and self._vault_token)

    def resolve_credential(self, ref: str, purpose_code: str) -> CredentialResolution:
        if not self.is_configured():
            return CredentialResolution(
                ok=False,
                purpose_code=purpose_code,
                ref=ref,
                error="vault_env_not_configured",
            )
        if not is_known_purpose_code(purpose_code):
            return CredentialResolution(
                ok=False,
                purpose_code=purpose_code,
                ref=ref,
                error="unknown_purpose_code",
            )
        intent = token_intent_for_purpose(purpose_code)
        if not self._vault_reachable():
            return CredentialResolution(
                ok=False,
                purpose_code=purpose_code,
                ref=ref,
                token_intent=intent,
                error="vault_unreachable",
            )
        return CredentialResolution(
            ok=True,
            purpose_code=purpose_code,
            ref=ref,
            token_intent=intent,
        )

    def _vault_reachable(self) -> bool:
        """Read-only health probe — operatör PoC; secret döndürmez."""
        base = self._vault_url.rstrip("/")
        url = f"{base}/api/status"
        req = Request(url, method="GET")
        req.add_header("Authorization", f"Bearer {self._vault_token}")
        try:
            with urlopen(req, timeout=3) as resp:  # noqa: S310 — operatör env URL
                return 200 <= resp.status < 300
        except (URLError, OSError, ValueError):
            return False


_default_adapter: InfisicalVaultAdapter | None = None


def get_default_vault_adapter() -> InfisicalVaultAdapter:
    global _default_adapter  # noqa: PLW0603
    if _default_adapter is None:
        _default_adapter = InfisicalVaultAdapter()
    return _default_adapter
