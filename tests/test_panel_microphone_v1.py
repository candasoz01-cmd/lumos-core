from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PANEL_RUNTIME = ROOT / "ui" / "src" / "components" / "panel" / "PanelRuntime.astro"
PANEL_TR = ROOT / "ui" / "src" / "i18n" / "messages" / "panel" / "tr.ts"
PANEL_EN = ROOT / "ui" / "src" / "i18n" / "messages" / "panel" / "en.ts"


def read_runtime() -> str:
    return PANEL_RUNTIME.read_text(encoding="utf-8")


def voice_capture_block() -> str:
    text = read_runtime()
    start = text.index('const voiceBtn = document.getElementById("panel-voice-input");')
    end = text.index("function syncCameraPhotoStatusVisibilityForViewport()", start)
    return text[start:end]


def test_panel_microphone_uses_bounded_server_transcription_flow() -> None:
    block = voice_capture_block()

    assert "navigator.mediaDevices.getUserMedia({ audio: true })" in block
    assert "new MediaRecorder(" in block
    assert "const VOICE_CAPTURE_MAX_MS = 60_000;" in block
    assert "window.setTimeout(stopVoiceCapture, VOICE_CAPTURE_MAX_MS)" in block
    assert "requestLocalTranscription(" in block
    assert '"panel_voice_input"' in block
    assert 'const TRANSCRIBE_BRIDGE_URL = "/api/bridge/transcribe";' in read_runtime()


def test_panel_microphone_inserts_transcript_without_sending() -> None:
    block = voice_capture_block()

    assert "fillPanelChatInputWithTranscript(result.text)" in block
    assert 'setVoiceHintKey("panel.modules.chat.compose.voiceHints.added")' in block
    assert "sendBtn.click(" not in block
    assert 'document.getElementById("panel-send")' not in block
    assert 'dispatchEvent(new KeyboardEvent("keydown"' not in block


def test_panel_microphone_does_not_open_realtime_or_expose_api_credentials() -> None:
    block = voice_capture_block()

    forbidden = (
        "SpeechRecognition",
        "webkitSpeechRecognition",
        "RTCPeerConnection",
        "/v1/realtime",
        "OPENAI_API_KEY",
        "Authorization",
        "apiKey",
    )
    for token in forbidden:
        assert token not in block

    tr = PANEL_TR.read_text(encoding="utf-8")
    en = PANEL_EN.read_text(encoding="utf-8")
    assert "tarayıcı ses tanıma servisi" not in tr
    assert "browser speech recognition" not in en


def test_panel_microphone_handles_permission_empty_audio_and_bridge_failures() -> None:
    block = voice_capture_block()

    expected = (
        'name === "NotAllowedError"',
        "voiceHints.micDenied",
        "voiceHints.micUnavailable",
        "blob.size < 512",
        "voiceHints.noSpeech",
        'result.error === "network_error"',
        "result.engineUnavailable",
        "result.blocked",
        "voiceHints.startFailed",
        "voiceHints.failed",
    )
    for token in expected:
        assert token in block


def test_panel_microphone_locales_describe_review_before_send() -> None:
    tr = PANEL_TR.read_text(encoding="utf-8")
    en = PANEL_EN.read_text(encoding="utf-8")

    for key in ("recording:", "transcribing:", "added:"):
        assert key in tr
        assert key in en
    assert "göndermek için siz onaylayın" in tr
    assert "review it before sending" in en
