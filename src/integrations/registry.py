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
    from integrations.providers.bilibili_provider import register_bilibili_provider
    from integrations.providers.china_provider import register_china_provider
    from integrations.providers.communications_provider import register_communications_provider
    from integrations.providers.device_provider import register_device_provider
    from integrations.providers.douyin_provider import register_douyin_provider
    from integrations.providers.global_catalog_provider import register_global_catalog_provider
    from integrations.providers.integration_onboarding_provider import register_integration_onboarding_provider
    from integrations.providers.mail_provider import register_mail_provider
    from integrations.providers.meetings_provider import register_meetings_provider
    from integrations.providers.openai_provider import register_openai_provider
    from integrations.providers.quantum_provider import register_quantum_provider
    from integrations.providers.rutube_provider import register_rutube_provider
    from integrations.providers.service_gateway_provider import register_service_gateway_provider
    from integrations.providers.sharechat_provider import register_sharechat_provider
    from integrations.providers.sonos_provider import register_sonos_provider
    from integrations.providers.vk_provider import register_vk_provider
    from integrations.providers.web_search_provider import register_web_search_provider
    from integrations.providers.wechat_provider import register_wechat_provider
    from integrations.providers.weibo_provider import register_weibo_provider
    from integrations.providers.xiaohongshu_provider import register_xiaohongshu_provider
    from integrations.providers.youtube_provider import register_youtube_provider

    register_openai_provider(registry.register)
    register_web_search_provider(registry.register)
    register_device_provider(registry.register)
    register_global_catalog_provider(registry.register)
    register_integration_onboarding_provider(registry.register)
    register_mail_provider(registry.register)
    register_meetings_provider(registry.register)
    register_quantum_provider(registry.register)
    register_communications_provider(registry.register)
    register_china_provider(registry.register)
    register_youtube_provider(registry.register)
    register_bilibili_provider(registry.register)
    register_rutube_provider(registry.register)
    register_service_gateway_provider(registry.register)
    register_sharechat_provider(registry.register)
    register_vk_provider(registry.register)
    register_douyin_provider(registry.register)
    register_weibo_provider(registry.register)
    register_xiaohongshu_provider(registry.register)
    register_wechat_provider(registry.register)
    register_sonos_provider(registry.register)
    return registry
