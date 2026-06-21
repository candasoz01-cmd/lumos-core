"""build_pending_approvals_list boş dizin / okuma dayanıklılığı."""
import json

from kando_bridge.server import build_pending_approvals_list
from policy.confirmation_policy import attach_bridge_pending_confirmation


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
    items = build_pending_approvals_list(include_approval_token=True)
    assert len(items) == 1
    assert items[0]["approval_token"] == "tok1"
    assert items[0]["reasoning_summary"] == "yüksek risk"
    assert items[0]["risk_level"] == "high"
    assert items[0]["used"] is False
    assert items[0]["pending_summary"] == "README.md güncellenecek"


def test_build_pending_approvals_list_redacts_token_by_default(tmp_path, monkeypatch):
    from kando_bridge import server as srv

    pdir = tmp_path / "pending"
    pdir.mkdir()
    rec = {
        "schema_version": "lumos.pending_approval.v1",
        "approval_token": "secret-tok",
        "approval_id": "aid1",
        "used": False,
    }
    (pdir / "x.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(srv, "PENDING_APPROVALS_DIR", pdir)
    items = build_pending_approvals_list()
    assert "approval_token" not in items[0]
    with_token = build_pending_approvals_list(include_approval_token=True)
    assert with_token[0]["approval_token"] == "secret-tok"


def test_build_pending_approvals_list_tolerates_cu4_correlation_fields(
    tmp_path, monkeypatch
) -> None:
    """Legacy list API CU4 korelasyon alanları diskte varken bozulmaz (td-08 karakterizasyon)."""
    from kando_bridge import server as srv

    lumos = tmp_path / ".lumos"
    pdir = lumos / "pending_approvals"
    pdir.mkdir(parents=True)
    rec = {
        "schema_version": "lumos.pending_approval.v1",
        "created_at": "2026-01-01T00:00:00+00:00",
        "approval_file": ".lumos/pending_approvals/cu4.json",
        "approval_token": "tok-cu4",
        "risk_level": "high",
        "reasoning_summary": "cu4 shadow",
        "original_payload": "TARGET: z.py\nfix\n",
        "used": False,
        "normalized_task": {"target_rel": "z.py"},
        "execution_plan": {"steps": [{"type": "patch", "file": "z.py", "content": "fix"}]},
        "reasoning_snapshot": {"summary": "cu4 shadow"},
        "policy_ok": True,
        "execution_mode": "pending_approval",
        "final_decision": "await_user_approval",
    }
    attach_bridge_pending_confirmation(rec, base_dir=lumos, risk="high", source="lumos_gate")
    (pdir / "cu4.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(srv, "PENDING_APPROVALS_DIR", pdir)
    items = build_pending_approvals_list(include_approval_token=True)
    assert len(items) == 1
    assert items[0]["approval_token"] == "tok-cu4"
    on_disk = json.loads((pdir / "cu4.json").read_text(encoding="utf-8"))
    assert on_disk.get("confirmation_id")
    assert on_disk.get("confirmation_scope_hash")
    assert "confirmation_id" not in items[0]
