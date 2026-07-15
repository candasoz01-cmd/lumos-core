import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from integrations.models import IntegrationRequest
from integrations.providers import youtube_provider
from integrations.registry import register_default_integrations


def _run(action: str, *, requires_approval: bool = False):
    return register_default_integrations().run(
        IntegrationRequest(
            provider="youtube",
            action=action,
            payload={},
            requires_approval=requires_approval,
        ),
    )


def test_youtube_oauth_contract_uses_env_and_reports_identity_required(monkeypatch):
    for name in (
        "LUMOS_GOOGLE_OAUTH_CLIENT_ID",
        "LUMOS_GOOGLE_OAUTH_CLIENT_SECRET",
        "LUMOS_GOOGLE_OAUTH_REDIRECT_URI",
    ):
        monkeypatch.delenv(name, raising=False)

    result = _run("authorization_contract")

    assert result.ok is True
    assert result.data["identity_status"] == "identity_required"
    assert result.data["oauth_configuration"] == "missing"
    assert result.data["secret_source"] == "environment_only"
    assert result.data["execution_live"] is False
    assert result.data["workflow"] == ["connect", "draft", "explicit_approval", "publish"]


def test_youtube_publish_requires_explicit_approval_and_never_fakes_execution():
    denied = _run("publish")
    approved = _run("publish", requires_approval=True)

    assert denied.ok is False
    assert denied.error == "approval_required"
    assert denied.data["execution_started"] is False
    assert approved.ok is False
    assert approved.error == "youtube_publish_connector_not_live"
    assert approved.data["execution_started"] is False


def test_youtube_live_check_returns_safe_identity(monkeypatch):
    monkeypatch.setenv("LUMOS_YOUTUBE_ACCESS_TOKEN", "test-secret-token")
    monkeypatch.setattr(
        youtube_provider,
        "_http_get_json",
        lambda request: {"sub": "yt-123", "name": "Lumos YouTube"},
    )

    result = _run("verify_connection", requires_approval=True)

    assert result.ok is True
    assert result.data["status"] == "connected"
    assert result.data["identity"]["name"] == "Lumos YouTube"
    assert "test-secret-token" not in str(result.data)


def test_youtube_live_check_requires_approval_and_configuration(monkeypatch):
    monkeypatch.delenv("LUMOS_YOUTUBE_ACCESS_TOKEN", raising=False)

    denied = _run("verify_connection")
    unconfigured = _run("verify_connection", requires_approval=True)

    assert denied.ok is False
    assert denied.error == "approval_required"
    assert unconfigured.ok is False
    assert unconfigured.error == "youtube_provider_not_configured"


def test_youtube_live_check_fails_closed(monkeypatch):
    monkeypatch.setenv("LUMOS_YOUTUBE_ACCESS_TOKEN", "test-secret-token")
    monkeypatch.setattr(youtube_provider, "_http_get_json", lambda request: {})

    result = _run("verify_connection", requires_approval=True)

    assert result.ok is False
    assert result.error == "youtube_connection_check_failed"
    assert result.data["status"] == "verification_failed"
