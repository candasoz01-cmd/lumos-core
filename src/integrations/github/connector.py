from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from integrations.vault.access import (
    CredentialAccessAction,
    CredentialAccessDecision,
    CredentialAccessRequest,
    CredentialBinding,
    CredentialBindingKey,
)
from integrations.vault.adapter import CredentialResolution, CredentialWriteResult, InfisicalVaultAdapter
from integrations.vault.purpose_codes import PURPOSE_GITHUB_METADATA_READ
from integrations.vault.registry import CredentialBindingRegistry

GITHUB_PROVIDER = "github"
GITHUB_SCOPE_USER_READ = "github.user.read"
GITHUB_SCOPE_REPOSITORY_METADATA_READ = "github.repository.metadata.read"
GITHUB_READ_ONLY_SCOPES = frozenset(
    {GITHUB_SCOPE_USER_READ, GITHUB_SCOPE_REPOSITORY_METADATA_READ}
)
GITHUB_API_VERSION = "2022-11-28"
GITHUB_VAULT_PATH = "/integrations/github"


class GitHubCredentialVault(Protocol):
    def store_credential(
        self,
        ref: str,
        purpose_code: str,
        secret_value: str,
    ) -> CredentialWriteResult:
        ...

    def resolve_credential(self, ref: str, purpose_code: str) -> CredentialResolution:
        ...

    def delete_credential(self, ref: str, purpose_code: str) -> CredentialWriteResult:
        ...


class GitHubApiError(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class GitHubApi(Protocol):
    def authenticated_user(self, access_token: str) -> dict[str, str]:
        ...

    def list_repositories(self, access_token: str, *, limit: int) -> tuple[dict[str, object], ...]:
        ...


class GitHubRestApi:
    """GitHub REST salt-okunur istemcisi; credential hiçbir yanıta eklenmez."""

    def __init__(self, *, base_url: str = "https://api.github.com", timeout: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def authenticated_user(self, access_token: str) -> dict[str, str]:
        payload = self._request_json("/user", access_token)
        if not isinstance(payload, dict) or not payload.get("id") or not payload.get("login"):
            raise GitHubApiError("github_identity_invalid")
        return {"account_id": str(payload["id"]), "login": str(payload["login"])}

    def list_repositories(self, access_token: str, *, limit: int) -> tuple[dict[str, object], ...]:
        safe_limit = min(max(1, limit), 100)
        query = urlencode(
            {
                "per_page": safe_limit,
                "sort": "updated",
                "direction": "desc",
                "affiliation": "owner,collaborator,organization_member",
            }
        )
        payload = self._request_json(f"/user/repos?{query}", access_token)
        if not isinstance(payload, list):
            raise GitHubApiError("github_repositories_invalid")
        repositories: list[dict[str, object]] = []
        for item in payload:
            if not isinstance(item, dict) or not item.get("id") or not item.get("full_name"):
                continue
            permissions = item.get("permissions")
            pull_allowed = bool(permissions.get("pull")) if isinstance(permissions, dict) else True
            repositories.append(
                {
                    "id": str(item["id"]),
                    "full_name": str(item["full_name"]),
                    "private": bool(item.get("private")),
                    "archived": bool(item.get("archived")),
                    "default_branch": str(item.get("default_branch") or ""),
                    "readable": pull_allowed,
                }
            )
        return tuple(repositories)

    def _request_json(self, path: str, access_token: str) -> object:
        request = Request(
            f"{self._base_url}{path}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "Lumos-GitHub-Connector",
                "X-GitHub-Api-Version": GITHUB_API_VERSION,
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:  # noqa: S310 — fixed API by default
                if not (200 <= response.status < 300):
                    raise GitHubApiError("github_request_failed")
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise GitHubApiError("github_credential_rejected") from None
            raise GitHubApiError("github_request_failed") from None
        except (URLError, TimeoutError, OSError):
            raise GitHubApiError("github_unreachable") from None
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            raise GitHubApiError("github_response_invalid") from None


@dataclass(frozen=True)
class GitHubConnectionResult:
    ok: bool
    account_id: str = ""
    login: str = ""
    scopes: tuple[str, ...] = ()
    status: str = ""
    approval_required: bool = False
    error: str = ""


@dataclass(frozen=True)
class GitHubReadResult:
    ok: bool
    repositories: tuple[dict[str, object], ...] = ()
    access_action: CredentialAccessAction = CredentialAccessAction.DENY
    reason: str = ""
    error: str = ""


class GitHubReadOnlyConnector:
    """Tamamlanmış GitHub bağlantısını vault + registry sınırında yönetir."""

    def __init__(
        self,
        *,
        vault: GitHubCredentialVault,
        registry: CredentialBindingRegistry,
        api: GitHubApi | None = None,
    ) -> None:
        self._vault = vault
        self._registry = registry
        self._api = api or GitHubRestApi()

    def complete_connection(
        self,
        *,
        owner_id: str,
        access_token: str,
        granted_scopes: frozenset[str],
        expires_at: datetime,
        verified_at: datetime | None = None,
    ) -> GitHubConnectionResult:
        checked_at = verified_at or datetime.now(timezone.utc)
        if not _aware(checked_at) or not _aware(expires_at) or expires_at <= checked_at:
            return GitHubConnectionResult(False, error="credential_expiry_invalid")
        scopes = _normalized_scopes(granted_scopes)
        if GITHUB_SCOPE_REPOSITORY_METADATA_READ not in scopes:
            return GitHubConnectionResult(False, error="github_metadata_read_scope_required")
        if not scopes.issubset(GITHUB_READ_ONLY_SCOPES):
            return GitHubConnectionResult(
                False,
                scopes=tuple(sorted(scopes)),
                approval_required=True,
                error="scope_expansion_required",
            )
        if not isinstance(access_token, str) or not access_token:
            return GitHubConnectionResult(False, error="github_credential_required")

        try:
            identity = self._api.authenticated_user(access_token)
        except GitHubApiError as exc:
            return GitHubConnectionResult(False, error=exc.reason)

        key = github_binding_key(owner_id=owner_id, account_id=identity["account_id"])
        vault_ref = f"github-{secrets.token_urlsafe(24)}"
        write_result = self._vault.store_credential(
            vault_ref,
            PURPOSE_GITHUB_METADATA_READ,
            access_token,
        )
        if not write_result.ok:
            return GitHubConnectionResult(False, error=write_result.error or "vault_write_failed")

        binding = CredentialBinding(
            key=key,
            vault_ref=vault_ref,
            granted_scopes=scopes,
            verified_at=checked_at,
            expires_at=expires_at,
            verification_source="github_authenticated_user",
        )
        if not self._registry.upsert(binding):
            # Registry kaybettiyse (eşzamanlı yarış), az önce vault'a yazılan
            # secret'ı yetim bırakmamak için en iyi çaba ile geri al.
            self._vault.delete_credential(vault_ref, PURPOSE_GITHUB_METADATA_READ)
            return GitHubConnectionResult(False, error="stale_connection_completion")
        return GitHubConnectionResult(
            True,
            account_id=key.account_id,
            login=identity["login"],
            scopes=tuple(sorted(scopes)),
            status="active",
        )

    def assess_access(
        self,
        *,
        owner_id: str,
        account_id: str,
        required_scopes: frozenset[str],
        consequential: bool = False,
        now: datetime | None = None,
    ) -> CredentialAccessDecision:
        request = CredentialAccessRequest(
            key=github_binding_key(owner_id=owner_id, account_id=account_id),
            required_scopes=_normalized_scopes(required_scopes),
            consequential=consequential,
        )
        return self._registry.evaluate(request, now=now)

    def list_repositories(
        self,
        *,
        owner_id: str,
        account_id: str,
        limit: int = 30,
        now: datetime | None = None,
    ) -> GitHubReadResult:
        decision = self.assess_access(
            owner_id=owner_id,
            account_id=account_id,
            required_scopes=frozenset({GITHUB_SCOPE_REPOSITORY_METADATA_READ}),
            now=now,
        )
        if not decision.reusable:
            return GitHubReadResult(
                False,
                access_action=decision.action,
                reason=decision.reason,
                error="github_access_not_reusable",
            )

        key = github_binding_key(owner_id=owner_id, account_id=account_id)
        binding = self._registry.get(key)
        if binding is None:
            return GitHubReadResult(False, error="credential_binding_missing")
        resolution = self._vault.resolve_credential(binding.vault_ref, binding.key.purpose_code)
        if not resolution.ok or not resolution.secret_value:
            return GitHubReadResult(False, error=resolution.error or "vault_credential_unavailable")
        try:
            repositories = self._api.list_repositories(resolution.secret_value, limit=limit)
        except GitHubApiError as exc:
            if exc.reason == "github_credential_rejected":
                self._registry.revoke(key, revoked_at=now)
                return GitHubReadResult(
                    False,
                    access_action=CredentialAccessAction.APPROVAL_REQUIRED,
                    reason="credential_revoked_approval_required",
                    error=exc.reason,
                )
            return GitHubReadResult(False, error=exc.reason)
        return GitHubReadResult(
            True,
            repositories=repositories,
            access_action=CredentialAccessAction.REUSE,
            reason="verified_context_reused",
        )


def github_binding_key(*, owner_id: str, account_id: str) -> CredentialBindingKey:
    return CredentialBindingKey(
        owner_id=owner_id,
        provider=GITHUB_PROVIDER,
        account_id=account_id,
        purpose_code=PURPOSE_GITHUB_METADATA_READ,
    )


def build_github_read_only_connector(
    *,
    registry_path: str | Path,
    api: GitHubApi | None = None,
) -> GitHubReadOnlyConnector:
    return GitHubReadOnlyConnector(
        vault=InfisicalVaultAdapter(vault_secret_path=GITHUB_VAULT_PATH),
        registry=CredentialBindingRegistry(registry_path),
        api=api,
    )


def _normalized_scopes(scopes: frozenset[str]) -> frozenset[str]:
    return frozenset(scope.strip() for scope in scopes if isinstance(scope, str) and scope.strip())


def _aware(value: datetime) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None
