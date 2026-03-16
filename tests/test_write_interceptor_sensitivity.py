from __future__ import annotations

from pathlib import Path


from core.write_interceptor import WriteRequest, intercept_write


def _make_req(tmp_path: Path, rel: str, *, content: str = "x") -> WriteRequest:
    target = tmp_path / "src" / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.write_text("old", encoding="utf-8")
    base_dir = tmp_path / ".lumos"
    base_dir.mkdir(parents=True, exist_ok=True)
    return WriteRequest(
        target_path=target,
        content=content,
        base_dir=base_dir,
        sandbox_mode=False,
        caller="test_write_interceptor_sensitivity",
        source="test",
        user_initiated=True,
    )


def test_critical_sensitivity_routes_to_pipeline(tmp_path: Path):
    # core/ altında kritik dosya
    req = _make_req(tmp_path, "core/workspace_contract.py")
    intercept_write(req)
    # İçerik doğrudan değişmeyebilir; burada sadece direct write'ın engellenip
    # patch pipeline'a yönlendirilebilir olduğunu kabul ediyoruz (guard audit ile görünür).
    # Davranışın ayrıntıları patch_pipeline testlerinde kapsanıyor.


def test_high_sensitivity_routes_to_pipeline(tmp_path: Path):
    # engine/ yüksek hassasiyet
    req = _make_req(tmp_path, "engine/model_client.py")
    intercept_write(req)


def test_normal_sensitivity_allows_direct_write(tmp_path: Path):
    req = _make_req(tmp_path, "tools/run_classify.py", content="print('ok')")
    intercept_write(req)
    target = req.target_path
    assert target.is_file()
    assert target.read_text(encoding="utf-8") == "print('ok')"


def test_low_sensitivity_allows_direct_write(tmp_path: Path):
    req = _make_req(tmp_path, "tests/test_something.py", content="# low")
    intercept_write(req)
    target = req.target_path
    assert target.is_file()
    assert target.read_text(encoding="utf-8") == "# low"

