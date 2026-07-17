from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from integrations.models import IntegrationRequest
from integrations.quantum_cloud_connect import (
    QuantumCloudConfigurationError,
    configuration_error_data,
    connect_quantum_cloud,
)
from integrations.registry import register_default_integrations


@pytest.mark.parametrize(
    ("provider_id", "missing"),
    [
        ("ibm_quantum", "IBM_QUANTUM_API_KEY"),
        ("azure_quantum", "AZURE_QUANTUM_RESOURCE_ID"),
        ("amazon_braket", "AWS_REGION|AWS_DEFAULT_REGION"),
        ("google_quantum_ai", "GOOGLE_QUANTUM_PROJECT_ID"),
    ],
)
def test_cloud_provider_requires_configuration(provider_id: str, missing: str):
    with pytest.raises(QuantumCloudConfigurationError) as caught:
        connect_quantum_cloud(provider_id, environ={})
    data = configuration_error_data(caught.value)
    assert data["missing_config"] == [missing]
    assert data["job_submission"] is False


def test_ibm_adapter_lists_backends_without_exposing_token(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, str] = {}

    class Service:
        def __init__(self, **kwargs: str):
            captured.update(kwargs)

        def backends(self):
            return [SimpleNamespace(name="ibm_test_backend")]

    fake_module = SimpleNamespace(QiskitRuntimeService=Service)
    monkeypatch.setitem(__import__("sys").modules, "qiskit_ibm_runtime", fake_module)
    result = connect_quantum_cloud(
        "ibm_quantum",
        environ={"IBM_QUANTUM_API_KEY": "secret-token"},
    )

    assert captured["token"] == "secret-token"
    assert result["resources"] == [{"name": "ibm_test_backend"}]
    assert result["job_submission"] is False
    assert "secret-token" not in repr(result)


def test_azure_adapter_lists_targets(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, str] = {}

    class Workspace:
        def __init__(self, *, resource_id: str):
            captured["resource_id"] = resource_id

        def get_targets(self):
            return [SimpleNamespace(name="ionq.simulator", provider_id="ionq")]

    fake_module = SimpleNamespace(Workspace=Workspace)
    monkeypatch.setitem(__import__("sys").modules, "qdk.azure", fake_module)
    result = connect_quantum_cloud(
        "azure_quantum",
        environ={"AZURE_QUANTUM_RESOURCE_ID": "/subscriptions/test/workspaces/lumos"},
    )

    assert captured["resource_id"] == "/subscriptions/test/workspaces/lumos"
    assert result["resources"] == [{"name": "ionq.simulator", "provider": "ionq"}]
    assert result["job_submission"] is False


def test_aws_adapter_lists_devices(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    class Client:
        def search_devices(self, **kwargs: object):
            captured.update(kwargs)
            return {
                "devices": [
                    {
                        "deviceName": "SV1",
                        "providerName": "Amazon Braket",
                        "deviceType": "SIMULATOR",
                        "deviceStatus": "ONLINE",
                    },
                ],
            }

    def client(service: str, *, region_name: str):
        captured["service"] = service
        captured["region_name"] = region_name
        return Client()

    monkeypatch.setitem(__import__("sys").modules, "boto3", SimpleNamespace(client=client))
    result = connect_quantum_cloud(
        "amazon_braket",
        environ={"AWS_DEFAULT_REGION": "eu-west-2"},
    )

    assert captured == {
        "service": "braket",
        "region_name": "eu-west-2",
        "filters": [],
        "maxResults": 25,
    }
    assert result["resources"] == [
        {
            "name": "SV1",
            "provider": "Amazon Braket",
            "type": "SIMULATOR",
            "status": "ONLINE",
        },
    ]


def test_google_adapter_lists_processors(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, str] = {}

    class Engine:
        def __init__(self, *, project_id: str):
            captured["project_id"] = project_id

        def list_processors(self):
            return [SimpleNamespace(processor_id="willow")]

    fake_module = SimpleNamespace(Engine=Engine)
    monkeypatch.setitem(__import__("sys").modules, "cirq_google", fake_module)
    result = connect_quantum_cloud(
        "google_quantum_ai",
        environ={"GOOGLE_QUANTUM_PROJECT_ID": "lumos-test"},
    )

    assert captured["project_id"] == "lumos-test"
    assert result["resources"] == [{"name": "willow"}]
    assert result["job_submission"] is False


def test_cloud_connect_keeps_approval_gate():
    result = register_default_integrations().run(
        IntegrationRequest(
            provider="quantum",
            action="connect",
            payload={"provider_id": "ibm_quantum"},
        ),
    )
    assert result.ok is False
    assert result.error == "approval_required"


def test_cloud_connect_success_is_read_only():
    connection = {
        "provider_id": "ibm_quantum",
        "connection_status": "connected",
        "read_only": True,
        "job_submission": False,
        "resource_count": 1,
        "resources": [{"name": "backend"}],
    }
    with patch(
        "integrations.providers.quantum_provider.connect_quantum_cloud",
        return_value=connection,
    ):
        result = register_default_integrations().run(
            IntegrationRequest(
                provider="quantum",
                action="connect",
                payload={"provider_id": "ibm_quantum", "approved": True},
            ),
        )
    assert result.ok is True
    assert result.data["connection_status"] == "connected"
    assert result.data["job_submission"] is False
    assert result.data["autonomous_connect"] is False
