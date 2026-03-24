import subprocess
from pathlib import Path

def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except Exception:
        return ""

def get_diff():
    tracked = run("git diff --unified=3 -- src/kando")
    untracked = run("git ls-files --others --exclude-standard src/kando")
    extra = []
    if untracked:
        for fp in untracked.splitlines():
            fp = fp.strip()
            if not fp:
                continue
            try:
                txt = Path(fp).read_text()
                extra.append(f"--- UNTRACKED: {fp} ---\n{txt[:4000]}")
            except Exception:
                pass
    out = tracked
    if extra:
        out = (out + "\n\n" if out else "") + "\n\n".join(extra)
    return out

def get_changed_functions():
    files = []
    status = run("git status --porcelain src/kando")
    if status:
        for line in status.splitlines():
            fp = line[3:].strip()
            if fp and fp not in files:
                files.append(fp)
    if not files:
        return ""
    out = []
    for fp in files:
        path = Path(fp)
        if not path.exists() or path.suffix != ".py":
            continue
        try:
            txt = path.read_text().splitlines()
        except Exception:
            continue
        for i, line in enumerate(txt, 1):
            s = line.strip()
            if s.startswith("def ") or s.startswith("class "):
                out.append(f"{fp}:{i}: {s}")
    return "\n".join(out)
