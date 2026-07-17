"""
Elektronik Uzmanı — sağlayıcı (Provider) arayüzü ve BOŞ registry (bkz.
design doc §7, `integrations/quantum_registry.py` deseniyle hizalı).

Bu dosya bilinçli olarak BOŞTUR: `ELECTRONICS_TOOL_PROVIDERS` bu fazda hiçbir
kayıt içermez. Faz 2'de (canlı E-Helper entegrasyonu, datasheet servisi,
parça veritabanı, ölçüm cihazı adaptörleri) buraya `ElectronicsToolProviderEntry`
kayıtları eklenecektir — bu turda hiçbir gerçek veya stub sağlayıcı yoktur.

`ElectronicsToolProvider`, gelecekteki adaptörlerin uyması gereken arayüzdür.
Mevcut hiçbir sınıf bu arayüzü uygulamıyor; yalnızca sözleşme şeklini sabitler.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

ElectronicsToolType = Literal[
    "datasheet", "part_database", "measurement_device", "equivalent_finder"
]
ElectronicsApprovalTier = Literal["auto-doc", "needs-owner", "blocked"]
ElectronicsProviderStatus = Literal["planned", "stub", "none"]


@dataclass(frozen=True)
class ElectronicsToolProviderEntry:
    """Bir dış araç sağlayıcısının katalog kaydı (yalnızca metadata)."""

    provider_id: str
    display_name: str
    tool_type: ElectronicsToolType
    auth_model: str
    approval_tier: ElectronicsApprovalTier
    status: ElectronicsProviderStatus
    demo_safe_note: str


@runtime_checkable
class ElectronicsToolProvider(Protocol):
    """Faz 2 sağlayıcı adaptörlerinin uygulaması gereken arayüz.

    `verify_connection` yalnızca erişilebilirlik kontrolüdür; hiçbir veri
    çekmez, yazmaz veya sipariş vermez (bkz. ADR-016 `verify_connection`
    sözleşmesi ve design doc §8 NEVER_AUTO tablosu).
    """

    def describe(self) -> ElectronicsToolProviderEntry: ...

    def verify_connection(self) -> bool: ...


# Bilinçli olarak boş — bkz. modül docstring'i.
ELECTRONICS_TOOL_PROVIDERS: tuple[ElectronicsToolProviderEntry, ...] = ()


def list_electronics_tool_providers() -> list[dict[str, str]]:
    """Kayıtlı sağlayıcıların metadata listesini döner. Bu fazda daima []."""
    return [_entry_to_dict(entry) for entry in ELECTRONICS_TOOL_PROVIDERS]


def get_electronics_tool_provider(provider_id: str) -> ElectronicsToolProviderEntry | None:
    """Verilen id ile eşleşen kaydı döner. Registry boş olduğu için bu fazda
    daima None döner."""
    for entry in ELECTRONICS_TOOL_PROVIDERS:
        if entry.provider_id == provider_id:
            return entry
    return None


def _entry_to_dict(entry: ElectronicsToolProviderEntry) -> dict[str, str]:
    return {
        "provider_id": entry.provider_id,
        "display_name": entry.display_name,
        "tool_type": entry.tool_type,
        "auth_model": entry.auth_model,
        "approval_tier": entry.approval_tier,
        "status": entry.status,
        "demo_safe_note": entry.demo_safe_note,
    }
