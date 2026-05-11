from __future__ import annotations
from collections.abc import Callable
from .models import IntegrationRequest, IntegrationResult
IntegrationHandler = Callable[[IntegrationRequest], IntegrationResult]
class IntegrationRegistry:
    def __init__(self) -> None:
        self._handlers: dict[tuple[str, str], IntegrationHandler] = {}
    def register(self, provider: str, action: str, handler: IntegrationHandler) -> None:
        key = (provider.strip().lower(), action.strip().lower())
        if not key[0] or not key[1]:
            raise ValueError("provider/action boş olamaz")
        self._handlers[key] = handler
    def run(self, request: IntegrationRequest) -> IntegrationResult:
        key = (request.provider.strip().lower(), request.action.strip().lower())
        handler = self._handlers.get(key)
        if handler is None:
            return IntegrationResult(
                ok=False,
                provider=request.provider,
                action=request.action,
                data={},
                error="integration_handler_not_found",
            )
        return handler(request)
registry = IntegrationRegistry()


def register_default_integrations() -> IntegrationRegistry:
    from integrations.providers.openai_provider import register_openai_provider
    from integrations.providers.web_search_provider import register_web_search_provider
    from integrations.providers.device_provider import register_device_provider

    register_openai_provider(registry.register)
    register_web_search_provider(registry.register)
    register_device_provider(registry.register)
    return registry
