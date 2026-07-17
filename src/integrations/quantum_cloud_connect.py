"""Read-only connection checks for supported quantum cloud providers.

These adapters only list backends/targets/devices. They never submit a job.
Credentials are read from the environment and are never returned.
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

SUPPORTED_QUANTUM_CLOUD_PROVIDERS = (
    "ibm_quantum",
    "azure_quantum",
    "amazon_braket",
    "google_quantum_ai",
)

INSTALL_HINTS = {
    "ibm_quantum": "pip install 'lumos-core[quantum-ibm]'",
    "azure_quantum": "pip install 'lumos-core[quantum-azure]'",
    "amazon_braket": "pip install 'lumos-core[quantum-aws]'",
    "google_quantum_ai": "pip install 'lumos-core[quantum-google]'",
}

REQUIRED_CONFIG = {
    "ibm_quantum": ("IBM_QUANTUM_API_KEY",),
    "azure_quantum": ("AZURE_QUANTUM_RESOURCE_ID",),
    "amazon_braket": ("AWS_REGION|AWS_DEFAULT_REGION",),
    "google_quantum_ai": ("GOOGLE_QUANTUM_PROJECT_ID",),
}


class QuantumCloudConfigurationError(RuntimeError):
    def __init__(self, provider_id: str, reason: str, missing: tuple[str, ...] = ()):
        super().__init__(reason)
        self.provider_id = provider_id
        self.reason = reason
        self.missing = missing


def is_quantum_cloud_provider(provider_id: str) -> bool:
    return provider_id.strip().lower() in SUPPORTED_QUANTUM_CLOUD_PROVIDERS


def _require_config(
    provider_id: str,
    environ: Mapping[str, str],
) -> None:
    missing: list[str] = []
    for key in REQUIRED_CONFIG[provider_id]:
        alternatives = key.split("|")
        if not any(environ.get(candidate, "").strip() for candidate in alternatives):
            missing.append(key)
    if missing:
        raise QuantumCloudConfigurationError(
            provider_id,
            "credentials_or_workspace_missing",
            tuple(missing),
        )


def _safe_name(item: Any, *attributes: str) -> str:
    for attribute in attributes:
        value = getattr(item, attribute, None)
        if callable(value):
            value = value()
        if value:
            return str(value)
    return type(item).__name__


def _summary(provider_id: str, resources: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "provider_id": provider_id,
        "connection_status": "connected",
        "read_only": True,
        "job_submission": False,
        "resource_count": len(resources),
        "resources": resources[:25],
    }


def _connect_ibm(environ: Mapping[str, str]) -> dict[str, Any]:
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError as exc:
        raise QuantumCloudConfigurationError("ibm_quantum", "optional_dependency_missing") from exc

    kwargs: dict[str, str] = {
        "channel": "ibm_quantum_platform",
        "token": environ["IBM_QUANTUM_API_KEY"],
    }
    instance = environ.get("IBM_QUANTUM_INSTANCE", "").strip()
    if instance:
        kwargs["instance"] = instance
    service = QiskitRuntimeService(**kwargs)
    backends = service.backends()
    resources = [{"name": _safe_name(item, "name")} for item in backends]
    return _summary("ibm_quantum", resources)


def _connect_azure(environ: Mapping[str, str]) -> dict[str, Any]:
    try:
        from qdk.azure import Workspace
    except ImportError as exc:
        raise QuantumCloudConfigurationError(
            "azure_quantum",
            "optional_dependency_missing",
        ) from exc

    workspace = Workspace(resource_id=environ["AZURE_QUANTUM_RESOURCE_ID"])
    targets = workspace.get_targets()
    resources = [
        {
            "name": _safe_name(item, "name", "target_id"),
            "provider": _safe_name(item, "provider_id", "provider"),
        }
        for item in targets
    ]
    return _summary("azure_quantum", resources)


def _connect_aws(environ: Mapping[str, str]) -> dict[str, Any]:
    try:
        import boto3
    except ImportError as exc:
        raise QuantumCloudConfigurationError(
            "amazon_braket",
            "optional_dependency_missing",
        ) from exc

    region = environ.get("AWS_REGION") or environ["AWS_DEFAULT_REGION"]
    client = boto3.client("braket", region_name=region)
    response = client.search_devices(filters=[], maxResults=25)
    resources = [
        {
            "name": str(item.get("deviceName", "unknown")),
            "provider": str(item.get("providerName", "unknown")),
            "type": str(item.get("deviceType", "unknown")),
            "status": str(item.get("deviceStatus", "unknown")),
        }
        for item in response.get("devices", [])
    ]
    return _summary("amazon_braket", resources)


def _connect_google(environ: Mapping[str, str]) -> dict[str, Any]:
    try:
        import cirq_google
    except ImportError as exc:
        raise QuantumCloudConfigurationError(
            "google_quantum_ai",
            "optional_dependency_missing",
        ) from exc

    engine = cirq_google.Engine(project_id=environ["GOOGLE_QUANTUM_PROJECT_ID"])
    processors = engine.list_processors()
    resources = [{"name": _safe_name(item, "processor_id", "name")} for item in processors]
    return _summary("google_quantum_ai", resources)


def connect_quantum_cloud(
    provider_id: str,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    normalized = provider_id.strip().lower()
    if normalized not in SUPPORTED_QUANTUM_CLOUD_PROVIDERS:
        raise QuantumCloudConfigurationError(normalized, "unsupported_provider")

    config = os.environ if environ is None else environ
    _require_config(normalized, config)
    handlers = {
        "ibm_quantum": _connect_ibm,
        "azure_quantum": _connect_azure,
        "amazon_braket": _connect_aws,
        "google_quantum_ai": _connect_google,
    }
    return handlers[normalized](config)


def configuration_error_data(error: QuantumCloudConfigurationError) -> dict[str, Any]:
    return {
        "provider_id": error.provider_id,
        "reason": error.reason,
        "missing_config": list(error.missing),
        "install_hint": INSTALL_HINTS.get(error.provider_id, ""),
        "read_only": True,
        "job_submission": False,
        "autonomous_connect": False,
    }
