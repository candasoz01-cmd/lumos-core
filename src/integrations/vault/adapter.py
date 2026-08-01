from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from integrations.vault.purpose_codes import is_known_purpose_code, token_intent_for_purpose

ENV_VAULT_URL = "LUMOS_VAULT_URL"
ENV_VAULT_TOKEN = "LUMOS_VAULT_TOKEN"
ENV_VAULT_PROJECT = "LUMOS_VAULT_PROJECT"
ENV_VAULT_ENV = "LUMOS_VAULT_ENV"
ENV_VAULT_SECRET_PATH = "LUMOS_VAULT_SECRET_PATH"
DEFAULT_VAULT_SECRET_PATH = "/integrations/mail"


@dataclass(frozen=True)
class CredentialResolution:
    """Vault çözümleme sonucu — secret_value yalnızca operatör PoC'ta dolu olabilir."""

    ok: bool
    purpose_code: str
    ref: str
    token_intent: str | None = None
    secret_value: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class CredentialWriteResult:
    """Secret yazma sonucu; yazılan değer hiçbir alanda geri dönmez."""

    ok: bool
    purpose_code: str
    ref: str
    error: str | None = None


class VaultAdapter(Protocol):
    """Vault kasa geçidi — Lumos yüzeyinde secret taşınmaz."""

    def is_configured(self) -> bool:
        ...

    def resolve_credential(self, ref: str, purpose_code: str) -> CredentialResolution:
        ...

    def store_credential(
        self,
        ref: str,
        purpose_code: str,
        secret_value: str,
    ) -> CredentialWriteResult:
        ...

    def delete_credential(
        self,
        ref: str,
        purpose_code: str,
    ) -> CredentialWriteResult:
        ...


class InfisicalVaultAdapter:
    """Infisical self-host PoC adapter — env-gated, fails closed when unset."""

    def __init__(
        self,
        *,
        vault_url: str | None = None,
        vault_token: str | None = None,
        vault_project: str | None = None,
        vault_env: str | None = None,
        vault_secret_path: str | None = None,
        timeout: float = 3.0,
    ) -> None:
        self._vault_url = (vault_url if vault_url is not None else os.environ.get(ENV_VAULT_URL, "")).strip()
        self._vault_token = (
            vault_token if vault_token is not None else os.environ.get(ENV_VAULT_TOKEN, "")
        ).strip()
        self._vault_project = (
            vault_project if vault_project is not None else os.environ.get(ENV_VAULT_PROJECT, "")
        ).strip()
        self._vault_env = (vault_env if vault_env is not None else os.environ.get(ENV_VAULT_ENV, "")).strip()
        configured_path = (
            vault_secret_path
            if vault_secret_path is not None
            else os.environ.get(ENV_VAULT_SECRET_PATH, DEFAULT_VAULT_SECRET_PATH)
        ).strip()
        self._vault_secret_path = configured_path or DEFAULT_VAULT_SECRET_PATH
        self._timeout = timeout

    def is_configured(self) -> bool:
        return bool(
            self._vault_url
            and self._vault_token
            and self._vault_project
            and self._vault_env
        )

    def resolve_credential(self, ref: str, purpose_code: str) -> CredentialResolution:
        if not self._vault_url or not self._vault_token:
            return CredentialResolution(
                ok=False,
                purpose_code=purpose_code,
                ref=ref,
                error="vault_env_not_configured",
            )
        if not self._vault_project or not self._vault_env:
            return CredentialResolution(
                ok=False,
                purpose_code=purpose_code,
                ref=ref,
                error="vault_project_env_not_configured",
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
        secret_value, fetch_error = self._fetch_secret_value(ref)
        if fetch_error:
            return CredentialResolution(
                ok=False,
                purpose_code=purpose_code,
                ref=ref,
                token_intent=intent,
                error=fetch_error,
            )
        return CredentialResolution(
            ok=True,
            purpose_code=purpose_code,
            ref=ref,
            token_intent=intent,
            secret_value=secret_value,
        )

    def store_credential(
        self,
        ref: str,
        purpose_code: str,
        secret_value: str,
    ) -> CredentialWriteResult:
        error = self._configuration_error(purpose_code)
        if error:
            return CredentialWriteResult(False, purpose_code, ref, error)
        if not isinstance(secret_value, str) or not secret_value:
            return CredentialWriteResult(False, purpose_code, ref, "secret_value_required")
        if not self._vault_reachable():
            return CredentialWriteResult(False, purpose_code, ref, "vault_unreachable")

        write_error = self._create_secret_value(ref, secret_value)
        return CredentialWriteResult(
            ok=write_error is None,
            purpose_code=purpose_code,
            ref=ref,
            error=write_error,
        )

    def delete_credential(
        self,
        ref: str,
        purpose_code: str,
    ) -> CredentialWriteResult:
        """Best-effort cleanup for orphaned writes — caller must not treat failure as fatal."""
        error = self._configuration_error(purpose_code)
        if error:
            return CredentialWriteResult(False, purpose_code, ref, error)
        if not self._vault_reachable():
            return CredentialWriteResult(False, purpose_code, ref, "vault_unreachable")

        delete_error = self._delete_secret_value(ref)
        return CredentialWriteResult(
            ok=delete_error is None,
            purpose_code=purpose_code,
            ref=ref,
            error=delete_error,
        )

    def _configuration_error(self, purpose_code: str) -> str | None:
        if not self._vault_url or not self._vault_token:
            return "vault_env_not_configured"
        if not self._vault_project or not self._vault_env:
            return "vault_project_env_not_configured"
        if not is_known_purpose_code(purpose_code):
            return "unknown_purpose_code"
        return None

    def _vault_reachable(self) -> bool:
        """Read-only health probe — operatör PoC; secret döndürmez."""
        base = self._vault_url.rstrip("/")
        url = f"{base}/api/status"
        req = Request(url, method="GET")
        req.add_header("Authorization", f"Bearer {self._vault_token}")
        try:
            with urlopen(req, timeout=self._timeout) as resp:  # noqa: S310 — operatör env URL
                return 200 <= resp.status < 300
        except (URLError, OSError, ValueError, TimeoutError):
            return False

    def _fetch_secret_value(self, ref: str) -> tuple[str | None, str | None]:
        """Infisical raw secret read — ref doğrudan secretKey (örn. mail-read:{account_id})."""
        base = self._vault_url.rstrip("/")
        secret_name = quote(ref, safe="")
        query = urlencode(
            {
                "projectId": self._vault_project,
                "environment": self._vault_env,
                "secretPath": self._vault_secret_path,
            }
        )
        url = f"{base}/api/v4/secrets/{secret_name}?{query}"
        req = Request(url, method="GET")
        req.add_header("Authorization", f"Bearer {self._vault_token}")
        try:
            with urlopen(req, timeout=self._timeout) as resp:  # noqa: S310 — operatör env URL
                if not (200 <= resp.status < 300):
                    return None, "secret_fetch_failed"
                payload = json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 404:
                return None, "secret_not_found"
            return None, "secret_fetch_failed"
        except TimeoutError:
            return None, "vault_timeout"
        except URLError as exc:
            reason = exc.reason
            if isinstance(reason, TimeoutError) or (
                reason is not None and "timed out" in str(reason).lower()
            ):
                return None, "vault_timeout"
            return None, "vault_unreachable"
        except (OSError, ValueError, json.JSONDecodeError):
            return None, "secret_fetch_failed"

        secret = payload.get("secret")
        if not isinstance(secret, dict):
            return None, "secret_fetch_failed"
        value = secret.get("secretValue")
        if not isinstance(value, str) or not value:
            return None, "secret_not_found"
        return value, None

    def _create_secret_value(self, ref: str, secret_value: str) -> str | None:
        """Infisical v4 create; sonuç ve hatalar secret değerini geri taşımaz."""
        base = self._vault_url.rstrip("/")
        secret_name = quote(ref, safe="")
        url = f"{base}/api/v4/secrets/{secret_name}"
        payload = json.dumps(
            {
                "projectId": self._vault_project,
                "environment": self._vault_env,
                "secretValue": secret_value,
                "secretPath": self._vault_secret_path,
                "type": "shared",
            },
            separators=(",", ":"),
        ).encode("utf-8")
        req = Request(url, data=payload, method="POST")
        req.add_header("Authorization", f"Bearer {self._vault_token}")
        req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req, timeout=self._timeout) as resp:  # noqa: S310 — operatör env URL
                if 200 <= resp.status < 300:
                    return None
                return "secret_write_failed"
        except TimeoutError:
            return "vault_timeout"
        except HTTPError as exc:
            if exc.code in (401, 403):
                return "vault_write_unauthorized"
            if exc.code in (409, 422):
                return "secret_ref_conflict"
            return "secret_write_failed"
        except URLError as exc:
            reason = exc.reason
            if isinstance(reason, TimeoutError) or (
                reason is not None and "timed out" in str(reason).lower()
            ):
                return "vault_timeout"
            return "vault_unreachable"
        except (OSError, ValueError):
            return "secret_write_failed"

    def _delete_secret_value(self, ref: str) -> str | None:
        """Infisical v4 delete; 404 (zaten yok) temizlik amacıyla başarı sayılır."""
        base = self._vault_url.rstrip("/")
        secret_name = quote(ref, safe="")
        query = urlencode(
            {
                "projectId": self._vault_project,
                "environment": self._vault_env,
                "secretPath": self._vault_secret_path,
            }
        )
        url = f"{base}/api/v4/secrets/{secret_name}?{query}"
        req = Request(url, method="DELETE")
        req.add_header("Authorization", f"Bearer {self._vault_token}")
        try:
            with urlopen(req, timeout=self._timeout) as resp:  # noqa: S310 — operatör env URL
                if 200 <= resp.status < 300:
                    return None
                return "secret_delete_failed"
        except HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code in (401, 403):
                return "vault_delete_unauthorized"
            return "secret_delete_failed"
        except TimeoutError:
            return "vault_timeout"
        except URLError as exc:
            reason = exc.reason
            if isinstance(reason, TimeoutError) or (
                reason is not None and "timed out" in str(reason).lower()
            ):
                return "vault_timeout"
            return "vault_unreachable"
        except (OSError, ValueError):
            return "secret_delete_failed"


_default_adapter: InfisicalVaultAdapter | None = None


def get_default_vault_adapter() -> InfisicalVaultAdapter:
    global _default_adapter  # noqa: PLW0603
    if _default_adapter is None:
        _default_adapter = InfisicalVaultAdapter()
    return _default_adapter
