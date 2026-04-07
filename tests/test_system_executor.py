"""system_executor: dosya yazma, simülasyon logu, whitelist komut."""

from pathlib import Path

from kando_runtime.system_executor import run


def test_delete_all_blocked_when_pending(tmp_path: Path) -> None:
    out = {
        "execution_mode": "pending_approval",
        "http_body": {"lumos_gate": {"execution_mode": "pending_approval"}},
    }
    r = run({"text": "tüm dosyaları sil", "out": out}, repo_root=tmp_path)
    assert r["executed"] is False
    assert r["outcome_tr"] == "reddedildi"
    log = tmp_path / ".lumos" / "logs" / "file_executor.log"
    assert not log.is_file()


def test_delete_all_simulation_logs(tmp_path: Path) -> None:
    out = {"execution_mode": "restricted", "http_body": {}}
    r = run({"text": "tüm dosyaları sil", "out": out}, repo_root=tmp_path)
    assert r["executed"] is True
    assert r["status"] == "simulation"
    assert r["outcome_tr"] == "çalıştırıldı (simülasyon)"
    log = tmp_path / ".lumos" / "logs" / "file_executor.log"
    assert log.is_file()
    assert "SIMULATION delete_all" in log.read_text(encoding="utf-8")


def test_create_test_txt(tmp_path: Path) -> None:
    out = {"execution_mode": "restricted", "http_body": {}}
    r = run({"text": "test.txt oluştur", "out": out}, repo_root=tmp_path)
    assert r["executed"] is True
    assert r["outcome_tr"] == "başarılı"
    p = Path(r["path"])
    assert p.resolve() == (tmp_path / "workspace" / "test.txt").resolve()
    assert r.get("stdout") == str(p.resolve())
    assert p.read_text(encoding="utf-8") == "ok\n"


def test_create_nested_path(tmp_path: Path) -> None:
    out = {"execution_mode": "restricted", "http_body": {}}
    r = run({"text": "a/b/c.md oluştur", "out": out}, repo_root=tmp_path)
    assert r["executed"] is True
    p = Path(r["path"])
    assert p == (tmp_path / "workspace" / "a" / "b" / "c.md").resolve()
    assert p.read_text(encoding="utf-8") == "ok\n"


def test_whitelisted_pwd(tmp_path: Path) -> None:
    out = {"execution_mode": "restricted", "http_body": {}}
    r = run({"text": "komut çalıştır: pwd", "out": out}, repo_root=tmp_path)
    assert r["executed"] is True
    assert r["outcome_tr"] == "başarılı"
    assert "stdout" in r
    assert str(tmp_path.resolve() / ".lumos" / "system_workspace") in str(r.get("stdout", ""))


def test_bare_pwd_stdout(tmp_path: Path) -> None:
    out = {"execution_mode": "restricted", "http_body": {}}
    from kando_runtime.shell_executor import run as shell_run

    r = shell_run({"text": "pwd", "out": out}, repo_root=tmp_path)
    assert r["executed"] is True
    assert r["returncode"] == 0
    assert r["stdout"].strip()
    assert not (r.get("stderr") or "").strip()


def test_non_whitelisted_cmd_rejected(tmp_path: Path) -> None:
    out = {"execution_mode": "restricted", "http_body": {}}
    r = run({"text": "komut çalıştır: rm", "out": out}, repo_root=tmp_path)
    assert r["executed"] is False
    assert r["outcome_tr"] == "reddedildi"
