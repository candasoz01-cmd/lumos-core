"""/legal/privacy is the legal notice; open legal items stay visible and unindexed."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "ui" / "src" / "pages" / "legal" / "privacy.astro"

TR_TODO = "KARAR GEREKLİ"
EN_TODO = "DECISION REQUIRED"

# Sections a legal notice needs. Each must exist in both languages.
TR_SECTIONS = (
    "Veri sorumlusu",
    "İletişim ve başvuru kanalı",
    "Hukuki dayanak",
    "Aktarılan taraflar",
    "Saklama süreleri",
    "Haklarınız ve başvuru usulü",
    "Silme",
    "Google kullanıcı verileri",
    "Meta platform verileri",
    "Değişiklikler ve yürürlük",
)
EN_SECTIONS = (
    "Data controller",
    "Contact and request channel",
    "Legal basis",
    "Recipients",
    "Retention",
    "Your rights and how to request",
    "Deletion",
    "Google user data",
    "Meta platform data",
    "Changes and effective date",
)

# Promises nobody has approved yet must not appear in the draft.
BANNED = (
    "Veriler satılmaz",
    "Data is not sold",
    "model eğitimi için kullanılmaz",
    "not used for advertising",
    "Limited Use",
    "garanti",
    "guarantee",
)


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_page_has_every_legal_section_in_both_languages():
    text = _page()
    for heading in TR_SECTIONS + EN_SECTIONS:
        assert re.search(rf"<h2[^>]*>\d+\. {re.escape(heading)}</h2>", text), heading


def test_open_items_keep_the_page_unindexed_and_marked_as_draft():
    text = _page()
    if TR_TODO in text or EN_TODO in text:
        assert '<meta name="robots" content="noindex, nofollow" />' in text
        assert "taslak, hukuk onayı yok" in text
        assert "draft, no legal approval" in text
    tr_items = text.count(f'class="legal-todo">{TR_TODO}')
    en_items = text.count(f'class="legal-todo">{EN_TODO}')
    assert tr_items == en_items


def test_page_does_not_invent_contact_details_or_unapproved_promises():
    text = _page()
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text), (
        "contact address needs a legal decision"
    )
    lowered = text.lower()
    for phrase in BANNED:
        assert phrase.lower() not in lowered, phrase


def test_page_points_to_the_technical_inventory_and_its_own_canonical_url():
    text = _page()
    assert 'const INVENTORY = "/privacy";' in text
    assert text.count("href={INVENTORY}") >= 2
    assert '<link rel="canonical" href="https://welockai.com/legal/privacy" />' in text
