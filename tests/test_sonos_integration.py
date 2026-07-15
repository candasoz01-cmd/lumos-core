import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from integrations.models import IntegrationRequest
from integrations.providers import sonos_provider
from integrations.registry import register_default_integrations


def _run(action: str, *, requires_approval: bool = False):
    return register_default_integrations().run(
        IntegrationRequest(
            provider="sonos",
            action=action,
            payload={},
            requires_approval=requires_approval,
        ),
    )


def test_sonos_connection_status_reports_identity_required(monkeypatch):
    monkeypatch.delenv("LUMOS_SONOS_ACCESS_TOKEN", raising=False)

    result = _run("connection_status")

    assert result.ok is True
    assert result.data["identity_status"] == "identity_required"
    assert result.data["oauth_configuration"] == "missing"
    assert result.data["secret_source"] == "environment_only"
    assert result.data["execution_live"] is False


def test_sonos_live_check_returns_safe_identity(monkeypatch):
    monkeypatch.setenv("LUMOS_SONOS_ACCESS_TOKEN", "test-secret-token")
    monkeypatch.setattr(
        sonos_provider,
        "_http_get_json",
        lambda request: {"households": [{"id": "Sonos_abc123"}]},
    )

    result = _run("verify_connection", requires_approval=True)

    assert result.ok is True
    assert result.data["status"] == "connected"
    assert result.data["identity"]["household_count"] == 1
    assert "test-secret-token" not in str(result.data)


def test_sonos_live_check_requires_approval_and_configuration(monkeypatch):
    monkeypatch.delenv("LUMOS_SONOS_ACCESS_TOKEN", raising=False)

    denied = _run("verify_connection")
    unconfigured = _run("verify_connection", requires_approval=True)

    assert denied.ok is False
    assert denied.error == "approval_required"
    assert unconfigured.ok is False
    assert unconfigured.error == "sonos_provider_not_configured"


def test_sonos_live_check_fails_closed(monkeypatch):
    monkeypatch.setenv("LUMOS_SONOS_ACCESS_TOKEN", "test-secret-token")
    monkeypatch.setattr(sonos_provider, "_http_get_json", lambda request: {})

    result = _run("verify_connection", requires_approval=True)

    assert result.ok is False
    assert result.error == "sonos_connection_check_failed"
    assert result.data["status"] == "verification_failed"
