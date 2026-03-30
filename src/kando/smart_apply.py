from __future__ import annotations

import difflib
from pathlib import Path
import shutil
import subprocess
import sys

from kando.auto_fix import is_valid_python_output, strip_code_fence
from kando.llm_client import call_claude


def backup_file(path: Path) -> Path:
    backup = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup)
    return backup


def restore_file(backup: Path, target: Path) -> None:
    shutil.copy2(backup, target)


def compile_check(path: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "py_compile", str(path)],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0, proc.stderr.strip()


def is_reasonable_change(original: str, fixed: str) -> bool:
    diff = list(
        difflib.unified_diff(
            original.splitlines(),
            fixed.splitlines(),
            lineterm="",
        )
    )
    changes = [
        line
        for line in diff
        if (line.startswith("+") or line.startswith("-"))
        and not (line.startswith("+++") or line.startswith("---"))
    ]
    return len(changes) < 20


def needs_repair(path: Path) -> bool:
    ok, _ = compile_check(path)
    return not ok


def repair_file(path: Path, backup: Path) -> bool:
    print("REPAIR BAŞLADI")

    original = path.read_text(encoding="utf-8")

    prompt = """
Fix ONLY syntax errors in this Python file.

STRICT RULES:
- Do NOT change logic
- Do NOT remove functions
- Do NOT refactor
- ONLY fix syntax errors (missing :, indentation, etc.)
- Output raw Python ONLY (no markdown)
"""

    fixed = call_claude(prompt + "\n\n" + original)
    fixed = strip_code_fence(fixed)

    if not is_valid_python_output(fixed):
        print("REPAIR RED: geçersiz python")
        return False

    if fixed.strip() == original.strip():
        print("REPAIR: değişiklik yok")
        return False

    if not is_reasonable_change(original, fixed):
        print("REPAIR RED: aşırı değişiklik")
        return False

    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(fixed, encoding="utf-8")

    ok, err = compile_check(temp_path)
    if not ok:
        temp_path.unlink(missing_ok=True)
        print("REPAIR RED: compile fail")
        print(err)
        return False

    path.write_text(fixed, encoding="utf-8")
    temp_path.unlink(missing_ok=True)

    print("REPAIR OK")
    return True


def apply_unused_import_fix(path: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "autoflake",
            "--in-place",
            "--remove-all-unused-imports",
            "--remove-unused-variables",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return False, proc.stderr.strip() or "autoflake failed"
    return True, "unused imports temizlendi"


def route_task(task: str) -> str:
    t = task.lower()
    if "unused import" in t or "kullanılmayan import" in t or "importları kaldır" in t:
        return "unused_imports"
    return "unknown"


def run_task(file_path: str, task: str) -> dict[str, bool | str]:
    path = Path(file_path)

    if not path.is_file():
        print("DOSYA YOK")
        return {"ok": False, "mode": "", "changed": False, "message": "DOSYA YOK"}

    mode = route_task(task)
    print("MOD:", mode)

    if mode == "unknown":
        print("BU GÖREV İÇİN DETERMINISTIC UYGULAYICI YOK. DURDU.")
        return {
            "ok": False,
            "mode": mode,
            "changed": False,
            "message": "BU GÖREV İÇİN DETERMINISTIC UYGULAYICI YOK. DURDU.",
        }

    original = path.read_text(encoding="utf-8")
    backup = backup_file(path)

    try:
        if mode == "unused_imports":
            ok, msg = apply_unused_import_fix(path)
            if not ok:
                restore_file(backup, path)
                print("UYGULAMA HATASI")
                print(msg)
                return {
                    "ok": False,
                    "mode": mode,
                    "changed": False,
                    "message": msg,
                }

        changed = path.read_text(encoding="utf-8") != original
        if not changed:
            print("DEĞİŞİKLİK YOK")
            return {
                "ok": True,
                "mode": mode,
                "changed": False,
                "message": "DEĞİŞİKLİK YOK",
            }

        repaired_ok = False
        if needs_repair(path):
            print("DOSYA BOZUK → REPAIR MODE")
            success = repair_file(path, backup)
            if not success:
                restore_file(backup, path)
                print("REPAIR BAŞARISIZ → GERİ ALINDI")
                return {
                    "ok": False,
                    "mode": mode,
                    "changed": False,
                    "message": "REPAIR BAŞARISIZ → GERİ ALINDI",
                }
            repaired_ok = True

        if not repaired_ok:
            ok, err = compile_check(path)
            if not ok:
                restore_file(backup, path)
                print("COMPILE HATASI, GERİ ALINDI")
                print(err)
                return {
                    "ok": False,
                    "mode": mode,
                    "changed": False,
                    "message": err,
                }

        print("BAŞARILI")
        return {"ok": True, "mode": mode, "changed": True, "message": "BAŞARILI"}
    except Exception as e:
        restore_file(backup, path)
        print("BEKLENMEDİK HATA, GERİ ALINDI")
        print(str(e))
        return {
            "ok": False,
            "mode": mode,
            "changed": False,
            "message": str(e),
        }


if __name__ == "__main__":
    run_task(
        "src/core/runtime_state.py",
        "Remove unused imports only",
    )
