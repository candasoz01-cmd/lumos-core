from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATIONS_PAGE = ROOT / "ui/src/pages/integrations.astro"
PANEL_PAGE = ROOT / "ui/src/pages/panel.astro"


def test_catalog_surface_has_four_approved_regional_packages():
    text = INTEGRATIONS_PAGE.read_text(encoding="utf-8")

    for region in ("global", "china", "india", "russia"):
        assert f'id: "{region}"' in text
    for platform in (
        "YouTube",
        "Bilibili",
        "Rutube",
        "ShareChat",
        "Douyin",
        "VK",
    ):
        assert platform in text
    assert 'id="social-media-packages"' in text
    assert "Kimlik bekliyor" in text


def test_panel_has_real_slots_without_claiming_live_publish():
    text = PANEL_PAGE.read_text(encoding="utf-8")

    for provider_id in ("youtube", "bilibili", "rutube", "sharechat"):
        assert f'value="{provider_id}"' in text
    assert text.count('value="youtube"') == 2
    assert text.count('value="instagram"') == 2
    assert "Paylaş (demo kapalı)" in text
    assert "Bağlantı bekliyor" not in text
