import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from integrations.models import IntegrationRequest
from integrations.registry import register_default_integrations


def _run(action: str, payload: dict | None = None, *, requires_approval: bool = False):
    return register_default_integrations().run(
        IntegrationRequest(
            provider="lumos_id",
            action=action,
            payload=payload or {},
            requires_approval=requires_approval,
        ),
    )


def test_lumos_id_contract_states_identity_is_provider_independent():
    result = _run("describe_contract")

    assert result.ok is True
    assert result.data["name"] == "Lumos ID"
    assert result.data["identity_owned_by_provider"] is False
    assert result.data["real_identity_storage"] is False
    assert result.data["real_memory_storage"] is False
    assert result.data["cross_use_requires_approval"] is True
    assert "no_provider_owns_the_identity" in result.data["principles"]
    assert "no_automatic_cross_provider_sharing" in result.data["principles"]
    assert "identity_and_memory_survive_provider_changes" in result.data["principles"]


def test_memory_sources_are_segregated_and_not_auto_shared():
    result = _run("list_memory_sources")

    ids = {source["source_provider"] for source in result.data["sources"]}
    assert {"openai", "anthropic", "google_gemini", "github", "gmail"} <= ids
    assert result.data["segregation"] == "per_provider"
    assert result.data["auto_shared_across_sources"] is False
    assert all(source["connected"] is False for source in result.data["sources"])


def test_cross_use_requires_explicit_approval():
    result = _run("plan_cross_use", {"from_source": "openai", "to_source": "gmail"})

    assert result.ok is False
    assert result.error == "approval_required"
    assert result.data["data_moved"] is False


def test_cross_use_plan_never_moves_real_data_even_when_approved():
    result = _run(
        "plan_cross_use",
        {"from_source": "openai", "to_source": "gmail"},
        requires_approval=True,
    )

    assert result.ok is True
    assert result.data["cross_use_status"] == "plan_only"
    assert result.data["execution_permitted"] is False
    assert result.data["data_moved"] is False


def test_cross_use_requires_both_sources():
    result = _run("plan_cross_use", {"from_source": "openai"}, requires_approval=True)

    assert result.ok is False
    assert result.error == "cross_use_sources_required"
