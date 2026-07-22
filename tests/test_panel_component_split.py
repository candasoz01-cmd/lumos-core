"""Panel source helpers and TD-02 component-boundary regression tests."""

from __future__ import annotations

from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_PANEL_PAGE = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"
_PANEL_COMPONENTS = _REPO_ROOT / "ui" / "src" / "components" / "panel"


def read_panel_source() -> str:
    """Return the page and its local Panel components as one test surface."""
    sources = [_PANEL_PAGE.read_text(encoding="utf-8")]
    sources.extend(
        path.read_text(encoding="utf-8")
        for path in sorted(_PANEL_COMPONENTS.glob("*.astro"))
    )
    return "\n".join(sources)


def test_panel_runtime_is_extracted_without_inline_duplicate() -> None:
    page = _PANEL_PAGE.read_text(encoding="utf-8")
    runtime = (_PANEL_COMPONENTS / "PanelRuntime.astro").read_text(encoding="utf-8")

    assert 'import PanelRuntime from "../components/panel/PanelRuntime.astro";' in page
    assert "<PanelRuntime" in page
    assert "<script define:vars={{ CHAT_URL" not in page
    assert "<script define:vars={{ CHAT_URL" in runtime
    assert len(page.splitlines()) < 7000
    assert len(runtime.splitlines()) > 9000
