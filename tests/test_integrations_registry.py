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
