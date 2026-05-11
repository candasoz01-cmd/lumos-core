import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from integrations.models import IntegrationRequest, IntegrationResult
from integrations.registry import IntegrationRegistry, register_default_integrations
def test_registry_returns_missing_handler_error():
    reg = IntegrationRegistry()
    result = reg.run(IntegrationRequest(provider="missing", action="noop", payload={}))
    assert result.ok is False
    assert result.error == "integration_handler_not_found"
def test_registry_runs_registered_handler():
    reg = IntegrationRegistry()
    def handler(request: IntegrationRequest) -> IntegrationResult:
        return IntegrationResult(
            ok=True,
            provider=request.provider,
            action=request.action,
            data={"echo": request.payload["value"]},
        )
    reg.register("demo", "echo", handler)
    result = reg.run(IntegrationRequest(provider="demo", action="echo", payload={"value": "ok"}))
    assert result.ok is True
    assert result.data == {"echo": "ok"}
def test_default_integrations_register_openai_actions():
    reg = register_default_integrations()
    for action in ["respond", "complete", "chat"]:
        result = reg.run(IntegrationRequest(provider="openai", action=action, payload={}))
        assert result.ok is False
        assert result.error == "prompt_required"


def test_default_integrations_web_search_not_configured():
    reg = register_default_integrations()
    result = reg.run(IntegrationRequest(provider="web", action="search", payload={"query": "lumos"}))
    assert result.ok is False
    assert result.error == "web_search_provider_not_configured"
    assert result.data["query"] == "lumos"
    assert result.data["results"] == []
    assert [e["name"] for e in result.data["engines"]] == ["brave", "google", "bing", "duckduckgo"]


def test_web_search_payload_routing_and_engines():
    reg = register_default_integrations()
    result = reg.run(
        IntegrationRequest(
            provider="web",
            action="search",
            payload={
                "query": "conta nerede",
                "country": "TR",
                "language": "tr",
                "engines": ["brave", "google", "bing"],
                "vertical": "repair_parts",
            },
        )
    )
    assert result.ok is False
    assert result.error == "web_search_provider_not_configured"
    assert result.data["query"] == "conta nerede"
    assert result.data["country"] == "TR"
    assert result.data["language"] == "tr"
    assert result.data["vertical"] == "repair_parts"
    assert [e["name"] for e in result.data["engines"]] == ["brave", "google", "bing"]
