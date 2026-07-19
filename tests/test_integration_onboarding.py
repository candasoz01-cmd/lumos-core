import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from integrations.models import IntegrationRequest
from integrations.registry import register_default_integrations


def _run(action: str, payload: dict, requires_approval: bool = False):
    return register_default_integrations().run(
        IntegrationRequest(
            provider="integration_onboarding",
            action=action,
            payload=payload,
            requires_approval=requires_approval,
        ),
    )


def test_login_offer_never_invents_detected_accounts_from_region():
    result = _run("build_offer", {"region": "JP", "signals": []})

    assert result.ok is True
    assert result.data["offers"] == []
    assert result.data["regional_suggestions"]
    assert all(item["detected"] is False for item in result.data["regional_suggestions"])
    assert result.data["detection_claim"] == "signal_backed_only"


def test_signal_backed_account_becomes_a_consent_offer():
    result = _run(
        "build_offer",
        {
            "region": "KR",
            "signals": [
                {"provider_id": "kakao_talk", "source": "installed_app"},
                {"provider_id": "bluetooth_le_audio", "source": "bluetooth_scan"},
            ],
        },
    )

    assert result.ok is True
    assert {item["provider_id"] for item in result.data["offers"]} == {
        "kakao_talk",
        "bluetooth_le_audio",
    }
    assert all(item["detected"] is True for item in result.data["offers"])
    assert all(item["requires_user_consent"] is True for item in result.data["offers"])
    assert all(item["payment_authorized"] is False for item in result.data["offers"])


def test_local_and_free_path_is_ranked_before_external_oauth():
    result = _run(
        "build_offer",
        {
            "signals": [
                {"provider_id": "zoom", "source": "installed_app"},
                {"provider_id": "bluetooth_classic_audio", "source": "bluetooth_scan"},
                {"provider_id": "telegram", "source": "installed_app"},
            ],
        },
    )

    assert [item["provider_id"] for item in result.data["offers"]] == [
        "bluetooth_classic_audio",
        "telegram",
        "zoom",
    ]
    assert result.data["pricing_rule"] == "live_check_then_lowest_total_cost"
    assert result.data["automatic_purchase"] is False


def test_sensitive_credentials_and_card_data_are_rejected():
    for forbidden in (
        {"token": "secret"},
        {"signals": [{"provider_id": "zoom", "source": "installed_app", "password": "secret"}]},
        {"card_number": "4111111111111111"},
    ):
        result = _run("build_offer", forbidden)
        assert result.ok is False
        assert result.error == "sensitive_input_not_allowed"


def test_accept_offer_requires_consent_and_does_not_authorize_payment():
    denied = _run("accept_offer", {"provider_id": "zoom"})
    accepted = _run("accept_offer", {"provider_id": "zoom"}, requires_approval=True)

    assert denied.ok is False
    assert denied.error == "approval_required"
    assert accepted.ok is True
    assert accepted.data["consent_status"] == "recorded"
    assert accepted.data["connection_status"] == "provider_authorization_pending"
    assert accepted.data["payment_authorized"] is False
    assert accepted.data["automatic_purchase"] is False


def test_regional_suggestions_cover_russia_korea_and_japan():
    ru = _run("build_offer", {"region": "RU", "signals": []})
    kr = _run("build_offer", {"region": "KR", "signals": []})
    jp = _run("build_offer", {"region": "JP", "signals": []})

    ru_ids = {item["provider_id"] for item in ru.data["regional_suggestions"]}
    kr_ids = {item["provider_id"] for item in kr.data["regional_suggestions"]}
    jp_ids = {item["provider_id"] for item in jp.data["regional_suggestions"]}
    assert {"vk", "yandex_browser", "yandex_gpt"} <= ru_ids
    assert {"kakao_talk", "naver_works", "samsung_smartthings"} <= kr_ids
    assert {"line", "chatwork", "kintone"} <= jp_ids
