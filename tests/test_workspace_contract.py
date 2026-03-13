"""Kalıcı silme yasağı + sabit trash hedefi guard sözleşmesi testleri."""
import tempfile

from core.workspace_contract import (
    CORE_STATE_PATH_NAMES,
    LUMOS_TRASH_DIRNAME,
    trash_path,
    is_allowed_trash_path,
    may_perform_permanent_delete,
    is_core_state_path,
)


def test_trash_dirname_is_fixed():
    """Sözleşme: tek çöp dizin adı; sistem yeni trash hedefi üretmez."""
    assert LUMOS_TRASH_DIRNAME == "trash"


def test_trash_path_under_base():
    """trash_path(base) her zaman base/trash döner."""
    with tempfile.TemporaryDirectory() as d:
        p = trash_path(d)
        assert p == p.parent / "trash"
        assert p.parent.name != "trash"
        assert p.name == "trash"


def test_is_allowed_trash_path_accepts_only_contract_path():
    """Sadece sözleşmedeki trash path kabul edilir; başka dizin reddedilir."""
    with tempfile.TemporaryDirectory() as d:
        base = d
        allowed = trash_path(base)
        assert is_allowed_trash_path(base, allowed) is True
        assert is_allowed_trash_path(base, str(allowed)) is True
        # Farklı path'ler reddedilir
        assert is_allowed_trash_path(base, base) is False
        assert is_allowed_trash_path(base, base + "/tasks") is False
        assert is_allowed_trash_path(base, base + "/trash/extra") is False
        assert is_allowed_trash_path(base, base + "/trash2") is False
        assert is_allowed_trash_path(base, base + "/deleted") is False


def test_may_perform_permanent_delete_only_user_initiated():
    """Kalıcı silme yalnızca kullanıcı kararı ile; otomatik yasak."""
    assert may_perform_permanent_delete(False) is False
    assert may_perform_permanent_delete(True) is True


def test_core_state_path_names_non_empty_and_contains_contract_paths():
    """Çekirdek state path listesi boş değil; tasks.json, trash, config, notes.enc.json dahil (overwrite yasağı referansı)."""
    assert len(CORE_STATE_PATH_NAMES) >= 3
    assert "tasks.json" in CORE_STATE_PATH_NAMES
    assert "trash" in CORE_STATE_PATH_NAMES
    assert "config" in CORE_STATE_PATH_NAMES
    assert "notes.enc.json" in CORE_STATE_PATH_NAMES


def test_is_core_state_path_accepts_core_paths_under_base():
    """Çekirdek state path'leri True döner; sandbox guard hazırlığı."""
    with tempfile.TemporaryDirectory() as d:
        base = d
        assert is_core_state_path(base, f"{base}/aliases.json") is True
        assert is_core_state_path(base, f"{base}/config") is True
        assert is_core_state_path(base, f"{base}/config.json") is True
        assert is_core_state_path(base, f"{base}/logs") is True
        assert is_core_state_path(base, f"{base}/trash") is True
        assert is_core_state_path(base, f"{base}/notes.enc.json") is True
        assert is_core_state_path(base, f"{base}/tasks/tasks.json") is True
        assert is_core_state_path(base, f"{base}/config/foo.json") is True
        assert is_core_state_path(base, f"{base}/logs/log.txt") is True


def test_is_core_state_path_rejects_non_core_under_base():
    """Çekirdek dışı path'ler False döner."""
    with tempfile.TemporaryDirectory() as d:
        base = d
        assert is_core_state_path(base, f"{base}/sandbox") is False
        assert is_core_state_path(base, f"{base}/sandbox/tasks.json") is False
        assert is_core_state_path(base, f"{base}/other.json") is False
        assert is_core_state_path(base, f"{base}/tasks/other.json") is False
        assert is_core_state_path(base, f"{base}/data") is False


def test_is_core_state_path_rejects_outside_base():
    """Base dışı path False döner."""
    with tempfile.TemporaryDirectory() as d:
        base = d
        with tempfile.TemporaryDirectory() as other:
            assert is_core_state_path(base, f"{other}/aliases.json") is False
