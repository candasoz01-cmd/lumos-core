import json
import re
from pathlib import Path

def _norm_name(s: str) -> str:
    t = (s or "").strip().lower()
    t = t.replace("’", "'")
    t = t.replace("'", "")
    t = t.replace("ı", "i")
    t = t.replace("İ", "i")
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = t.replace(" ", "")

    suffixes = ["ya", "ye", "a", "e"]
    for suf in suffixes:
        if len(t) > len(suf) + 2 and t.endswith(suf):
            base = t[: -len(suf)]
            if len(base) >= 3:
                t = base
            break

    return t

class Contacts:
    def __init__(self, path: str = "config/contacts.json"):
        self.path = path

    def find_number(self, name: str) -> str | None:
        p = Path(self.path)
        if not p.exists():
            return None

        data = json.loads(p.read_text(encoding="utf-8"))

        if name in data and data.get(name):
            return data.get(name)

        want = _norm_name(name)
        if not want:
            return None

        index = {}
        for k, v in data.items():
            nk = _norm_name(k)
            if nk and v:
                index[nk] = v

        return index.get(want)
