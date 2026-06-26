"""Naming registry compliance — umbrella UI and foundation docs."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_REGISTRY = _REPO_ROOT / "docs" / "analysis" / "lumos-approved-naming-registry.md"
_ORG_MODEL = _REPO_ROOT / "docs" / "analysis" / "lumos-organization-model-draft.md"
_UMBRELLA_I18N = (
    _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "umbrella" / "tr.ts",
    _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "umbrella" / "en.ts",
)
_UMBRELLA_PAGES = (
    _REPO_ROOT / "ui" / "src" / "pages" / "slack.astro",
    _REPO_ROOT / "ui" / "src" / "pages" / "cyber.astro",
    _REPO_ROOT / "ui" / "src" / "pages" / "index.astro",
)

_BANNED_UI_LITERALS = (
    "#general",
    "#proj-x",
    "Acme Corp",
    "Example Inc.",
    "Org A",
    "Org B",
    "Org C",
)


def test_registry_section_c_slack_and_cyber_resolved() -> None:
    text = _REGISTRY.read_text(encoding="utf-8")
    assert "### A.8 Slack eşlemesi" in text
    assert "### C.1 Çözüldü — APPROVED LOCKED" in text
    assert "duyuru konusu" in text
    assert "announcement topic" in text
    assert "ÖrnekKuruluş-C" in text
    assert "cyberpunk arayüz değil" in text


def test_org_model_uses_ornek_kurulus_pattern() -> None:
    text = _ORG_MODEL.read_text(encoding="utf-8")
    assert "ÖrnekKuruluş-A" in text
    assert "ÖrnekKuruluş-C" in text
    assert "duyuru konusu" in text


def test_umbrella_ui_avoids_banned_example_literals() -> None:
    for path in _UMBRELLA_I18N + _UMBRELLA_PAGES:
        text = path.read_text(encoding="utf-8")
        for banned in _BANNED_UI_LITERALS:
            assert banned not in text, f"{banned!r} found in {path.relative_to(_REPO_ROOT)}"


def test_slack_i18n_uses_konu_topic_hierarchy_terms() -> None:
    tr = _UMBRELLA_I18N[0].read_text(encoding="utf-8")
    en = _UMBRELLA_I18N[1].read_text(encoding="utf-8")
    assert "Konu" in tr
    assert "Kuruluş" in tr
    assert "Topic" in en
    assert "Organization" in en
    slack_tr_start = tr.index("  slack: {")
    slack_tr = tr[slack_tr_start : tr.index("  mac: {", slack_tr_start)]
    assert "Konu" in slack_tr
    assert "Kuruluş özel alanı" in slack_tr or "Kuruluş" in slack_tr


def test_cyber_tagline_matches_registry_locked_copy() -> None:
    tr = _UMBRELLA_I18N[0].read_text(encoding="utf-8")
    registry = _REGISTRY.read_text(encoding="utf-8")
    cyber_start = tr.index("  cyber: {")
    cyber_block = tr[cyber_start : tr.index("  integrations: {", cyber_start)]
    lead_match = re.search(r'lead:\s*(?:"([^"]+)"|\n\s*"([^"]+)")', cyber_block)
    assert lead_match is not None
    lead = lead_match.group(1) or lead_match.group(2)
    assert lead in registry
