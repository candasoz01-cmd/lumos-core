"""Elektronik Uzmanı — sağlayıcı (Provider) arayüzü ve boş registry testleri."""
from __future__ import annotations

from electronics.registry import (
    ELECTRONICS_TOOL_PROVIDERS,
    ElectronicsToolProvider,
    ElectronicsToolProviderEntry,
    get_electronics_tool_provider,
    list_electronics_tool_providers,
)


def test_registry_is_empty_this_phase():
    assert ELECTRONICS_TOOL_PROVIDERS == ()
    assert list_electronics_tool_providers() == []


def test_get_provider_returns_none_when_empty():
    assert get_electronics_tool_provider("anything") is None


def test_provider_entry_shape_is_usable_even_though_unregistered():
    # Registry boş olsa da, gelecekteki adaptörlerin uyacağı veri şeklini
    # burada doğruluyoruz (Faz 2 hazırlığı; bu turda gerçek kayıt yok).
    entry = ElectronicsToolProviderEntry(
        provider_id="example_datasheet_service",
        display_name="Örnek Datasheet Servisi",
        tool_type="datasheet",
        auth_model="API key",
        approval_tier="needs-owner",
        status="planned",
        demo_safe_note="Henüz bağlı değil; yalnızca arayüz şekli için örnek.",
    )
    assert entry.provider_id == "example_datasheet_service"
    assert entry not in ELECTRONICS_TOOL_PROVIDERS


def test_electronics_tool_provider_protocol_is_runtime_checkable():
    class DummyProvider:
        def describe(self) -> ElectronicsToolProviderEntry:
            return ElectronicsToolProviderEntry(
                provider_id="dummy",
                display_name="Dummy",
                tool_type="part_database",
                auth_model="none",
                approval_tier="blocked",
                status="none",
                demo_safe_note="Test-only stand-in; not a real adapter.",
            )

        def verify_connection(self) -> bool:
            return False

    assert isinstance(DummyProvider(), ElectronicsToolProvider)


def test_object_missing_methods_does_not_satisfy_protocol():
    class NotAProvider:
        pass

    assert not isinstance(NotAProvider(), ElectronicsToolProvider)
