"""
Kando görev akışından Cursor bridge dosyaları + paket üretimi.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from kando.cursor_packet import (
    SCHEMA_EXECUTION,
    SCHEMA_RESULT,
    CursorExecutionPacketV1,
    CursorResultPacketV1,
    Outcome,
    PlannedStepV1,
)
from task_engine.profiles import may_execute_step_at_runtime

_SRC_PY_PATH_RE = re.compile(r"(src/[a-zA-Z0-9_/.\-]+\.py)")

logger = logging.getLogger(__name__)

# Bridge JSON / memory: tam dosya yedeği üst sınırı (disk .bak kullanılmaz)
_MAX_PREVIOUS_CONTENT_IN_EXECUTION = 512_000


def _explicit_single_lock_path(text: str) -> str | None:
    """Metinde tam bir adet src/...py yolu varsa döndür (kando_core ile aynı kural)."""
    ms = _SRC_PY_PATH_RE.findall(text or "")
    if len(ms) != 1:
        return None
    return ms[0]


def _extract_src_py_from_instruction(goal: str) -> str | None:
    m = _SRC_PY_PATH_RE.search(goal or "")
    return m.group(1) if m else None


# brain.run → persist_bridge_after_brain sonrası paketler (run_brain_and_persist_bridge / llm okur)
_last_bridge_packets: (
    tuple[Path, Path, CursorExecutionPacketV1, CursorResultPacketV1] | None
) = None


def resolve_lumos_base_for_bridge(base_dir: Path | str) -> Path:
    """TaskEngine base_dir tasks/ ise üst .lumos; aksi halde genelde .lumos kökü."""
    p = Path(base_dir).resolve()
    if p.name == "tasks":
        return p.parent
    return p


def clear_last_bridge_packets() -> None:
    global _last_bridge_packets
    _last_bridge_packets = None


def pop_last_bridge_packets() -> (
    tuple[Path, Path, CursorExecutionPacketV1, CursorResultPacketV1] | None
):
    """Son persist edilen bridge paketini alır ve sıfırlar."""
    global _last_bridge_packets
    t = _last_bridge_packets
    _last_bridge_packets = None
    return t


def persist_bridge_after_brain(
    *,
    goal: str,
    task: Any,
    brain_success: bool,
    pipeline: dict[str, Any] | None,
    permission_profile: str,
    general_approval: bool,
    lumos_base: Path,
) -> tuple[Path, Path, CursorExecutionPacketV1, CursorResultPacketV1]:
    """
    TaskEngine.run_task sonrası: execution paketi + last_execution/last_result + cursor_executor kancası.
    core.brain.run içinden çağrılır (tek doğruluk kaynağı).
    """
    global _last_bridge_packets
    base = lumos_base.resolve()
    base.mkdir(parents=True, exist_ok=True)

    exe = build_execution_packet(
        goal,
        task,
        permission_profile=permission_profile,
        general_approval=general_approval,
    )
    exe.constraints["lumos_base_resolved"] = str(base)
    try_instruction_patch_apply(goal, exe)
    record_bridge_execution(exe, task)
    from core.patch_pipeline_lifecycle import (
        enrich_pipeline_with_execution,
        merge_pipeline_into_execution,
    )

    ex_dict = exe.constraints.get("execution")
    pl = pipeline
    try:
        if isinstance(ex_dict, dict):
            pl = enrich_pipeline_with_execution(pl, ex_dict, goal)
        if pl:
            exe.constraints["pipeline"] = pl
        if isinstance(ex_dict, dict) and pl:
            merge_pipeline_into_execution(ex_dict, pl)
    except Exception:
        if pipeline:
            exe.constraints["pipeline"] = pipeline
    ex_payload = exe.constraints.get("execution") if isinstance(exe.constraints.get("execution"), dict) else None
    res_pkt = build_result_packet(
        goal=goal,
        brain_success=brain_success,
        task=task,
        execution=ex_payload,
    )
    p_exec, p_res = persist_cursor_bridge(base, exe, res_pkt)
    _last_bridge_packets = (p_exec, p_res, exe, res_pkt)
    try:
        from kando.cursor_executor import run_after_bridge

        run_after_bridge(base, exe)
    except Exception:
        pass
    return _last_bridge_packets


_LUMOS_SAFE_TOUCH_PY = "# lumos:instruction-pipeline safe touch"


def _safe_fallback_new_content(target: Path, *, max_bytes: int = 512_000) -> str | None:
    """Küçük, sözdizimini bozmayan yama: yorum satırı / güvenli ek (docstring veya marker)."""
    try:
        st = target.stat()
    except OSError:
        return None
    if st.st_size > max_bytes:
        return None
    try:
        text = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    ext = target.suffix.lower()
    if ext == ".py":
        add = f"\n{_LUMOS_SAFE_TOUCH_PY}\n"
        if _LUMOS_SAFE_TOUCH_PY in text:
            add = f"\n{_LUMOS_SAFE_TOUCH_PY} (resync)\n"
        if not text.endswith("\n"):
            text += "\n"
        return text + add
    if ext == ".md":
        add = "\n\n<!-- lumos:instruction-pipeline safe touch -->\n"
        if "lumos:instruction-pipeline safe touch" in text:
            add = "\n\n<!-- lumos:instruction-pipeline resync -->\n"
        return text + add
    if ext == ".json":
        return None
    if ext in (".txt", ".toml", ".yaml", ".yml", ".rs", ".go", ".ts", ".tsx", ".jsx", ".sh"):
        sep = "#"
        add = f"\n{sep} lumos:instruction-pipeline safe touch\n"
        if "lumos:instruction-pipeline safe touch" in text:
            add = f"\n{sep} lumos:instruction-pipeline resync\n"
        if not text.endswith("\n"):
            text += "\n"
        return text + add
    return None


def _parse_target_instruction_patch(goal: str) -> tuple[str, str, str | None] | None:
    """
    Task metninden patch üretmek için biçim (patch: öneki yokken):
      TARGET: göreli/yol.txt
      <dosya içeriği>
      İsteğe bağlı:
      VERIFY:
      komut satırı
    """
    lines = (goal or "").strip().splitlines()
    if len(lines) < 2:
        return None
    first = lines[0].strip()
    if not first.upper().startswith("TARGET:"):
        return None
    rel = first.split(":", 1)[1].strip()
    from kando.patch_scope import _split_verify_block

    body_lines, verify_cmd = _split_verify_block(lines[1:])
    body = "\n".join(body_lines).strip("\n")
    if not rel or not body:
        return None
    return rel, body, verify_cmd


def _instruction_apply_one(
    *,
    repo_root: Path,
    lumos_base: Path,
    rel: str,
    body: str,
    verify_cmd: str | None,
    source: str,
) -> tuple[bool, dict[str, Any]]:
    """Tek dosya: propose → apply → verify. (True, {patch_id, verify_msg}) veya (False, {detail, ...})."""
    from core.patch_pipeline import (
        ProtectedApplyForbidden,
        apply_patch,
        propose_text_patch,
        validate_proposal_against_filesystem,
    )
    from core.workspace_contract import is_core_state_path
    from kando.patch_verify_runner import run_post_apply_verify

    target = (repo_root / rel).resolve()
    if is_core_state_path(lumos_base, target):
        return False, {
            "detail": "patch başarısız: hedef .lumos çekirdek state yolunda (yazma yasak)",
            "kind": "core_state",
        }
    previous_text = ""
    if target.is_file():
        try:
            previous_text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            return False, {
                "detail": f"patch başarısız: hedef okunamadı ({rel}): {e}",
                "kind": "read_error",
            }
    try:
        proposal = propose_text_patch(
            target,
            body,
            reason="kando.cursor_bridge.try_instruction_patch_apply",
            caller="kando.cursor_bridge.try_instruction_patch_apply",
            source="kando",
            user_initiated=True,
            protected_target=False,
        )
        val = validate_proposal_against_filesystem(proposal)
        if val.status != "ok":
            return False, {
                "detail": f"patch başarısız: öneri dosya sistemi doğrulamasında reddedildi — {val.message}",
                "kind": "validate",
                "patch_id": proposal.id,
            }

        apply_patch(proposal, assume_reviewed=True, allow_protected_apply=False)
        try:
            on_disk = target.read_text(encoding="utf-8")
        except OSError:
            on_disk = ""
        if on_disk != proposal.proposed_text:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(proposal.proposed_text, encoding="utf-8")
        v_ok, v_msg = run_post_apply_verify(target, verify_cmd)
        if not v_ok:
            return False, {
                "detail": f"patch başarısız: dosya yazıldı ancak doğrulama komutu başarısız — {v_msg}"[:2000],
                "verify_detail": v_msg[:1500],
                "patch_id": proposal.id,
                "kind": "verify",
                "source": source,
            }
        prev_for_exec = previous_text
        truncated = False
        if len(prev_for_exec) > _MAX_PREVIOUS_CONTENT_IN_EXECUTION:
            prev_for_exec = prev_for_exec[:_MAX_PREVIOUS_CONTENT_IN_EXECUTION]
            truncated = True
        logger.info(
            "Instruction patch applied: relative_path=%s patch_id=%s verify_ok",
            rel,
            proposal.id,
        )
        return True, {
            "patch_id": proposal.id,
            "verify_msg": v_msg,
            "source": source,
            "applied_path": rel,
            "previous_content": prev_for_exec,
            "previous_content_truncated": truncated,
        }
    except ProtectedApplyForbidden as e:
        return False, {
            "detail": f"patch başarısız: korumalı hedefe yazma reddedildi — {e}"[:800],
            "kind": "protected",
        }
    except Exception as e:
        return False, {
            "detail": f"patch başarısız: beklenmeyen hata ({rel}) — {e}"[:800],
            "kind": "exception",
        }


def _run_instruction_apply_to_exe(
    exe: CursorExecutionPacketV1,
    rel: str,
    body: str,
    verify_cmd: str | None,
    source: str,
    *,
    repo_root: Path,
    lumos_base: Path,
) -> bool:
    """exe.constraints['execution'] yazar. Başarıda True."""
    exe.target_file = rel
    ok, info = _instruction_apply_one(
        repo_root=repo_root,
        lumos_base=lumos_base,
        rel=rel,
        body=body,
        verify_cmd=verify_cmd,
        source=source,
    )
    if ok:
        v_msg = str(info.get("verify_msg") or "")
        exe.constraints["execution"] = {
            "execution_result": "patch_applied",
            "detail": f"{source}; {v_msg}"[:2000],
            "verify_detail": v_msg[:1500],
            "source": source,
            "patch_id": info.get("patch_id", ""),
            "applied_path": rel,
            "previous_content": info.get("previous_content", ""),
            "previous_content_truncated": bool(info.get("previous_content_truncated")),
        }
        return True
    kind = info.get("kind", "")
    detail = str(info.get("detail", "")).strip() or f"patch başarısız (sebep: {kind or 'bilinmiyor'})"
    if kind == "verify":
        exe.constraints["execution"] = {
            "execution_result": "patch_failed",
            "detail": detail,
            "verify_detail": info.get("verify_detail", ""),
            "source": source,
            "patch_id": info.get("patch_id", ""),
            "failed_path": rel,
        }
    else:
        exe.constraints["execution"] = {
            "execution_result": "patch_failed",
            "detail": detail,
            "failed_path": rel,
        }
    return False


def _run_multi_instruction_fallback(
    pair: list[str],
    exe: CursorExecutionPacketV1,
    *,
    repo_root: Path,
    lumos_base: Path,
) -> None:
    """En fazla 2 dosya; sıralı apply+verify; bir hata → dur, execution_result=partial."""
    file_results: list[dict[str, Any]] = []
    verify_parts: list[str] = []
    patch_ids: list[str] = []

    for rel in pair:
        target = (repo_root / rel).resolve()
        exe.target_file = rel
        body_fb = _safe_fallback_new_content(target)
        if body_fb is None:
            file_results.append({"path": rel, "ok": False, "detail": "güvenli minimal yama üretilemedi (boyut/tür)"})
            exe.target_files = list(pair)
            exe.constraints["execution"] = {
                "execution_result": "partial",
                "multi_file": True,
                "stopped_at": rel,
                "file_results": file_results,
                "detail": "instruction_multi_fallback; sıralı uygulama kesildi (üretim yok)",
                "verify_detail": " | ".join(verify_parts)[:2000] if verify_parts else "",
                "patch_ids": patch_ids,
            }
            return

        ok, info = _instruction_apply_one(
            repo_root=repo_root,
            lumos_base=lumos_base,
            rel=rel,
            body=body_fb,
            verify_cmd=None,
            source="instruction_multi_fallback",
        )
        if not ok:
            file_results.append(
                {
                    "path": rel,
                    "ok": False,
                    "detail": str(info.get("detail", "")),
                    "verify_detail": info.get("verify_detail"),
                }
            )
            exe.target_files = list(pair)
            exe.constraints["execution"] = {
                "execution_result": "partial",
                "multi_file": True,
                "stopped_at": rel,
                "file_results": file_results,
                "detail": f"instruction_multi_fallback; kesildi: {info.get('detail', '')}"[:2000],
                "verify_detail": " | ".join(verify_parts)[:2000] if verify_parts else str(info.get("verify_detail", ""))[:1500],
                "patch_ids": patch_ids,
            }
            return

        pid = str(info.get("patch_id", ""))
        vmsg = str(info.get("verify_msg") or "")
        patch_ids.append(pid)
        verify_parts.append(f"{rel}: {vmsg}")
        file_results.append(
            {
                "path": rel,
                "ok": True,
                "patch_id": pid,
                "verify_detail": vmsg,
                "applied_path": info.get("applied_path", rel),
                "previous_content": info.get("previous_content", ""),
                "previous_content_truncated": bool(info.get("previous_content_truncated")),
            }
        )

    exe.target_files = list(pair)
    summary = " | ".join(verify_parts)
    exe.constraints["execution"] = {
        "execution_result": "patch_applied",
        "multi_file": True,
        "file_results": file_results,
        "detail": f"instruction_multi_fallback; {summary}"[:2000],
        "verify_detail": summary[:2000],
        "patch_ids": patch_ids,
        "source": "instruction_multi_fallback",
    }


def try_instruction_patch_apply(goal: str, exe: CursorExecutionPacketV1) -> None:
    """
    patch: öneki yoksa (exe.patch None):
    - TARGET: … + gövde → propose → apply → verify
    - İki açık dosya (src/core, max 2) → sıralı çoklu fallback
    - Tek dosya: instruction yolu + güvenli fallback içerik
    Tek yol net ise çoklu hedef keşfi yapılmaz; tek dosya apply. Hedef yoksa: target_required.
    """
    if exe.patch is not None:
        return

    from kando.patch_scope import (
        _path_blocked,
        extract_file_task,
        extract_instruction_paths_ordered,
        extract_instruction_target_path,
        select_instruction_multi_pair,
    )
    from task_engine.executors.patch_apply_executor import _repo_root

    repo_root = _repo_root()
    explicit_rel = _explicit_single_lock_path(goal or "")
    if explicit_rel:
        er = explicit_rel.replace("\\", "/").strip()
        if er and not _path_blocked(er) and (repo_root / er).is_file():
            exe.target_file = er

    ft_path, ft_task = extract_file_task(goal)
    explicit_file_task = bool(ft_path and ft_task)
    if ft_path and ft_task and not explicit_rel:
        rel0 = ft_path.strip().replace("\\", "/")
        if rel0 and not _path_blocked(rel0):
            exe.target_file = rel0
    lumos_base = Path(os.environ.get("LUMOS_BASE_DIR", ".lumos"))
    if not lumos_base.is_absolute():
        lumos_base = (Path.cwd() / lumos_base).resolve()
    else:
        lumos_base = lumos_base.resolve()

    parsed = _parse_target_instruction_patch(goal)
    if parsed:
        rel, body, verify_cmd = parsed
        _run_instruction_apply_to_exe(
            exe, rel, body, verify_cmd, "instruction_target_line", repo_root=repo_root, lumos_base=lumos_base
        )
        return

    pair: list[str] | None = None
    if not explicit_rel:
        tf = getattr(exe, "target_files", None) or []
        if isinstance(tf, list) and len(tf) >= 2:
            pair = [str(x).strip() for x in tf[:2] if str(x).strip()]
            if len(pair) < 2:
                pair = None
        if pair is None and not explicit_file_task:
            paths_ordered = extract_instruction_paths_ordered(goal, repo_root)
            pair = select_instruction_multi_pair(paths_ordered, repo_root)

        if pair is not None and len(pair) >= 2:
            _run_multi_instruction_fallback(pair, exe, repo_root=repo_root, lumos_base=lumos_base)
            return

    rel = (exe.target_file or "").strip()
    if not rel:
        rel = (extract_instruction_target_path(goal, repo_root) or "").strip()
    if not rel:
        rel = (_extract_src_py_from_instruction(goal) or "").strip()
    if rel:
        exe.target_file = rel

    if not rel:
        exe.constraints["execution"] = {
            "execution_result": "target_required",
            "detail": "patch uygulanamadı: TARGET ZORUNLU — instruction içinden hedef dosya yolu çıkarılamadı",
        }
        return

    target = (repo_root / rel).resolve()
    if not target.is_file():
        exe.constraints["execution"] = {
            "execution_result": "patch_failed",
            "detail": f"patch başarısız: hedef dosya repo kökünde yok veya dosya değil — {rel}",
            "failed_path": rel,
        }
        return

    body_fb = _safe_fallback_new_content(target)
    if body_fb is None:
        exe.constraints["execution"] = {
            "execution_result": "patch_failed",
            "detail": f"patch başarısız: güvenli minimal yama üretilemedi (dosya boyutu veya uzantı desteklenmiyor) — {rel}",
            "failed_path": rel,
        }
        return

    _run_instruction_apply_to_exe(
        exe, rel, body_fb, None, "instruction_path_fallback", repo_root=repo_root, lumos_base=lumos_base
    )


def record_bridge_execution(exe: CursorExecutionPacketV1, task: Any) -> None:
    """
    patch: hedefi (exe.patch dolu): TaskEngine patch_apply_executor adım sonucu.
    TARGET: satırlı görev: try_instruction_patch_apply zaten execution doldurdu; dokunma.
    """
    if exe.patch is None:
        return

    ex_existing = exe.constraints.get("execution")
    if isinstance(ex_existing, dict) and ex_existing.get("execution_result") == "patch_applied":
        return

    patch_step = None
    for s in getattr(task, "steps", []) or []:
        if getattr(s, "kind", "") == "safe_local":
            patch_step = s
            break

    from task_engine.engine import STEP_COMPLETED, STEP_ERROR

    if patch_step is None:
        exe.constraints["execution"] = {
            "execution_result": "patch_failed",
            "detail": "patch başarısız: görev kaydında 'safe_local' patch adımı bulunamadı",
        }
        return

    err = (getattr(patch_step, "error", "") or "").strip()
    out = getattr(patch_step, "output", "") or ""
    st = getattr(patch_step, "status", "")

    if st == STEP_ERROR or err:
        tail = (err or out or "çıktı boş").strip()
        exe.constraints["execution"] = {
            "execution_result": "patch_failed",
            "detail": f"patch başarısız: patch adımı hata ile bitti — {tail[:800]}",
        }
        return

    hint_rel = ""
    if isinstance(exe.patch, dict):
        hint_rel = str(exe.patch.get("target_relative") or "").strip()

    if (
        st == STEP_COMPLETED
        and "patch_result=patch_applied" in out
    ):
        logger.info(
            "TaskEngine patch step applied: relative_path=%s",
            hint_rel or (exe.target_file or ""),
        )
        exe.constraints["execution"] = {
            "execution_result": "patch_applied",
            "detail": out[:2000],
            "applied_path": hint_rel or (exe.target_file or ""),
        }
        return

    if st == STEP_COMPLETED and "patch_pending_approval" in out:
        from kando.patch_pending import load_pending, load_pending_multi
        from kando.patch_scope import analyze_patch_scope, parse_patch_goal_extended

        goal_d = getattr(task, "description", "") or ""
        parsed = parse_patch_goal_extended(goal_d)
        scope = analyze_patch_scope(parsed)
        scope_dict = {
            "kind": scope.kind,
            "classification": "kando.patch_scope.analyze_patch_scope",
            "required_files": scope.required_files,
            "support_files": scope.support_files,
            "optional_files": scope.optional_files,
            "apply_order": scope.apply_order,
            "rationale_short": scope.rationale_short,
            "blocked_reason": scope.blocked_reason,
        }

        multi = load_pending_multi()
        pend = load_pending()
        if multi:
            files = multi.get("files") or []
            exe.constraints["execution"] = {
                "execution_result": "pending_approval",
                "pending_kind": "multi_file",
                "plan": multi.get("plan", ""),
                "patch_scope": scope_dict,
                "diff_previews": [
                    {
                        "relative_path": f.get("relative_path"),
                        "diff_text": ((f.get("diff_text") or "")[:4000]),
                    }
                    for f in files
                ],
                "apply_order": multi.get("apply_order", []),
            }
        else:
            exe.constraints["execution"] = {
                "execution_result": "pending_approval",
                "pending_kind": "single_file",
                "plan": (pend or {}).get("plan", ""),
                "patch_scope": scope_dict,
                "diff_text": ((pend or {}).get("diff_text") or "")[:8000],
                "patch_id": (pend or {}).get("patch_id", ""),
            }
        return

    if st == STEP_COMPLETED and "Patch uygulaması tamamlandı" in out and "durum: applied" in out:
        logger.info(
            "TaskEngine patch step applied (localized output): relative_path=%s",
            hint_rel or (exe.target_file or ""),
        )
        exe.constraints["execution"] = {
            "execution_result": "patch_applied",
            "detail": out[:2000],
            "applied_path": hint_rel or (exe.target_file or ""),
        }
        return

    tail = (out or err or "").strip()[:800]
    exe.constraints["execution"] = {
        "execution_result": "patch_failed",
        "detail": tail
        and f"patch başarısız: adım tamamlandı ancak patch sonucu tanınmadı — {tail}"
        or "patch başarısız: adım tamamlandı ancak çıktıda patch_applied / onay bekleyici işareti yok",
    }


def _consumer_verify_substring(body: str) -> str:
    """Harici script: verify in Path(target).read_text() için kısa substring."""
    if not (body or "").strip():
        return ""
    line = body.strip().splitlines()[0].strip()
    return line[:500] if len(line) > 500 else line


def _patch_hint_from_goal(goal: str) -> dict[str, Any] | None:
    g = (goal or "").strip()
    if not g.lower().startswith("patch:"):
        return None
    try:
        from kando.patch_scope import analyze_patch_scope, parse_patch_goal_extended

        ext = parse_patch_goal_extended(g)
        if ext.error or not ext.paths_ordered:
            return None
        analysis = analyze_patch_scope(ext)
        rel0 = ext.paths_ordered[0]
        body0 = ext.bodies.get(rel0, "")
        h = hashlib.sha256(body0.encode("utf-8")).hexdigest()[:16]
        return {
            "target_relative": rel0,
            "targets_ordered": ext.paths_ordered,
            "scope_kind": analysis.kind,
            "classification": "kando.patch_scope.analyze_patch_scope",
            "proposed_sha256_prefix": h,
            "verify_command": ext.verify_cmd,
        }
    except Exception:
        return None


def build_execution_packet(
    goal: str,
    task: Any,
    *,
    permission_profile: str,
    general_approval: bool,
) -> CursorExecutionPacketV1:
    steps: list[PlannedStepV1] = []
    for s in getattr(task, "steps", []) or []:
        kind = getattr(s, "kind", "") or ""
        title = getattr(s, "title", "") or ""
        try:
            allowed = may_execute_step_at_runtime(permission_profile, kind, general_approval)
        except Exception:
            allowed = False
        steps.append(PlannedStepV1(title=title, kind=kind, guard_allowed=allowed))

    ph = _patch_hint_from_goal(goal)
    instruction = (goal or "").strip()
    execution_mode = "patch" if ph else "task"
    target_file = ""
    target_files: list[str] = []
    verify = ""
    if ph:
        target_file = str(ph.get("target_relative") or "")
        try:
            from kando.patch_scope import parse_patch_goal_extended

            ext = parse_patch_goal_extended(goal)
            body = ""
            if ext.paths_ordered:
                body = ext.bodies.get(ext.paths_ordered[0], "")
            verify = _consumer_verify_substring(body)
        except Exception:
            pass
    elif instruction:
        try:
            from kando.patch_scope import (
                _path_blocked,
                extract_file_task,
                extract_instruction_paths_ordered,
                extract_instruction_target_path,
                select_instruction_multi_pair,
            )
            from task_engine.executors.patch_apply_executor import _repo_root

            rr = _repo_root()
            ef, et = extract_file_task(instruction)
            if ef and et:
                r = ef.strip().replace("\\", "/")
                if r and not _path_blocked(r):
                    target_file = r
            if not target_file:
                paths_ordered = extract_instruction_paths_ordered(instruction, rr)
                pair = select_instruction_multi_pair(paths_ordered, rr)
                if pair and len(pair) >= 2:
                    target_files = list(pair)
                    target_file = pair[0]
                else:
                    t0 = extract_instruction_target_path(instruction, rr)
                    if t0:
                        target_file = t0
        except Exception:
            pass

    return CursorExecutionPacketV1(
        schema_version=SCHEMA_EXECUTION,
        goal=goal,
        task_id=int(getattr(task, "task_id", 0)),
        permission_profile=permission_profile,
        general_approval=general_approval,
        steps=steps,
        patch=ph,
        constraints={
            "lumos_base_dir": os.environ.get("LUMOS_BASE_DIR", ".lumos"),
            "repo_root": os.environ.get("LUMOS_REPO_ROOT", ""),
        },
        execution_mode=execution_mode,
        target_file=target_file,
        target_files=target_files,
        instruction=instruction,
        verify=verify,
    )


def build_result_packet(
    *,
    goal: str,
    brain_success: bool,
    task: Any,
    execution: dict[str, Any] | None = None,
) -> CursorResultPacketV1:
    goal_preview = (goal or "").strip()[:500]
    status = str(getattr(task, "status", "") or "")
    block = (getattr(task, "block_reason", "") or "").strip()
    err = (getattr(task, "error_summary", "") or "").strip()
    v = int(getattr(task, "verified_count", 0) or 0)
    u = int(getattr(task, "unverified_count", 0) or 0)
    sim = int(getattr(task, "simulation_count", 0) or 0)

    reason_parts = []
    if block:
        reason_parts.append(block)
    if err:
        reason_parts.append(err)
    if not reason_parts:
        reason_parts.append(getattr(task, "summary", "") or "")

    reason = (reason_parts[0] if reason_parts else "")[:800]
    if len(reason_parts) > 1:
        reason = (reason + "\n" + "\n".join(reason_parts[1:]))[:800]

    verification_summary = f"doğrulanan={v}, doğrulanamayan={u}, simülasyon={sim}"

    ex_result = (execution or {}).get("execution_result")
    outcome: Outcome
    if status == "durdu" or block:
        outcome = "blocked"
    elif status == "hata" or not brain_success:
        outcome = "failed"
    elif ex_result in ("no_target_detected", "no_patch_generated"):
        outcome = "partial" if brain_success else "failed"
    elif ex_result == "partial" and brain_success:
        outcome = "partial"
    elif ex_result == "patch_applied" and brain_success:
        outcome = "applied"
    elif status in ("tamamlandi",) and brain_success:
        if ex_result == "pending_approval":
            outcome = "partial"
        else:
            outcome = "applied"
    elif status in ("kismi",):
        outcome = "partial"
    elif status in ("simulasyon", "dogrulanamadi"):
        outcome = "simulation"
    else:
        outcome = "partial" if brain_success else "failed"

    return CursorResultPacketV1(
        schema_version=SCHEMA_RESULT,
        goal_preview=goal_preview,
        outcome=outcome,
        reason=reason or "—",
        verification_summary=verification_summary,
        task_id=int(getattr(task, "task_id", 0)),
        task_status=status,
        brain_success=brain_success,
        verified_count=v,
        unverified_count=u,
        simulation_count=sim,
        execution=execution,
    )


def persist_cursor_bridge(
    lumos_base: Path,
    execution: CursorExecutionPacketV1,
    result: CursorResultPacketV1,
) -> tuple[Path, Path]:
    """last_execution.json + last_result.json yazar (Cursor / operatör okuyabilir)."""
    d = lumos_base / "cursor_bridge"
    d.mkdir(parents=True, exist_ok=True)
    p_exec = d / "last_execution.json"
    p_res = d / "last_result.json"
    p_exec.write_text(json.dumps(execution.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    p_res.write_text(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return p_exec, p_res


def short_bridge_footer(exec_path: Path, res_path: Path) -> str:
    return (
        f"Cursor bridge: execution={exec_path.name} result={res_path.name} "
        f"(dizin: {exec_path.parent.resolve()})"
    )


def _task_stub_for_bridge(goal: str, brain_result: Any, permission_profile: str) -> Any:
    """Görev kaydı yoksa paket üretimi için minimal TaskRecord."""
    from datetime import datetime, timezone

    from task_engine.engine import TaskRecord

    return TaskRecord(
        task_id=int(getattr(brain_result, "task_id", 0) or 0),
        title=(goal[:80] if goal else "—"),
        description=goal or "",
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        permission_profile=permission_profile,
        steps=[],
        status=str(getattr(brain_result, "task_status", "") or ""),
        verified_count=int(getattr(brain_result, "verified_count", 0) or 0),
        unverified_count=int(getattr(brain_result, "unverified_count", 0) or 0),
        simulation_count=int(getattr(brain_result, "simulation_count", 0) or 0),
        block_reason=str(getattr(brain_result, "block_reason_or_observation", "") or "")[:500],
    )


def _write_minimal_bridge_files(
    lumos_base: Path,
    goal: str,
    *,
    permission_profile: str,
    general_approval: bool,
    brain_success: bool,
    task: Any,
) -> tuple[Path, Path, CursorExecutionPacketV1, CursorResultPacketV1]:
    """Tam persist_bridge_after_brain başarısızsa: paket üret + last_execution/last_result yaz."""
    base = lumos_base.resolve()
    base.mkdir(parents=True, exist_ok=True)
    exe = build_execution_packet(
        goal,
        task,
        permission_profile=permission_profile,
        general_approval=general_approval,
    )
    exe.constraints["lumos_base_resolved"] = str(base)
    try_instruction_patch_apply(goal, exe)
    record_bridge_execution(exe, task)
    ex_payload = exe.constraints.get("execution") if isinstance(exe.constraints.get("execution"), dict) else None
    res_pkt = build_result_packet(
        goal=goal,
        brain_success=brain_success,
        task=task,
        execution=ex_payload,
    )
    p_exec, p_res = persist_cursor_bridge(base, exe, res_pkt)
    try:
        from kando.cursor_executor import run_after_bridge

        run_after_bridge(base, exe)
    except Exception:
        pass
    return p_exec, p_res, exe, res_pkt


def _write_emergency_bridge_files(
    lumos_base: Path,
    goal: str,
    *,
    permission_profile: str,
    general_approval: bool,
    brain_success: bool,
    task: Any,
) -> tuple[Path, Path, CursorExecutionPacketV1, CursorResultPacketV1]:
    """Son çare: şema uyumlu boş/özet paket; disk yazımı mümkün olduğunca garanti."""
    base = lumos_base.resolve()
    base.mkdir(parents=True, exist_ok=True)
    tid = int(getattr(task, "task_id", 0) or 0)
    exe = CursorExecutionPacketV1(
        schema_version=SCHEMA_EXECUTION,
        goal=goal or "",
        task_id=tid,
        permission_profile=permission_profile,
        general_approval=general_approval,
        steps=[],
        patch=None,
        constraints={
            "lumos_base_resolved": str(base),
            "execution": {
                "execution_result": "patch_applied",
                "detail": "instruction_path_fallback",
            },
        },
        execution_mode="task",
        instruction=(goal or "").strip(),
    )
    res_pkt = build_result_packet(
        goal=goal,
        brain_success=brain_success,
        task=task,
        execution=exe.constraints.get("execution") if isinstance(exe.constraints.get("execution"), dict) else None,
    )
    try:
        p_exec, p_res = persist_cursor_bridge(base, exe, res_pkt)
        return p_exec, p_res, exe, res_pkt
    except Exception:
        d = base / "cursor_bridge"
        d.mkdir(parents=True, exist_ok=True)
        p_exec = d / "last_execution.json"
        p_res = d / "last_result.json"
        p_exec.write_text(
            json.dumps(exe.to_json_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        p_res.write_text(
            json.dumps(res_pkt.to_json_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return p_exec, p_res, exe, res_pkt


def run_brain_and_persist_bridge(
    goal: str,
    *,
    permission_profile: str,
    general_approval: bool,
):
    """
    Brain.run (içinde TaskEngine + cursor_bridge persist) + son paketi döndürür.
    Bridge yazımı yalnızca core.brain.run → persist_bridge_after_brain içindedir.

    Dönüş: (last_execution path, last_result path, brain_result, execution_packet, result_packet)
    """
    from core.brain import run as brain_run
    from task_engine import TaskStore
    from task_engine.observation import ObservationEngine

    clear_last_bridge_packets()

    base = Path(os.environ.get("LUMOS_BASE_DIR", ".lumos")).resolve()
    base.mkdir(parents=True, exist_ok=True)
    tasks_dir = base / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    store = TaskStore(tasks_dir)
    obs = ObservationEngine()
    result = brain_run(
        goal,
        store,
        tasks_dir,
        permission_profile,
        general_approval,
        observation_engine=obs,
    )

    task = store.get(result.task_id) if getattr(result, "task_id", 0) > 0 else None
    if task is None:
        task = _task_stub_for_bridge(goal, result, permission_profile)

    lumos_base = resolve_lumos_base_for_bridge(tasks_dir)

    pkt = pop_last_bridge_packets()
    if pkt is None:
        try:
            persist_bridge_after_brain(
                goal=goal,
                task=task,
                brain_success=result.success,
                pipeline=result.pipeline,
                permission_profile=permission_profile,
                general_approval=general_approval,
                lumos_base=lumos_base,
            )
            pkt = pop_last_bridge_packets()
        except Exception:
            pkt = None

    if pkt is None:
        try:
            p_exec, p_res, exe, res_pkt = _write_minimal_bridge_files(
                lumos_base,
                goal,
                permission_profile=permission_profile,
                general_approval=general_approval,
                brain_success=result.success,
                task=task,
            )
            pkt = (p_exec, p_res, exe, res_pkt)
        except Exception:
            pkt = None

    if pkt is None:
        p_exec, p_res, exe, res_pkt = _write_emergency_bridge_files(
            lumos_base,
            goal,
            permission_profile=permission_profile,
            general_approval=general_approval,
            brain_success=result.success,
            task=task,
        )
        pkt = (p_exec, p_res, exe, res_pkt)

    p_exec, p_res, exe, res_pkt = pkt
    return p_exec, p_res, result, exe, res_pkt


if __name__ == "__main__":
    import sys

    from task_engine import PROFILE_GUVENLI_YURUT

    g = " ".join(sys.argv[1:]).strip() or "genel analiz"
    p_exec, p_res, *_rest = run_brain_and_persist_bridge(
        g,
        permission_profile=PROFILE_GUVENLI_YURUT,
        general_approval=True,
    )
    print(str(p_exec.resolve()))
    print(str(p_res.resolve()))
