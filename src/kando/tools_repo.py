import re
import shutil
import subprocess


def summarize_hits(lines: list[str]) -> str:
    files = {}
    for line in lines:
        path = line.split(":")[0]
        files.setdefault(path, 0)
        files[path] += 1

    out = []
    for path, count in files.items():
        out.append(f"- {path} ({count} kullanım)")

    return "\n".join(out)


def repo_search(query: str) -> str:
    try:
        q = query.strip()
        tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", q)
        if not tokens:
            return "Sonuç bulunamadı"

        keywords = [t for t in tokens if t.lower() not in {
            "nerede", "kullaniliyor", "kullanılıyor", "hangi", "dosyada",
            "repo", "kod", "fonksiyon", "class", "import",
        }]
        needle = keywords[0] if keywords else tokens[0]

        if shutil.which("rg"):
            cmd = [
                "rg", "-n", "-S", needle, "src",
                "--glob", "!*.pyc",
                "--glob", "!*egg-info*",
                "--glob", "!__pycache__",
            ]
        else:
            cmd = [
                "grep", "-Rni",
                "--exclude=*.pyc",
                "--exclude-dir=__pycache__",
                "--exclude-dir=*egg-info*",
                needle, "src",
            ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        out = (result.stdout or "").strip()
        if not out:
            return "Sonuç bulunamadı"

        lines = []
        for line in out.splitlines():
            if "egg-info" in line:
                continue
            lines.append(line)

        return summarize_hits(lines)
    except Exception as e:
        return f"Hata: {e}"
