from __future__ import annotations
from typing import Any
from integrations.models import IntegrationRequest, IntegrationResult
from engine.model_client import CyberModelError, PURPOSE_CHAT, PURPOSE_CYBER


def _purpose_from_payload(payload: dict[str, Any]) -> str:
    raw = payload.get("purpose") or payload.get("layer") or PURPOSE_CHAT
    if not isinstance(raw, str):
        return PURPOSE_CHAT
    value = raw.strip().lower()
    if value == PURPOSE_CYBER:
        return PURPOSE_CYBER
    return PURPOSE_CHAT


def run_openai_action(request: IntegrationRequest) -> IntegrationResult:
    action = request.action.strip().lower()
    if action not in {"respond", "complete", "chat"}:
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={},
            error="unsupported_openai_action",
        )
    prompt = request.payload.get("prompt") or request.payload.get("message") or request.payload.get("input")
    if not isinstance(prompt, str) or not prompt.strip():
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={},
            error="prompt_required",
        )
    purpose = _purpose_from_payload(request.payload)
    try:
        from engine.model_client import ModelClient
        client = ModelClient()
        text = client.generate(prompt.strip(), purpose=purpose)
        return IntegrationResult(
            ok=True,
            provider=request.provider,
            action=request.action,
            data={"text": text},
        )
    except CyberModelError as exc:
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={"status": exc.status, "model": exc.model},
            error=f"openai_cyber_{exc.status}",
        )
    except Exception as exc:
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={},
            error=f"openai_provider_error:{type(exc).__name__}",
        )
def register_openai_provider(register: Any) -> None:
    register("openai", "respond", run_openai_action)
    register("openai", "complete", run_openai_action)
    register("openai", "chat", run_openai_action)
