import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from integrations.models import IntegrationRequest
from integrations.providers import meetings_provider
from integrations.registry import register_default_integrations


def test_meetings_catalog_contains_video_and_calling_platforms():
    result = register_default_integrations().run(
        IntegrationRequest(provider="meetings", action="list_catalog", payload={}),
    )

    assert result.ok is True
    assert result.data["autonomous_connect"] is False
    assert result.data["credentials_in_payload"] is False
    ids = {item["provider_id"] for item in result.data["providers"]}
    assert {"zoom", "microsoft_teams", "google_meet", "webex", "jitsi"} <= ids


def test_meetings_connect_requires_explicit_approval():
    result = register_default_integrations().run(
        IntegrationRequest(
            provider="meetings",
            action="start_connect",
            payload={"provider_id": "zoom"},
        ),
    )

    assert result.ok is False
    assert result.error == "approval_required"
    assert result.data["requires_approval"] is True


def test_meetings_connect_stops_until_credentials_are_configured(monkeypatch):
    monkeypatch.delenv("LUMOS_ZOOM_ACCESS_TOKEN", raising=False)
    result = register_default_integrations().run(
        IntegrationRequest(
            provider="meetings",
            action="start_connect",
            payload={"provider_id": "zoom"},
            requires_approval=True,
        ),
    )

    assert result.ok is False
    assert result.error == "meetings_provider_not_configured"
    assert result.data["status"] == "awaiting_credentials"


def test_zoom_live_check_returns_safe_identity(monkeypatch):
    monkeypatch.setenv("LUMOS_ZOOM_ACCESS_TOKEN", "test-secret-token")
    monkeypatch.setattr(
        meetings_provider,
        "_http_get_json",
        lambda request: {"id": "zoom-123", "email": "lumos@example.com"},
    )

    result = register_default_integrations().run(
        IntegrationRequest(
            provider="meetings",
            action="verify_connection",
            payload={"provider_id": "zoom"},
            requires_approval=True,
        ),
    )

    assert result.ok is True
    assert result.data["status"] == "connected"
    assert result.data["identity"]["email"] == "lumos@example.com"
    assert "test-secret-token" not in str(result.data)


def test_microsoft_teams_live_check_returns_safe_identity(monkeypatch):
    monkeypatch.setenv("LUMOS_MICROSOFT_TEAMS_ACCESS_TOKEN", "test-secret-token")
    monkeypatch.setattr(
        meetings_provider,
        "_http_get_json",
        lambda request: {"id": "ms-123", "displayName": "Lumos Teams"},
    )

    result = register_default_integrations().run(
        IntegrationRequest(
            provider="meetings",
            action="verify_connection",
            payload={"provider_id": "microsoft_teams"},
            requires_approval=True,
        ),
    )

    assert result.ok is True
    assert result.data["identity"]["display_name"] == "Lumos Teams"
    assert "test-secret-token" not in str(result.data)


def test_google_meet_live_check_returns_safe_identity(monkeypatch):
    monkeypatch.setenv("LUMOS_GOOGLE_MEET_ACCESS_TOKEN", "test-secret-token")
    monkeypatch.setattr(
        meetings_provider,
        "_http_get_json",
        lambda request: {"sub": "gm-123", "name": "Lumos Meet"},
    )

    result = register_default_integrations().run(
        IntegrationRequest(
            provider="meetings",
            action="verify_connection",
            payload={"provider_id": "google_meet"},
            requires_approval=True,
        ),
    )

    assert result.ok is True
    assert result.data["identity"]["name"] == "Lumos Meet"
    assert result.data["identity"]["verified_scope"] == "google_account_identity_only"
    assert "test-secret-token" not in str(result.data)


def test_webex_live_check_returns_safe_identity(monkeypatch):
    monkeypatch.setenv("LUMOS_WEBEX_ACCESS_TOKEN", "test-secret-token")
    monkeypatch.setattr(
        meetings_provider,
        "_http_get_json",
        lambda request: {"id": "webex-123", "displayName": "Lumos Webex"},
    )

    result = register_default_integrations().run(
        IntegrationRequest(
            provider="meetings",
            action="verify_connection",
            payload={"provider_id": "webex"},
            requires_approval=True,
        ),
    )

    assert result.ok is True
    assert result.data["identity"]["display_name"] == "Lumos Webex"
    assert "test-secret-token" not in str(result.data)


def test_meetings_live_check_fails_closed(monkeypatch):
    monkeypatch.setenv("LUMOS_ZOOM_ACCESS_TOKEN", "test-secret-token")
    monkeypatch.setattr(meetings_provider, "_http_get_json", lambda request: {})

    result = register_default_integrations().run(
        IntegrationRequest(
            provider="meetings",
            action="verify_connection",
            payload={"provider_id": "zoom"},
            requires_approval=True,
        ),
    )

    assert result.ok is False
    assert result.error == "meetings_connection_check_failed"
    assert result.data["status"] == "verification_failed"


def test_meetings_live_check_not_supported_for_catalog_only_provider(monkeypatch):
    result = register_default_integrations().run(
        IntegrationRequest(
            provider="meetings",
            action="verify_connection",
            payload={"provider_id": "jitsi"},
            requires_approval=True,
        ),
    )

    assert result.ok is False
    assert result.error == "meetings_live_check_not_supported"


def test_meetings_rejects_unknown_provider():
    result = register_default_integrations().run(
        IntegrationRequest(
            provider="meetings",
            action="connection_status",
            payload={"provider_id": "unknown"},
        ),
    )

    assert result.ok is False
    assert result.error == "meetings_provider_unknown"
