"""build_pending_approvals_list boş dizin / okuma dayanıklılığı."""
import json

from kando_bridge.server import build_pending_approvals_list


def test_build_pending_approvals_list_empty(tmp_path, monkeypatch):
    from kando_bridge import server as srv

    monkeypatch.setattr(srv, "PENDING_APPROVALS_DIR", tmp_path / "pending")
    assert build_pending_approvals_list() == []


def test_build_pending_approvals_list_one_file(tmp_path, monkeypatch):
    from kando_bridge import server as srv

    pdir = tmp_path / "pending"
    pdir.mkdir()
    rec = {
        "schema_version": "lumos.pending_approval.v1",
        "created_at": "2026-01-01T00:00:00+00:00",
        "approval_file": ".lumos/pending_approvals/x.json",
        "approval_token": "tok1",
        "risk_level": "high",
        "reasoning_summary": "yüksek risk",
        "original_payload": "README.md dosyasını düzelt",
        "used": False,
    }
    (pdir / "x.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(srv, "PENDING_APPROVALS_DIR", pdir)
    items = build_pending_approvals_list()
    assert len(items) == 1
    assert items[0]["approval_token"] == "tok1"
    assert items[0]["reasoning_summary"] == "yüksek risk"
    assert items[0]["risk_level"] == "high"
    assert items[0]["used"] is False
    assert items[0]["pending_summary"] == "README.md güncellenecek"
