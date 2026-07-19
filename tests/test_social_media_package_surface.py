from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATIONS_PAGE = ROOT / "ui/src/pages/integrations.astro"
PANEL_PAGE = ROOT / "ui/src/pages/panel.astro"


def test_ecosystem_map_covers_categories_and_platforms_without_a_flat_logo_wall():
    text = INTEGRATIONS_PAGE.read_text(encoding="utf-8")

    for category in ("ai", "identity", "communication", "developer", "media", "home", "cloud"):
        assert f'id: "{category}"' in text
    for platform in (
        "YouTube",
        "Bilibili",
        "Rutube",
        "ShareChat",
        "Douyin",
        "VK",
    ):
        assert platform in text
    assert 'id="ecosystem-map"' in text
    assert 'class="ecosystem-category"' in text
    assert "Kimlik bekliyor" in text
    # Old flat card/region grouping is gone — logos only render inside category panels.
    assert "social-media-packages" not in text
    assert "integration-social-package-card" not in text


def test_ecosystem_map_logos_are_monochrome_until_hover():
    text = INTEGRATIONS_PAGE.read_text(encoding="utf-8")

    assert "monochrome" in text


def test_panel_has_real_slots_without_claiming_live_publish():
    text = PANEL_PAGE.read_text(encoding="utf-8")

    for provider_id in ("youtube", "bilibili", "rutube", "sharechat"):
        assert f'value="{provider_id}"' in text
    assert text.count('value="youtube"') == 2
    assert text.count('value="instagram"') == 2
    assert "Paylaş (demo kapalı)" in text
    assert "Bağlantı bekliyor" not in text
