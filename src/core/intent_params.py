"""Minimal parameter extraction for deterministic intents.

Extracts simple parameters from the same user input when the intent is known.
No filesystem or tools; intent routing only.
"""
from __future__ import annotations

import re


# Folder name blacklist: do not treat these as extracted folder (they are part of the phrase)
_FOLDER_BLACKLIST = frozenset(
    s.lower()
    for s in (
        "dosyalari",
        "dosyaları",
        "klasor",
        "klasör",
        "klasördeki",
        "folder",
        "the",
        "in",
        "listele",
    )
)


def extract_intent_params(intent: str, raw: str) -> dict[str, str]:
    """
    Extract parameters for a known deterministic intent from the raw user message.

    - list_files: tries to extract "folder" from patterns like
      "WORK_2026 klasörünü listele", "work_2026 listele", "lumos-core dosyaları listele".
    - unlock, lock, exit: no params; returns {}.

    Returns a dict of param name -> value (e.g. {"folder": "WORK_2026"}).
    """
    if not intent or not (raw or "").strip():
        return {}
    t = (raw or "").strip()
    low = t.lower()

    if intent == "list_files":
        folder = _extract_list_files_folder(low, t)
        if folder:
            return {"folder": folder}
        return {}
    if intent in ("unlock", "lock", "exit"):
        return {}
    return {}


def _extract_list_files_folder(lower_text: str, original: str) -> str:
    """
    Extract folder/path for list_files intent from message.
    Uses simple regexes; returns empty string if none or blacklisted.
    """
    # Order: more specific first so "dosyaları listele" is not parsed as folder "dosyaları"
    # 1) "X klasörünü listele" / "X klasörü listele" / "X klasördeki ... listele"
    m = re.search(
        r"^([\w\-\.]+)\s+klas[o\u00f6]r(?:\w*|deki)?\s*(?:dosyalar[\u0131i]\s*)?listele",
        lower_text,
        re.IGNORECASE,
    )
    if m:
        cand = (m.group(1) or "").strip()
        if cand and cand.lower() not in _FOLDER_BLACKLIST:
            return original[m.start(1) : m.end(1)].strip()

    # 2) "X dosyaları listele" (X = folder name, e.g. lumos-core)
    m = re.search(r"^([\w\-\.]+)\s+dosyalar[\u0131i]\s*listele", lower_text, re.IGNORECASE)
    if m:
        cand = (m.group(1) or "").strip()
        if cand and cand.lower() not in _FOLDER_BLACKLIST:
            return original[m.start(1) : m.end(1)].strip()

    # 3) "X listele" (single token before listele)
    m = re.search(r"^([\w\-\.]+)\s+listele\s*$", lower_text, re.IGNORECASE)
    if m:
        cand = (m.group(1) or "").strip()
        if cand and cand.lower() not in _FOLDER_BLACKLIST:
            return original[m.start(1) : m.end(1)].strip()

    return ""
