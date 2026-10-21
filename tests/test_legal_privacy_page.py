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


def test_page_wires_the_language_switcher_and_links_the_english_section():
    text = _page()
    assert 'import I18nInit from "../../components/I18nInit.astro";' in text
    assert "<I18nInit />" in text
    assert 'href="#en-title"' in text
    assert 'id="en-title"' in text


def test_draft_notice_is_not_wired_as_the_live_privacy_url():
    # While open legal items remain, nothing else in the public surface may
    # point at /legal/privacy (footer, auth, app manifests, docs).
    if TR_TODO not in _page():
        return
    offenders = []
    for base in (ROOT / "ui" / "src", ROOT / "api", ROOT / "docs"):
        for path in base.rglob("*"):
            if (
                not path.is_file()
                or path == PAGE
                or path.suffix not in {".astro", ".ts", ".js", ".md", ".json"}
            ):
                continue
            if "/legal/privacy" in path.read_text(encoding="utf-8", errors="ignore"):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
