import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from integrations.mail.models import MailMessageSummary
from integrations.mail.providers.gmail_api_client import (
    ENV_GMAIL_SMOKE,
    ENV_GMAIL_SMOKE_ACCOUNT,
    extract_access_token,
    is_gmail_smoke_enabled,
    list_unread_summaries,
)
from integrations.mail.providers.gmail_oauth import GmailOAuthConnector
from integrations.mail.vault_credential import DemoVaultCredentialBridge, mail_read_credential_ref
from integrations.vault.adapter import CredentialResolution

_MOCK_ACCESS_TOKEN = "mock-gmail-access-token-placeholder"
_MOCK_SECRET_JSON = json.dumps({"access_token": _MOCK_ACCESS_TOKEN})
_LIST_RESPONSE = {
    "messages": [{"id": "msg-001", "threadId": "thr-001"}],
}
_DETAIL_RESPONSE = {
    "id": "msg-001",
    "internalDate": "1718899200000",
    "payload": {
        "headers": [
            {"name": "Subject", "value": "Smoke test subject"},
            {"name": "From", "value": "sender@example.invalid"},
            {"name": "Date", "value": "Thu, 20 Jun 2024 12:00:00 +0000"},
        ],
    },
}


def _mock_http_response(*, status: int = 200, body: bytes = b""):
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = body
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_is_gmail_smoke_enabled_default_off(monkeypatch):
    monkeypatch.delenv(ENV_GMAIL_SMOKE, raising=False)
    assert is_gmail_smoke_enabled() is False


def test_is_gmail_smoke_enabled_on(monkeypatch):
    monkeypatch.setenv(ENV_GMAIL_SMOKE, "1")
    assert is_gmail_smoke_enabled() is True


def test_extract_access_token_plain():
    assert extract_access_token(_MOCK_ACCESS_TOKEN) == _MOCK_ACCESS_TOKEN


def test_extract_access_token_json():
    assert extract_access_token(_MOCK_SECRET_JSON) == _MOCK_ACCESS_TOKEN


def test_extract_access_token_empty():
    assert extract_access_token("") is None
    assert extract_access_token("   ") is None


@patch("integrations.mail.providers.gmail_api_client.urlopen")
def test_list_unread_summaries_maps_metadata(mock_urlopen):
    mock_urlopen.side_effect = [
        _mock_http_response(body=json.dumps(_LIST_RESPONSE).encode()),
        _mock_http_response(body=json.dumps(_DETAIL_RESPONSE).encode()),
    ]

    summaries = list_unread_summaries(_MOCK_ACCESS_TOKEN, limit=5)
    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.message_id == "msg-001"
    assert summary.subject_preview == "Smoke test subject"
    assert summary.from_preview == "sender@example.invalid"
    assert summary.received_at.startswith("2024-06-20T")
    assert summary.received_at.endswith("Z")
    assert _MOCK_ACCESS_TOKEN not in str(summary)


@patch("integrations.mail.providers.gmail_api_client.urlopen")
def test_list_unread_summaries_empty_inbox(mock_urlopen):
    mock_urlopen.return_value = _mock_http_response(body=json.dumps({}).encode())
    assert list_unread_summaries(_MOCK_ACCESS_TOKEN, limit=3) == []


class _SmokeVault(DemoVaultCredentialBridge):
    def is_configured(self, ref):  # noqa: ARG002
        return True

    def resolve_credential(self, ref):
        return CredentialResolution(
            ok=True,
            purpose_code=ref.purpose_code,
            ref=ref.ref_id,
            token_intent="gmail.readonly",
            secret_value=_MOCK_SECRET_JSON,
        )


@patch("integrations.mail.providers.gmail_oauth.gmail_list_unread_summaries")
def test_gmail_connector_uses_live_api_when_smoke_on(mock_live, monkeypatch):
    monkeypatch.setenv(ENV_GMAIL_SMOKE, "1")
    mock_live.return_value = [
        MailMessageSummary(
            message_id="live-msg-001",
            subject_preview="Live subject",
            from_preview="live@example.invalid",
            received_at="2026-06-20T12:00:00Z",
        ),
    ]
    connector = GmailOAuthConnector(vault_bridge=_SmokeVault())
    ref = mail_read_credential_ref("operator@example.invalid")
    summaries = connector.list_unread_summaries(account_id=ref.account_id, limit=1)
    assert len(summaries) == 1
    assert summaries[0].message_id == "live-msg-001"
    mock_live.assert_called_once()
    assert mock_live.call_args.args[0] == _MOCK_ACCESS_TOKEN


@patch("integrations.mail.providers.gmail_oauth.gmail_list_unread_summaries")
def test_gmail_connector_falls_back_to_mock_when_smoke_off(mock_live, monkeypatch):
    monkeypatch.delenv(ENV_GMAIL_SMOKE, raising=False)
    connector = GmailOAuthConnector(vault_bridge=_SmokeVault())
    ref = mail_read_credential_ref("operator@example.invalid")
    summaries = connector.list_unread_summaries(account_id=ref.account_id, limit=1)
    assert len(summaries) == 1
    assert summaries[0].message_id.startswith("vault-mail-read:")
    mock_live.assert_not_called()


@pytest.mark.skipif(
    not is_gmail_smoke_enabled(),
    reason="LUMOS_GMAIL_SMOKE not set — operator-only live Gmail smoke",
)
def test_live_gmail_smoke_via_vault():
    """Operatör smoke — vault + Gmail readonly; CI default kapalı."""
    account_id = os.environ.get(ENV_GMAIL_SMOKE_ACCOUNT, "").strip()
    if not account_id:
        pytest.skip("LUMOS_GMAIL_SMOKE_ACCOUNT required for live smoke")

    bridge = DemoVaultCredentialBridge()
    ref = mail_read_credential_ref(account_id)
    if not bridge.is_configured(ref):
        pytest.skip("vault env not configured for smoke account")

    connector = GmailOAuthConnector(vault_bridge=bridge)
    summaries = connector.list_unread_summaries(account_id=account_id, limit=5)
    assert isinstance(summaries, list)
    for item in summaries:
        assert isinstance(item.message_id, str) and item.message_id
        assert isinstance(item.subject_preview, str)
        assert isinstance(item.from_preview, str)
        assert _MOCK_ACCESS_TOKEN not in str(item)
        assert "access_token" not in str(item).lower()
