"""
Patch hedefi için minimum kapsam: etki analizi + sınıflandırma (tek / çok dosya / engelli).
Otomatik serbest çok dosya yok; yalnızca açıkça listelenen minimum küme.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# Çok dosya üst sınırı — aşımı blocked_scope_too_wide
MAX_PATHS_IN_SCOPE = 6

# Instruction köprüsü: açıkça listelenen yollar, en fazla 2, yalnızca src/core (bkz. instruction_path_allowed_for_multi)
INSTRUCTION_MULTI_MAX = 2

ScopeKind = Literal["single_file_safe", "multi_file_required", "blocked_scope_too_wide"]

# Instruction metnindeki repo göreli yollar (ör. src/core/foo.py) — TARGET:/patch: olmadan hedef çıkarma
_RE_INSTRUCTION_REL_PATH = re.compile(
    r"\b((?:src|tests?|test|docs|lib|pkg|internal|examples?)/[a-zA-Z0-9_.\-/]+\.(?:py|md|txt|toml|ya?ml|json|rs|go|ts|tsx|jsx|sh))\b",
    re.IGNORECASE,
)


def _looks_like_test_or_support(path: str) -> bool:
    p = (path or "").replace("\\", "/").lower()
    if "/tests/" in p or p.startswith("tests/"):
        return True
    if "test_" in p or "_test." in p or p.endswith("_test.py"):
        return True
    if "/test/" in p or "/spec/" in p:
        return True
    return False


def _path_blocked(path: str) -> str | None:
    p = (path or "").strip()
    if not p or p in (".", ".."):
        return "geçersiz yol"
    if "*" in p or "?" in p or "**" in p:
        return "glob/joker yol kabul edilmez"
    if ".." in p.split("/"):
        return "üst dizin (..) yol içinde yok"
    return None


def extract_file_task(goal: str) -> tuple[str | None, str | None]:
    """Köprü / panel: satır başı 'file:' ve 'task:' ile yapılandırılmış hedef + eylem."""
    lines = (goal or "").strip().split("\n")
    file: str | None = None
    task: str | None = None

    for line in lines:
        s = line.strip()
        low = s.lower()
        if low.startswith("görev:") or low.startswith("gorev:"):
            s = s.split(":", 1)[1].strip()
            low = s.lower()
        if low.startswith("file:"):
            file = s.split(":", 1)[1].strip()
        if low.startswith("task:"):
            task = s.split(":", 1)[1].strip()

    return file, task


def extract_instruction_target_path(text: str, repo_root: Path) -> str | None:
    """
    patch:/TARGET: olmayan görev metninden olası hedef dosya yolu (repo göreli).

    Önce diskte var olan eşleşmeler, yoksa metinde geçen ilk geçerli yol döner.
    """
    raw = (text or "").strip()
    if not raw:
        return None
    root = repo_root.resolve()
    matches = list(_RE_INSTRUCTION_REL_PATH.finditer(raw))
    if not matches:
        return None
    rels: list[str] = []
    for m in matches:
        rel = m.group(1).strip().replace("\\", "/")
        rels.append(rel)
    rels = _dedupe_preserve(rels)
    existing: list[str] = []
    missing: list[str] = []
    for rel in rels:
        if _path_blocked(rel):
            continue
        p = (root / rel).resolve()
        try:
            p.relative_to(root)
        except ValueError:
            continue
        if p.is_file():
            existing.append(rel)
        else:
            missing.append(rel)
    if existing:
        return existing[0]
    if missing:
        return missing[0]
    return None


def instruction_path_allowed_for_multi(rel: str) -> bool:
    """
    Kontrollü çok dosya modu: yalnızca src/core altı; tests/config/scripts dizinlerine dokunma.
    (src/core/config.py gibi dosya adları serbest; yol segmenti 'config' ise engellenir.)
    """
    rel = rel.replace("\\", "/").strip()
    if _path_blocked(rel):
        return False
    low = rel.lower()
    if not low.startswith("src/core/"):
        return False
    parts = [x for x in rel.split("/") if x]
    if len(parts) < 3:
        return False
    for seg in parts[2:]:
        sl = seg.lower()
        if sl in ("tests", "test", "scripts"):
            return False
        if sl == "config":
            return False
    return True


@dataclass
class ExtendedPatchParse:
    """patch: hedefi ayrıştırması (tek veya çok dosya)."""

    paths_ordered: list[str] = field(default_factory=list)
    bodies: dict[str, str] = field(default_factory=dict)
    verify_cmd: str | None = None
    error: str | None = None


@dataclass
class PatchScopeAnalysis:
    """Etki analizi + görev türü (sınıflandırma burada)."""

    kind: ScopeKind
    required_files: list[str] = field(default_factory=list)
    support_files: list[str] = field(default_factory=list)
    optional_files: list[str] = field(default_factory=list)
    apply_order: list[str] = field(default_factory=list)
    rationale_short: str = ""
    blocked_reason: str | None = None


def _dedupe_preserve(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for p in paths:
        n = p.strip()
        if not n or n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out


def extract_instruction_paths_ordered(text: str, repo_root: Path) -> list[str]:
    """Metinde geçen tüm repo göreli dosya yolları (ilk geçiş sırası, tekrarsız)."""
    raw = (text or "").strip()
    if not raw:
        return []
    root = repo_root.resolve()
    matches = list(_RE_INSTRUCTION_REL_PATH.finditer(raw))
    if not matches:
        return []
    rels: list[str] = []
    for m in matches:
        rel = m.group(1).strip().replace("\\", "/")
        if _path_blocked(rel):
            continue
        p = (root / rel).resolve()
        try:
            p.relative_to(root)
        except ValueError:
            continue
        rels.append(rel)
    return _dedupe_preserve(rels)


def select_instruction_multi_pair(ordered_paths: list[str], repo_root: Path) -> list[str] | None:
    """
    En fazla INSTRUCTION_MULTI_MAX dosya; policy + mevcut dosya.
    İki veya daha fazla uygun yol yoksa None (tek dosya akışı).
    """
    root = repo_root.resolve()
    out: list[str] = []
    for rel in ordered_paths:
        if not instruction_path_allowed_for_multi(rel):
            continue
        p = (root / rel).resolve()
        try:
            p.relative_to(root)
        except ValueError:
            continue
        if not p.is_file():
            continue
        out.append(rel)
        if len(out) >= INSTRUCTION_MULTI_MAX:
            break
    if len(out) >= 2:
        return out[:INSTRUCTION_MULTI_MAX]
    return None


def _split_verify_block(lines: list[str]) -> tuple[list[str], str | None]:
    verify_idx: int | None = None
    verify_cmd: str | None = None
    for i, line in enumerate(lines):
        u = line.strip()
        if u.upper() == "VERIFY:":
            verify_idx = i
            if i + 1 < len(lines):
                verify_cmd = lines[i + 1].strip()
            break
        if u.upper().startswith("VERIFY:") and u.upper() != "VERIFY:":
            verify_idx = i
            verify_cmd = line.split(":", 1)[1].strip()
            break
    if verify_idx is None:
        return lines, None
    return lines[:verify_idx], verify_cmd


def _parse_files_section(lines: list[str]) -> tuple[list[str], list[str]]:
    """FILES: altındaki yollar + kalan satırlar."""
    if not lines:
        return [], []
    if not lines[0].strip().upper().startswith("FILES:"):
        return [], lines
    extra: list[str] = []
    i = 1
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            break
        if s.upper().startswith("FILES:"):
            i += 1
            continue
        if s.startswith("---"):
            break
        extra.append(s)
        i += 1
    rest = lines[i:]
    return extra, rest


def _split_section_bodies(rest: list[str]) -> dict[str, str] | None:
    """--- rel/path --- ile bölünmüş içerikler."""
    text = "\n".join(rest)
    pattern = re.compile(r"^---\s+(.+?)\s+---\s*$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    if not matches:
        return None
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        rel = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end].strip("\n")
        out[rel] = chunk
    return out


def parse_patch_goal_extended(description: str) -> ExtendedPatchParse:
    """
    Biçimler:
    - Tek dosya (geriye dönük): patch: rel.txt\\n<body> [VERIFY:]
    - Çok dosya: ilk satır patch: a.txt,b.txt veya patch: a.txt + FILES:\\n b.txt
      ve --- a.txt --- / --- b.txt --- bölümleri (VERIFY öncesi).
    """
    raw = (description or "").strip()
    if not raw.lower().startswith("patch:"):
        return ExtendedPatchParse(error="patch: ile başlamalı")

    lines = raw.splitlines()
    first = lines[0].strip()
    m = re.match(r"patch:\s*(.*)$", first, re.IGNORECASE)
    if not m:
        return ExtendedPatchParse(error="patch: satırı geçersiz")
    primary_raw = (m.group(1) or "").strip()
    primary_paths = [p.strip() for p in primary_raw.split(",") if p.strip()]

    body_lines, verify_cmd = _split_verify_block(lines[1:])
    extra_paths, rest_after_files = _parse_files_section(body_lines)
    paths = _dedupe_preserve(primary_paths + extra_paths)

    if not paths:
        return ExtendedPatchParse(error="En az bir hedef yol gerekli (patch: y veya FILES:).")

    section_map = _split_section_bodies(rest_after_files)
    bodies: dict[str, str] = {}

    if section_map is not None:
        for p in paths:
            if p not in section_map:
                return ExtendedPatchParse(
                    error=f"--- {p} --- bölümü eksik (çok dosya için her hedefe bölüm gerekli).",
                )
        bodies = {p: section_map[p] for p in paths}
    else:
        plain = "\n".join(rest_after_files).strip("\n")
        if len(paths) == 1:
            bodies[paths[0]] = plain
        else:
            return ExtendedPatchParse(
                error="Birden fazla hedef var; her dosya için --- dosya/yolu --- bölümleri kullanın.",
            )

    return ExtendedPatchParse(paths_ordered=paths, bodies=bodies, verify_cmd=verify_cmd)


def analyze_patch_scope(parsed: ExtendedPatchParse) -> PatchScopeAnalysis:
    """Sınıflandırma ve etki listeleri (zorunlu / test / opsiyonel)."""
    if parsed.error:
        return PatchScopeAnalysis(
            kind="blocked_scope_too_wide",
            blocked_reason=parsed.error,
            rationale_short="Ayrıştırma hatası.",
        )

    paths = list(parsed.paths_ordered)
    apply_order = list(paths)

    for p in paths:
        br = _path_blocked(p)
        if br:
            return PatchScopeAnalysis(
                kind="blocked_scope_too_wide",
                blocked_reason=f"{p}: {br}",
                apply_order=apply_order,
                rationale_short="Yol politikası ihlali.",
            )

    if len(paths) > MAX_PATHS_IN_SCOPE:
        return PatchScopeAnalysis(
            kind="blocked_scope_too_wide",
            blocked_reason=f"En fazla {MAX_PATHS_IN_SCOPE} dosya; kapsam çok geniş.",
            apply_order=apply_order,
            rationale_short="Üst sınır aşıldı.",
        )

    support = [p for p in paths if _looks_like_test_or_support(p)]
    required = [p for p in paths if p not in support]
    if not required and support:
        required = list(paths)

    if len(paths) == 1:
        kind: ScopeKind = "single_file_safe"
        rationale = "Tek dosya; minimum kapsam."
    else:
        kind = "multi_file_required"
        rationale = (
            f"{len(paths)} dosya: policy/test/bağlı modül zinciri için minimum küme "
            "(zorunlu + gerekli test/destek ayrımı heuristik)."
        )

    return PatchScopeAnalysis(
        kind=kind,
        required_files=required,
        support_files=[p for p in support if p in paths],
        optional_files=[],
        apply_order=apply_order,
        rationale_short=rationale,
        blocked_reason=None,
    )


def parse_patch_goal_legacy(description: str) -> tuple[str, str, str | None]:
    """Eski API: tek dosyalı patch için (rel, body, verify). Çok dosyada boş."""
    ext = parse_patch_goal_extended(description)
    if ext.error:
        return "", "", None
    if len(ext.paths_ordered) != 1:
        return "", "", None
    p0 = ext.paths_ordered[0]
    body = ext.bodies.get(p0, "")
    return p0, body, ext.verify_cmd
