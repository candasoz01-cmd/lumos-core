"""
Dosya odaklı yürütücü: kontrollü dosya oluşturma, toplu silme simülasyonu (yalnızca log).

Komut çalıştırma shell_executor'dadır.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kando_runtime.executor_gate import gate_blocks_execution

_DELETE_ALL_SIM_RE = re.compile(
    r"(?:tüm|tum)\s+dosyaları\s+sil|(?:delete|remove)\s+all\s+(?:files?)?",
    re.I,
)
_CREATE_FILE_RE = re.compile(
    r"(?:(?P<a>\S+\.(?:txt|md|json|py|csv|yaml|yml))\s+(?:oluştur|olustur|yarat|create)|"
    r"(?:oluştur|olustur|yarat|create)\s+(?P<b>\S+\.\w{2,16}))(?:\s|$)",
    re.I,
)
_CREATE_VERB_RE = re.compile(
    r"\b(?:oluştur|olustur|yarat|create)\b",
    re.I,
)
_PATH_TOKEN_RE = re.compile(r"\b([\w./-]+\.\w{2,16})\b")


def _file_executor_workspace(repo_root: Path) -> Path:
    """Tüm dosya oluşturma işlemleri repo kökü altında ./workspace içinde yapılır."""
    d = (repo_root / "workspace").resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _resolve_under_workspace(ws: Path, rel: str) -> Path | None:
    rel = rel.strip().replace("\\", "/").lstrip("/")
    if not rel or ".." in rel.split("/"):
        return None
    target = (ws / rel).resolve()
    try:
        target.relative_to(ws)
    except ValueError:
        return None
    return target


def _extract_create_rel_path(text: str) -> str | None:
    """TARGET: satırı, yerleşik create kalıbı veya «oluştur» + yol ipucu."""
    lines = text.strip().splitlines()
    if lines and lines[0].strip().upper().startswith("TARGET:"):
        rel = lines[0].split(":", 1)[1].strip()
        if rel:
            return rel.replace("\\", "/")
    m = _CREATE_FILE_RE.search(text)
    if m:
        name = (m.group("a") or m.group("b") or "").strip()
        if name:
            return name.replace("\\", "/")
    if _CREATE_VERB_RE.search(text):
        pm = _PATH_TOKEN_RE.search(text)
        if pm:
            return pm.group(1).replace("\\", "/")
    return None


def _log_path(repo_root: Path) -> Path:
    p = repo_root / ".lumos" / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p / "file_executor.log"


def _append_log(repo_root: Path, line: str) -> str:
    lp = _log_path(repo_root)
    ts = datetime.now(timezone.utc).isoformat()
    with lp.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] {line}\n")
    return str(lp.resolve())


def run(task_ctx: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    """
    task_ctx: text (kullanıcı komutu), out (gate çıktısı).
    """
    if task_ctx.get("mock"):
        return {
            "outcome": "applied",
            "result": "mock_ok",
        }
    text = str(task_ctx.get("text") or "").strip()
    out = task_ctx.get("out") or {}
    repo_root = repo_root.resolve()

    if gate_blocks_execution(out):
        return {
            "executed": False,
            "status": "rejected",
            "outcome_tr": "reddedildi",
            "action": "blocked_by_gate",
            "executor": "file_executor",
            "detail": "Onay veya netleştirme gerekli; dosya yürütücüsü çalıştırılmadı.",
        }

    if not text:
        return {
            "executed": False,
            "status": "skipped",
            "outcome_tr": "reddedildi",
            "action": "none",
            "executor": "file_executor",
            "detail": "Boş komut",
        }

    if _DELETE_ALL_SIM_RE.search(text):
        lp = _append_log(
            repo_root,
            "SIMULATION delete_all — gerçek silme yapılmadı; yalnızca kayıt",
        )
        return {
            "executed": True,
            "status": "simulation",
            "outcome_tr": "çalıştırıldı (simülasyon)",
            "action": "delete_all_simulation",
            "executor": "file_executor",
            "detail": f"Silme simülasyonu loga yazıldı: {lp}",
            "log_path": lp,
        }

    rel = _extract_create_rel_path(text)
    if rel and _CREATE_VERB_RE.search(text):
        ws = _file_executor_workspace(repo_root)
        target = _resolve_under_workspace(ws, rel)
        if target is None:
            return {
                "executed": False,
                "status": "rejected",
                "outcome_tr": "reddedildi",
                "action": "create_file",
                "executor": "file_executor",
                "detail": "Geçersiz hedef yolu",
            }
        body = ""
        if "içerik" in text.lower() or "icerik" in text.lower():
            im = re.search(
                r"(?:içerik|icerik)\s*[:：]\s*(.+)$", text, re.I | re.S
            )
            if im:
                body = im.group(1).strip()
        if not body:
            body = "ok\n"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        path_str = str(target)
        return {
            "executed": True,
            "status": "success",
            "outcome_tr": "başarılı",
            "action": "create_file",
            "executor": "file_executor",
            "detail": f"Dosya yazıldı: {target}",
            "path": path_str,
            "stdout": path_str,
        }

    return {
        "executed": False,
        "status": "skipped",
        "outcome_tr": "reddedildi",
        "action": "unhandled",
        "executor": "file_executor",
        "detail": "Bu dosya komutu tanınmadı",
    }
