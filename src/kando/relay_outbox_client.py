"""
Relay'e JSON POST + .lumos/outbox bekleme/özet (chatgpt_agent ve local_clipboard_relay için ortak).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.client import HTTPException
from pathlib import Path
from uuid import uuid4

_DEFAULT_RELAY_PORT = 8766
_DEFAULT_WAIT_SEC = 600.0
_POLL_SEC = 0.5


@dataclass(frozen=True)
class OutboxSnapshot:
    """Correlated packets retained for classification and display without rereading."""

    execution: dict[str, object]
    result: dict[str, object]

    @property
    def succeeded(self) -> bool:
        return (
            self.result.get("outcome") == "applied"
            and self.result.get("task_status") == "tamamlandi"
            and self.result.get("brain_success") is True
        )


class RelayResultError(RuntimeError):
    """A non-completion state that must stop both interactive and watch clients."""

    def __init__(self, message: str, exit_code: int):
        super().__init__(message + " Otomatik yeniden gönderilmedi.")
        self.exit_code = exit_code


@dataclass(frozen=True)
class AgentJobSnapshot:
    """Per-job terminal record after validating the request/receipt/job chain."""

    record: dict[str, object]
    expected_task: str | None

    @property
    def succeeded(self) -> bool:
        report = self.record.get("final_report")
        if not isinstance(report, dict):
            return False
        verify = report.get("verify")
        task = report.get("task")
        return (
            self.record.get("status") == "completed"
            and self.record.get("phase") == "done"
            and self.record.get("errors") == []
            and report.get("status") == "ok"
            and report.get("errors") == []
            and isinstance(verify, dict)
            and verify.get("ok") is True
            and isinstance(task, str)
            and bool(task.strip())
            and (self.expected_task is None or task == self.expected_task)
        )


def tag_request(goal: str) -> str:
    """One identifier per explicit submission, carried by the existing goal field."""
    return f"{goal.strip()} [relay:{uuid4().hex}]"


def repo_root_from_kando_file() -> Path:
    """src/kando/*.py → depo kökü."""
    return Path(__file__).resolve().parents[2]


def outbox_paths(root: Path | None = None) -> tuple[Path, Path]:
    base = root or repo_root_from_kando_file()
    out = base / ".lumos" / "outbox"
    return out / "last_execution.json", out / "last_result.json"


def env_float(name: str, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def relay_url() -> str:
    u = (os.getenv("RELAY_URL") or "").strip()
    if u:
        return u
    port = int((os.getenv("RELAY_PORT") or str(_DEFAULT_RELAY_PORT)).strip())
    return f"http://127.0.0.1:{port}"


def post_relay(url: str, goal_text: str) -> dict[str, object] | None:
    payload = json.dumps({"goal": goal_text}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            if resp.status != 200:
                raise RuntimeError(
                    f"Relay HTTP {resp.status}. Teslim belirsiz olabilir; otomatik yeniden gönderilmedi."
                )
            body = resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        raise RuntimeError(
            f"Relay HTTP {e.code}: {body}. Teslim belirsiz olabilir; otomatik yeniden gönderilmedi."
        ) from e
    except (OSError, HTTPException) as e:
        raise RuntimeError(
            f"Relay yanıtı alınamadı ({url}): {e}. "
            "Teslim belirsiz; otomatik yeniden gönderilmedi."
        ) from e
    # Backward compatibility with the old relay's literal acknowledgement.
    if body.strip() == b"ok":
        return None
    try:
        receipt = json.loads(body)
    except (ValueError, UnicodeDecodeError) as e:
        raise RuntimeError("Relay yanıtı okunamadı; teslim belirsiz. Otomatik yeniden gönderilmedi.") from e
    if not isinstance(receipt, dict):
        raise RuntimeError("Relay yanıtı nesne değil; teslim belirsiz. Otomatik yeniden gönderilmedi.")
    return receipt


def mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return None


def outbox_bytes_mark(path: Path) -> bytes | None:
    """Content identity for a rewrite that does not advance filesystem mtime."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return hashlib.sha256(data).digest()


def _is_newer_observation(
    prev_mtime: float | None,
    cur_mtime: float | None,
    prev_mark: bytes | None,
    cur_mark: bytes | None,
) -> bool:
    if cur_mtime is None:
        return False
    if prev_mtime is None or cur_mtime > prev_mtime + 1e-6:
        return True
    # Same-tick rewrites keep st_mtime. A captured byte mark still sees them.
    # Callers that pass no mark keep the mtime-only rule, including stale files.
    return prev_mark is not None and cur_mark is not None and cur_mark != prev_mark


def expected_goal_inbox(task_text: str) -> str:
    return f"görev: {task_text.strip()}"


def _goal_matches_execution(exe: dict[str, object] | None, task_text: str) -> bool:
    if not exe:
        return False
    return exe.get("goal") == expected_goal_inbox(task_text)


def _packets_match(exe: dict[str, object], res: dict[str, object]) -> bool:
    task_id = exe.get("task_id")
    # bool compares equal to 1 in Python; neither bool nor string/float IDs qualify.
    return (
        type(task_id) is int
        and task_id > 0
        and type(res.get("task_id")) is int
        and res["task_id"] == task_id
        and res.get("goal_preview") == str(exe["goal"])[:500]
    )


def _file_version(path: Path) -> tuple[int, ...] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def load_json(path: Path) -> dict[str, object] | None:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    try:
        val = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return val if isinstance(val, dict) else None


def wait_for_new_outbox(
    prev_exec: float | None,
    prev_res: float | None,
    task_text: str,
    timeout_sec: float,
    *,
    root: Path | None = None,
    prev_exec_mark: bytes | None = None,
    prev_res_mark: bytes | None = None,
) -> OutboxSnapshot | None:
    out_exec, out_res = outbox_paths(root)
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        before = (_file_version(out_exec), _file_version(out_res))
        m_e = mtime(out_exec)
        m_r = mtime(out_res)
        if not (
            _is_newer_observation(prev_exec, m_e, prev_exec_mark, outbox_bytes_mark(out_exec))
            and _is_newer_observation(prev_res, m_r, prev_res_mark, outbox_bytes_mark(out_res))
        ):
            time.sleep(_POLL_SEC)
            continue
        exe = load_json(out_exec)
        res = load_json(out_res)
        after = (_file_version(out_exec), _file_version(out_res))
        if (
            None not in before
            and before == after
            and exe is not None
            and res is not None
            and _goal_matches_execution(exe, task_text)
            and _packets_match(exe, res)
        ):
            return OutboxSnapshot(execution=exe, result=res)
        time.sleep(_POLL_SEC)
    return None


def wait_for_relay_result(
    receipt: dict[str, object] | None,
    prev_exec: float | None,
    prev_res: float | None,
    task_text: str,
    timeout_sec: float,
    *,
    root: Path | None = None,
    prev_exec_mark: bytes | None = None,
    prev_res_mark: bytes | None = None,
) -> OutboxSnapshot | AgentJobSnapshot | None:
    if receipt is None:
        return wait_for_new_outbox(
            prev_exec,
            prev_res,
            task_text,
            timeout_sec,
            root=root,
            prev_exec_mark=prev_exec_mark,
            prev_res_mark=prev_res_mark,
        )
    if any(receipt.get(key) is True for key in (
        "requires_approval", "requires_clarification", "video_prompt_clarification",
    )):
        raise RelayResultError("PENDING: görev onay veya netleştirme bekliyor.", 7)
    if (
        receipt.get("accepted") is False
        or receipt.get("ok") is False
        or receipt.get("error")
        or receipt.get("outcome") in ("failed", "blocked", "partial", "simulation")
    ):
        raise RelayResultError("FAILED: bridge görevi reddetti veya başarısız sonuç bildirdi.", 6)
    job_id = receipt.get("job_id")
    if (
        receipt.get("accepted") is not True
        or receipt.get("mode") not in ("agent", "lumos_plan")
        or not isinstance(job_id, str)
        or re.fullmatch(r"[0-9a-f]{16}", job_id) is None
        or any(receipt.get(key) not in (None, False) for key in (
            "requires_approval", "requires_clarification", "video_prompt_clarification",
        ))
    ):
        raise RelayResultError("UNSUPPORTED: alındı kaydı için desteklenen ilişkili terminal okuyucu yok.", 8)

    expected_task = expected_goal_inbox(task_text)
    if receipt.get("mode") == "lumos_plan":
        steps = receipt.get("step_results")
        # The current planner wraps even ONE agent job in a plan. A last job_id
        # cannot certify multiple, nested, patch or agent_auto steps.
        if (
            receipt.get("execution") != "plan_completed"
            or receipt.get("outcome") != "applied"
            or not isinstance(steps, list)
            or len(steps) != 1
            or not isinstance(steps[0], dict)
            or set(steps[0]) != {"type", "job_id", "ok"}
            or steps[0].get("type") != "agent"
            or steps[0].get("ok") is not True
            or steps[0].get("job_id") != job_id
        ):
            raise RelayResultError("UNSUPPORTED: plan tek ve ilişkili bir agent adımı değil.", 8)
        normalized = receipt.get("normalized_task")
        if not isinstance(normalized, dict) or not all(
            key in normalized for key in ("mode", "raw_payload", "agent_blob")
        ):
            raise RelayResultError("UNSUPPORTED: plan alındısında özgün istek bağı yok.", 8)
        if (
            normalized.get("mode") != "agent"
            or normalized.get("raw_payload") != expected_task
            or normalized.get("agent_blob") != expected_task
        ):
            raise RelayResultError("CORRELATION_MISMATCH: plan alındısı bu isteğe ait değil.", 6)
        # build_execution_plan rewrites the worker's task to Intent/Reason.
        # The actual response wrapper echoes raw_payload/agent_blob above; do not
        # demand the original text in that rewritten terminal task.
        expected_task = None

    from kando.agent_runner import get_job_status

    outbox = outbox_paths(root)[0].parent
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            record = get_job_status(job_id, outbox)
        except (OSError, ValueError):
            record = None
        if isinstance(record, dict) and record.get("job_id") == job_id:
            if record.get("status") in ("completed", "failed"):
                return AgentJobSnapshot(record=record, expected_task=expected_task)
        time.sleep(_POLL_SEC)
    raise RelayResultError(f"PENDING: job_id={job_id} için ilişkili terminal sonuç henüz yok.", 7)


def print_summary(*, snapshot: OutboxSnapshot | AgentJobSnapshot) -> None:
    if isinstance(snapshot, AgentJobSnapshot):
        record = snapshot.record
        print("\n--- Kando agent sonucu ---")
        for key in ("job_id", "phase", "status", "errors"):
            print(f"  {key}: {record.get(key)}")
        report = record.get("final_report")
        if isinstance(report, dict):
            for key in ("status", "verify", "errors"):
                print(f"  final_report.{key}: {report.get(key)}")
        print()
        return
    res = snapshot.result
    exe = snapshot.execution

    print("\n--- Kando özeti ---")
    if res:
        for k in ("outcome", "task_status", "brain_success", "reason", "verification_summary", "goal_preview"):
            if k in res:
                print(f"  {k}: {res[k]}")

    if exe:
        goal = exe.get("goal")
        if goal is not None:
            print(f"  execution.goal: {goal}")
        steps = exe.get("steps")
        if isinstance(steps, list) and steps:
            print(f"  steps: {len(steps)} adım")
    print()


def macos_notify(title: str, message: str) -> None:
    """Kısa bildirim (başarısız olursa sessiz)."""
    try:
        import subprocess

        t = title.replace('"', "'")[:80]
        m = message.replace('"', "'")[:400]
        script = f'display notification "{m}" with title "{t}"'
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
    except Exception:
        pass
