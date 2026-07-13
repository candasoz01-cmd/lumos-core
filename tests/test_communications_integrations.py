import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from integrations.models import IntegrationRequest
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


def test_communications_connect_stops_until_credentials_are_configured():
    result = register_default_integrations().run(
        IntegrationRequest(
            provider="communications",
            action="start_connect",
            payload={"provider_id": "gmail"},
            requires_approval=True,
        ),
    )

    assert result.ok is False
    assert result.error == "communications_provider_not_configured"
    assert result.data["status"] == "awaiting_credentials"


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
