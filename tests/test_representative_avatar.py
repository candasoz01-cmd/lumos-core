"""Google Meet avatar assets/state tests; no network or meeting is created."""

from __future__ import annotations

import base64

from representative.avatar import AvatarStateController, load_meet_avatar_assets


def test_avatar_assets_are_valid_recall_sized_jpegs():
    assets = load_meet_avatar_assets()
    for encoded in (assets.idle_jpeg_b64, assets.speaking_jpeg_b64):
        data = base64.b64decode(encoded)
        assert data.startswith(b"\xff\xd8")
        assert data.endswith(b"\xff\xd9")
        assert len(data) <= 1_300_000


def test_avatar_visual_failure_does_not_escape_to_audio_path():
    assets = load_meet_avatar_assets()
    errors = []
    controller = AvatarStateController(
        publish=lambda _jpeg: (_ for _ in ()).throw(RuntimeError("offline")),
        assets=assets,
        on_error=errors.append,
        background=False,
    )

    controller.idle()

    assert len(errors) == 1
    assert isinstance(errors[0], RuntimeError)


def test_avatar_returns_to_idle_after_speaking(monkeypatch):
    assets = load_meet_avatar_assets()
    published = []
    callbacks = []

    class FakeTimer:
        daemon = False

        def __init__(self, _seconds, callback):
            callbacks.append(callback)

        def start(self):
            return None

    monkeypatch.setattr("representative.avatar.threading.Timer", FakeTimer)
    controller = AvatarStateController(published.append, assets, background=False)

    controller.speaking_for(1.0)
    callbacks[0]()

    assert published == [assets.speaking_jpeg_b64, assets.idle_jpeg_b64]
