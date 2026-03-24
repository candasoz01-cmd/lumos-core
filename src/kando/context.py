import os
import subprocess
from pathlib import Path

def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except Exception:
        return ""

def _changed_files():
    out = []
    status = run("git status --porcelain")
    if status:
        for line in status.splitlines():
            fp = line[3:].strip()
            if fp and fp.endswith(".py"):
                out.append(fp)
    return out

def _extract_defs_with_bodies(path_str):
    p = Path(path_str)
    if not p.exists():
        return []
    try:
        lines = p.read_text().splitlines()
    except Exception:
        return []
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if stripped.startswith("def ") or stripped.startswith("class "):
            indent = len(line) - len(stripped)
            head = f"{path_str}:{i+1}: {stripped}"
            body = [line]
            j = i + 1
            while j < len(lines):
                cur = lines[j]
                cur_strip = cur.lstrip()
                if cur_strip and (len(cur) - len(cur_strip)) <= indent and not cur_strip.startswith("#"):
                    break
                body.append(cur)
                if len(body) >= 80:
                    break
                j += 1
            out.append((head, "\n".join(body)))
            i = j
            continue
        i += 1
    return out

def get_changed_functions():
    out = []
    for fp in _changed_files():
        out.extend([head for head, _ in _extract_defs_with_bodies(fp)])
    return "\n".join(out)

def get_changed_snippets():
    chunks = []
    for fp in _changed_files():
        for head, body in _extract_defs_with_bodies(fp):
            chunks.append(head + "\n" + body)
    return "\n\n---\n\n".join(chunks)[:12000]

def collect_context():
    return {
        "cwd": os.getcwd(),
        "git_branch": run("git rev-parse --abbrev-ref HEAD"),
        "git_status": run("git status --short"),
        "last_commit": run("git log -1 --oneline"),
        "changed_functions": get_changed_functions(),
        "changed_snippets": get_changed_snippets(),
    }
