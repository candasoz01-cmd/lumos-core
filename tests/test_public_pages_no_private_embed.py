"""Fail-closed: private markdown must not land in public Astro pages."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PAGES = _REPO_ROOT / "ui" / "src" / "pages"

_EMBEDDED_PAGES = (
    "kararlar.astro",
    "pay-kontrol.astro",
    "banka-orkestrasyon.astro",
    "baglanti-aktivasyonlari.astro",
)

_FORBIDDEN_MARKERS = (
    "const BODY",
    "raw.githubusercontent.com/candasoz01-cmd/Lumos",
    "gömülü statik metin",
    "yayın anı gömülü",
    'href="/kararlar"',
    "href='/kararlar'",
    'id="body">{BODY}',
)

# Stubs must stay short; a restored private body would exceed this.
_MAX_STUB_BYTES = 900


def _astro_pages() -> list[Path]:
    return sorted(_PAGES.rglob("*.astro"))


def test_public_pages_have_no_kararlar_href() -> None:
    for path in _astro_pages():
        text = path.read_text(encoding="utf-8")
        assert 'href="/kararlar"' not in text, path.relative_to(_REPO_ROOT)
        assert "href='/kararlar'" not in text, path.relative_to(_REPO_ROOT)


def test_public_pages_have_no_private_raw_fetch() -> None:
    for path in _astro_pages():
        text = path.read_text(encoding="utf-8")
        for marker in _FORBIDDEN_MARKERS:
            if marker.startswith("href="):
                continue
            assert marker not in text, f"{marker!r} in {path.relative_to(_REPO_ROOT)}"


def test_former_embed_routes_are_short_public_stubs() -> None:
    for name in _EMBEDDED_PAGES:
        path = _PAGES / name
        text = path.read_text(encoding="utf-8")
        assert path.is_file()
        assert "const BODY" not in text
        assert "Bu sayfa kullanılamıyor." in text
        assert "noindex" in text
        assert len(text.encode("utf-8")) <= _MAX_STUB_BYTES
