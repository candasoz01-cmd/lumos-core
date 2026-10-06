"""Public narrative stays inside what this repository implements."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "ui" / "src" / "pages"
MESSAGES = ROOT / "ui" / "src" / "i18n" / "messages"

PUBLIC = [
    ROOT / "README.md",
    ROOT / "README.tr.md",
    ROOT / "docs" / "data-and-trust.md",
    ROOT / "docs" / "PRODUCT_SUMMARY.md",
    ROOT / "docs" / "app-store-product-safety-privacy.md",
    PAGES / "index.astro",
    PAGES / "data-and-trust.astro",
    PAGES / "trust.astro",
    PAGES / "help.astro",
    PAGES / "terms.astro",
    PAGES / "world.astro",
    PAGES / "panel.astro",
    PAGES / "mimari.astro",
    PAGES / "auth.astro",
    PAGES / "geri-bildirim.astro",
    ROOT / "ui" / "src" / "components" / "LumosPlatformHero.astro",
    ROOT / "ui" / "src" / "components" / "WeLockSiteFooter.astro",
    MESSAGES / "tr.ts",
    MESSAGES / "en.ts",
    MESSAGES / "landing" / "tr.ts",
    MESSAGES / "landing" / "en.ts",
    MESSAGES / "umbrella" / "tr.ts",
    MESSAGES / "umbrella" / "en.ts",
    MESSAGES / "panel" / "tr.ts",
    MESSAGES / "panel" / "en.ts",
]

BANNED = (
    # Chat product names and unverifiable promises.
    "ChatGPT",
    "Copilot",
    "model eğitimi için kullanılmaz",
    "not used for advertising, sale, or general-purpose model training",
    "Veriler satılmaz",
    "Data is not sold",
    # The confirmation layer is off unless LUMOS_CONFIRMATION_ENABLED is set.
    "Onaysız kalıcı işlem yapmaz",
    "Act permanently without approval",
    "Kalıcı işlemler için onay ister.",
    "Asks for approval before permanent actions",
    # The memory service stores "remember" summaries; only the chat handler writes nothing.
    "Lumos veritabanına yazmaz",
    "to a Lumos database",
    "Lumos hiçbir veriyi saklamaz",
    "Lumos veri saklamaz",
    "Lumos stores no data",
    "Lumos does not store any data",
    "No data is stored",
    # Country rules, masking and provider retention checks do not exist.
    "ülkenize göre saklanır",
    "ülke kurallarına göre saklanır",
    "stored according to your country",
    "per-country rules are applied",
    "maskelenir",
    "maskelenerek",
    "is masked before",
    "are masked before",
    "sağlayıcı veriyi saklamaz",
    "sağlayıcı kopya tutmaz",
    "provider does not retain",
    "provider keeps no copy",
    "zero data retention",
    # Logout clears the browser cookie; there is no server-side revocation.
    "oturumu sunucuda iptal eder",
    "oturum sunucuda iptal edilir",
    "logout revokes",
    "revokes the session",
    "session is revoked",
    # The confirmation layer is off by default; no status reads as an active gate.
    "Kapı aktif",
    "Gate active",
    # Meta data deletion and deauthorize callbacks do not exist.
    "Meta verileriniz silinir",
    "Meta data is deleted",
)

# Short descriptions of what goes to the model must keep the permitted memory summaries.
MODEL_INPUT_SUMMARIES = {
    ROOT / "ui" / "src" / "components" / "LumosPlatformHero.astro": "hafıza özeti",
    MESSAGES / "landing" / "tr.ts": "hafıza özeti",
    MESSAGES / "landing" / "en.ts": "memory summaries",
    PAGES / "help.astro": "hafıza özetleri",
}

DATA_TRUST_LINK_TR = "Teknik veri ve güven envanteri"

UMBRELLA_TR = MESSAGES / "umbrella" / "tr.ts"
UMBRELLA_EN = MESSAGES / "umbrella" / "en.ts"
DATA_TRUST_PAGE = PAGES / "data-and-trust.astro"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _message_block(text: str, name: str) -> str:
    start = text.index(f"  {name}: {{\n")
    end = text.index("\n  },\n", start) + len("\n  },")
    return text[start:end]


def _data_trust_messages(path: Path) -> dict[str, str]:
    text = _read(path)
    start = text.index("  dataTrust: {\n")
    end = text.index("\n  },\n", start)
    pairs = re.findall(r'(\w+):\s*"([^"]*)"', text[start:end])
    assert len(pairs) == len(dict(pairs)), "duplicate technical inventory message key"
    return dict(pairs)


def _data_trust_page_text() -> dict[str, str]:
    pairs = re.findall(
        r'data-i18n="umbrella\.dataTrust\.(\w+)">\s*(.*?)\s*</',
        _read(DATA_TRUST_PAGE),
        flags=re.DOTALL,
    )
    return {key: " ".join(value.split()) for key, value in pairs}


def test_public_narrative_does_not_name_chat_products_or_unverifiable_promises():
    for path in PUBLIC:
        text = _read(path)
        # Preserve the registered legal notice verbatim; it is not an
        # implementation claim. Only the privacy namespace is excluded; the
        # separate route contract below keeps it distinct from the inventory.
        if path in (UMBRELLA_TR, UMBRELLA_EN):
            text = text.replace(_message_block(text, "privacy"), "", 1)
        for phrase in BANNED:
            assert phrase not in text, f"{path.relative_to(ROOT)} contains {phrase!r}"


def test_inventory_states_implemented_limits_and_gaps():
    inventory = _read(ROOT / "docs" / "data-and-trust.md")
    for needle in (
        "store: false",
        ".lumos/logs",
        "LUMOS_CONFIRMATION_ENABLED",
        "Ülkeye göre",
        "maskeleme",
        "identityInstruction",
        "BRIDGE_UPSTREAM_URL",
        "gmail.readonly",
        "session_version",
        "502",
        "503",
        "hukuki gizlilik bildirimi değildir",
    ):
        assert needle in inventory, needle


def test_technical_page_states_model_inputs_memory_gmail_logout_and_fallback():
    tr = " ".join(_data_trust_messages(UMBRELLA_TR).values())
    en = " ".join(_data_trust_messages(UMBRELLA_EN).values())
    for needle in (
        "Kendi modelini çalıştırmaz",
        "LUMOS_CONFIRMATION_ENABLED",
        "maskeleme",
        "Ülkeye göre",
        "oturumdaki ad",
        "hafıza özet",
        "lookup",
        "remember",
        "BRIDGE_UPSTREAM_URL",
        "gmail.readonly",
        "session_version",
        "503",
        "502",
        "istisna fırlatırsa",
        "hukuki gizlilik bildirimi değildir",
    ):
        assert needle in tr, needle
    for needle in (
        "does not run its own model",
        "LUMOS_CONFIRMATION_ENABLED",
        "mask",
        "per-country",
        "the name from the session",
        "memory summaries",
        "lookup",
        "remember",
        "BRIDGE_UPSTREAM_URL",
        "gmail.readonly",
        "session_version",
        "503",
        "502",
        "throws",
        "not a legal privacy notice",
    ):
        assert needle in en, needle
    for text in (tr, en, _read(DATA_TRUST_PAGE)):
        assert "garanti" not in text.lower()
        assert "guarantee" not in text.lower()


def test_short_model_input_copy_keeps_memory_summaries():
    for path, needle in MODEL_INPUT_SUMMARIES.items():
        assert needle in _read(path), f"{path.relative_to(ROOT)} omits {needle!r}"


def test_technical_links_use_a_separate_route_and_title():
    title = _data_trust_messages(UMBRELLA_TR)["title"]
    assert title == DATA_TRUST_LINK_TR
    for path in PAGES.rglob("*.astro"):
        for href, label in re.findall(
            r'href="(/privacy|/data-and-trust)"[^>]*>([^<]*)<', _read(path)
        ):
            if label == DATA_TRUST_LINK_TR:
                assert href == "/data-and-trust", path
            if href == "/data-and-trust":
                assert label == DATA_TRUST_LINK_TR, path
    footer = _read(ROOT / "ui/src/components/WeLockSiteFooter.astro")
    assert 'href="/privacy" data-i18n="umbrella.nav.privacy">Gizlilik</a>' in footer
    assert 'href="/data-and-trust" data-i18n="umbrella.nav.dataTrust">' in footer
    for path, privacy_label, inventory_label in (
        (UMBRELLA_TR, "Gizlilik", DATA_TRUST_LINK_TR),
        (UMBRELLA_EN, "Privacy", "Technical data and trust inventory"),
    ):
        nav = _message_block(_read(path), "nav")
        assert f'privacy: "{privacy_label}"' in nav
        assert f'dataTrust: "{inventory_label}"' in nav
    technical = _read(DATA_TRUST_PAGE)
    assert 'href="https://welockai.com/data-and-trust"' in technical
    assert "umbrella.privacy." not in technical


def test_meta_connection_path_is_documented():
    inventory = _read(ROOT / "docs" / "data-and-trust.md")
    tr = " ".join(_data_trust_messages(UMBRELLA_TR).values())
    en = " ".join(_data_trust_messages(UMBRELLA_EN).values())
    scopes = (
        "public_profile",
        "instagram_business_basic",
        "pages_show_list",
        "whatsapp_business_management",
    )
    for text in (inventory, tr, en):
        for needle in (
            *scopes,
            "LUMOS_CREDENTIAL_VAULT_WRITE_URL",
            "LUMOS_META_WEBHOOK_SINK_URL",
        ):
            assert needle in text, needle
        assert "revoked_local" in text
    assert "veri silme geri çağrısı" in tr
    assert "data deletion callback" in en
    assert "veri silme geri çağrısı" in inventory


def test_technical_page_and_messages_stay_in_sync():
    tr = _data_trust_messages(UMBRELLA_TR)
    en = _data_trust_messages(UMBRELLA_EN)
    assert tr.keys() == en.keys()
    page = _data_trust_page_text()
    assert page
    for key, value in page.items():
        assert key in tr, key
        if key.endswith("Cta"):
            continue
        assert value == tr[key], key


def test_registered_privacy_route_remains_a_legal_notice():
    legal = _read(PAGES / "privacy.astro")
    assert 'href="https://welockai.com/privacy"' in legal
    assert 'umbrella.privacy.title">Gizlilik bildirimi<' in legal
    assert "umbrella.dataTrust." not in legal
    assert "hukuki gizlilik bildirimi değildir" not in legal
    assert "TEKNİK VERİ ENVANTERİ" not in legal
    for path, title in (
        (UMBRELLA_TR, "Gizlilik bildirimi"),
        (UMBRELLA_EN, "Privacy notice"),
    ):
        body = _message_block(_read(path), "privacy")
        assert f'title: "{title}"' in body
        assert "not a legal privacy notice" not in body
        assert "hukuki gizlilik bildirimi değildir" not in body
        assert "cleanup_audit_logs" not in body
        for key in (
            "googleBody",
            "sharingBody",
            "retentionBody",
            "controlsTitle",
            "googleControlsCta",
        ):
            assert f"{key}:" in body


def test_local_cleanup_capabilities_are_not_claimed_as_applied_controls():
    for path, retention_gap, explicit_call, unavailable, forbidden in (
        (
            UMBRELLA_TR,
            "Varsayılan 14 günlük saklama süresi bugün otomatik uygulanmaz.",
            "açıkça çağrılması gerekir",
            "panel/API üzerinden sunulan silme işlemleri değildir",
            ("yerel günlük temizliği", "yerel not silme"),
        ),
        (
            UMBRELLA_EN,
            "The default 14-day retention is not automatically enforced today.",
            "require an explicit call",
            "not automatically applied controls or deletion actions exposed in the panel or API",
            ("local log cleanup", "local note deletion"),
        ),
    ):
        messages = _data_trust_messages(path)
        assert retention_gap in messages["qHowLongBody"]
        assert explicit_call in messages["qDeleteBody"]
        assert unavailable in messages["qDeleteBody"]
        for name in ("Memory.delete_all", "delete_audit_logs"):
            assert name in messages["qDeleteBody"]
        for phrase in forbidden:
            assert phrase not in messages["assuranceBody"]

    inventory = _read(ROOT / "docs" / "data-and-trust.md")
    applied = inventory.split("## Uygulanan\n", 1)[1].split("\n## ", 1)[0]
    capabilities = inventory.split(
        "## Mevcut yetenekler — otomatik uygulanan kontrol değil\n", 1
    )[1].split("\n## ", 1)[0]
    for name in ("cleanup_audit_logs", "delete_audit_logs", "Memory.delete_all"):
        assert name not in applied
        assert name in capabilities
    assert (
        "Varsayılan 14 günlük saklama süresi bugün otomatik uygulanmaz." in capabilities
    )


def test_candidate_inventory_keeps_implemented_security_controls_and_release_scope():
    inventory = _read(ROOT / "docs/data-and-trust.md")
    assert "PR #903 aday kod envanteri" in inventory
    assert "üretim doğrulaması değildir" in inventory
    assert "session_version" in inventory
    assert "prepareProviderPayload" in inventory
    for path in (UMBRELLA_TR, UMBRELLA_EN):
        messages = _data_trust_messages(path)
        assert "session_version" in " ".join(messages.values())
