import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from integrations.models import IntegrationRequest
from integrations.registry import register_default_integrations


def _run(action: str, *, requires_approval: bool = False):
    return register_default_integrations().run(
        IntegrationRequest(
            provider="douyin",
            action=action,
            payload={},
            requires_approval=requires_approval,
        ),
    )


def test_douyin_oauth_contract_uses_env_and_reports_identity_required(monkeypatch):
    for name in (
        "LUMOS_DOUYIN_OAUTH_CLIENT_ID",
        "LUMOS_DOUYIN_OAUTH_CLIENT_SECRET",
        "LUMOS_DOUYIN_OAUTH_REDIRECT_URI",
    ):
        monkeypatch.delenv(name, raising=False)

    result = _run("authorization_contract")

    assert result.ok is True
    assert result.data["identity_status"] == "identity_required"
    assert result.data["oauth_configuration"] == "missing"
    assert result.data["secret_source"] == "environment_only"
    assert result.data["execution_live"] is False
    assert result.data["workflow"] == ["connect", "draft", "explicit_approval", "publish"]


def test_douyin_publish_requires_explicit_approval_and_never_fakes_execution():
    denied = _run("publish")
    approved = _run("publish", requires_approval=True)

    assert denied.ok is False
    assert denied.error == "approval_required"
    assert denied.data["execution_started"] is False
    assert approved.ok is False
    assert approved.error == "douyin_publish_connector_not_live"
    assert approved.data["execution_started"] is False
