"""Kalıcı silme yasağı + sabit trash hedefi guard sözleşmesi testleri."""
import tempfile

from core.workspace_contract import (
    LUMOS_TRASH_DIRNAME,
    trash_path,
    is_allowed_trash_path,
    may_perform_permanent_delete,
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
