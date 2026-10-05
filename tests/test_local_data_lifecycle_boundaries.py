"""Offline foundation checks; these do not claim a production deletion workflow."""

import json

import pytest

from memory.memory import Memory
from memory.schema import MemoryNote
from memory.secure_store import SecureNotesStore


def test_memory_delete_without_store_clears_ram_only():
    memory = Memory(notes=[MemoryNote(kind="fact", content="synthetic note")])
    memory._is_unlocked = True
    assert memory.store is None
    assert memory.delete_all() == 1
    assert memory.notes == []
    assert memory.delete_all() == 0


def test_local_memory_delete_requires_unlock_and_persists_empty_store(tmp_path):
    key = b"k" * 32  # Disposable test key, not a user credential.
    store = SecureNotesStore(base_dir=str(tmp_path / "notes"))
    memory = Memory()
    memory.attach_store(store, key)
    memory.add(MemoryNote(kind="fact", content="synthetic note"))
    before = store.path.read_bytes()
    memory.device_lock()
    assert memory.delete_all() == 0
    assert store.path.read_bytes() == before
    assert len(store.load(key)) == 1
    memory.attach_store(store, key)
    assert memory.delete_all() == 1
    assert store.load(key) == []
    assert memory.notes == []
    assert memory.delete_all() == 0
    assert store.load(key) == []


@pytest.mark.parametrize("failure", ["before_write", "partial_write", "after_write", "no_write", "readback"])
def test_memory_delete_does_not_report_uncertain_persistence_as_success(tmp_path, monkeypatch, failure):
    key = b"k" * 32
    store = SecureNotesStore(base_dir=str(tmp_path / "notes"))
    memory = Memory()
    memory.attach_store(store, key)
    memory.add(MemoryNote(kind="fact", content="synthetic note"))
    before = store.path.read_bytes()
    notes_before = memory.notes
    save, load = store.save, store.load
    attempts = []

    def uncertain_save(root_key, notes):
        attempts.append("save")
        if failure == "before_write":
            raise OSError("fixture write rejected")
        if failure == "partial_write":
            store.path.write_bytes(b"partial fixture")
            raise OSError("fixture partial write")
        if failure == "no_write":
            return
        save(root_key, notes)
        if failure == "after_write":
            raise OSError("fixture acknowledgement lost")

    def uncertain_load(root_key, **kwargs):
        if failure == "readback":
            raise OSError("fixture readback unavailable")
        return load(root_key, **kwargs)

    monkeypatch.setattr(store, "save", uncertain_save)
    monkeypatch.setattr(store, "load", uncertain_load)
    with pytest.raises((OSError, RuntimeError)):
        memory.delete_all()
    assert attempts == ["save"]  # No automatic retry or disk rollback.
    assert memory.notes is notes_before
    assert len(memory.notes) == 1
    if failure in {"before_write", "no_write"}:
        assert store.path.read_bytes() == before
    elif failure == "partial_write":
        assert store.path.read_bytes() == b"partial fixture"
    else:
        assert load(key) == []  # An exception does not imply disk was unchanged.

    monkeypatch.setattr(store, "save", save)
    monkeypatch.setattr(store, "load", load)
    # A separate explicit invocation can finish; count describes local notes cleared.
    assert memory.delete_all() == 1
    assert load(key) == []
    assert memory.delete_all() == 0


def test_memory_delete_with_store_but_missing_key_fails_without_write(tmp_path):
    store = SecureNotesStore(base_dir=str(tmp_path / "notes"))
    memory = Memory(store=store, notes=[MemoryNote(kind="fact", content="fixture")])
    memory._is_unlocked = True
    with pytest.raises(RuntimeError):
        memory.delete_all()
    assert len(memory.notes) == 1
    assert not store.path.exists()


@pytest.mark.parametrize("plain", [
    b'{"v":1}', b'{"v":1,"notes":{}}', b'{"v":1,"notes":""}',
    b'{"notes":[]}', b'{"v":2,"notes":[]}', b'{"v":true,"notes":[]}',
    b'{"v":1,"notes":null}', b'[]', b'{invalid',
])
def test_delete_rejects_normalized_invalid_plaintext(tmp_path, monkeypatch, plain):
    key = b"k" * 32
    store = SecureNotesStore(base_dir=str(tmp_path / "notes"))
    memory = Memory()
    memory.attach_store(store, key)
    memory.add(MemoryNote(kind="fact", content="fixture"))
    original = memory.notes
    monkeypatch.setattr(store, "_to_plain", lambda notes: plain)
    with pytest.raises(ValueError):
        memory.delete_all()
    assert memory.notes is original
    if plain in [b'{"v":1}', b'{"v":1,"notes":{}}', b'{"v":1,"notes":""}']:
        assert store.load(key) == []  # Legacy permissive reads remain compatible.


@pytest.mark.parametrize("write_first", [True, False])
def test_delete_rejects_readback_permission_error(tmp_path, monkeypatch, write_first):
    key = b"k" * 32
    store = SecureNotesStore(base_dir=str(tmp_path / "notes"))
    memory = Memory()
    memory.attach_store(store, key)
    memory.add(MemoryNote(kind="fact", content="fixture"))
    original = memory.notes
    save = store.save

    def save_then_deny(root_key, notes):
        if write_first:
            save(root_key, notes)
        store.base.chmod(0)

    monkeypatch.setattr(store, "save", save_then_deny)
    try:
        with pytest.raises(PermissionError):
            memory.delete_all()
        assert memory.notes is original
    finally:
        store.base.chmod(0o700)


def test_delete_requires_created_store_after_save(tmp_path, monkeypatch):
    store = SecureNotesStore(base_dir=str(tmp_path / "notes"))
    memory = Memory()
    memory.attach_store(store, b"k" * 32)
    assert memory.notes == []  # An initially absent store is allowed at attachment.
    save = store.save
    monkeypatch.setattr(store, "save", lambda key, notes: None)
    with pytest.raises(FileNotFoundError):
        memory.delete_all()
    monkeypatch.setattr(store, "save", save)
    assert memory.delete_all() == 0
    assert store.path.is_file()


@pytest.mark.parametrize("field,value", [("v", 2), ("v", True), ("cipher", "unknown"), ("aad", None)])
def test_delete_rejects_invalid_store_envelope(tmp_path, monkeypatch, field, value):
    store = SecureNotesStore(base_dir=str(tmp_path / "notes"))
    memory = Memory()
    memory.attach_store(store, b"k" * 32)
    memory.add(MemoryNote(kind="fact", content="fixture"))
    original, save = memory.notes, store.save

    def invalid_envelope(key, notes):
        save(key, notes)
        envelope = json.loads(store.path.read_text())
        envelope[field] = value
        store.path.write_text(json.dumps(envelope))

    monkeypatch.setattr(store, "save", invalid_envelope)
    with pytest.raises(ValueError):
        memory.delete_all()
    assert memory.notes is original
