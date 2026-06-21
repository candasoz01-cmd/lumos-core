"""ADR-011 Faz 3: panel bridge keystore display honesty (keystore_ready vs consent)."""
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.panel_bridge_state import build_panel_read_state  # noqa: E402


def test_keystore_ready_follows_file_not_consent(tmp_path, monkeypatch):
    """keystore_ready = dosya init; consent ayrı alan."""
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    (tmp_path / "consent.json").write_text("{}", encoding="utf-8")
    state = build_panel_read_state(repo_root=_REPO_ROOT)
    ks = state["keystore"]
    assert ks["consent_ok"] is True
    assert ks["consent_state"] == "kayıtlı"
    assert ks["keystore_ready"] is False
    assert ks["keystore_state"] == "eksik"


def test_keystore_ready_true_when_keystore_file_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    (tmp_path / "keystore.json").write_text(
        json.dumps({"v": 1, "root_key": {"v": 1}}), encoding="utf-8"
    )
    state = build_panel_read_state(repo_root=_REPO_ROOT)
    ks = state["keystore"]
    assert ks["keystore_ready"] is True
    assert ks["keystore_state"] == "hazır"
    assert ks["consent_ok"] is False
    assert ks["consent_state"] == "bekleniyor"


def test_guidance_separates_consent_and_general_approval(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("LUMOS_GENERAL_APPROVAL", "true")
    state = build_panel_read_state(repo_root=_REPO_ROOT)
    g = state["guidance"]
    assert g["consent_ok"] is False
    assert g["general_approval_active"] is True
    assert g["session_unlocked"] is None
    assert "doğrulamaz" in g["session_unlocked_note"]


def test_no_misleading_hazir_kilitli_labels(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    (tmp_path / "consent.json").write_text("{}", encoding="utf-8")
    state = build_panel_read_state(repo_root=_REPO_ROOT)
    ks = state["keystore"]
    assert ks["keystore_state"] not in ("Hazır", "Kilitli", "Hazir", "Açık")
