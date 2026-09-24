from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "macos" / "LumosApp" / "Sources" / "Lumos"


def _read(name: str) -> str:
    return (SOURCES / name).read_text(encoding="utf-8")


def _translation_sources() -> str:
    return "\n".join(
        _read(name)
        for name in (
            "LumosShortcut.swift",
            "LumosSelectionReader.swift",
            "LumosTranslationPanel.swift",
        )
    )


def test_selection_translation_is_wired_into_app_launch() -> None:
    main = _read("main.swift")

    assert "private let selectionTranslator = LumosSelectionTranslator()" in main
    assert "selectionTranslator.start()" in main


def test_shortcut_is_a_hot_key_not_a_global_keyboard_monitor() -> None:
    source = _translation_sources()

    assert "RegisterEventHotKey(" in source
    for forbidden in (
        "addGlobalMonitorForEvents",
        "CGEvent.tapCreate",
        "tapCreate(",
        "Timer.scheduledTimer",
        "CGWindowListCreateImage",
        "ScreenCaptureKit",
    ):
        assert forbidden not in source, forbidden


def test_accessibility_permission_is_checked_not_requested_or_bypassed() -> None:
    source = _translation_sources()

    assert "AXIsProcessTrusted()" in source
    assert "AXIsProcessTrustedWithOptions" not in source
    assert "kAXTrustedCheckOptionPrompt" not in source
    assert "Privacy_Accessibility" in source


def test_secure_input_is_refused_before_any_copy_fallback() -> None:
    reader = _read("LumosSelectionReader.swift")

    assert "IsSecureEventInputEnabled()" in reader
    assert "kAXSecureTextFieldSubrole" in reader
    first_secure_check = reader.index("IsSecureEventInputEnabled()")
    copy_fallback = reader.index("await copySelectionPreservingPasteboard(")
    assert first_secure_check < copy_fallback
    assert reader.count("IsSecureEventInputEnabled()") >= 2


def test_copy_fallback_restores_previous_pasteboard() -> None:
    reader = _read("LumosSelectionReader.swift")

    assert "LumosPasteboardSnapshot(pasteboard)" in reader
    assert "snapshot.restore(to: pasteboard)" in reader
    assert "postToPid(pid)" in reader


def test_panel_shows_source_translation_copy_and_lumos_name() -> None:
    panel = _read("LumosTranslationPanel.swift")

    assert 'panel.title = "Lumos Çeviri"' in panel
    assert '"Kaynak metin"' in panel
    assert '"Türkçe çeviri"' in panel
    assert '"Kopyala"' in panel
    assert ".translationTask(" in panel
    assert "Kando" not in _translation_sources()
