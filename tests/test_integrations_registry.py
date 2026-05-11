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


def test_brave_api_called_when_engine_brave_and_key_set(monkeypatch):
    import integrations.providers.web_search_provider as wsp

    class FakeResp:
        def read(self):
            import json

            return json.dumps(
                {
                    "web": {
                        "results": [
                            {"title": "T", "url": "https://u.test", "description": "D"},
                        ],
                    },
                },
            ).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "k-test")
    monkeypatch.setattr(wsp.urllib.request, "urlopen", lambda *a, **k: FakeResp())
    reg = register_default_integrations()
    r = reg.run(
        IntegrationRequest(
            provider="web",
            action="search",
            payload={"query": "lumos", "engine": "brave"},
        ),
    )
    assert r.ok is True
    assert r.error == ""
    assert len(r.data["results"]) == 1
    assert r.data["results"][0]["engine"] == "brave"
    assert r.data["results"][0]["items"][0]["url"] == "https://u.test"


def test_brave_api_skipped_for_multi_engine_even_with_key(monkeypatch):
    import integrations.providers.web_search_provider as wsp

    calls: list[int] = []

    def boom(*a, **k):
        calls.append(1)
        raise AssertionError("Brave HTTP should not run for multi-engine list")

    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "k-test")
    monkeypatch.setattr(wsp.urllib.request, "urlopen", boom)
    reg = register_default_integrations()
    r = reg.run(
        IntegrationRequest(
            provider="web",
            action="search",
            payload={"query": "x", "engines": ["brave", "google"]},
        ),
    )
    assert calls == []
    assert r.ok is False


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
def test_device_unlock_requires_approval():
    reg = register_default_integrations()
    result = reg.run(
        IntegrationRequest(
            provider="device",
            action="unlock",
            payload={"device_id": "front-door", "vendor": "welock"},
        )
    )
    assert result.ok is False
    assert result.error == "approval_required"
    assert result.data["risk_level"] == "high"
    assert result.data["requires_approval"] is True
def test_device_status_requires_device_id():
    reg = register_default_integrations()
    result = reg.run(
        IntegrationRequest(
            provider="device",
            action="lock_status",
            payload={},
        )
    )
    assert result.ok is False
    assert result.error == "device_id_required"
def test_device_unlock_with_approval_is_not_configured_without_vendor_adapter():
    reg = register_default_integrations()
    result = reg.run(
        IntegrationRequest(
            provider="device",
            action="unlock",
            payload={"device_id": "front-door", "vendor": "welock"},
            risk_level="high",
            requires_approval=True,
        )
    )
    assert result.ok is False
    assert result.error == "device_provider_not_configured"
