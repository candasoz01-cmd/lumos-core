"""
Relay'e JSON POST + .lumos/outbox bekleme/özet (chatgpt_agent ve local_clipboard_relay için ortak).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

_DEFAULT_RELAY_PORT = 8766
_DEFAULT_WAIT_SEC = 600.0
_POLL_SEC = 0.5


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


def post_relay(url: str, goal_text: str) -> None:
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
                raise RuntimeError(f"Relay HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        raise RuntimeError(f"Relay HTTP {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Relay erişilemedi ({url}): {e}") from e


def mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return None


def expected_goal_inbox(task_text: str) -> str:
    return f"görev: {task_text.strip()}"


def _goal_matches_execution(exe: dict[str, object] | None, task_text: str) -> bool:
    if not exe:
        return False
    expected = expected_goal_inbox(task_text)
    g = str(exe.get("goal", "")).strip()
    if g == expected:
        return True
    return task_text.strip() in g and g.startswith("görev:")


def _both_fresher(
    prev_exec: float | None,
    prev_res: float | None,
    m_e: float | None,
    m_r: float | None,
) -> bool:
    if m_e is None or m_r is None:
        return False
    ok_e = prev_exec is None or m_e > prev_exec + 1e-6
    ok_r = prev_res is None or m_r > prev_res + 1e-6
    return ok_e and ok_r


def load_json(path: Path) -> dict[str, object] | None:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
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
) -> bool:
    out_exec, out_res = outbox_paths(root)
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        m_e = mtime(out_exec)
        m_r = mtime(out_res)
        if not _both_fresher(prev_exec, prev_res, m_e, m_r):
            time.sleep(_POLL_SEC)
            continue
        exe = load_json(out_exec)
        if _goal_matches_execution(exe, task_text):
            return True
        time.sleep(_POLL_SEC)
    return False


def print_summary(*, root: Path | None = None) -> None:
    out_exec, out_res = outbox_paths(root)
    res = load_json(out_res)
    exe = load_json(out_exec)

    print("\n--- Kando özeti ---")
    if res:
        for k in ("outcome", "task_status", "brain_success", "reason", "verification_summary", "goal_preview"):
            if k in res:
                print(f"  {k}: {res[k]}")
    else:
        print(f"  (okunamadı: {out_res})")

    if exe:
        goal = exe.get("goal")
        if goal is not None:
            print(f"  execution.goal: {goal}")
        steps = exe.get("steps")
        if isinstance(steps, list) and steps:
            print(f"  steps: {len(steps)} adım")
    else:
        print(f"  (okunamadı veya yok: {out_exec})")
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
