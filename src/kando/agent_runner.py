"""
Tek tuş agent akışı: repo tarama → hedef seçimi → file+task ile executor → verify → commit → push → rapor.
Executor katmanına yalnızca somut `file:\\n...\\ntask:\\n...` hedefi gider (no_target_detected önlenir).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

# Güvenli varsayılanlar (istek spec)
MAX_CANDIDATE_FILES = 2
PREFERRED_PREFIX = "src/core/"
SKIP_TEST_PATHS = True

# _run_executor_goal dönüşündeki execution_result için sık kullanılan üçlü (tam sözlük cursor_bridge).
# Örnek: assert result["execution_result"] in EXECUTION_RESULT_PATCH_TRIPLET
EXECUTION_RESULT_PATCH_TRIPLET = ("patch_applied", "no_change", "blocked")


def _repo_root(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.resolve()
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


def _tokenize_goal(goal: str) -> list[str]:
    g = (goal or "").lower()
    return [t for t in re.findall(r"[a-zğüşıöçĞÜŞİÖÇ]{3,}", g) if len(t) >= 3]


def _is_risky_goal(goal: str) -> str | None:
    low = (goal or "").lower()
    risky = (
        "rm -rf",
        "format c:",
        "drop database",
        ":(){",
        "mkfs",
        "dd if=",
    )
    for r in risky:
        if r in low:
            return f"risky_pattern:{r}"
    return None


def _allowed_agent_target(rel: str) -> bool:
    """Yalnızca src/core altı tek dosya; patch_scope policy ile uyumlu."""
    from kando.patch_scope import instruction_path_allowed_for_multi

    r = rel.replace("\\", "/").strip()
    return bool(r) and instruction_path_allowed_for_multi(r)


def _list_src_core_py_files(repo_root: Path, *, limit_scan: int = 400) -> list[Path]:
    core = repo_root / "src" / "core"
    if not core.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(core.rglob("*.py")):
        if SKIP_TEST_PATHS and "test" in p.name.lower():
            continue
        rel = p.relative_to(repo_root).as_posix()
        if not _allowed_agent_target(rel):
            continue
        out.append(p)
        if len(out) >= limit_scan:
            break
    return out


def _score_file_for_goal(path: Path, repo_root: Path, tokens: list[str]) -> int:
    if not tokens:
        return 0
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:24_000]
    except OSError:
        return 0
    low = text.lower()
    return sum(low.count(t) for t in tokens)


def select_target_and_task(goal: str, repo_root: Path) -> tuple[str, str, dict[str, Any]]:
    """
    Serbest metni somut (relative_path, task) çiftine çevirir — executor öncesi zorunlu adım.
    Dönüş: (rel_path, task_string, discovery_meta)
    """
    goal = (goal or "").strip()
    tokens = _tokenize_goal(goal)

    from kando.kando_core import explicit_single_lock_path

    lock_path = explicit_single_lock_path(goal)
    if lock_path:
        rel = lock_path.replace("\\", "/").strip()
        if rel and _allowed_agent_target(rel) and (repo_root / rel).is_file():
            return rel, goal, {
                "candidates_considered": 0,
                "tokens": tokens[:20],
                "explicit_target": True,
                "top_scores": [],
            }

    files = _list_src_core_py_files(repo_root)
    meta: dict[str, Any] = {"candidates_considered": len(files), "tokens": tokens[:20]}

    if not files:
        fallback = repo_root / "src" / "core" / "runtime_state.py"
        if fallback.is_file():
            rel = "src/core/runtime_state.py"
            return rel, goal or " küçük güvenli dokunuş (repo taraması boş)", meta
        return "", "repo src/core altında uygun .py bulunamadı", meta

    scored: list[tuple[int, Path]] = []
    for fp in files:
        s = _score_file_for_goal(fp, repo_root, tokens)
        scored.append((s, fp))
    scored.sort(key=lambda x: (-x[0], x[1].as_posix()))

    top = scored[: max(MAX_CANDIDATE_FILES, 1)]
    meta["top_scores"] = [
        {"path": t[1].relative_to(repo_root).as_posix(), "score": t[0]} for t in top
    ]

    best_path = top[0][1]
    rel = best_path.relative_to(repo_root).as_posix()
    task = goal if goal else f"İncele ve gerekirse minimal düzelt: {rel}"
    return rel, task, meta


def _git_cmd(repo: Path, *args: str, timeout: float = 120.0) -> tuple[int, str, str]:
    try:
        r = subprocess.run(
            ["git", *args],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (r.stdout or "") + (r.stderr or "")
        return r.returncode, out.strip(), out.strip()
    except Exception as e:
        return 1, "", str(e)[:2000]


def _filter_changed_to_explicit(goal: str, paths: list[str]) -> list[str]:
    """Görev metninde tek explicit src/...py varsa changed_files yalnızca o yol (veya [])."""
    from kando.kando_core import explicit_single_lock_path

    ex = explicit_single_lock_path(goal or "")
    if not ex:
        return paths
    exn = ex.replace("\\", "/").strip()
    out: list[str] = []
    for p in paths:
        pn = p.replace("\\", "/").strip()
        if pn == exn:
            out.append(exn)
    return list(dict.fromkeys(out))


def _apply_explicit_target_final(report: dict[str, Any], goal: str) -> None:
    from kando.kando_core import explicit_single_lock_path

    explicit_target = explicit_single_lock_path(goal or "")
    if not explicit_target:
        return
    et = explicit_target.replace("\\", "/").strip()
    report["selected_target"] = et
    cf = report.get("changed_files") or []
    report["changed_files"] = [
        f for f in cf if f.replace("\\", "/").strip() == et
    ]


def _git_uncommitted_paths(repo: Path) -> list[str]:
    """Çalışma ağacında commitlenmemiş değişen dosyalar."""
    code, out, _ = _git_cmd(repo, "diff", "--name-only")
    a = [x.strip() for x in out.splitlines() if x.strip()]
    code2, out2, _ = _git_cmd(repo, "diff", "--cached", "--name-only")
    b = [x.strip() for x in out2.splitlines() if x.strip()]
    return list(dict.fromkeys(a + b))


def _run_executor_goal(goal_multiline: str, repo_root: Path) -> dict[str, Any]:
    """
    Brain + cursor bridge; LUMOS env repo köküne ayarlı olmalı.

    ``execution_result`` köprü ``constraints.execution`` ile aynıdır (``outcome`` alanından farklıdır).
    Dar senaryolarda: ``assert result["execution_result"] in EXECUTION_RESULT_PATCH_TRIPLET``.
    """
    os.environ["LUMOS_REPO_ROOT"] = str(repo_root)
    lumos = repo_root / ".lumos"
    os.environ["LUMOS_BASE_DIR"] = str(lumos)

    from kando.cursor_bridge import run_brain_and_persist_bridge
    from task_engine import PROFILE_GUVENLI_YURUT

    _p_exec, _p_res, brain_result, exe, res_pkt = run_brain_and_persist_bridge(
        goal_multiline,
        permission_profile=PROFILE_GUVENLI_YURUT,
        general_approval=True,
    )
    ex = getattr(exe, "constraints", {}).get("execution") if exe else None
    er = (ex or {}).get("execution_result") if isinstance(ex, dict) else None
    outcome = getattr(res_pkt, "outcome", None)
    return {
        "brain_success": getattr(brain_result, "success", False),
        "execution_result": er,
        "execution_detail": (ex or {}).get("detail") if isinstance(ex, dict) else None,
        "outcome": str(outcome) if outcome is not None else None,
    }


def _verify_python_files(repo_root: Path, paths: list[str]) -> dict[str, Any]:
    from kando.patch_verify_runner import mandatory_py_compile

    results = []
    ok_all = True
    for rel in paths:
        if not rel.endswith(".py"):
            continue
        p = (repo_root / rel).resolve()
        try:
            p.relative_to(repo_root.resolve())
        except ValueError:
            ok_all = False
            results.append({"path": rel, "ok": False, "msg": "path_outside_repo"})
            continue
        ok, msg = mandatory_py_compile(p, cwd=repo_root)
        ok_all = ok_all and ok
        results.append({"path": rel, "ok": ok, "msg": msg[:1500]})
    return {"ok": ok_all, "details": results}


def _commit_files(repo_root: Path, paths: list[str], message: str) -> dict[str, Any]:
    if not paths:
        return {"ok": False, "detail": "no_files_to_commit"}
    for rel in paths:
        code, _, err = _git_cmd(repo_root, "add", "--", rel)
        if code != 0:
            return {"ok": False, "detail": f"git_add_failed:{err[:500]}"}
    code, out, err = _git_cmd(
        repo_root,
        "commit",
        "-m",
        message[:500],
        timeout=60.0,
    )
    if code != 0:
        return {"ok": False, "detail": (out or err)[:1500]}
    hcode, hout, _ = _git_cmd(repo_root, "rev-parse", "HEAD")
    return {"ok": True, "hash": hout.strip()[:40] if hcode == 0 else None, "detail": out[:800]}


def _push_repo(repo_root: Path) -> dict[str, Any]:
    code, out, err = _git_cmd(repo_root, "push", timeout=180.0)
    ok = code == 0
    return {"ok": ok, "detail": (out or err)[:2000]}


def _default_final_report() -> dict[str, Any]:
    return {
        "status": "failed",
        "selected_target": "",
        "task": "",
        "changed_files": [],
        "verify": {"ok": False, "detail": ""},
        "commit": {"ok": False, "detail": ""},
        "push": {"ok": False, "detail": ""},
        "next_focus": "",
        "errors": [],
    }


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _cursor_bridge_source_dir(repo_root: Path) -> Path:
    """
    Bridge yazımı LUMOS_BASE_DIR altındadır; outbox sync aynı kökü kullanmalı (repo_root/.lumos ile drift olmasın).
    """
    raw = (os.environ.get("LUMOS_BASE_DIR") or "").strip()
    if raw:
        base = Path(raw).expanduser()
        base = base.resolve() if base.is_absolute() else (Path.cwd() / base).resolve()
    else:
        base = (repo_root / ".lumos").resolve()
    return base / "cursor_bridge"


def _copy_cursor_bridge_snapshots_to_outbox(repo_root: Path, outbox_dir: Path) -> None:
    """`.lumos/cursor_bridge/last_*.json` → outbox (bayt birebir; json.loads/dumps yok)."""
    try:
        src_dir = _cursor_bridge_source_dir(repo_root)
        dst_dir = outbox_dir.resolve()
        dst_dir.mkdir(parents=True, exist_ok=True)
        for name in ("last_result.json", "last_execution.json"):
            src = src_dir / name
            dst = dst_dir / name
            if not src.is_file():
                continue
            data = src.read_bytes()
            tmp = dst.with_suffix(dst.suffix + ".tmp")
            tmp.write_bytes(data)
            tmp.replace(dst)
    except OSError:
        pass


@dataclass
class AgentJobState:
    job_id: str
    phase: str = "queued"
    status: str = "running"
    final_report: dict[str, Any] = field(default_factory=_default_final_report)
    errors: list[str] = field(default_factory=list)


_jobs_lock = threading.Lock()
_jobs: dict[str, AgentJobState] = {}


def run_agent_pipeline(
    goal: str,
    *,
    auto_approve_safe: bool,
    repo_root: Path | None,
    on_phase: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """
    Tam zincir: repo_scan → … → final_report.
    """
    rr = _repo_root(repo_root)
    report = _default_final_report()
    report["task"] = (goal or "").strip()

    def phase(name: str) -> None:
        if on_phase:
            on_phase(name)

    def _done() -> dict[str, Any]:
        _apply_explicit_target_final(report, goal)
        return report

    phase("repo_scan")
    risky = _is_risky_goal(goal)
    if risky:
        report["status"] = "failed"
        report["errors"] = [f"blocked:{risky}"]
        return _done()

    phase("issue_discovery")
    phase("target_selection")
    rel, task, _meta = select_target_and_task(goal, rr)
    report["selected_target"] = rel
    report["task"] = task

    if not rel or not _allowed_agent_target(rel):
        report["status"] = "failed"
        report["errors"] = ["no_safe_target_in_src_core"]
        report["next_focus"] = "src/core altında .py hedefi seçilemedi"
        return _done()

    goal_body = f"file: {rel}\ntask: {task}\n"
    if auto_approve_safe:
        os.environ["KANDO_AGENT_AUTO_APPROVE"] = "1"

    phase("task_lock")

    phase("patch_execute")
    try:
        ex_out = _run_executor_goal(goal_body, rr)
    except Exception as e:
        report["status"] = "failed"
        report["errors"] = [f"executor:{e!s}"[:2000]]
        return _done()

    if ex_out.get("execution_result") == "no_target_detected":
        report["status"] = "failed"
        report["errors"] = ["executor_returned_no_target_detected"]
        return _done()

    phase("verify")
    changed = _filter_changed_to_explicit(goal, _git_uncommitted_paths(rr))
    if not changed:
        report["status"] = "failed"
        report["errors"].append("no_worktree_changes_after_patch")
        report["next_focus"] = "Executor çıktısı git diff üretmedi"
        report["changed_files"] = []
        report["verify"] = {"ok": False, "detail": "değişen dosya yok"}
        return _done()

    report["changed_files"] = changed

    ver = _verify_python_files(rr, changed)
    report["verify"] = {
        "ok": ver["ok"],
        "detail": "; ".join(
            f"{d.get('path')}:{'ok' if d.get('ok') else d.get('msg', '')}" for d in ver["details"]
        )[:3000],
    }
    if not ver["ok"]:
        report["status"] = "partial"
        report["errors"].append("verify_failed")
        report["next_focus"] = "py_compile hatalarını gider"
        return _done()

    phase("commit")
    cm = _commit_files(rr, changed, f"agent: {task[:72]}")
    report["commit"] = {
        "ok": bool(cm.get("ok")),
        "detail": (cm.get("detail") or str(cm))[:2000],
        "hash": cm.get("hash"),
    }
    if not cm.get("ok"):
        report["status"] = "partial"
        report["errors"].append("commit_failed")
        return _done()

    # Persona offline: auto git push yok — dış gönderim açık onay + Lumos kanalı gerektirir.
    report["status"] = "ok"
    report["next_focus"] = ""
    phase("final_report")
    return _done()


def start_agent_job(
    goal: str,
    auto_approve_safe: bool,
    *,
    repo_root: Path | None,
    outbox_dir: Path,
) -> str:
    job_id = uuid.uuid4().hex[:16]
    state = AgentJobState(job_id=job_id)
    with _jobs_lock:
        _jobs[job_id] = state

    rr = _repo_root(repo_root)

    def worker() -> None:
        path_status = outbox_dir / f"agent_status_{job_id}.json"
        prev_cwd = os.getcwd()

        def on_phase(name: str) -> None:
            state.phase = name
            payload = {
                "job_id": job_id,
                "phase": name,
                "status": state.status,
                "final_report": None,
                "errors": state.errors,
            }
            try:
                _write_json(path_status, payload)
            except OSError:
                pass

        try:
            os.chdir(rr)
            fr = run_agent_pipeline(
                goal,
                auto_approve_safe=auto_approve_safe,
                repo_root=rr,
                on_phase=on_phase,
            )
            state.final_report = fr
            state.status = "completed"
            state.phase = "done"
            if fr.get("errors"):
                state.errors = list(fr["errors"])
            done_payload = {
                "job_id": job_id,
                "phase": "done",
                "status": "completed",
                "final_report": fr,
                "errors": state.errors,
            }
            _write_json(path_status, done_payload)
            last_path = outbox_dir / "agent_last.json"
            _write_json(last_path, fr)
            _copy_cursor_bridge_snapshots_to_outbox(rr, outbox_dir)
        except Exception as e:
            state.status = "failed"
            state.errors.append(str(e)[:2000])
            state.phase = "error"
            fr = _default_final_report()
            fr["status"] = "failed"
            fr["errors"] = state.errors
            state.final_report = fr
            try:
                _write_json(
                    path_status,
                    {
                        "job_id": job_id,
                        "phase": "error",
                        "status": "failed",
                        "final_report": fr,
                        "errors": state.errors,
                    },
                )
                _write_json(outbox_dir / "agent_last.json", fr)
            except OSError:
                pass
        finally:
            try:
                os.chdir(prev_cwd)
            except OSError:
                pass
            with _jobs_lock:
                _jobs[job_id] = state

    t = threading.Thread(target=worker, name=f"agent-{job_id}", daemon=True)
    t.start()
    return job_id


def get_job_status(job_id: str, outbox_dir: Path) -> dict[str, Any] | None:
    p = outbox_dir / f"agent_status_{job_id}.json"
    if not p.is_file():
        with _jobs_lock:
            st = _jobs.get(job_id)
        if st is None:
            return None
        return {
            "job_id": job_id,
            "phase": st.phase,
            "status": st.status,
            "final_report": st.final_report if st.status == "completed" else None,
            "errors": st.errors,
        }
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
