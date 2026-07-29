from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "ui/src/data/integration-guide.ts"
PAGE = ROOT / "ui/src/pages/integrations/guide.astro"
DOC = ROOT / "docs/integration-benefits-security-guide.md"
TR = ROOT / "ui/src/i18n/messages/umbrella/tr.ts"
EN = ROOT / "ui/src/i18n/messages/umbrella/en.ts"


def test_guide_has_global_catalog_projection_across_functional_categories():
    text = DATA.read_text(encoding="utf-8")
    ids = re.findall(r'\{\s+id: "([^"]+)"', text)
    categories = set(re.findall(r'category: "([^"]+)"', text))

    assert len(ids) >= 30
    assert len(ids) == len(set(ids))
    assert {"development", "productivity", "communication", "social", "browser", "ai", "device"} <= categories
    assert 'category: "regional"' not in text
    assert 'catalogId: "lark"' in text
    assert 'catalogId: "dingtalk"' in text
    assert 'catalogId: "yandex_browser"' in text
    assert 'catalogId: "yandex_gpt"' in text
    assert 'catalogId: "naver_works"' in text
    assert 'catalogId: "jiomeet"' in text
    assert 'status: "configurationRequired"' in text


def test_site_and_github_guide_explain_benefit_security_and_honest_status():
    page = PAGE.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")

    assert "INTEGRATION_GUIDE_ITEMS" in page
    assert "INTEGRATION_GUIDE_GROUPS" in page
    assert "data-catalog-id" in page
    assert "data-catalog-source" in page
    assert "data-support-status" in page
    assert "benefitLabel" in page
    assert "securityLabel" in page
    assert "Katalog kaydı, canlı bağlantı değildir" in page
    assert "beforeAfterTitle" in page
    assert "readyBody" in page
    assert "## Önce / sonra" in doc
    assert "Bugün gerçekten hazır olanlar" in doc
    assert "sekme turizmi azalır" in doc
    assert "## Ortak güvenlik modeli" in doc
    assert "## 24 popüler uygulama ve cihaz bağlantısı" in doc
    assert "Entegrasyon onboarding onayı ödeme yetkisine dönüşmez" in doc


def test_every_guide_item_has_tr_and_en_copy():
    data = DATA.read_text(encoding="utf-8")
    tr = TR.read_text(encoding="utf-8")
    en = EN.read_text(encoding="utf-8")
    ids = re.findall(r'\{\s+id: "([^"]+)"', data)

    for item_id in ids:
        pattern = rf"\b{re.escape(item_id)}:\s*\{{\s*benefit:"
        assert re.search(pattern, tr), f"missing TR copy: {item_id}"
        assert re.search(pattern, en), f"missing EN copy: {item_id}"
