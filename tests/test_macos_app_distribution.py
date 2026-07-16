from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "macos" / "LumosApp"


def test_macos_bundle_uses_current_mark_and_associated_domain() -> None:
    build_script = (APP_DIR / "build-app.sh").read_text(encoding="utf-8")
    entitlements = (APP_DIR / "Lumos.entitlements").read_text(encoding="utf-8")

    assert "ui/public/lumos-logo-mark.svg" in build_script
    assert "lumos-skull-mark.svg" not in build_script
    assert "--options runtime --timestamp" in build_script
    assert "applinks:welockai.com" in entitlements


def test_macos_ci_builds_and_uploads_installable_bundle() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "./build-app.sh" in workflow
    assert "dist/Lumos-macOS.zip" in workflow
    assert "actions/upload-artifact@v4" in workflow


def test_macos_external_navigation_is_not_silently_cancelled() -> None:
    source = (APP_DIR / "Sources" / "Lumos" / "main.swift").read_text(
        encoding="utf-8"
    )

    assert "NSWorkspace.shared.open(url)\n        decisionHandler(.cancel)" in source
