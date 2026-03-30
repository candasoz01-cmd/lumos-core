import difflib
from pathlib import Path
from kando.llm_client import call_claude


def strip_code_fence(text: str) -> str:
    s = text.strip()

    if s.startswith("```python"):
        s = s[len("```python"):].strip()
    elif s.startswith("```"):
        s = s[len("```"):].strip()

    if s.endswith("```"):
        s = s[:-3].strip()

    return s


def is_valid_python_output(text: str) -> bool:
    s = text.strip()

    if len(s) < 50:
        return False

    if "```" in s:
        return False

    if "def " in s and "->" in s:
        for line in s.splitlines():
            if "def " in line and "->" in line and not line.strip().endswith(":"):
                return False

    try:
        compile(s, "<string>", "exec")
    except Exception:
        return False

    return True


def is_reasonable_change(original: str, new: str) -> bool:
    diff = list(
        difflib.unified_diff(
            original.splitlines(),
            new.splitlines(),
            lineterm="",
        )
    )

    # unified_diff: '+' / '-' satırları (--- / +++ başlıkları hariç)
    change_lines = [
        line
        for line in diff
        if (line.startswith("-") and not line.startswith("---"))
        or (line.startswith("+") and not line.startswith("+++"))
    ]

    if len(change_lines) > 20:
        return False

    return True


def auto_fix(file_path: str, task: str):
    path = Path(file_path)

    if not path.is_file():
        print("DOSYA YOK")
        return

    content = path.read_text(encoding="utf-8")

    prompt = f"""
You are an extremely strict Python refactoring engine.

Task:
{task}

CRITICAL RULES:
- ONLY remove unused imports
- NEVER change logic
- NEVER change function signatures
- NEVER delete function bodies
- NEVER leave empty or incomplete blocks
- NEVER use markdown code fences
- If unsure, return the original file unchanged
- Return ONLY raw Python code

FILE:
"""

    print("AI ÇALIŞIYOR...")
    fixed = call_claude(prompt + content)
    fixed = strip_code_fence(fixed)

    if fixed.strip() == content.strip():
        print("DEĞİŞİKLİK YOK")
        return

    if not is_valid_python_output(fixed):
        print("GEÇERSİZ PYTHON")
        return

    if not is_reasonable_change(content, fixed):
        print("AŞIRI DEĞİŞİKLİK, RED")
        return

    path.write_text(fixed, encoding="utf-8")
    print("YAZILDI")


if __name__ == "__main__":
    auto_fix(
        "src/core/runtime_state.py",
        "Remove unused imports only"
    )
