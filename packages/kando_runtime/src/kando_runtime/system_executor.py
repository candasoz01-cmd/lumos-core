"""
Geriye dönük birleşik yüzey: metin türüne göre file_executor veya shell_executor.

Yeni kod doğrudan file_executor / shell_executor veya task_dispatch kullanmalıdır.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from kando_runtime.file_executor import run as run_file
from kando_runtime.shell_executor import run as run_shell
from kando_runtime.task_dispatch import infer_task_type


def run(task_ctx: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    text = str(task_ctx.get("text") or "").strip()
    if infer_task_type(text) == "shell":
        return run_shell(task_ctx, repo_root=repo_root)
    return run_file(task_ctx, repo_root=repo_root)
