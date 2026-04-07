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


def run_task(_task: dict, repo_root: Path | None = None) -> str:
    """repo_root şu an kullanılmıyor; köprü imzasıyla uyum için bırakıldı."""
    base = Path("/Users/candasoz/WORK_2026/lumos-core")
    path = base / "test.py"
    path.write_text("print('hello')", encoding="utf-8")
    return "OK"
