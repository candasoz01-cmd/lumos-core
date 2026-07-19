import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from integrations.models import IntegrationRequest
from integrations.registry import register_default_integrations


def _run(action: str, payload: dict | None = None):
    return register_default_integrations().run(
        IntegrationRequest(provider="service_gateway", action=action, payload=payload or {}),
    )


def test_service_gateway_describes_one_trust_contract_for_all_families():
    result = _run("describe_contract")

    assert result.ok is True
    assert result.data["name"] == "Lumos API"
    assert result.data["status"] == "public_foundation"
    assert result.data["production_transport"] is False
    assert result.data["external_effects_require_approval"] is True
    assert result.data["provider_credentials_embedded"] is False
    assert "execute_or_deny" in result.data["trust_stages"]
    assert {family["id"] for family in result.data["families"]} == {
        "ai",
        "security",
        "identity",
        "tools",
        "integrations",
        "regional",
        "public_services",
    }


def test_service_gateway_route_is_a_non_executable_plan():
    result = _run("plan_route", {"family": "public_services"})

    assert result.ok is True
    assert result.data["family"]["path"] == "/v1/public-services/route"
    assert result.data["route_status"] == "plan_only"
    assert result.data["execution_permitted"] is False
    assert result.data["requires_approval"] is True
    assert result.data["provider_selection"] == "not_executed"


def test_service_gateway_rejects_unknown_family():
    result = _run("plan_route", {"family": "unknown"})

    assert result.ok is False
    assert result.error == "service_family_unknown"
    assert "public_services" in result.data["available_families"]
