#!/usr/bin/env python3
"""Lumos yayın kapısı — iki bağımsız katman, fail-closed.

Katman 1 — Public Release Gate: public yüzeye gömülü belge gövdesi taşıyan her
dosya, `config/publication/public_release_manifest.json` içinde içerik hash'i
eşleşen açık bir kayıt olmadan yayın hattına giremez. Varsayılan durum
PRIVATE_NOT_APPROVED'dır.

Katman 2 — Sensitive Content Boundary: Katman 1'den bağımsız tarama. Private
kaynak izleri, sınıflandırma işaretleri ve secret desenleri public yüzeyde
bulunursa işlem durur. Secret bulgusu hiçbir kayıtla aklanamaz.

Bilinçli tasarım sınırları (gevşetme değişikliği kurucu onayı ister):
- Ortam değişkeni OKUNMAZ; skip/force benzeri bypass bayrağı YOKTUR.
- Bulgu raporu içerik alıntılamaz; yalnız dosya, satır ve kural kimliği verir.
- Şüpheli durumda çıkış kodu sıfır olmaz (kontrollü false positive tercih edilir).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CONFIG = REPO_ROOT / "config" / "publication" / "gate_config.json"

BLOCK_PREFIX = "BLOCKED_PUBLICATION_REVIEW_REQUIRED"

TEXT_EXTENSIONS = {
    ".astro", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".svelte", ".vue",
    ".html", ".htm", ".css", ".md", ".mdx", ".txt", ".json", ".xml", ".svg",
    ".yml", ".yaml", ".toml",
}

EXCLUDED_DIR_NAMES = {"node_modules", "dist", ".astro", ".git", "__pycache__"}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class Finding:
    def __init__(self, layer: str, rule: str, path: str, line: int, missing: str, required: str):
        self.layer = layer
        self.rule = rule
        self.path = path
        self.line = line
        self.missing = missing
        self.required = required

    def report_line(self, surface: str) -> str:
        return (
            f"{BLOCK_PREFIX} | katman={self.layer} | kural={self.rule} | "
            f"kaynak={self.path}:{self.line} | hedef_yuzey={surface} | "
            f"eksik={self.missing} | gereken={self.required}"
        )


def iter_surface_files(root: Path, surfaces: list[str]) -> list[Path]:
    files: list[Path] = []
    for surface in surfaces:
        base = root / surface
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if any(part in EXCLUDED_DIR_NAMES for part in path.relative_to(root).parts):
                continue
            if path.suffix.lower() in TEXT_EXTENSIONS:
                files.append(path)
    return files


def detect_embedded_document_body(text: str, cfg: dict) -> list[int]:
    """D1: kod dosyası içine tek parça gömülmüş markdown belge gövdesi.

    Sızıntı sınıfının yapısal izi: kaçışlı satır sonları (\\n) ile tek satıra
    yazılmış, başlık/tablo taşıyan büyük string sabiti.
    """
    min_chars = int(cfg.get("min_embedded_chars", 1500))
    hits: list[int] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if len(line) < min_chars:
            continue
        heading_marks = line.count("\\n#") + line.count("\\n\\n#")
        table_marks = line.count("\\n|")
        if heading_marks >= 2 or table_marks >= 5:
            hits.append(idx)
            continue
    body_const = re.compile(r"\b(BODY|DOC|MARKDOWN|CONTENT)\s*=\s*([\"'`]).{800,}", re.IGNORECASE)
    for idx, line in enumerate(text.splitlines(), start=1):
        if body_const.search(line) and ("\\n" in line) and idx not in hits:
            hits.append(idx)
    return sorted(hits)


def detect_pattern_hits(text: str, patterns: list[str]) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    compiled = [(p, re.compile(p)) for p in patterns]
    for idx, line in enumerate(text.splitlines(), start=1):
        for raw, rx in compiled:
            if rx.search(line):
                hits.append((idx, raw))
    return hits


def manifest_entry_for(manifest: dict, rel_path: str) -> dict | None:
    for entry in manifest.get("entries", []):
        if entry.get("path") == rel_path:
            return entry
    return None


def check_layer1(rel_path: str, file_path: Path, hits: list[int], manifest: dict) -> list[Finding]:
    findings: list[Finding] = []
    entry = manifest_entry_for(manifest, rel_path)
    line = hits[0]
    if entry is None:
        findings.append(Finding(
            "1-public-release-gate", "embedded-document-body", rel_path, line,
            "public_release manifest kaydı yok (varsayılan: PRIVATE_NOT_APPROVED)",
            "kurucudan ayrı yayın onayı + manifest kaydı (status, sha256, approved_by, approved_date)",
        ))
        return findings
    actual_sha = sha256_of(file_path)
    if entry.get("content_sha256") != actual_sha:
        findings.append(Finding(
            "1-public-release-gate", "content-hash-drift", rel_path, line,
            "manifest kaydındaki content_sha256 mevcut içerikle eşleşmiyor",
            "içerik değişikliği için kurucudan yeniden yayın onayı + manifest güncellemesi",
        ))
        return findings
    status = entry.get("status")
    if status == "approved":
        if entry.get("public_release_approved") is True and entry.get("approved_by") and entry.get("approved_date"):
            return findings
        findings.append(Finding(
            "1-public-release-gate", "approval-metadata-incomplete", rel_path, line,
            "approved kaydında public_release_approved/approved_by/approved_date eksik",
            "eksik onay metadata'sının kurucu tarafından tamamlanması",
        ))
        return findings
    if status == "legacy_baseline_review_required":
        # Halihazırda yayında olan eski içerik: hash sabitlenmiştir, kurucu
        # incelemesi bekler; içerik değişirse yukarıdaki hash kontrolü durdurur.
        return findings
    findings.append(Finding(
        "1-public-release-gate", "unknown-status", rel_path, line,
        f"tanınmayan manifest status değeri: {status!r}",
        "status=approved (tam metadata) veya legacy_baseline_review_required",
    ))
    return findings


def baseline_entry_for(baseline: dict, rel_path: str) -> dict | None:
    for entry in baseline.get("entries", []):
        if entry.get("path") == rel_path:
            return entry
    return None


def check_layer2(rel_path: str, file_path: Path, text: str, cfg: dict, baseline: dict) -> list[Finding]:
    findings: list[Finding] = []

    for line, pattern in detect_pattern_hits(text, cfg.get("secret_patterns", [])):
        findings.append(Finding(
            "2-sensitive-content-boundary", "secret-material", rel_path, line,
            "secret deseni public yüzeyde (hiçbir kayıtla aklanamaz)",
            "secret'ın kaldırılması ve rotasyonu; baseline ile geçilemez",
        ))

    sensitive_hits: list[tuple[int, str, str]] = []
    for line, pattern in detect_pattern_hits(text, cfg.get("private_source_patterns", [])):
        sensitive_hits.append((line, "private-source-reference", pattern))
    for line, pattern in detect_pattern_hits(text, cfg.get("classification_patterns", [])):
        sensitive_hits.append((line, "classification-marker", pattern))

    if not sensitive_hits:
        return findings

    entry = baseline_entry_for(baseline, rel_path)
    if entry is None or entry.get("content_sha256") != sha256_of(file_path):
        for line, rule, _pattern in sensitive_hits:
            findings.append(Finding(
                "2-sensitive-content-boundary", rule, rel_path, line,
                "sensitive baseline kaydı yok veya content_sha256 eşleşmiyor",
                "kurucu incelemesi + hash sabitlenmiş baseline kaydı (ayrı ikinci onay)",
            ))
    return findings


def validate_registries(manifest: dict, baseline: dict, root: Path) -> list[str]:
    """Kayıt → repo yönünde türetme kontrolü: ölü veya bayat kayıt bırakma."""
    problems: list[str] = []
    for name, registry in (("manifest", manifest), ("baseline", baseline)):
        for entry in registry.get("entries", []):
            rel = entry.get("path", "")
            target = root / rel
            if not target.is_file():
                problems.append(f"{name} kaydı repo'da olmayan dosyayı gösteriyor: {rel}")
                continue
            if entry.get("content_sha256") != sha256_of(target):
                problems.append(f"{name} kaydı bayat (hash uyuşmuyor): {rel}")
    return problems


def run_gate(root: Path, config_path: Path) -> tuple[int, list[str]]:
    cfg = load_json(config_path)
    manifest = load_json(root / cfg["public_release_manifest"])
    baseline = load_json(root / cfg["sensitive_boundary_baseline"])
    surface_label = cfg.get(
        "surface_label", "public web (production + preview + public repo/PR)")

    lines: list[str] = []
    findings: list[Finding] = []

    for file_path in iter_surface_files(root, cfg["public_surfaces"]):
        rel_path = file_path.relative_to(root).as_posix()
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        d1_hits = detect_embedded_document_body(text, cfg)
        if d1_hits:
            findings.extend(check_layer1(rel_path, file_path, d1_hits, manifest))
        findings.extend(check_layer2(rel_path, file_path, text, cfg, baseline))

    registry_problems = validate_registries(manifest, baseline, root)

    for finding in findings:
        lines.append(finding.report_line(surface_label))
    for problem in registry_problems:
        lines.append(f"{BLOCK_PREFIX} | katman=registry | {problem}")

    if lines:
        lines.append(
            f"SONUC: {len(findings) + len(registry_problems)} bulgu — yayın hattı DURDU (fail-closed).")
        return 1, lines
    lines.append("SONUC: 0 bulgu — yayın kapısı geçildi.")
    return 0, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lumos yayın kapısı (fail-closed; bypass bayrağı yoktur)")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG,
                        help="gate_config.json yolu")
    parser.add_argument("--root", type=Path, default=REPO_ROOT,
                        help="taranacak repo kökü")
    parser.add_argument("--hash", type=Path, default=None, metavar="DOSYA",
                        help="tek dosyanın sha256 değerini yazdır (manifest kaydı hazırlamak için)")
    args = parser.parse_args(argv)

    if args.hash is not None:
        print(sha256_of(args.hash))
        return 0

    exit_code, lines = run_gate(args.root.resolve(), args.config)
    for line in lines:
        print(line)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
