import json
import logging
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from integrations.github.connector import (
    GITHUB_READ_ONLY_SCOPES,
    GITHUB_SCOPE_REPOSITORY_METADATA_READ,
    GitHubApiError,
    GitHubReadOnlyConnector,
    GitHubRestApi,
    github_binding_key,
)
from integrations.vault.access import CredentialAccessAction
from integrations.vault.adapter import (
    CredentialResolution,
    CredentialWriteResult,
    InfisicalVaultAdapter,
)
from integrations.vault.purpose_codes import PURPOSE_GITHUB_METADATA_READ
from integrations.vault.registry import CredentialBindingRegistry

NOW = datetime(2026, 8, 20, 15, 0, tzinfo=timezone.utc)
OWNER_ID = "lumos-owner-1"
ACCOUNT_ID = "442211"
TOKEN_CANARY = "ghu_CANARY_SECRET_MUST_NOT_LEAK_123456"


class _FakeVault:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.resolve_calls = 0

    def store_credential(
        self,
        ref: str,
        purpose_code: str,
        secret_value: str,
    ) -> CredentialWriteResult:
        self.values[ref] = secret_value
        return CredentialWriteResult(True, purpose_code, ref)

    def resolve_credential(self, ref: str, purpose_code: str) -> CredentialResolution:
        self.resolve_calls += 1
        value = self.values.get(ref)
        return CredentialResolution(
            ok=value is not None,
            purpose_code=purpose_code,
            ref=ref,
            secret_value=value,
            error=None if value is not None else "secret_not_found",
        )

    def delete_credential(self, ref: str, purpose_code: str) -> CredentialWriteResult:
        self.values.pop(ref, None)
        return CredentialWriteResult(True, purpose_code, ref)


class _FakeGitHubApi:
    def __init__(self) -> None:
        self.identity_calls = 0
        self.repository_calls = 0
        self.reject_repository_read = False

    def authenticated_user(self, access_token: str) -> dict[str, str]:
        self.identity_calls += 1
        assert access_token
        return {"account_id": ACCOUNT_ID, "login": "lumos-test-user"}

    def list_repositories(self, access_token: str, *, limit: int) -> tuple[dict[str, object], ...]:
        self.repository_calls += 1
        assert access_token
        if self.reject_repository_read:
            raise GitHubApiError("github_credential_rejected")
        return (
            {
                "id": "1001",
                "full_name": "lumos-test-user/example",
                "private": True,
                "archived": False,
                "default_branch": "main",
                "readable": True,
            },
        )[:limit]


def _connector(tmp_path):
    vault = _FakeVault()
    api = _FakeGitHubApi()
    registry = CredentialBindingRegistry(tmp_path / "github-bindings.sqlite3")
    connector = GitHubReadOnlyConnector(vault=vault, registry=registry, api=api)
    return connector, vault, api, registry


def _complete(connector, *, token: str = TOKEN_CANARY, verified_at: datetime = NOW):
    return connector.complete_connection(
        owner_id=OWNER_ID,
        access_token=token,
        granted_scopes=GITHUB_READ_ONLY_SCOPES,
        verified_at=verified_at,
        expires_at=verified_at + timedelta(hours=8),
    )


def _mock_http_response(*, status: int = 200, body: bytes = b""):
    response = MagicMock()
    response.status = status
    response.read.return_value = body
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)
    return response


def test_connection_writes_token_only_to_vault_and_safe_metadata_to_registry(tmp_path):
    connector, vault, _, registry = _connector(tmp_path)

    result = _complete(connector)
    binding = registry.get(github_binding_key(owner_id=OWNER_ID, account_id=ACCOUNT_ID))

    assert result.ok is True
    assert result.account_id == ACCOUNT_ID
    assert result.status == "active"
    assert binding is not None
    assert vault.values[binding.vault_ref] == TOKEN_CANARY
    assert TOKEN_CANARY not in str(result)
    assert TOKEN_CANARY not in str(binding.public_metadata())
    assert TOKEN_CANARY.encode() not in (tmp_path / "github-bindings.sqlite3").read_bytes()


def test_valid_read_only_connection_is_reused_automatically(tmp_path):
    connector, vault, api, _ = _connector(tmp_path)
    assert _complete(connector).ok is True

    result = connector.list_repositories(
        owner_id=OWNER_ID,
        account_id=ACCOUNT_ID,
        now=NOW + timedelta(minutes=1),
    )

    assert result.ok is True
    assert result.access_action is CredentialAccessAction.REUSE
    assert result.repositories[0]["full_name"] == "lumos-test-user/example"
    assert vault.resolve_calls == 1
    assert api.repository_calls == 1
    assert TOKEN_CANARY not in str(result)


def test_scope_expansion_and_write_intent_require_approval_without_vault_read(tmp_path):
    connector, vault, _, _ = _connector(tmp_path)
    assert _complete(connector).ok is True

    expanded = connector.assess_access(
        owner_id=OWNER_ID,
        account_id=ACCOUNT_ID,
        required_scopes=frozenset(
            {GITHUB_SCOPE_REPOSITORY_METADATA_READ, "github.repository.contents.write"}
        ),
        now=NOW + timedelta(minutes=1),
    )
    write_intent = connector.assess_write_intent(
        owner_id=OWNER_ID,
        account_id=ACCOUNT_ID,
        now=NOW + timedelta(minutes=1),
    )

    assert expanded.action is CredentialAccessAction.APPROVAL_REQUIRED
    assert expanded.reason == "scope_expansion_required"
    assert write_intent.action is CredentialAccessAction.APPROVAL_REQUIRED
    assert write_intent.reason == "consequential_action_required"
    assert vault.resolve_calls == 0


def test_connection_with_write_scope_is_not_stored_before_approval(tmp_path):
    connector, vault, api, registry = _connector(tmp_path)

    result = connector.complete_connection(
        owner_id=OWNER_ID,
        access_token=TOKEN_CANARY,
        granted_scopes=GITHUB_READ_ONLY_SCOPES | {"github.repository.contents.write"},
        verified_at=NOW,
        expires_at=NOW + timedelta(hours=8),
    )

    assert result.ok is False
    assert result.approval_required is True
    assert result.error == "scope_expansion_required"
    assert vault.values == {}
    assert api.identity_calls == 0
    assert registry.get(github_binding_key(owner_id=OWNER_ID, account_id=ACCOUNT_ID)) is None


def test_revoked_connection_requires_approval_without_resolving_token(tmp_path):
    connector, vault, _, registry = _connector(tmp_path)
    assert _complete(connector).ok is True
    key = github_binding_key(owner_id=OWNER_ID, account_id=ACCOUNT_ID)
    assert registry.revoke(key, revoked_at=NOW + timedelta(minutes=1)) is True

    result = connector.list_repositories(
        owner_id=OWNER_ID,
        account_id=ACCOUNT_ID,
        now=NOW + timedelta(minutes=2),
    )

    assert result.ok is False
    assert result.access_action is CredentialAccessAction.APPROVAL_REQUIRED
    assert result.reason == "credential_revoked_approval_required"
    assert vault.resolve_calls == 0


def test_github_rejection_revokes_binding_and_next_read_requires_approval(tmp_path):
    connector, vault, api, registry = _connector(tmp_path)
    assert _complete(connector).ok is True
    api.reject_repository_read = True

    first = connector.list_repositories(
        owner_id=OWNER_ID,
        account_id=ACCOUNT_ID,
        now=NOW + timedelta(minutes=1),
    )
    second = connector.list_repositories(
        owner_id=OWNER_ID,
        account_id=ACCOUNT_ID,
        now=NOW + timedelta(minutes=2),
    )
    binding = registry.get(github_binding_key(owner_id=OWNER_ID, account_id=ACCOUNT_ID))

    assert first.error == "github_credential_rejected"
    assert first.access_action is CredentialAccessAction.APPROVAL_REQUIRED
    assert second.reason == "credential_revoked_approval_required"
    assert binding is not None and binding.public_metadata()["status"] == "revoked"
    assert vault.resolve_calls == 1


def test_expired_connection_requires_reauthentication_without_vault_read(tmp_path):
    connector, vault, _, _ = _connector(tmp_path)
    assert _complete(connector).ok is True

    result = connector.list_repositories(
        owner_id=OWNER_ID,
        account_id=ACCOUNT_ID,
        now=NOW + timedelta(hours=9),
    )

    assert result.ok is False
    assert result.access_action is CredentialAccessAction.REAUTHENTICATE
    assert result.reason == "credential_expired"
    assert vault.resolve_calls == 0


def test_concurrent_connection_completions_keep_newest_token_reference(tmp_path):
    connector, vault, _, registry = _connector(tmp_path)
    older_at = NOW
    newer_at = NOW + timedelta(seconds=1)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda item: _complete(connector, token=item[0], verified_at=item[1]),
                (("token-older", older_at), ("token-newer", newer_at)),
            )
        )

    key = github_binding_key(owner_id=OWNER_ID, account_id=ACCOUNT_ID)
    binding = registry.get(key)
    with sqlite3.connect(tmp_path / "github-bindings.sqlite3") as connection:
        count = connection.execute("SELECT COUNT(*) FROM credential_bindings").fetchone()[0]

    assert any(result.ok for result in results)
    assert count == 1
    assert binding is not None
    assert binding.verified_at == newer_at
    assert vault.values[binding.vault_ref] == "token-newer"


def test_stale_connection_completion_rolls_back_orphaned_vault_secret(tmp_path):
    connector, vault, _, registry = _connector(tmp_path)
    newer_at = NOW + timedelta(seconds=1)
    assert _complete(connector, token="token-newer", verified_at=newer_at).ok is True
    newer_ref = registry.get(
        github_binding_key(owner_id=OWNER_ID, account_id=ACCOUNT_ID)
    ).vault_ref

    stale_result = _complete(connector, token="token-stale", verified_at=NOW)

    assert stale_result.ok is False
    assert stale_result.error == "stale_connection_completion"
    assert "token-stale" not in vault.values.values()
    assert vault.values[newer_ref] == "token-newer"


@patch("integrations.vault.adapter.urlopen")
def test_infisical_write_sends_token_but_never_returns_it(mock_urlopen):
    mock_urlopen.side_effect = [
        _mock_http_response(status=200),
        _mock_http_response(status=200, body=b'{"secret":{"id":"secret-id"}}'),
    ]
    adapter = InfisicalVaultAdapter(
        vault_url="https://vault.test",
        vault_token="vault-service-token",
        vault_project="project-id",
        vault_env="prod",
        vault_secret_path="/integrations/github",
    )

    result = adapter.store_credential(
        "github-opaque-ref",
        PURPOSE_GITHUB_METADATA_READ,
        TOKEN_CANARY,
    )
    request = mock_urlopen.call_args_list[1].args[0]
    payload = json.loads(request.data.decode("utf-8"))

    assert result.ok is True
    assert request.full_url == "https://vault.test/api/v3/secrets/raw/github-opaque-ref"
    assert request.get_method() == "POST"
    assert payload["secretValue"] == TOKEN_CANARY
    assert payload["secretPath"] == "/integrations/github"
    assert TOKEN_CANARY not in str(result)


@patch("integrations.vault.adapter.urlopen")
def test_infisical_delete_targets_correct_secret_and_treats_404_as_success(mock_urlopen):
    mock_urlopen.side_effect = [
        _mock_http_response(status=200),
        HTTPError("https://vault.test", 404, "not found", hdrs=None, fp=None),
    ]
    adapter = InfisicalVaultAdapter(
        vault_url="https://vault.test",
        vault_token="vault-service-token",
        vault_project="project-id",
        vault_env="prod",
        vault_secret_path="/integrations/github",
    )

    result = adapter.delete_credential("github-opaque-ref", PURPOSE_GITHUB_METADATA_READ)
    request = mock_urlopen.call_args_list[1].args[0]

    assert result.ok is True
    assert request.get_method() == "DELETE"
    assert request.full_url == "https://vault.test/api/v3/secrets/raw/github-opaque-ref"


def test_unconfigured_vault_refuses_to_store_credential():
    adapter = InfisicalVaultAdapter(
        vault_url="",
        vault_token="",
        vault_project="",
        vault_env="",
    )

    result = adapter.store_credential("ref", PURPOSE_GITHUB_METADATA_READ, TOKEN_CANARY)

    assert result.ok is False
    assert result.error == "vault_env_not_configured"
    assert TOKEN_CANARY not in str(result)


@patch("integrations.github.connector.urlopen")
def test_github_http_error_never_exposes_token(mock_urlopen):
    mock_urlopen.side_effect = HTTPError(
        "https://api.github.com/user",
        401,
        TOKEN_CANARY,
        hdrs=None,
        fp=None,
    )
    api = GitHubRestApi()

    try:
        api.authenticated_user(TOKEN_CANARY)
    except GitHubApiError as exc:
        assert exc.reason == "github_credential_rejected"
        assert TOKEN_CANARY not in str(exc)
    else:
        raise AssertionError("GitHubApiError bekleniyordu")


@patch("integrations.github.connector.urlopen")
def test_github_rest_api_uses_read_only_endpoints_and_sanitizes_output(mock_urlopen):
    mock_urlopen.side_effect = [
        _mock_http_response(
            body=b'{"id":442211,"login":"lumos-test-user","email":"private@example.test"}'
        ),
        _mock_http_response(
            body=(
                b'[{"id":1001,"full_name":"lumos-test-user/example","private":true,'
                b'"archived":false,"default_branch":"main","permissions":{"pull":true},'
                b'"temp_clone_token":"must-not-return"}]'
            )
        ),
    ]
    api = GitHubRestApi()

    identity = api.authenticated_user(TOKEN_CANARY)
    repositories = api.list_repositories(TOKEN_CANARY, limit=10)
    identity_request = mock_urlopen.call_args_list[0].args[0]
    repository_request = mock_urlopen.call_args_list[1].args[0]

    assert identity == {"account_id": ACCOUNT_ID, "login": "lumos-test-user"}
    assert identity_request.full_url == "https://api.github.com/user"
    assert identity_request.get_method() == "GET"
    assert repository_request.full_url.startswith("https://api.github.com/user/repos?")
    assert repository_request.get_method() == "GET"
    assert identity_request.get_header("Authorization") == f"Bearer {TOKEN_CANARY}"
    assert identity_request.get_header("X-github-api-version") == "2022-11-28"
    assert repositories[0]["full_name"] == "lumos-test-user/example"
    assert "temp_clone_token" not in repositories[0]
    assert "email" not in identity
    assert TOKEN_CANARY not in str(identity)
    assert TOKEN_CANARY not in str(repositories)


def test_token_is_absent_from_logs_errors_sqlite_and_test_output(tmp_path, caplog, capsys):
    connector, _, api, _ = _connector(tmp_path)
    caplog.set_level(logging.DEBUG)
    completed = _complete(connector)
    api.reject_repository_read = True
    failed = connector.list_repositories(
        owner_id=OWNER_ID,
        account_id=ACCOUNT_ID,
        now=NOW + timedelta(minutes=1),
    )
    captured = capsys.readouterr()

    assert TOKEN_CANARY not in str(completed)
    assert TOKEN_CANARY not in str(failed)
    assert TOKEN_CANARY not in caplog.text
    assert TOKEN_CANARY not in captured.out
    assert TOKEN_CANARY not in captured.err
    assert TOKEN_CANARY.encode() not in (tmp_path / "github-bindings.sqlite3").read_bytes()
