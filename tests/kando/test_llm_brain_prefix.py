"""görev: prefix → core.brain.run (TaskEngine + doğrulama)."""
import json
import tempfile

from kando.llm import llm


def test_gorev_prefix_empty_goal():
    assert llm("görev: ").strip() == "görev: <hedef> yaz."


def test_gorev_prefix_runs_brain(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setenv("LUMOS_BASE_DIR", d)
        out = llm("görev: not sistemini kontrol et ve özet ver")
        assert "Görev:" in out
        assert "Durum:" in out


def test_gorev_onayla_applies_pending(monkeypatch, tmp_path):
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path / ".lumos"))
    monkeypatch.setenv("LUMOS_REPO_ROOT", str(tmp_path))
    (tmp_path / ".lumos").mkdir(parents=True)
    fp = tmp_path / "t.txt"
    fp.write_text("a", encoding="utf-8")
    pending = {
        "schema_version": "kando.pending_patch.v1",
        "patch_id": "testid",
        "target_path": str(fp.resolve()),
        "diff_text": "",
        "proposed_text": "b",
        "plan": "test",
        "verify_command": "",
    }
    bridge = tmp_path / ".lumos" / "cursor_bridge"
    bridge.mkdir(parents=True)
    (bridge / "pending_patch.json").write_text(
        json.dumps(pending, ensure_ascii=False),
        encoding="utf-8",
    )
    out = llm("görev: onayla")
    assert "Patch uygulandı" in out or "uygulandı" in out.lower()
    assert fp.read_text(encoding="utf-8") == "b"
