"""Telefon PWA önizleme komutunun güvenli kapsam sözleşmesi."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "electronics_pilot_phone_preview.sh"


def test_phone_preview_builds_and_serves_static_panel_on_lan() -> None:
    text = _SCRIPT.read_text(encoding="utf-8")
    assert 'npm --prefix "$UI_DIR" run build' in text
    assert 'python3 -m http.server "$PORT" --bind 0.0.0.0' in text
    assert "/panel/" in text
    assert "aynı Wi-Fi" in text


def test_phone_preview_is_explicitly_temporary_not_production() -> None:
    text = _SCRIPT.read_text(encoding="utf-8")
    assert "Bu production deploy değildir" in text
    assert "Terminali kapatınca önizleme sona erer" in text
    assert "vercel deploy" not in text
    assert "git push" not in text


def test_phone_preview_validates_port_and_dependencies() -> None:
    text = _SCRIPT.read_text(encoding="utf-8")
    assert "PORT < 1024 || PORT > 65535" in text
    assert '[[ ! -x "$UI_DIR/node_modules/.bin/astro" ]]' in text
    assert "npm --prefix ui install" in text
