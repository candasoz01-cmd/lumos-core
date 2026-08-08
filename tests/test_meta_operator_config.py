import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = ROOT / ".env.example"
ADR = ROOT / "docs/decisions/ADR-020-meta-communications-exception.md"
META_MODULES = (
    ROOT / "api/_lib/meta_oauth.js",
    ROOT / "api/_lib/meta_vault.js",
    ROOT / "api/_lib/meta_webhook.js",
)


def _example_values() -> dict[str, str]:
    values = {}
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def test_meta_server_environment_contract_covers_runtime_usage():
    source = "\n".join(path.read_text(encoding="utf-8") for path in META_MODULES)
    runtime_keys = set(re.findall(r"process\.env\.(LUMOS_[A-Z0-9_]+)", source))
    values = _example_values()
    assert runtime_keys <= values.keys()
    assert values["LUMOS_META_OAUTH_REDIRECT_URI"] == "https://welockai.com/auth/meta/callback"


def test_meta_example_never_contains_secret_or_public_client_values():
    values = _example_values()
    meta_values = {key: value for key, value in values.items() if "META" in key or "VAULT" in key}
    assert not any(key.startswith("PUBLIC_") for key in meta_values)
    for key, value in meta_values.items():
        if key == "LUMOS_META_OAUTH_REDIRECT_URI":
            continue
        assert value == "", f"{key} must stay empty in the public example"


def test_meta_decision_records_code_complete_but_not_live_boundary():
    text = ADR.read_text(encoding="utf-8")
    assert "Kod/test/main teslimi tamamlandı; canlı aktivasyon dış bağımlılık bekliyor" in text
    assert "- [ ]" not in text
    assert "sağlayıcı bağlantısı **canlı** sayılmaz" in text
