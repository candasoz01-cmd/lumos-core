from integrations.models import IntegrationRequest
from integrations.registry import register_default_integrations


def test_china_catalog_is_local_and_payment_free():
    result = register_default_integrations().run(
        IntegrationRequest(provider="china", action="list_catalog", payload={}),
    )
    assert result.ok is True
    assert result.data["region"] == "CN"
    assert result.data["count"] == 4
    assert result.data["autonomous_sync"] is False
    assert result.data["payments_in_scope"] is False
    assert {item["provider_id"] for item in result.data["providers"]} == {
        "wecom",
        "dingtalk",
        "feishu",
        "alipay_mini_program",
    }


def test_china_sync_never_starts_without_approval():
    result = register_default_integrations().run(
        IntegrationRequest(
            provider="china",
            action="start_sync",
            payload={"provider_id": "feishu"},
        ),
    )
    assert result.ok is False
    assert result.error == "approval_required"
    assert result.data["autonomous_sync"] is False


def test_china_sync_waits_for_credentials_after_approval():
    result = register_default_integrations().run(
        IntegrationRequest(
            provider="china",
            action="start_sync",
            payload={"provider_id": "dingtalk"},
            requires_approval=True,
        ),
    )
    assert result.ok is False
    assert result.error == "china_provider_not_configured"
    assert result.data["status"] == "awaiting_credentials"


def test_china_sync_status_exposes_scopes():
    result = register_default_integrations().run(
        IntegrationRequest(
            provider="china",
            action="sync_status",
            payload={"provider_id": "wecom"},
        ),
    )
    assert result.ok is True
    assert result.data["sync_scopes"] == ["contacts", "messages", "calendar"]
