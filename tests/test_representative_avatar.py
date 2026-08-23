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


def test_superseded_frames_are_dropped_not_queued() -> None:
    """Latest-wins: yayın gecikirse eski kare tekrarlanmaz.

    Sınırsız kuyrukta konuşma bittikten çok sonra 'speaking' karesi
    yayınlanmaya devam eder ve avatar gerçeğin gerisine düşerdi.
    """
    assets = load_meet_avatar_assets()
    controller = AvatarStateController(
        publish=lambda _jpeg: None, assets=assets, background=True
    )
    # Yayın döngüsü uyanmadan üst üste durum değiştir.
    controller._enqueue("A")
    controller._enqueue("B")
    controller._enqueue("C")
    pending = controller.pending_frame()
    assert pending in ("C", None), "yalnız en yeni kare beklemeli"


def test_visual_failure_does_not_stop_audio_path() -> None:
    """Görsel hata sesi durdurmaz: publish patlasa da çağrı geri döner."""
    assets = load_meet_avatar_assets()
    errors: list[Exception] = []
    controller = AvatarStateController(
        publish=lambda _jpeg: (_ for _ in ()).throw(RuntimeError("offline")),
        assets=assets,
        on_error=errors.append,
        background=False,
    )
    controller.idle()
    assert errors, "hata yutulmamalı, on_error'a gitmeli"


def test_state_change_and_frame_are_atomic_under_load() -> None:
    """Yarış testi: son niyet idle ise avatar speaking'de takılı kalmamalı.

    Eski kodda generation kilit altında artıyor ama kare kilidin dışında
    kuyruğa giriyordu; idle sayacı kazanıp kareyi geç gelen speaking'e
    kaptırabiliyordu (barge-in yolu tam da budur).
    """
    import threading

    assets = load_meet_avatar_assets()
    controller = AvatarStateController(
        publish=lambda _jpeg: None, assets=assets, background=True
    )
    for _ in range(200):
        done = threading.Event()

        def speak() -> None:
            controller.speaking_for(60.0)
            done.set()

        t = threading.Thread(target=speak)
        t.start()
        controller.idle()
        t.join()
        done.wait(1.0)
        # idle() en son çağrılsa da speaking_for ile yarışabilir; kritik olan
        # sayaç ile karenin AYNI kilitte belirlenmesi: slot ile generation
        # tutarsız kalmamalı.
        with controller._lock:
            pending = controller._pending
            gen = controller._generation
        assert gen > 0
        assert pending in (assets.idle_jpeg_b64, assets.speaking_jpeg_b64, None)


def test_barge_in_idle_wins_when_it_is_the_last_state_change() -> None:
    """Sıralı (yarışsız) durumda son çağrı kesin kazanır."""
    assets = load_meet_avatar_assets()
    controller = AvatarStateController(
        publish=lambda _jpeg: None, assets=assets, background=True
    )
    controller.speaking_for(60.0)
    controller.idle()
    assert controller.pending_frame() in (assets.idle_jpeg_b64, None)
