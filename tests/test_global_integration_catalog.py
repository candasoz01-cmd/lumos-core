import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from integrations.models import IntegrationRequest
from integrations.registry import register_default_integrations


def _catalog(**payload):
    return register_default_integrations().run(
        IntegrationRequest(provider="global_catalog", action="list_catalog", payload=payload),
    )


def test_catalog_covers_all_requested_integration_groups():
    result = _catalog()

    assert result.ok is True
    categories = {item["category"] for item in result.data["providers"]}
    assert {"messaging", "meeting", "browser", "social", "ai", "work_tool", "device"} <= categories
    assert result.data["catalog_scope"] == "representative_extensible"
    assert result.data["connection_claim"] == "metadata_only"


def test_catalog_includes_zoom_and_regional_platforms():
    result = _catalog()
    ids = {item["provider_id"] for item in result.data["providers"]}

    assert {"zoom", "line", "kakao_talk", "wechat", "zalo"} <= ids
    assert {"kintone", "chatwork", "naver_works", "dingtalk"} <= ids
    assert {"yandex_browser", "uc_browser", "qq_browser"} <= ids


def test_catalog_includes_approved_regional_social_video_package():
    result = _catalog()
    ids = {item["provider_id"] for item in result.data["providers"]}

    assert {"facebook", "instagram", "x", "tiktok", "linkedin", "youtube"} <= ids
    assert {"wechat", "douyin", "bilibili", "xiaohongshu", "weibo"} <= ids
    assert {"whatsapp", "sharechat", "telegram"} <= ids
    assert {"vk", "ok_ru", "rutube"} <= ids

    youtube = next(item for item in result.data["providers"] if item["provider_id"] == "youtube")
    assert youtube["connection_kind"] == "google_oauth"
    assert youtube["support_level"] == "oauth_skeleton"
    assert youtube["connected"] is False


def test_japan_filter_keeps_global_and_japan_specific_options():
    result = _catalog(region="JP")
    ids = {item["provider_id"] for item in result.data["providers"]}

    assert {"whatsapp", "telegram", "line", "kintone", "chatwork", "sony_audio"} <= ids
    assert "kakao_talk" not in ids
    assert "zalo" not in ids


def test_device_catalog_covers_bluetooth_audio_and_home_ecosystems():
    result = _catalog(category="device")
    ids = {item["provider_id"] for item in result.data["providers"]}

    assert {"bluetooth_classic_audio", "bluetooth_le_audio", "bluetooth_hid"} <= ids
    assert {"matter", "apple_home", "google_home", "samsung_smartthings", "home_assistant"} <= ids
    assert all(item["connected"] is False for item in result.data["providers"])


def test_capability_filter_finds_audio_devices_without_claiming_connection():
    result = _catalog(category="device", capability="audio_output")

    assert result.ok is True
    assert result.data["providers"]
    assert all("audio_output" in item["capabilities"] for item in result.data["providers"])
    assert all(item["support_level"] == "discovery_only" for item in result.data["providers"])


def test_provider_details_returns_connection_metadata():
    result = register_default_integrations().run(
        IntegrationRequest(
            provider="global_catalog",
            action="provider_details",
            payload={"provider_id": "zoom"},
        ),
    )

    assert result.ok is True
    assert result.data["connection_kind"] == "oauth_webhook"
    assert result.data["connected"] is False
