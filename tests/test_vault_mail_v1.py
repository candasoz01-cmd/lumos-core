import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from integrations.mail.providers.gmail_oauth import (
    GMAIL_OAUTH_SCOPE_READONLY,
    GmailOAuthConnector,
)
from integrations.mail.vault_credential import DemoVaultCredentialBridge, mail_read_credential_ref
from integrations.vault.adapter import CredentialResolution, InfisicalVaultAdapter
from integrations.vault.purpose_codes import (
    PURPOSE_MAIL_NOTIFY,
    PURPOSE_MAIL_READ,
    PURPOSE_TOKEN_INTENT,
    is_known_purpose_code,
    token_intent_for_purpose,
)

_MOCK_SECRET_PLACEHOLDER = "mock-oauth-credential-placeholder"
_MOCK_SECRET_JSON = (
    b'{"secret":{"secretKey":"mail-read:a@example.invalid","secretValue":"'
    + _MOCK_SECRET_PLACEHOLDER.encode()
    + b'"}}'
)


def _adapter_kwargs(**overrides):
    base = {
        "vault_url": "https://vault.test",
        "vault_token": "tok",
        "vault_project": "proj-id",
        "vault_env": "dev",
    }
    base.update(overrides)
    return base


def _mock_http_response(*, status: int = 200, body: bytes = b""):
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = body
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_purpose_code_constants():
    assert PURPOSE_MAIL_READ == "integration.mail.read"
    assert PURPOSE_MAIL_NOTIFY == "integration.mail.notify"


def test_purpose_token_intent_mapping():
    assert PURPOSE_TOKEN_INTENT[PURPOSE_MAIL_READ] == "gmail.readonly"
    assert "gmail.readonly" in PURPOSE_TOKEN_INTENT[PURPOSE_MAIL_NOTIFY]
    assert token_intent_for_purpose(PURPOSE_MAIL_READ) == "gmail.readonly"
    assert token_intent_for_purpose("unknown.code") is None


def test_is_known_purpose_code():
    assert is_known_purpose_code(PURPOSE_MAIL_READ) is True
    assert is_known_purpose_code(PURPOSE_MAIL_NOTIFY) is True
    assert is_known_purpose_code("vault.connect") is False


def test_infisical_adapter_fails_closed_without_env():
    adapter = InfisicalVaultAdapter(vault_url="", vault_token="")
    assert adapter.is_configured() is False
    resolution = adapter.resolve_credential("mail-read:user@example.invalid", PURPOSE_MAIL_READ)
    assert resolution.ok is False
    assert resolution.error == "vault_env_not_configured"


def test_infisical_adapter_missing_project_env():
    adapter = InfisicalVaultAdapter(vault_url="https://vault.test", vault_token="tok")
    assert adapter.is_configured() is False
    resolution = adapter.resolve_credential("mail-read:a@example.invalid", PURPOSE_MAIL_READ)
    assert resolution.ok is False
    assert resolution.error == "vault_project_env_not_configured"


def test_infisical_adapter_unknown_purpose():
    adapter = InfisicalVaultAdapter(**_adapter_kwargs())
    resolution = adapter.resolve_credential("ref-1", "vault.unknown")
    assert resolution.ok is False
    assert resolution.error == "unknown_purpose_code"


@patch("integrations.vault.adapter.urlopen")
def test_infisical_adapter_resolves_secret_when_reachable(mock_urlopen):
    mock_urlopen.side_effect = [
        _mock_http_response(status=200),
        _mock_http_response(status=200, body=_MOCK_SECRET_JSON),
    ]

    adapter = InfisicalVaultAdapter(**_adapter_kwargs())
    assert adapter.is_configured() is True
    resolution = adapter.resolve_credential("mail-read:a@example.invalid", PURPOSE_MAIL_READ)
    assert resolution.ok is True
    assert resolution.token_intent == "gmail.readonly"
    assert resolution.secret_value == _MOCK_SECRET_PLACEHOLDER
    assert _MOCK_SECRET_PLACEHOLDER not in str(resolution.error)


@patch("integrations.vault.adapter.urlopen")
def test_infisical_adapter_secret_not_found(mock_urlopen):
    from urllib.error import HTTPError

    mock_urlopen.side_effect = [
        _mock_http_response(status=200),
        HTTPError("https://vault.test", 404, "Not Found", hdrs=None, fp=None),
    ]

    adapter = InfisicalVaultAdapter(**_adapter_kwargs())
    resolution = adapter.resolve_credential("mail-read:a@example.invalid", PURPOSE_MAIL_READ)
    assert resolution.ok is False
    assert resolution.error == "secret_not_found"
    assert resolution.secret_value is None


@patch("integrations.vault.adapter.urlopen")
def test_infisical_adapter_secret_fetch_timeout(mock_urlopen):
    mock_urlopen.side_effect = [
        _mock_http_response(status=200),
        TimeoutError("timed out"),
    ]

    adapter = InfisicalVaultAdapter(**_adapter_kwargs())
    resolution = adapter.resolve_credential("mail-read:a@example.invalid", PURPOSE_MAIL_READ)
    assert resolution.ok is False
    assert resolution.error == "vault_timeout"


@patch("integrations.vault.adapter.urlopen")
def test_infisical_adapter_unreachable(mock_urlopen):
    mock_urlopen.side_effect = OSError("connection refused")
    adapter = InfisicalVaultAdapter(**_adapter_kwargs())
    resolution = adapter.resolve_credential("mail-read:a@example.invalid", PURPOSE_MAIL_READ)
    assert resolution.ok is False
    assert resolution.error == "vault_unreachable"


def test_mail_vault_connection_hint_resolved_without_secret_leak():
    mock_adapter = MagicMock()
    mock_adapter.is_configured.return_value = True
    mock_adapter.resolve_credential.return_value = CredentialResolution(
        ok=True,
        purpose_code=PURPOSE_MAIL_READ,
        ref="mail-read:user@example.invalid",
        token_intent="gmail.readonly",
        secret_value=_MOCK_SECRET_PLACEHOLDER,
    )

    bridge = DemoVaultCredentialBridge(adapter=mock_adapter)
    ref = mail_read_credential_ref("user@example.invalid")
    hint = bridge.connection_hint(ref)
    assert hint["credential_resolved"] is True
    assert hint["boundary"] == "vault_poc_ready"
    assert _MOCK_SECRET_PLACEHOLDER not in str(hint)


def test_gmail_oauth_scope_constant():
    assert GMAIL_OAUTH_SCOPE_READONLY == "https://www.googleapis.com/auth/gmail.readonly"


def test_gmail_connector_stub_without_vault():
    connector = GmailOAuthConnector(vault_bridge=None)
    summaries = connector.list_unread_summaries(account_id="a@example.invalid", limit=2)
    assert len(summaries) == 2
    assert summaries[0].message_id == "demo-msg-001"


class _MockVault(DemoVaultCredentialBridge):
    def is_configured(self, ref):  # noqa: ARG002
        return True

    def resolve_credential(self, ref):
        return CredentialResolution(
            ok=True,
            purpose_code=ref.purpose_code,
            ref=ref.ref_id,
            token_intent="gmail.readonly",
        )


def test_gmail_connector_vault_backed_read_path():
    connector = GmailOAuthConnector(vault_bridge=_MockVault())
    ref = mail_read_credential_ref("user@example.invalid")
    summaries = connector.list_unread_summaries(account_id=ref.account_id, limit=2)
    assert len(summaries) == 2
    assert summaries[0].message_id.startswith("vault-mail-read:")
    assert "[vault-backed]" in summaries[0].subject_preview
    assert "token" not in summaries[0].subject_preview.lower()
