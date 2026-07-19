import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from integrations.models import IntegrationRequest
from integrations.providers import communications_provider
from integrations.registry import register_default_integrations


def test_communications_catalog_contains_mainstream_and_regional_providers():
    result = register_default_integrations().run(
        IntegrationRequest(provider="communications", action="list_catalog", payload={}),
    )

    assert result.ok is True
    assert result.data["autonomous_connect"] is False
    assert result.data["credentials_in_payload"] is False
    ids = {item["provider_id"] for item in result.data["providers"]}
    assert {"telegram", "whatsapp", "tiktok", "facebook", "instagram", "x"} <= ids
    assert {"gmail", "outlook", "hotmail", "yahoo_mail"} <= ids
    assert {"line", "kakao_talk", "gmx", "zoho_mail"} <= ids


def test_communications_catalog_can_filter_category():
    result = register_default_integrations().run(
        IntegrationRequest(
            provider="communications",
            action="list_catalog",
            payload={"category": "mail"},
        ),
    )

    assert result.ok is True
    assert result.data["providers"]
    assert {item["category"] for item in result.data["providers"]} == {"mail"}


def test_communications_connect_requires_explicit_approval():
    result = register_default_integrations().run(
        IntegrationRequest(
            provider="communications",
            action="start_connect",
            payload={"provider_id": "telegram"},
        ),
    )

    assert result.ok is False
    assert result.error == "approval_required"
    assert result.data["requires_approval"] is True


def test_communications_connect_stops_until_credentials_are_configured(monkeypatch):
    monkeypatch.delenv("LUMOS_TELEGRAM_BOT_TOKEN", raising=False)
    result = register_default_integrations().run(
        IntegrationRequest(
            provider="communications",
            action="start_connect",
            payload={"provider_id": "telegram"},
            requires_approval=True,
        ),
    )

    assert result.ok is False
    assert result.error == "communications_provider_not_configured"
    assert result.data["status"] == "awaiting_credentials"
    assert result.data["missing_configuration"] == ["LUMOS_TELEGRAM_BOT_TOKEN"]


def test_whatsapp_configuration_can_be_prepared_without_exposing_secrets(monkeypatch):
    monkeypatch.setenv("LUMOS_WHATSAPP_ACCESS_TOKEN", "test-secret-token")
    monkeypatch.setenv("LUMOS_WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("LUMOS_META_GRAPH_VERSION", "v99.0")

    result = register_default_integrations().run(
        IntegrationRequest(
            provider="communications",
            action="start_connect",
            payload={"provider_id": "whatsapp"},
            requires_approval=True,
        ),
    )

    assert result.ok is True
    assert result.data["status"] == "configured"
    assert result.data["next_action"] == "verify_connection"
    assert "test-secret-token" not in str(result.data)


def test_whatsapp_live_check_returns_safe_identity(monkeypatch):
    monkeypatch.setenv("LUMOS_WHATSAPP_ACCESS_TOKEN", "test-secret-token")
    monkeypatch.setenv("LUMOS_WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("LUMOS_META_GRAPH_VERSION", "v99.0")
    monkeypatch.setattr(
        communications_provider,
        "_http_get_json",
        lambda request: {
            "id": "123456",
            "verified_name": "Lumos",
            "display_phone_number": "+90 555 000 00 00",
        },
    )

    result = register_default_integrations().run(
        IntegrationRequest(
            provider="communications",
            action="verify_connection",
            payload={"provider_id": "whatsapp"},
            requires_approval=True,
        ),
    )

    assert result.ok is True
    assert result.data["status"] == "connected"
    assert result.data["identity"]["verified_name"] == "Lumos"
    assert "test-secret-token" not in str(result.data)


def test_telegram_live_check_returns_safe_identity(monkeypatch):
    monkeypatch.setenv("LUMOS_TELEGRAM_BOT_TOKEN", "123:test-secret-token")
    monkeypatch.setattr(
        communications_provider,
        "_http_get_json",
        lambda request: {
            "ok": True,
            "result": {"id": 42, "username": "lumos_bot", "first_name": "Lumos"},
        },
    )

    result = register_default_integrations().run(
        IntegrationRequest(
            provider="communications",
            action="verify_connection",
            payload={"provider_id": "telegram"},
            requires_approval=True,
        ),
    )

    assert result.ok is True
    assert result.data["identity"]["username"] == "lumos_bot"
    assert "test-secret-token" not in str(result.data)


def test_whatsapp_live_check_fails_closed(monkeypatch):
    monkeypatch.setenv("LUMOS_WHATSAPP_ACCESS_TOKEN", "test-secret-token")
    monkeypatch.setenv("LUMOS_WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("LUMOS_META_GRAPH_VERSION", "v99.0")
    monkeypatch.setattr(communications_provider, "_http_get_json", lambda request: {})

    result = register_default_integrations().run(
        IntegrationRequest(
            provider="communications",
            action="verify_connection",
            payload={"provider_id": "whatsapp"},
            requires_approval=True,
        ),
    )

    assert result.ok is False
    assert result.error == "communications_connection_check_failed"
    assert result.data["status"] == "verification_failed"
    assert "test-secret-token" not in str(result.data)


def test_facebook_live_check_returns_safe_identity(monkeypatch):
    monkeypatch.setenv("LUMOS_FACEBOOK_PAGE_ACCESS_TOKEN", "test-secret-token")
    monkeypatch.setenv("LUMOS_META_GRAPH_VERSION", "v99.0")
    monkeypatch.setattr(
        communications_provider,
        "_http_get_json",
        lambda request: {"id": "fb-123", "name": "Lumos Page"},
    )

    result = register_default_integrations().run(
        IntegrationRequest(
            provider="communications",
            action="verify_connection",
            payload={"provider_id": "facebook"},
            requires_approval=True,
        ),
    )

    assert result.ok is True
    assert result.data["status"] == "connected"
    assert result.data["identity"]["name"] == "Lumos Page"
    assert "test-secret-token" not in str(result.data)


def test_instagram_live_check_returns_safe_identity(monkeypatch):
    monkeypatch.setenv("LUMOS_INSTAGRAM_ACCESS_TOKEN", "test-secret-token")
    monkeypatch.setenv("LUMOS_META_GRAPH_VERSION", "v99.0")
    monkeypatch.setattr(
        communications_provider,
        "_http_get_json",
        lambda request: {"id": "ig-123", "username": "lumos_ig"},
    )

    result = register_default_integrations().run(
        IntegrationRequest(
            provider="communications",
            action="verify_connection",
            payload={"provider_id": "instagram"},
            requires_approval=True,
        ),
    )

    assert result.ok is True
    assert result.data["identity"]["username"] == "lumos_ig"
    assert "test-secret-token" not in str(result.data)


def test_threads_live_check_returns_safe_identity(monkeypatch):
    monkeypatch.setenv("LUMOS_THREADS_ACCESS_TOKEN", "test-secret-token")
    captured_request = {}

    def fake_http_get_json(request):
        captured_request["url"] = request.full_url
        captured_request["authorization"] = request.get_header("Authorization")
        return {"id": "th-123", "username": "lumos_threads"}

    monkeypatch.setattr(
        communications_provider,
        "_http_get_json",
        fake_http_get_json,
    )

    result = register_default_integrations().run(
        IntegrationRequest(
            provider="communications",
            action="verify_connection",
            payload={"provider_id": "threads"},
            requires_approval=True,
        ),
    )

    assert result.ok is True
    assert result.data["identity"]["username"] == "lumos_threads"
    assert "test-secret-token" not in str(result.data)
    assert "test-secret-token" not in captured_request["url"]
    assert captured_request["authorization"] == "Bearer test-secret-token"


def test_x_live_check_returns_safe_identity(monkeypatch):
    monkeypatch.setenv("LUMOS_X_BEARER_TOKEN", "test-secret-token")
    monkeypatch.setattr(
        communications_provider,
        "_http_get_json",
        lambda request: {"data": {"id": "x-123", "username": "lumos_x"}},
    )

    result = register_default_integrations().run(
        IntegrationRequest(
            provider="communications",
            action="verify_connection",
            payload={"provider_id": "x"},
            requires_approval=True,
        ),
    )

    assert result.ok is True
    assert result.data["identity"]["username"] == "lumos_x"
    assert "test-secret-token" not in str(result.data)


def test_linkedin_live_check_returns_safe_identity(monkeypatch):
    monkeypatch.setenv("LUMOS_LINKEDIN_ACCESS_TOKEN", "test-secret-token")
    monkeypatch.setattr(
        communications_provider,
        "_http_get_json",
        lambda request: {"sub": "li-123", "name": "Lumos LinkedIn"},
    )

    result = register_default_integrations().run(
        IntegrationRequest(
            provider="communications",
            action="verify_connection",
            payload={"provider_id": "linkedin"},
            requires_approval=True,
        ),
    )

    assert result.ok is True
    assert result.data["identity"]["name"] == "Lumos LinkedIn"
    assert "test-secret-token" not in str(result.data)


def test_tiktok_live_check_returns_safe_identity(monkeypatch):
    monkeypatch.setenv("LUMOS_TIKTOK_ACCESS_TOKEN", "test-secret-token")
    monkeypatch.setattr(
        communications_provider,
        "_http_get_json",
        lambda request: {"data": {"user": {"open_id": "tt-123", "display_name": "Lumos TikTok"}}},
    )

    result = register_default_integrations().run(
        IntegrationRequest(
            provider="communications",
            action="verify_connection",
            payload={"provider_id": "tiktok"},
            requires_approval=True,
        ),
    )

    assert result.ok is True
    assert result.data["identity"]["display_name"] == "Lumos TikTok"
    assert "test-secret-token" not in str(result.data)


def test_social_live_check_fails_closed_when_identity_missing(monkeypatch):
    monkeypatch.setenv("LUMOS_X_BEARER_TOKEN", "test-secret-token")
    monkeypatch.setattr(communications_provider, "_http_get_json", lambda request: {})

    result = register_default_integrations().run(
        IntegrationRequest(
            provider="communications",
            action="verify_connection",
            payload={"provider_id": "x"},
            requires_approval=True,
        ),
    )

    assert result.ok is False
    assert result.error == "communications_connection_check_failed"
    assert result.data["status"] == "verification_failed"


def test_communications_rejects_unknown_provider():
    result = register_default_integrations().run(
        IntegrationRequest(
            provider="communications",
            action="connection_status",
            payload={"provider_id": "unknown"},
        ),
    )

    assert result.ok is False
    assert result.error == "communications_provider_unknown"
