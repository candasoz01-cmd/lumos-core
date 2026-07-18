from __future__ import annotations

from typing import Any

from integrations.models import IntegrationRequest, IntegrationResult


IDENTITY_PRINCIPLES: tuple[str, ...] = (
    "lumos_id_is_singular_and_provider_independent",
    "no_provider_owns_the_identity",
    "mandatory_source_tag_per_memory_record",
    "per_provider_data_segregation",
    "no_automatic_cross_provider_sharing",
    "cross_use_requires_explicit_approval",
    "identity_and_memory_survive_provider_changes",
    "new_provider_is_adapter_only",
)

# Kaynak etiketleri mevcut kayıtlı sağlayıcı kimlikleriyle (`global_catalog_provider`,
# `communications_provider`) hizalıdır — burada yeni bir sağlayıcı icat edilmez.
KNOWN_MEMORY_SOURCES: tuple[dict[str, Any], ...] = (
    {"source_provider": "openai", "category": "ai"},
    {"source_provider": "anthropic", "category": "ai"},
    {"source_provider": "google_gemini", "category": "ai"},
    {"source_provider": "github", "category": "work_tool"},
    {"source_provider": "gmail", "category": "mail"},
    {"source_provider": "youtube", "category": "social"},
    {"source_provider": "slack", "category": "work_tool"},
)

TRUST_STAGES = (
    "request_validation",
    "trust_snapshot",
    "policy_decision",
    "confirmation_gate",
    "provider_route",
    "execute_or_deny",
    "redacted_audit",
)


def _public_source(source: dict[str, Any]) -> dict[str, Any]:
    return {**source, "connected": False, "storage_claim": "no_real_records_in_oss"}


def run_lumos_id_action(request: IntegrationRequest) -> IntegrationResult:
    action = request.action.strip().lower()

    if action == "describe_contract":
        return IntegrationResult(
            True,
            request.provider,
            request.action,
            {
                "name": "Lumos ID",
                "contract_version": "lumos.id_memory_gateway.v1",
                "status": "public_foundation",
                "identity_owned_by_provider": False,
                "principles": list(IDENTITY_PRINCIPLES),
                "trust_stages": list(TRUST_STAGES),
                "cross_use_requires_approval": True,
                "real_identity_storage": False,
                "real_memory_storage": False,
            },
        )

    if action == "list_memory_sources":
        return IntegrationResult(
            True,
            request.provider,
            request.action,
            {
                "count": len(KNOWN_MEMORY_SOURCES),
                "sources": [_public_source(source) for source in KNOWN_MEMORY_SOURCES],
                "catalog_scope": "representative_extensible",
                "segregation": "per_provider",
                "auto_shared_across_sources": False,
            },
        )

    if action == "plan_cross_use":
        from_source = str(request.payload.get("from_source", "")).strip().lower()
        to_source = str(request.payload.get("to_source", "")).strip().lower()

        if not from_source or not to_source:
            return IntegrationResult(
                False,
                request.provider,
                request.action,
                {"from_source": from_source, "to_source": to_source},
                "cross_use_sources_required",
            )

        if not request.requires_approval:
            return IntegrationResult(
                False,
                request.provider,
                request.action,
                {
                    "from_source": from_source,
                    "to_source": to_source,
                    "requires_approval": True,
                    "data_moved": False,
                },
                "approval_required",
            )

        return IntegrationResult(
            True,
            request.provider,
            request.action,
            {
                "from_source": from_source,
                "to_source": to_source,
                "cross_use_status": "plan_only",
                "execution_permitted": False,
                "data_moved": False,
                "trust_stages": list(TRUST_STAGES),
            },
        )

    return IntegrationResult(False, request.provider, request.action, {}, "unsupported_lumos_id_action")


def register_lumos_id_provider(register) -> None:
    register("lumos_id", "describe_contract", run_lumos_id_action)
    register("lumos_id", "list_memory_sources", run_lumos_id_action)
    register("lumos_id", "plan_cross_use", run_lumos_id_action)
