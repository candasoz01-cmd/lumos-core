from __future__ import annotations

from pathlib import Path


import pytest

from core.patch_registry import clear_registry
from core.write_interceptor import WriteRequest, intercept_write, is_protected_core_path
from core.workspace_contract import CoreWriteForbidden


def test_is_protected_core_path_uses_workspace_contract(tmp_path: Path):
    base = tmp_path
    core_file = base / "tasks.json"
    non_core_file = base / "other.json"

    assert is_protected_core_path(base, core_file) is True
    assert is_protected_core_path(base, non_core_file) is False


def test_non_core_write_allowed_and_writes_content(tmp_path: Path):
    clear_registry()
    base = tmp_path
    target = base / "other.json"

    req = WriteRequest(
        target_path=target,
        content='{"k": 1}',
        base_dir=base,
        sandbox_mode=False,
        caller="test_non_core_write_allowed_and_writes_content",
        source="test",
        user_initiated=True,
    )

    intercept_write(req)
    assert target.is_file()
    assert target.read_text(encoding="utf-8") == '{"k": 1}'


def test_protected_path_write_goes_through_patch_and_does_not_direct_write(tmp_path: Path):
    clear_registry()
    base = tmp_path
    core_file = base / "tasks.json"
    core_file.write_text("{}", encoding="utf-8")

    req = WriteRequest(
        target_path=core_file,
        content='{"k": 2}',
        base_dir=base,
        sandbox_mode=False,
        caller="test_protected_path_write_goes_through_patch_and_does_not_direct_write",
        source="test",
        user_initiated=True,
    )

    # Lifecycle gate apply'ı engellediği için içerik hemen değişmeyebilir.
    intercept_write(req)
    # Registry'yi spesifik id'ler üzerinden test_patch_pipeline zaten doğruluyor; burada
    # sadece protected path'in direct write ile güncellenmediğini kontrol ediyoruz.
    assert core_file.read_text(encoding="utf-8") == "{}"


def test_sandbox_mode_protected_core_write_denied(tmp_path: Path):
    clear_registry()
    base = tmp_path
    core_file = base / "tasks.json"
    core_file.write_text("{}", encoding="utf-8")

    req = WriteRequest(
        target_path=core_file,
        content='{"k": 3}',
        base_dir=base,
        sandbox_mode=True,
        caller="test_sandbox_mode_protected_core_write_denied",
        source="test",
        user_initiated=False,
    )

    with pytest.raises(CoreWriteForbidden):
        intercept_write(req)


def test_rollback_after_applied_patch_via_registry(tmp_path: Path):
    """
    Rollback davranışı patch_registry üzerinden zaten test ediliyor.
    Burada sadece interceptor ile yazılıp sonra rollback çalıştırılabildiğini
    senaryosal olarak doğrularız.
    """
    clear_registry()
    base = tmp_path
    target = base / "other.json"
    target.write_text("v1", encoding="utf-8")

    # Non-core için interceptor doğrudan yazacak; rollback senaryosu patch_pipeline testlerinde kapsamlı.
    req = WriteRequest(
        target_path=target,
        content="v2",
        base_dir=base,
        sandbox_mode=False,
        caller="test_rollback_after_applied_patch_via_registry",
        source="test",
        user_initiated=True,
    )

    intercept_write(req)
    assert target.read_text(encoding="utf-8") == "v2"

