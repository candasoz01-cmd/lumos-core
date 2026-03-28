"""
Patch: öner → diff → (güvenli tek dosyada otomatik uygula + verify) veya onay bekle → uygula → doğrula.
Çok dosya / riskli: apply_patch yalnızca onaydan sonra (görev: onayla).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from core.patch_model import PatchProposal
from core.patch_pipeline import (
    ProtectedApplyForbidden,
    apply_patch,
    propose_text_patch,
    validate_proposal_against_filesystem,
)
from kando.patch_verify_runner import (
    mandatory_py_compile,
    run_integration_verify_command,
    run_post_apply_verify,
)

PENDING_SCHEMA = "kando.pending_patch.v1"
PENDING_NAME = "pending_patch.json"
MULTI_SCHEMA = "kando.pending_multi_patch.v1"
MULTI_NAME = "pending_multi_patch.json"


def _bridge_dir() -> Path:
    base = Path(os.environ.get("LUMOS_BASE_DIR", ".lumos")).resolve()
    d = base / "cursor_bridge"
    d.mkdir(parents=True, exist_ok=True)
    return d


def pending_patch_path() -> Path:
    return _bridge_dir() / PENDING_NAME


def pending_multi_patch_path() -> Path:
    return _bridge_dir() / MULTI_NAME


def save_pending_proposal(
    proposal: PatchProposal,
    *,
    plan: str,
    verify_command: str | None = None,
) -> dict[str, Any]:
    """Disk: tek hedef; uygulama yok."""
    mp = pending_multi_patch_path()
    if mp.is_file():
        mp.unlink()
    payload: dict[str, Any] = {
        "schema_version": PENDING_SCHEMA,
        "patch_id": proposal.id,
        "target_path": str(proposal.target_path),
        "diff_text": proposal.diff_text or "",
        "proposed_text": proposal.proposed_text,
        "plan": plan,
        "verify_command": (verify_command or "").strip(),
    }
    pending_patch_path().write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def save_pending_multi(
    *,
    files: list[dict[str, Any]],
    plan: str,
    verify_command: str | None,
    scope_kind: str,
    rationale_short: str,
    apply_order: list[str],
    impact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Minimum çok dosya kümesi; sıra apply_order ile."""
    p1 = pending_patch_path()
    if p1.is_file():
        p1.unlink()
    payload: dict[str, Any] = {
        "schema_version": MULTI_SCHEMA,
        "files": files,
        "plan": plan,
        "verify_command": (verify_command or "").strip(),
        "scope_kind": scope_kind,
        "rationale_short": rationale_short,
        "apply_order": apply_order,
        "impact": impact or {},
    }
    pending_multi_patch_path().write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def load_pending() -> dict[str, Any] | None:
    p = pending_patch_path()
    if not p.is_file():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if d.get("schema_version") != PENDING_SCHEMA:
        return None
    return d


def load_pending_multi() -> dict[str, Any] | None:
    p = pending_multi_patch_path()
    if not p.is_file():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if d.get("schema_version") != MULTI_SCHEMA:
        return None
    return d


def clear_pending() -> None:
    p = pending_patch_path()
    if p.is_file():
        p.unlink()
    m = pending_multi_patch_path()
    if m.is_file():
        m.unlink()


def _apply_one_pending_file(
    target: Path,
    proposed: str,
    *,
    step_label: str,
) -> tuple[bool, str, str]:
    """Tek dosya: propose → validate → apply. Dönüş: ok, mesaj satırı, patch_id."""
    try:
        proposal = propose_text_patch(
            target,
            proposed,
            reason="kando.patch_pending.apply_pending_after_approval",
            caller="kando.patch_pending.apply_pending_after_approval",
            source="kando",
            user_initiated=True,
            protected_target=False,
        )
        val = validate_proposal_against_filesystem(proposal)
        if val.status != "ok":
            return False, f"[{step_label}] doğrulama: {val.message}", ""
        apply_patch(proposal, assume_reviewed=True, allow_protected_apply=False)
        return True, f"[{step_label}] uygulandı: {target} patch_id={proposal.id}", proposal.id
    except ProtectedApplyForbidden as e:
        return False, f"[{step_label}] {e}", ""
    except Exception as e:
        return False, f"[{step_label}] {str(e)[:500]}", ""


def apply_pending_after_approval() -> tuple[bool, str]:
    """
    Onay sonrası: güncel dosyaya göre propose → validate → apply_patch → isteğe VERIFY.
    Çok dosya: apply_order sırasıyla her adımda guard (validate) + apply; sonda VERIFY.
    """
    multi = load_pending_multi()
    if multi:
        files = multi.get("files") or []
        verify_cmd = (multi.get("verify_command") or "").strip()
        order = multi.get("apply_order") or [f.get("relative_path") for f in files]
        by_rel = {f["relative_path"]: f for f in files if f.get("relative_path")}
        lines: list[str] = [
            "Çok dosya onay akışı (sıra: " + ", ".join(str(x) for x in order) + ")"
        ]
        for i, rel in enumerate(order):
            rec = by_rel.get(rel)
            if not rec:
                clear_pending()
                return False, f"Hedef kaydı bulunamadı: {rel}"
            proposed = rec.get("proposed_text") or ""
            ok, msg, _pid = _apply_one_pending_file(
                Path(rec["target_path"]),
                proposed,
                step_label=f"{i + 1}/{len(order)}",
            )
            lines.append(msg)
            if not ok:
                clear_pending()
                return False, "\n".join(lines)
            tp = Path(rec["target_path"])
            py_ok, py_msg = mandatory_py_compile(tp)
            lines.append(f"py_compile: {py_msg[:1500]}")
            if not py_ok:
                clear_pending()
                return False, "\n".join(lines)
        root = Path(os.environ.get("LUMOS_REPO_ROOT", ".")).resolve()
        if verify_cmd:
            ok_v, vmsg = run_integration_verify_command(verify_cmd, cwd=root)
            lines.append(f"verify: {'ok' if ok_v else 'failed'} — {vmsg[:2000]}")
            if not ok_v:
                clear_pending()
                return False, "\n".join(lines)

        clear_pending()
        return True, "\n".join(lines)

    data = load_pending()
    if not data:
        return False, "Bekleyen patch yok. Önce patch: veya TARGET: ile öneri oluştur."

    target = Path(data["target_path"])
    proposed = data.get("proposed_text") or ""
    verify_cmd = (data.get("verify_command") or "").strip()

    ok, msg, _pid = _apply_one_pending_file(target, proposed, step_label="1/1")
    if not ok:
        return False, msg

    lines = [
        "Patch uygulandı.",
        f"hedef: {target}",
        msg,
    ]
    root = Path(os.environ.get("LUMOS_REPO_ROOT", ".")).resolve()
    v_ok, v_msg = run_post_apply_verify(target, verify_cmd, cwd=root)
    lines.append(v_msg[:3000])
    if not v_ok:
        clear_pending()
        return False, "\n".join(lines)

    clear_pending()
    return True, "\n".join(lines)
