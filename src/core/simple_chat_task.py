"""
/chat → TASK kolu: basit extract_task + run_task (kısa yol).

Köprü TASK algıladıktan sonra, niyet sınıfı TASK ve extract_task doluysa
dosya yazıp yanıt döner; aksi halde mevcut gate boru hattı devam eder.
"""
from __future__ import annotations

import re
from pathlib import Path


def extract_task(intent_text: str) -> dict | None:
    """Metinden create_file benzeri görev çıkar; yoksa None."""
    text = (intent_text or "").strip()
    if not text:
        return None
    low = text.lower()
    wants_create = (
        "oluştur" in low
        or "olustur" in low
        or "yarat" in low
        or "create" in low
    )
    if not wants_create:
        return None
    m = re.search(r"\b[\w./\\-]+\.py\b", text, re.I)
    if not m:
        return None
    filename = m.group(0).replace("\\", "/").split("/")[-1]
    if not filename.endswith(".py"):
        return None
    content = "print('hello')\n"
    return {
        "action": "create_file",
        "input": {
            "filename": filename,
            "content": content,
        },
    }


def run_task(task: dict, repo_root: Path | None = None) -> str:
    """Görevi yalnız verilen çalışma klasörüne yazar.

    Köprü imzası ``run_task(task, repo_root=ROOT)`` olarak kalır. Yazılacak
    yer görevin içinden ve ``repo_root`` ile belirlenir; kişisel bir yol yok.
    """
    if repo_root is None:
        raise ValueError("repo_root gerekli")
    if not isinstance(task, dict):
        raise ValueError("görev nesne olmalı")
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise ValueError("repo_root klasör olmalı")
    raw_input = task.get("input")
    if task.get("action") != "create_file" or not isinstance(raw_input, dict):
        raise ValueError("create_file görevi gerekli")
    filename = raw_input.get("filename")
    content = raw_input.get("content")
    if not isinstance(filename, str) or not isinstance(content, str):
        raise ValueError("dosya adı ve içerik metin olmalı")
    if filename != Path(filename).name or not filename.endswith(".py") or filename in {".py"}:
        raise ValueError("dosya adı çalışma klasörü içinde tek bir .py olmalı")
    path = (root / filename).resolve()
    if path.parent != root:
        raise ValueError("dosya çalışma klasörünün dışına yazılamaz")
    path.write_text(content, encoding="utf-8")
    return "OK"
