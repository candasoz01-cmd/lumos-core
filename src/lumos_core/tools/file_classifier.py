from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Set

@dataclass
class ClassifiedFile:
    path: str
    category: str

KEYWORDS: Dict[str, List[str]] = {
    "sozlesme": ["sozlesme", "contract", "mukavele", "kira", "protokol"],
    "dilekce": ["dilekce", "petition", "arzuhal", "dava", "cevap"],
    "karar": ["karar", "decision", "ilam", "yargitay", "danistay", "emsal"],
    "icra": ["icra", "haciz", "takip", "tebligat", "muhabere"],
    "not": ["not", "note", "taslak", "draft"],
}

DEFAULT_EXTS: Set[str] = {".pdf", ".docx", ".doc", ".txt"}

def classify_filename(name: str) -> str:
    lower = name.lower()
    for cat, words in KEYWORDS.items():
        for w in words:
            if w in lower:
                return cat
    return "diger"

def scan_folder(folder: str, exts: Optional[Set[str]] = None) -> List[ClassifiedFile]:
    p = Path(folder).expanduser().resolve()
    if not p.exists() or not p.is_dir():
        raise FileNotFoundError(f"Klasör bulunamadı: {p}")

    use_exts = exts or DEFAULT_EXTS
    results: List[ClassifiedFile] = []

    for f in p.rglob("*"):
        if f.is_file():
            if f.suffix.lower() in use_exts:
                results.append(ClassifiedFile(path=str(f), category=classify_filename(f.name)))

    return results
