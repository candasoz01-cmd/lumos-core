"""Public narrative stays inside what this repository implements."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PUBLIC = [
    ROOT / "README.md",
    ROOT / "README.tr.md",
    ROOT / "docs" / "data-and-trust.md",
    ROOT / "docs" / "PRODUCT_SUMMARY.md",
    ROOT / "ui" / "src" / "pages" / "index.astro",
    ROOT / "ui" / "src" / "pages" / "privacy.astro",
    ROOT / "ui" / "src" / "i18n" / "messages" / "tr.ts",
    ROOT / "ui" / "src" / "i18n" / "messages" / "en.ts",
    ROOT / "ui" / "src" / "i18n" / "messages" / "landing" / "tr.ts",
    ROOT / "ui" / "src" / "i18n" / "messages" / "landing" / "en.ts",
]

BANNED = (
    "ChatGPT",
    "Copilot",
    "model eğitimi için kullanılmaz",
    "not used for advertising, sale, or general-purpose model training",
    "Veriler satılmaz",
    "Data is not sold",
)


def test_public_narrative_does_not_name_chat_products_or_unverifiable_promises():
    for path in PUBLIC:
        text = path.read_text(encoding="utf-8")
        for phrase in BANNED:
            assert phrase not in text, f"{path.relative_to(ROOT)} contains {phrase!r}"


def test_inventory_states_implemented_limits_and_gaps():
    inventory = (ROOT / "docs" / "data-and-trust.md").read_text(encoding="utf-8")
    privacy = (ROOT / "ui" / "src" / "pages" / "privacy.astro").read_text(encoding="utf-8")
    for needle in (
        "store: false",
        ".lumos/logs",
        "LUMOS_CONFIRMATION_ENABLED",
        "Ülkeye göre",
        "maskeleme",
    ):
        assert needle in inventory
    for needle in (
            "Kendi modelini çalıştırmaz",
        "LUMOS_CONFIRMATION_ENABLED",
        "maskeleme",
        "Ülkeye göre",
    ):
        assert needle in privacy
    assert "uygulanmıyor" in privacy or "uygulamaz" in privacy
    assert "garanti" not in privacy.lower()
