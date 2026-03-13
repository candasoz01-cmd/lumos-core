"""Kalıcı silme yasağı + sabit trash hedefi + runtime sandbox guard testleri."""
import json
import tempfile
from pathlib import Path

import pytest

from core.workspace_contract import (
    CORE_STATE_PATH_NAMES,
    LUMOS_TRASH_DIRNAME,
    CoreWriteForbidden,
    alias_file_path,
    allow_write_to_core,
    config_file_path,
    identity_file_path,
    is_allowed_trash_path,
    is_core_state_path,
    keystore_file_path,
    logs_dir_path,
    logs_file_path,
    append_log_line,
    may_perform_permanent_delete,
    notes_file_path,
    presence_cfg_path,
    save_aliases_json,
    save_identity_json,
    save_keystore_json,
    save_notes_enc_json,
    save_presence_cfg_json,
    trash_path,
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
    """Çekirdek state path listesi boş değil; tasks.json, trash, config, notes.enc.json, presence.json, identity.json, keystore.json dahil (overwrite yasağı referansı)."""
    assert len(CORE_STATE_PATH_NAMES) >= 3
    assert "tasks.json" in CORE_STATE_PATH_NAMES
    assert "trash" in CORE_STATE_PATH_NAMES
    assert "config" in CORE_STATE_PATH_NAMES
    assert "notes.enc.json" in CORE_STATE_PATH_NAMES
    assert "presence.json" in CORE_STATE_PATH_NAMES
    assert "identity.json" in CORE_STATE_PATH_NAMES
    assert "keystore.json" in CORE_STATE_PATH_NAMES


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
        assert is_core_state_path(base, f"{base}/presence.json") is True
        assert is_core_state_path(base, f"{base}/identity.json") is True
        assert is_core_state_path(base, f"{base}/keystore.json") is True
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


def test_allow_write_to_core_when_not_sandbox_mode():
    """is_sandbox_mode=False ise her zaman True (mevcut davranış)."""
    with tempfile.TemporaryDirectory() as d:
        assert allow_write_to_core(d, f"{d}/tasks/tasks.json", False) is True
        assert allow_write_to_core(d, f"{d}/aliases.json", False) is True


def test_allow_write_to_core_sandbox_mode_blocks_live_core():
    """Sandbox modunda canlı çekirdek path'e yazma reddedilir."""
    with tempfile.TemporaryDirectory() as d:
        assert allow_write_to_core(d, f"{d}/tasks/tasks.json", True) is False
        assert allow_write_to_core(d, f"{d}/aliases.json", True) is False
        assert allow_write_to_core(d, f"{d}/notes.enc.json", True) is False
        assert allow_write_to_core(d, f"{d}/presence.json", True) is False
        assert allow_write_to_core(d, f"{d}/identity.json", True) is False
        assert allow_write_to_core(d, f"{d}/keystore.json", True) is False


def test_allow_write_to_core_sandbox_mode_allows_non_core():
    """Sandbox modunda çekirdek dışı path'e yazma izinli."""
    with tempfile.TemporaryDirectory() as d:
        assert allow_write_to_core(d, f"{d}/sandbox/tasks.json", True) is True
        assert allow_write_to_core(d, f"{d}/other.json", True) is True


def test_allow_write_to_core_sandbox_mode_target_outside_live_allowed():
    """Sandbox modunda canlı base dışı hedefe yazma izinli."""
    with tempfile.TemporaryDirectory() as d:
        with tempfile.TemporaryDirectory() as other:
            assert allow_write_to_core(d, f"{other}/aliases.json", True) is True


def test_task_store_sandbox_mode_raises_on_live_core_write():
    """TaskStore sandbox_mode=True ve canlı çekirdek path'e yazma girişiminde CoreWriteForbidden."""
    from task_engine.engine import TaskStore

    with tempfile.TemporaryDirectory() as d:
        tasks_dir = f"{d}/tasks"
        store = TaskStore(tasks_dir, sandbox_mode=True)
        with pytest.raises(CoreWriteForbidden):
            store.create("Test", "Açıklama", "rapor")


def test_save_aliases_json_uses_core_guard_and_path(tmp_path):
    """aliases.json yazımı merkezi sink üzerinden ve core guard ile yapılır."""
    base = tmp_path
    aliases = {"g": "gorevler"}

    # Varsayılan: is_sandbox_mode=False → guard izin verir ve dosya yazılır.
    save_aliases_json(base, aliases)
    p = alias_file_path(base)
    assert p.is_file()
    assert json.loads(p.read_text(encoding="utf-8")) == aliases


def test_save_aliases_json_respects_sandbox_guard(tmp_path):
    """Sandbox modunda canlı çekirdek aliases.json path'ine yazma reddedilir."""
    base = tmp_path
    aliases = {"g": "gorevler"}

    with pytest.raises(CoreWriteForbidden):
        save_aliases_json(base, aliases, is_sandbox_mode=True)


def test_notes_file_path_under_base():
    """notes_file_path(base) base/notes.enc.json döner."""
    with tempfile.TemporaryDirectory() as d:
        p = notes_file_path(d)
        assert p == Path(d) / "notes.enc.json"
        assert p.name == "notes.enc.json"


def test_config_file_path_under_base():
    """config_file_path(base) base/config.json döner."""
    with tempfile.TemporaryDirectory() as d:
        p = config_file_path(d)
        assert p == Path(d) / "config.json"
        assert p.name == "config.json"


def test_logs_paths_under_base():
    """logs_dir_path ve logs_file_path base altında beklenen path'leri döner."""
    with tempfile.TemporaryDirectory() as d:
        base = d
        logs_dir = logs_dir_path(base)
        assert logs_dir == Path(base) / "logs"
        assert logs_dir.name == "logs"

        log_file = logs_file_path(base)
        assert log_file == logs_dir / "log.txt"
        assert log_file.name == "log.txt"


def test_save_notes_enc_json_uses_core_guard_and_path(tmp_path):
    """notes.enc.json yazımı merkezi sink üzerinden ve core guard ile yapılır."""
    base = tmp_path
    data = {"v": 1, "cipher": "aesgcm", "nonce_b64": "x", "ct_b64": "y"}

    save_notes_enc_json(base, data)
    p = notes_file_path(base)
    assert p.is_file()
    assert json.loads(p.read_text(encoding="utf-8")) == data


def test_save_notes_enc_json_respects_sandbox_guard(tmp_path):
    """Sandbox modunda canlı çekirdek notes.enc.json path'ine yazma reddedilir."""
    base = tmp_path
    data = {"v": 1, "cipher": "aesgcm", "nonce_b64": "x", "ct_b64": "y"}

    with pytest.raises(CoreWriteForbidden):
        save_notes_enc_json(base, data, is_sandbox_mode=True)


def test_secure_notes_store_sandbox_mode_raises_on_live_core_write(tmp_path):
    """SecureNotesStore(is_sandbox_mode=True).save() canlı çekirdek path'e yazarken CoreWriteForbidden."""
    from memory.secure_store import SecureNotesStore

    root_key = b"\x00" * 32  # 32-byte key for AESGCM
    store = SecureNotesStore(base_dir=str(tmp_path), is_sandbox_mode=True)
    with pytest.raises(CoreWriteForbidden):
        store.save(root_key, [])


def test_presence_cfg_path_under_base():
    """presence_cfg_path(base) base/presence.json döner."""
    with tempfile.TemporaryDirectory() as d:
        p = presence_cfg_path(d)
        assert p == Path(d) / "presence.json"
        assert p.name == "presence.json"


def test_save_presence_cfg_json_uses_core_guard_and_path(tmp_path):
    """presence.json yazımı merkezi sink üzerinden ve core guard ile yapılır."""
    base = tmp_path
    data = {"enabled": True, "timeout_sec": 30}

    save_presence_cfg_json(base, data)
    p = presence_cfg_path(base)
    assert p.is_file()
    assert json.loads(p.read_text(encoding="utf-8")) == data


def test_save_presence_cfg_json_respects_sandbox_guard(tmp_path):
    """Sandbox modunda canlı çekirdek presence.json path'ine yazma reddedilir."""
    base = tmp_path
    data = {"enabled": True}

    with pytest.raises(CoreWriteForbidden):
        save_presence_cfg_json(base, data, is_sandbox_mode=True)


def test_identity_file_path_under_base():
    """identity_file_path(base) base/identity.json döner."""
    with tempfile.TemporaryDirectory() as d:
        p = identity_file_path(d)
        assert p == Path(d) / "identity.json"
        assert p.name == "identity.json"


def test_save_identity_json_uses_core_guard_and_path(tmp_path):
    """identity.json yazımı merkezi sink üzerinden ve core guard ile yapılır."""
    base = tmp_path
    data = {"v": 1, "lumos_id": "x"}

    save_identity_json(base, data)
    p = identity_file_path(base)
    assert p.is_file()
    assert json.loads(p.read_text(encoding="utf-8")) == data


def test_save_identity_json_respects_sandbox_guard(tmp_path):
    """Sandbox modunda canlı çekirdek identity.json path'ine yazma reddedilir."""
    base = tmp_path
    data = {"v": 1}

    with pytest.raises(CoreWriteForbidden):
        save_identity_json(base, data, is_sandbox_mode=True)


def test_keystore_file_path_under_base():
    """keystore_file_path(base) base/keystore.json döner."""
    with tempfile.TemporaryDirectory() as d:
        p = keystore_file_path(d)
        assert p == Path(d) / "keystore.json"
        assert p.name == "keystore.json"


def test_save_keystore_json_uses_core_guard_and_path(tmp_path):
    """keystore.json yazımı merkezi sink üzerinden ve core guard ile yapılır."""
    base = tmp_path
    data = {"v": 1, "root_key": {"cipher": "aesgcm"}}

    save_keystore_json(base, data)
    p = keystore_file_path(base)
    assert p.is_file()
    assert json.loads(p.read_text(encoding="utf-8")) == data


def test_save_keystore_json_respects_sandbox_guard(tmp_path):
    """Sandbox modunda canlı çekirdek keystore.json path'ine yazma reddedilir."""
    base = tmp_path
    data = {"v": 1}

    with pytest.raises(CoreWriteForbidden):
        save_keystore_json(base, data, is_sandbox_mode=True)


def test_append_log_line_appends_lines_with_newline(tmp_path):
    """append_log_line(base, line) logs/log.txt dosyasına satır ekler."""
    base = tmp_path

    append_log_line(base, "first")
    log_file = logs_file_path(base)
    assert log_file.is_file()
    assert log_file.read_text(encoding="utf-8").splitlines() == ["first"]

    append_log_line(base, "second")
    assert log_file.read_text(encoding="utf-8").splitlines() == ["first", "second"]


def test_append_log_line_respects_sandbox_guard(tmp_path):
    """Sandbox modunda canlı çekirdek logs/log.txt path'ine yazma reddedilir."""
    base = tmp_path

    with pytest.raises(CoreWriteForbidden):
        append_log_line(base, "x", is_sandbox_mode=True)
