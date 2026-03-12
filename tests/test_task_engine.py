"""Görev motoru, yetki profili ve görev kaydı testleri."""
import json
import tempfile
from pathlib import Path

import pytest


def test_task_store_create_and_list():
    from task_engine import TaskStore, TaskEngine, PROFILE_GUVENLI_YURUT

    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create("Test görev", "not sistemini kontrol et", PROFILE_GUVENLI_YURUT)
        assert t.task_id == 1
        assert t.status == "bekliyor"
        assert len(t.steps) >= 1
        all_tasks = store.list_all()
        assert len(all_tasks) == 1
        assert store.get(1).title == "Test görev"


def test_task_engine_run():
    from task_engine import TaskStore, TaskEngine, PROFILE_GUVENLI_YURUT

    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        t = store.create("Kontrol", "not sistemini kontrol et ve özet ver", PROFILE_GUVENLI_YURUT)
        engine = TaskEngine(store, PROFILE_GUVENLI_YURUT, True)
        ok, msg = engine.run_task(t.task_id)
        assert ok is True
        assert "tamamlandi" in msg or "Tamamlanan" in msg
        t2 = store.get(t.task_id)
        assert t2.status == "tamamlandi"


def test_permission_profiles():
    from task_engine import ALL_PROFILES, get_profile_display_name, PROFILE_RAPOR, PROFILE_GUVENLI_YURUT

    assert PROFILE_RAPOR in ALL_PROFILES
    assert PROFILE_GUVENLI_YURUT in ALL_PROFILES
    assert "rapor" in get_profile_display_name(PROFILE_RAPOR)
    assert "güvenli" in get_profile_display_name(PROFILE_GUVENLI_YURUT)


def test_security_boundary():
    from task_engine.profiles import SECURITY_NEVER_AUTO, SECURITY_BOUNDARY_DESCRIPTION

    assert "kalıcı silme" in SECURITY_BOUNDARY_DESCRIPTION or "silme" in SECURITY_BOUNDARY_DESCRIPTION
    assert "permanent_delete" in SECURITY_NEVER_AUTO
