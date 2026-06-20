import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from integrations.mail.grants import MailGrantSession, validate_mail_grants
from integrations.mail.vault_credential import DemoVaultCredentialBridge, mail_read_credential_ref
from integrations.models import IntegrationRequest
from integrations.registry import register_default_integrations


def _session_payload(
    *,
    grants: list[str] | None = None,
    account_id: str = "user-demo@example.invalid",
) -> dict:
    effective_grants = ["read"] if grants is None else grants
    return {
        "grants": effective_grants,
        "account_id": account_id,
        "session_id": "sess-demo-001",
    }


def test_mail_connection_status_demo_stub():
    reg = register_default_integrations()
    result = reg.run(
        IntegrationRequest(
            provider="mail",
            action="connection_status",
            payload=_session_payload(),
        ),
    )
    assert result.ok is True
    assert result.data["provider"] == "gmail_oauth"
    assert result.data["vault_configured"] is False
    assert result.data["connector_ready"] is True
    assert result.data["vault_hint"]["boundary"] == "private_vault_impl_required"


def test_mail_list_unread_requires_read_grant():
    reg = register_default_integrations()
    result = reg.run(
        IntegrationRequest(
            provider="mail",
            action="list_unread",
            payload=_session_payload(grants=[]),
        ),
    )
    assert result.ok is False
    assert result.error == "read_grant_required"


def test_mail_notify_requires_read_and_notify_grants():
    reg = register_default_integrations()
    result = reg.run(
        IntegrationRequest(
            provider="mail",
            action="notify_check",
            payload=_session_payload(grants=["notify"]),
        ),
    )
    assert result.ok is False
    assert result.error == "read_grant_required"

    result2 = reg.run(
        IntegrationRequest(
            provider="mail",
            action="notify_check",
            payload=_session_payload(grants=["read"]),
        ),
    )
    assert result2.ok is False
    assert result2.error == "notify_grant_required"


def test_mail_send_reply_blocked_in_dar_v1():
    reg = register_default_integrations()
    result = reg.run(
        IntegrationRequest(
            provider="mail",
            action="send_reply",
            payload=_session_payload(grants=["read", "send_reply"]),
        ),
    )
    assert result.ok is False
    assert result.error == "unsupported_mail_action"


def test_mail_list_unread_vault_not_configured():
    reg = register_default_integrations()
    result = reg.run(
        IntegrationRequest(
            provider="mail",
            action="list_unread",
            payload=_session_payload(grants=["read"]),
        ),
    )
    assert result.ok is False
    assert result.error == "vault_credential_not_configured"


def test_mail_list_unread_with_mock_vault(monkeypatch):
    import integrations.providers.mail_provider as mp
    from integrations.vault.adapter import CredentialResolution

    class ConfiguredVault(DemoVaultCredentialBridge):
        def is_configured(self, ref):  # noqa: ARG002
            return True

        def resolve_credential(self, ref):
            return CredentialResolution(
                ok=True,
                purpose_code=ref.purpose_code,
                ref=ref.ref_id,
                token_intent="gmail.readonly",
            )

    monkeypatch.setattr(mp, "get_vault_credential_bridge", lambda: ConfiguredVault())
    reg = register_default_integrations()
    result = reg.run(
        IntegrationRequest(
            provider="mail",
            action="list_unread",
            payload={**_session_payload(grants=["read"]), "limit": 5},
        ),
    )
    assert result.ok is True
    assert result.data["count"] >= 1
    msg = result.data["messages"][0]
    assert "message_id" in msg
    assert "subject_preview" in msg
    assert msg["message_id"].startswith("vault-mail-read:")
    assert "oauth" not in str(msg).lower()
    assert "token" not in str(msg).lower()


def test_mail_notify_check_with_mock_vault(monkeypatch):
    import integrations.providers.mail_provider as mp

    class ConfiguredVault(DemoVaultCredentialBridge):
        def is_configured(self, ref):  # noqa: ARG002
            return True

    monkeypatch.setattr(mp, "get_vault_credential_bridge", lambda: ConfiguredVault())
    reg = register_default_integrations()
    result = reg.run(
        IntegrationRequest(
            provider="mail",
            action="notify_check",
            payload=_session_payload(grants=["read", "notify"]),
        ),
    )
    assert result.ok is True
    assert result.data["notify_eligible"] is True


def test_validate_mail_grants_rejects_send_in_session():
    session = MailGrantSession(
        grants=frozenset({"read", "send_reply"}),
        account_id="a@example.invalid",
        session_id="s1",
    )
    assert validate_mail_grants(session) == "unsupported_mail_grant"


def test_vault_credential_ref_has_no_secret():
    ref = mail_read_credential_ref("user@example.invalid")
    assert ref.purpose_code == "integration.mail.read"
    assert "secret" not in ref.ref_id.lower()
    assert "token" not in ref.ref_id.lower()
