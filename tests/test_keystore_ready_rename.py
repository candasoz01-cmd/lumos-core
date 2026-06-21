"""ADR-011 Phase 1: keystore_ready rename and two-signal CLI output regression."""
import tempfile
from pathlib import Path


def _mock_presence():
    class Cfg:
        enabled = False

    class Mod:
        def load_presence_cfg(self, base_dir: Path):
            return Cfg()

    return Mod()


def test_keystore_ready_helper():
    from core.startup_health import keystore_ready

    assert keystore_ready(True) is True
    assert keystore_ready(False) is False


def test_get_durum_parts_returns_keystore_ready_key():
    from core.startup_health import get_durum_parts

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        pl = _mock_presence()
        parts = get_durum_parts(base, keystore_initialized=False, presence_module=pl)
        assert "keystore_ready" in parts
        assert "lock_ok" not in parts
        assert parts["keystore_ready"] is False


def test_format_durum_keystore_and_session_lines():
    from core.state import format_durum

    snap_unlocked = {"lock_status": "UNLOCKED", "presence_enabled": False, "mode": "offline"}
    out = format_durum(snap_unlocked, consent_ok=True, keystore_ready=True, durum_label="güvenli", not_line="kritik eksik yok")
    assert "Keystore: hazır" in out
    assert "Oturum: açık" in out
    assert "Lock:" not in out

    snap_locked = {"lock_status": "LOCKED", "presence_enabled": False, "mode": "offline"}
    out2 = format_durum(snap_locked, consent_ok=False, keystore_ready=False, durum_label="kısmen hazır", not_line="consent alınmadı")
    assert "Keystore: eksik" in out2
    assert "Oturum: kilitli" in out2


def test_get_startup_summary_session_unlocked_kwarg():
    from core.startup_health import get_startup_summary

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        pl = _mock_presence()
        (base / "consent.json").write_text("{}")
        # Keystore not init but session unlocked — hazir path uses session_unlocked
        summary = get_startup_summary(
            base,
            keystore_initialized=False,
            presence_module=pl,
            session_unlocked=True,
        )
        assert "Oturum açık" in summary
        assert "Keystore hazır değil" not in summary

        summary_locked = get_startup_summary(
            base,
            keystore_initialized=True,
            presence_module=pl,
            session_unlocked=False,
        )
        assert "Oturum kilitli" in summary_locked

        # Default path (no session_unlocked) uses keystore signal
        summary_ks = get_startup_summary(base, keystore_initialized=False, presence_module=pl)
        assert "Keystore hazır değil" in summary_ks


def test_get_oneri_keystore_not_ready_points_to_durum_not_kilit():
    """ADR-011 Faz 2: keystore_ready eksikken öneri kilit değil durum komutuna yönlendirir."""
    from cli.cli_parse import _get_oneri

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        (base / "consent.json").write_text("{}")
        pl = _mock_presence()
        oneriler = _get_oneri(base, keystore_initialized=False, presence_module=pl)
        assert oneriler
        first = oneriler[0]
        assert "kilit" not in first.lower()
        assert first.endswith(": durum")
