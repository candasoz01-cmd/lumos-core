"""
Intent → plan → patch üret (propose) → apply → verify boru hattı.

Bu modül yalnızca durum özeti üretir; guard/apply/patch_pipeline kodunu değiştirmez.
Sözleşme: lumos.pipeline.v1
"""
from __future__ import annotations

from typing import Any, Literal

StageId = Literal["intent", "plan", "patch_produce", "apply", "verify"]
StageState = Literal["done", "pending", "failed", "skipped", "blocked"]

ORDER: tuple[StageId, ...] = ("intent", "plan", "patch_produce", "apply", "verify")
SCHEMA_VERSION = "lumos.pipeline.v1"


def _safe_local_output(task: Any) -> str:
    for s in reversed(getattr(task, "steps", None) or []):
        if getattr(s, "kind", "") == "safe_local":
            return getattr(s, "output", "") or ""
    return ""


def _stage(
    sid: StageId,
    state: StageState,
    *,
    detail: str = "",
    label: str | None = None,
) -> dict[str, Any]:
    d: dict[str, Any] = {"id": sid, "state": state}
    if detail:
        d["detail"] = detail
    if label:
        d["label"] = label
    return d


def build_pipeline_snapshot(goal: str, task: Any, brain_success: bool) -> dict[str, Any]:
    """
    Brain görev sonrası anlık boru hattı: intent … verify.

    - patch: hedefi: güvenli tek dosyada propose+validate+auto apply+verify; aksi pending+onay.
    - diğer: patch_produce = adım yürütme; apply = genelde skipped.
    """
    g = (goal or "").strip()
    gl = g.lower()
    is_patch_goal = gl.startswith("patch:")
    out_preview = _safe_local_output(task) if task else ""
    pending_out = "patch_pending_approval" in out_preview
    applied_out = "patch_auto_applied" in out_preview and "durum: applied" in out_preview
    patch_like = is_patch_goal or pending_out or applied_out

    if not task:
        return {
            "schema_version": SCHEMA_VERSION,
            "model": "intent_plan_patch_produce_apply_verify",
            "variant": "patch" if patch_like else "generic",
            "stages": [
                _stage("intent", "done"),
                _stage("plan", "pending"),
                _stage("patch_produce", "pending"),
                _stage("apply", "pending"),
                _stage("verify", "pending"),
            ],
            "current_stage": "plan",
            "notes": "task yok",
        }

    stages: list[dict[str, Any]] = [
        _stage("intent", "done", detail="hedef parse"),
        _stage("plan", "done", detail="planner → TaskStep dizisi"),
    ]

    if patch_like:
        out = out_preview
        pending = "patch_pending_approval" in out
        multi = "patch_multi_pending" in out

        if not brain_success:
            stages.append(
                _stage(
                    "patch_produce",
                    "failed",
                    detail="propose/validate veya kapsam",
                )
            )
            stages.append(_stage("apply", "blocked", detail="önceki aşama başarısız"))
            stages.append(_stage("verify", "blocked", detail="—"))
            return {
                "schema_version": SCHEMA_VERSION,
                "model": "intent_plan_patch_produce_apply_verify",
                "variant": "patch",
                "stages": stages,
                "current_stage": "patch_produce",
                "notes": (getattr(task, "error_summary", "") or "")[:200],
            }

        if applied_out:
            stages.append(
                _stage("patch_produce", "done", detail="propose+validate"),
            )
            stages.append(_stage("apply", "done", detail="otomatik uygulama (tek dosya güvenli)"))
            stages.append(_stage("verify", "done", detail="py_compile (+ isteğe VERIFY)"))
            return {
                "schema_version": SCHEMA_VERSION,
                "model": "intent_plan_patch_produce_apply_verify",
                "variant": "patch",
                "stages": stages,
                "current_stage": "verify",
            }

        if pending or multi:
            stages.append(
                _stage(
                    "patch_produce",
                    "done",
                    detail="propose+validate+diff → pending",
                )
            )
            stages.append(
                _stage(
                    "apply",
                    "pending",
                    detail="onay bekleniyor (görev: onayla)",
                )
            )
            stages.append(_stage("verify", "pending", detail="apply sonrası VERIFY"))
            return {
                "schema_version": SCHEMA_VERSION,
                "model": "intent_plan_patch_produce_apply_verify",
                "variant": "patch_multi" if multi else "patch",
                "stages": stages,
                "current_stage": "apply",
                "awaiting_user_action": "görev: onayla",
            }

        stages.append(_stage("patch_produce", "done"))
        stages.append(_stage("apply", "skipped", detail="beklenmeyen patch çıktısı"))
        stages.append(_stage("verify", "pending"))
        return {
            "schema_version": SCHEMA_VERSION,
            "model": "intent_plan_patch_produce_apply_verify",
            "variant": "patch",
            "stages": stages,
            "current_stage": "verify",
        }

    # generic (patch hedefi değil ve pending çıktısı yok)
    step_ok = brain_success
    v = int(getattr(task, "verified_count", 0) or 0)
    u = int(getattr(task, "unverified_count", 0) or 0)
    stages.append(
        _stage(
            "patch_produce",
            "done" if step_ok else "failed",
            label="step_execution",
            detail="TaskEngine executor çıktısı",
        )
    )
    stages.append(
        _stage(
            "apply",
            "skipped",
            label="not_applicable",
            detail="patch dışı görevde ayrı apply yok",
        )
    )
    ver_state: StageState = "done" if v > 0 and u == 0 else ("pending" if step_ok else "failed")
    if step_ok and v == 0 and u > 0:
        ver_state = "pending"
    stages.append(
        _stage(
            "verify",
            ver_state,
            detail="TaskEngine doğrulama + gözlem",
        )
    )
    cur: StageId = "verify"
    if not step_ok:
        cur = "patch_produce"
    elif ver_state == "pending":
        cur = "verify"

    return {
        "schema_version": SCHEMA_VERSION,
        "model": "intent_plan_patch_produce_apply_verify",
        "variant": "generic",
        "stages": stages,
        "current_stage": cur,
    }


def format_pipeline_summary_line(snapshot: dict[str, Any]) -> str:
    """İnsan okuması için tek satır özet."""
    if not snapshot:
        return ""
    var = snapshot.get("variant", "")
    cur = snapshot.get("current_stage", "")
    parts = [f"{s.get('id')}:{s.get('state')}" for s in snapshot.get("stages", [])]
    core = " → ".join(parts) if parts else ""
    wait = snapshot.get("awaiting_user_action")
    extra = f" | beklenen: {wait}" if wait else ""
    return f"Pipeline ({var}): {core} [şu an: {cur}]{extra}"


def merge_pipeline_into_execution(execution: dict[str, Any], snapshot: dict[str, Any]) -> None:
    """Bridge execution sözlüğüne pipeline ekler (referans üzerinde)."""
    execution["pipeline"] = snapshot
    execution["pipeline_model"] = snapshot.get("model", "")


def _goal_has_target_instruction(goal: str) -> bool:
    """İlk anlamlı satır TARGET: ile başlıyorsa (instruction patch apply yolu)."""
    for line in (goal or "").splitlines():
        s = line.strip()
        if s:
            return s.upper().startswith("TARGET:")
    return False


def _instruction_target_pipeline_from_execution(execution: dict[str, Any]) -> dict[str, Any]:
    """
    try_instruction_patch_apply sonucu: generic boru hattında apply=skipped yerine
    gerçek apply/verify aşamalarını yansıtır.
    """
    er = str(execution.get("execution_result") or "")
    et = str(execution.get("error_type") or "")
    detail = str(execution.get("detail") or "")[:200]
    vdet = (execution.get("verify_detail") or "")[:160]
    variant = "instruction_target_multi" if execution.get("multi_file") else "instruction_target"
    stop = (execution.get("stopped_at") or execution.get("detail") or "")[:120]

    common_top = [
        _stage("intent", "done", detail="hedef parse"),
        _stage("plan", "done", detail="planner → TaskStep dizisi"),
        _stage("patch_produce", "done", detail="propose+validate"),
    ]

    if er == "dry_run_success":
        return {
            "schema_version": SCHEMA_VERSION,
            "model": "intent_plan_patch_produce_apply_verify",
            "variant": variant,
            "stages": common_top
            + [
                _stage("apply", "done", detail="dry_run (disk yazılmadı)"),
                _stage("verify", "skipped", detail="dry_run"),
            ],
            "current_stage": "verify",
        }

    if er == "no_change":
        return {
            "schema_version": SCHEMA_VERSION,
            "model": "intent_plan_patch_produce_apply_verify",
            "variant": variant,
            "stages": common_top
            + [
                _stage("apply", "done", detail="değişiklik yok"),
                _stage("verify", "done", detail="—"),
            ],
            "current_stage": "verify",
        }

    if er == "blocked":
        if et == "high_risk_blocked":
            aid = str(execution.get("audit_id") or "").strip()
            wua = f"APPROVE {aid}" if aid else "APPROVE <audit_id>"
            return {
                "schema_version": SCHEMA_VERSION,
                "model": "intent_plan_patch_produce_apply_verify",
                "variant": variant,
                "stages": common_top
                + [
                    _stage("apply", "pending", detail="yüksek risk; onay"),
                    _stage("verify", "pending", detail="—"),
                ],
                "current_stage": "apply",
                "awaiting_user_action": wua,
            }
        if et == "policy_block":
            return {
                "schema_version": SCHEMA_VERSION,
                "model": "intent_plan_patch_produce_apply_verify",
                "variant": variant,
                "stages": common_top
                + [
                    _stage("apply", "blocked", detail=detail[:120] if detail else "policy_block"),
                    _stage("verify", "blocked", detail="—"),
                ],
                "current_stage": "apply",
            }
        return {
            "schema_version": SCHEMA_VERSION,
            "model": "intent_plan_patch_produce_apply_verify",
            "variant": variant,
            "stages": common_top
            + [
                _stage("apply", "blocked", detail=detail[:120] if detail else "blocked"),
                _stage("verify", "blocked", detail="—"),
            ],
            "current_stage": "apply",
        }

    if er == "partial":
        return {
            "schema_version": SCHEMA_VERSION,
            "model": "intent_plan_patch_produce_apply_verify",
            "variant": variant,
            "stages": common_top
            + [
                _stage("apply", "failed", detail=f"kısmi: {stop}" if stop else "kısmi"),
                _stage("verify", "skipped", detail="sıralı akış kesildi"),
            ],
            "current_stage": "apply",
            "notes": detail,
        }

    if er == "rollback_applied":
        return {
            "schema_version": SCHEMA_VERSION,
            "model": "intent_plan_patch_produce_apply_verify",
            "variant": variant,
            "stages": common_top
            + [
                _stage("apply", "failed", detail="apply/verify sonrası rollback"),
                _stage("verify", "failed", detail=vdet or detail[:120]),
            ],
            "current_stage": "verify",
            "notes": detail[:200],
        }

    if er in ("write_failed", "timeout", "timeout_total", "locked"):
        return {
            "schema_version": SCHEMA_VERSION,
            "model": "intent_plan_patch_produce_apply_verify",
            "variant": variant,
            "stages": common_top
            + [
                _stage("apply", "failed", detail=detail[:120] if detail else er),
                _stage("verify", "skipped", detail="—"),
            ],
            "current_stage": "apply",
        }

    if er == "target_required":
        return {
            "schema_version": SCHEMA_VERSION,
            "model": "intent_plan_patch_produce_apply_verify",
            "variant": "instruction_target",
            "stages": [
                _stage("intent", "done", detail="hedef parse"),
                _stage("plan", "done", detail="planner → TaskStep dizisi"),
                _stage("patch_produce", "done", detail="hedef çıkarılamadı"),
                _stage("apply", "skipped", detail="TARGET gerekli"),
                _stage("verify", "skipped", detail="—"),
            ],
            "current_stage": "verify",
            "notes": detail[:200],
        }

    if er == "blocked_by_rollback":
        return {
            "schema_version": SCHEMA_VERSION,
            "model": "intent_plan_patch_produce_apply_verify",
            "variant": variant,
            "stages": common_top
            + [
                _stage("apply", "blocked", detail="rollback sırasında patch yok"),
                _stage("verify", "blocked", detail="—"),
            ],
            "current_stage": "apply",
        }

    # Varsayılan: instruction apply denendi; apply artık not_applicable değil
    return {
        "schema_version": SCHEMA_VERSION,
        "model": "intent_plan_patch_produce_apply_verify",
        "variant": variant,
        "stages": common_top
        + [
            _stage("apply", "pending", detail=detail[:120] if detail else er or "execution"),
            _stage("verify", "pending", detail="—"),
        ],
        "current_stage": "apply",
        "notes": detail[:200],
    }


def enrich_pipeline_with_execution(
    snapshot: dict[str, Any] | None,
    execution: dict[str, Any] | None,
    goal: str,
) -> dict[str, Any]:
    """
    Bridge sonrası: try_instruction / execution sonucu ile pipeline düzeltmesi
    (ör. TARGET: satırı — task adımında patch çıktısı yok ama pending var).
    """
    if not execution:
        return snapshot or {}

    er = execution.get("execution_result")
    g0 = (goal or "").strip().lower()
    is_patch_header = g0.startswith("patch:")

    if er == "pending_approval":
        if snapshot and snapshot.get("variant") == "patch_multi":
            return snapshot
        if execution.get("pending_kind") == "multi_file":
            var = "patch_multi"
        elif is_patch_header:
            var = "patch"
        else:
            var = "instruction_target"
        aid = str(execution.get("audit_id") or "").strip()
        wua = f"APPROVE {aid}" if aid else "görev: onayla"
        return {
            "schema_version": SCHEMA_VERSION,
            "model": "intent_plan_patch_produce_apply_verify",
            "variant": var,
            "stages": [
                _stage("intent", "done"),
                _stage("plan", "done"),
                _stage("patch_produce", "done", detail="propose+validate+diff → pending"),
                _stage("apply", "pending", detail="onay (görev: onayla)"),
                _stage("verify", "pending", detail="apply sonrası"),
            ],
            "current_stage": "apply",
            "awaiting_user_action": wua,
        }

    if er == "no_target_detected":
        return {
            "schema_version": SCHEMA_VERSION,
            "model": "intent_plan_patch_produce_apply_verify",
            "variant": "instruction_target",
            "stages": [
                _stage("intent", "done"),
                _stage("plan", "done"),
                _stage("patch_produce", "done", detail="hedef çıkarılamadı"),
                _stage("apply", "skipped", detail="hedef dosya yok"),
                _stage("verify", "skipped", detail="—"),
            ],
            "current_stage": "verify",
            "notes": execution.get("detail", "")[:200],
        }

    if er == "no_patch_generated":
        return {
            "schema_version": SCHEMA_VERSION,
            "model": "intent_plan_patch_produce_apply_verify",
            "variant": "instruction_target",
            "stages": [
                _stage("intent", "done"),
                _stage("plan", "done"),
                _stage("patch_produce", "done", detail="güvenli yama üretilemedi veya hedef yok"),
                _stage("apply", "skipped"),
                _stage("verify", "skipped"),
            ],
            "current_stage": "verify",
            "notes": execution.get("detail", "")[:200],
        }

    if er == "partial" and execution.get("multi_file"):
        stop = (
            execution.get("stopped_at") or execution.get("detail") or ""
        )[:120]
        return {
            "schema_version": SCHEMA_VERSION,
            "model": "intent_plan_patch_produce_apply_verify",
            "variant": "instruction_target_multi",
            "stages": [
                _stage("intent", "done"),
                _stage("plan", "done"),
                _stage("patch_produce", "done", detail="çoklu (≤2, src/core)"),
                _stage("apply", "failed", detail=f"kısmi: {stop}" if stop else "kısmi"),
                _stage("verify", "skipped", detail="sıralı akış kesildi"),
            ],
            "current_stage": "apply",
            "notes": execution.get("detail", "")[:200],
        }

    if er == "patch_applied":
        vdet = (execution.get("verify_detail") or execution.get("detail") or "")[:160]
        variant = "patch" if is_patch_header else "instruction_target"
        if execution.get("multi_file"):
            variant = "instruction_target_multi"
        return {
            "schema_version": SCHEMA_VERSION,
            "model": "intent_plan_patch_produce_apply_verify",
            "variant": variant,
            "stages": [
                _stage("intent", "done"),
                _stage("plan", "done"),
                _stage("patch_produce", "done", detail="propose+validate"),
                _stage("apply", "done", detail="uygulandı"),
                _stage("verify", "done", detail=vdet or "doğrulama"),
            ],
            "current_stage": "verify",
        }

    if er == "patch_failed":
        return {
            "schema_version": SCHEMA_VERSION,
            "model": "intent_plan_patch_produce_apply_verify",
            "variant": "patch" if is_patch_header else "instruction_target",
            "stages": [
                _stage("intent", "done"),
                _stage("plan", "done"),
                _stage("patch_produce", "failed", detail=execution.get("detail", "")[:120]),
                _stage("apply", "blocked"),
                _stage("verify", "blocked"),
            ],
            "current_stage": "patch_produce",
        }

    # TARGET: … instruction patch apply (try_instruction_patch_apply) — generic snapshot'ta apply skipped görünmesin
    if _goal_has_target_instruction(goal) and (
        snapshot is None or snapshot.get("variant") == "generic"
    ):
        return _instruction_target_pipeline_from_execution(execution)

    return snapshot or {}

# lumos:instruction-pipeline safe touch

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)
