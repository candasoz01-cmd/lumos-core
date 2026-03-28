"""
Patch öner: minimum dosya kümesi → propose_text_patch → doğrula.
Tek dosya (single_file_safe): her zaman apply + verify (VERIFY veya .py py_compile; yoksa no_verify).
Çok dosya: pending + onay (görev: onayla).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from core.patch_pipeline import (
    ProtectedApplyForbidden,
    apply_patch,
    propose_text_patch,
    validate_proposal_against_filesystem,
)
from core.workspace_contract import is_core_state_path
from kando.patch_pending import save_pending_multi
from kando.patch_verify_runner import run_post_apply_verify
from kando.patch_scope import (
    analyze_patch_scope,
    parse_patch_goal_extended,
    parse_patch_goal_legacy,
)

if TYPE_CHECKING:
    from task_engine.engine import TaskRecord, TaskStep
    from task_engine.action_registry import ExecutionContext

# Geriye dönük: tests / cursor_bridge
parse_patch_goal = parse_patch_goal_legacy


def _repo_root() -> Path:
    env = (os.environ.get("LUMOS_REPO_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    base = os.environ.get("LUMOS_BASE_DIR", ".lumos")
    p = Path(base)
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    else:
        p = p.resolve()
    if p.name == ".lumos":
        return p.parent
    return Path.cwd().resolve()


def patch_apply_executor(
    step: "TaskStep",
    task: "TaskRecord",
    context: "ExecutionContext",
) -> tuple[bool, str, str, bool]:
    """patch: → tek dosyada zorunlu apply; çok dosyada pending."""
    ext = parse_patch_goal_extended(task.description)
    analysis = analyze_patch_scope(ext)

    if analysis.kind == "blocked_scope_too_wide":
        return (
            False,
            "",
            analysis.blocked_reason or "Kapsam engellendi.",
            False,
        )

    lumos_base = Path(os.environ.get("LUMOS_BASE_DIR", ".lumos"))
    if not lumos_base.is_absolute():
        lumos_base = (Path.cwd() / lumos_base).resolve()
    else:
        lumos_base = lumos_base.resolve()
    root = _repo_root()

    if analysis.kind == "single_file_safe":
        rel = ext.paths_ordered[0]
        body = ext.bodies.get(rel, "")
        target = (root / rel).resolve()
        if is_core_state_path(lumos_base, target):
            return (
                False,
                "",
                "Hedef çekirdek state kapsamında; patch bu yoldan uygulanamaz.",
                False,
            )
        try:
            proposal = propose_text_patch(
                target,
                body,
                reason="task_engine.patch_apply_executor",
                caller="task_engine.executors.patch_apply_executor",
                source="kando",
                user_initiated=True,
                protected_target=False,
            )
            val = validate_proposal_against_filesystem(proposal)
            if val.status != "ok":
                return False, "", f"Doğrulama: {val.message}", False

            apply_patch(proposal, assume_reviewed=True, allow_protected_apply=False)
            v_ok, v_msg = run_post_apply_verify(target, ext.verify_cmd)
            if not v_ok:
                return (
                    False,
                    "",
                    f"apply_ok_verify_failed: {v_msg}"[:2000],
                    False,
                )
            lines_out = [
                "patch_auto_applied",
                "patch_result=patch_applied",
                "Patch uygulaması tamamlandı",
                "durum: applied",
                f"SCOPE_KIND: {analysis.kind}",
                f"Hedef: {rel}",
                f"patch_id: {proposal.id}",
                f"verify: {v_msg}",
            ]
            return True, "\n".join(lines_out), "", True
        except ProtectedApplyForbidden as e:
            return False, "", str(e), False
        except Exception as e:
            return False, "", str(e)[:500], False

    # multi_file_required
    files_payload: list[dict] = []
    diff_lines: list[str] = []
    for rel in analysis.apply_order:
        body = ext.bodies.get(rel, "")
        target = (root / rel).resolve()
        if is_core_state_path(lumos_base, target):
            return (
                False,
                "",
                f"{rel}: çekirdek state kapsamında; patch uygulanamaz.",
                False,
            )
        try:
            proposal = propose_text_patch(
                target,
                body,
                reason="task_engine.patch_apply_executor.multi",
                caller="task_engine.executors.patch_apply_executor",
                source="kando",
                user_initiated=True,
                protected_target=False,
            )
            val = validate_proposal_against_filesystem(proposal)
            if val.status != "ok":
                return False, "", f"{rel}: doğrulama: {val.message}", False
            files_payload.append(
                {
                    "relative_path": rel,
                    "target_path": str(target.resolve()),
                    "patch_id": proposal.id,
                    "proposed_text": proposal.proposed_text,
                    "diff_text": proposal.diff_text or "",
                }
            )
            diff_lines.append(f"=== {rel} ===\n{(proposal.diff_text or '')[:8000]}")
        except ProtectedApplyForbidden as e:
            return False, "", str(e), False
        except Exception as e:
            return False, "", str(e)[:500], False

    impact = {
        "required_files": analysis.required_files,
        "support_files": analysis.support_files,
        "optional_files": analysis.optional_files,
    }
    plan = (
        f"Sınıflandırma: multi_file_required\n"
        f"Etki — zorunlu: {analysis.required_files}, destek/test: {analysis.support_files}, "
        f"opsiyonel: {analysis.optional_files}\n"
        f"Sıra: {', '.join(analysis.apply_order)}\n"
        f"Gerekçe: {analysis.rationale_short}"
    )
    save_pending_multi(
        files=files_payload,
        plan=plan,
        verify_command=ext.verify_cmd,
        scope_kind=analysis.kind,
        rationale_short=analysis.rationale_short,
        apply_order=list(analysis.apply_order),
        impact=impact,
    )

    lines_out = [
        "patch_pending_approval",
        "patch_multi_pending",
        f"SCOPE_KIND: {analysis.kind}",
        f"ETKI_ZORUNLU: {', '.join(analysis.required_files)}",
        f"ETKI_DESTEK: {', '.join(analysis.support_files)}",
        f"ETKI_OPSIYONEL: {', '.join(analysis.optional_files)}",
        f"SIRA: {', '.join(analysis.apply_order)}",
        f"Gerekçe: {analysis.rationale_short}",
        "DIFF (özet):",
        "\n\n".join(diff_lines)[:20000],
        "---",
        "Onay: görev: onayla (sırayla uygulanır; sonda VERIFY)",
    ]
    if ext.verify_cmd:
        lines_out.append(f"VERIFY (tüm dosyalar sonrası): {ext.verify_cmd}")
    return True, "\n".join(lines_out), "", False
