from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "ui/src/data/integration-guide.ts"
PAGE = ROOT / "ui/src/pages/integrations/guide.astro"
DOC = ROOT / "docs/integration-benefits-security-guide.md"
TR = ROOT / "ui/src/i18n/messages/umbrella/tr.ts"
EN = ROOT / "ui/src/i18n/messages/umbrella/en.ts"


def test_guide_has_at_least_twenty_cross_category_connections():
    text = DATA.read_text(encoding="utf-8")
    ids = re.findall(r'\{ id: "([^"]+)"', text)
    categories = set(re.findall(r'category: "([^"]+)"', text))

    assert len(ids) >= 20
    assert len(ids) == len(set(ids))
    assert {"development", "productivity", "communication", "regional", "browser", "ai", "device"} <= categories


def test_site_and_github_guide_explain_benefit_security_and_honest_status():
    page = PAGE.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")

    assert "INTEGRATION_GUIDE_ITEMS" in page
    assert "benefitLabel" in page
    assert "securityLabel" in page
    assert "Katalog kaydı, canlı bağlantı değildir" in page
    assert "## Ortak güvenlik modeli" in doc
    assert "## 24 popüler uygulama ve cihaz bağlantısı" in doc
    assert "Entegrasyon onboarding onayı ödeme yetkisine dönüşmez" in doc


def test_every_guide_item_has_tr_and_en_copy():
    data = DATA.read_text(encoding="utf-8")
    tr = TR.read_text(encoding="utf-8")
    en = EN.read_text(encoding="utf-8")
    ids = re.findall(r'\{ id: "([^"]+)"', data)

    for item_id in ids:
        pattern = rf"\b{re.escape(item_id)}:\s*\{{\s*benefit:"
        assert re.search(pattern, tr), f"missing TR copy: {item_id}"
        assert re.search(pattern, en), f"missing EN copy: {item_id}"
