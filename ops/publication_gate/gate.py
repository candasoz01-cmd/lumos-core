#!/usr/bin/env python3
"""Lumos yayın kapısı — iki bağımsız katman, fail-closed.

Katman 1 — Public Release Gate: public yüzeye gömülü belge gövdesi taşıyan her
dosya, `config/publication/public_release_manifest.json` içinde içerik hash'i
eşleşen VE kurucunun SSH imzasıyla doğrulanan açık bir kayıt olmadan yayın
hattına giremez. Varsayılan durum PRIVATE_NOT_APPROVED'dır; "inceleme
bekliyor" türü ara statü yoktur.

Katman 2 — Sensitive Content Boundary: Katman 1'den bağımsız tarama. Private
kaynak izleri ve sınıflandırma işaretleri ancak yine kurucu imzalı, hash'e
bağlı ayrı bir baseline kaydıyla geçer. Secret bulgusu hiçbir kayıtla
aklanamaz.

İnsan onayı doğrulaması: manifest/baseline kaydındaki düz metin alanlar tek
başına onay DEĞİLDİR — ajan da yazabilir. Onay, kurucunun private anahtarıyla
üretilmiş SSH imzasıdır (`ssh-keygen -Y sign`); kapı bunu repodaki
`allowed_signers` public anahtarlarıyla doğrular. İmza yükü katman + dosya
yolu + içerik sha256 + tarihe bağlıdır: içerik değişirse imza geçersizleşir,
bir katmanın imzası diğer katmanda kullanılamaz.

Bilinçli tasarım sınırları (gevşetme değişikliği kurucu onayı ister):
- Ortam değişkeni OKUNMAZ; skip/force benzeri bypass bayrağı YOKTUR.
- Tarama uzantı allowlist'i KULLANMAZ: medya (görüntü/font/ses-video) dışında
  her dosya kapsanır; metne çözülemeyen dosya atlanmaz, BULGUDUR.
- ssh-keygen yoksa veya imza çözülemiyorsa doğrulama BAŞARISIZ sayılır.
- Bulgu raporu içerik alıntılamaz; yalnız dosya, satır ve kural kimliği verir.
- Şüpheli durumda çıkış kodu sıfır olmaz (kontrollü false positive tercih edilir).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CONFIG = REPO_ROOT / "config" / "publication" / "gate_config.json"

BLOCK_PREFIX = "BLOCKED_PUBLICATION_REVIEW_REQUIRED"
SIGN_NAMESPACE = "lumos-publication"
LAYER1_ID = "layer1-public-release"
LAYER2_ID = "layer2-sensitive-boundary"

# Yayın onayı için GEÇERSİZ kılınan imza anahtarları. 2026-09-18: kurucunun
# genel amaçlı GitHub anahtarı geliştirme ortamında ajan erişimine açık
# bulundu; ajan erişebilen anahtar insan onayı kanıtlayamaz. Bu listeden
# çıkarma = güven kökü kararı, yalnız kurucuyla.
REVOKED_SIGNER_FINGERPRINTS = {
    "SHA256:fCmMHAEP2k865znMPpzZdBZEdEVSLQVST9WT/hHhNHc",
}

# Tarama VARSAYILAN OLARAK her dosyayı kapsar (uzantı allowlist'i yok — .log,
# .csv, .pem, uzantısız dosyalar dahil). Yalnız görüntü/font/ses-video medyası
# atlanır; belge taşıyabilen hiçbir tür (pdf, zip, ...) bu listeye eklenmez.
KNOWN_BINARY_MEDIA = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".icns", ".bmp", ".avif",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp3", ".mp4", ".webm", ".ogg", ".wav", ".mov", ".heic",
}

EXCLUDED_DIR_NAMES = {"node_modules", "dist", ".astro", ".git", "__pycache__"}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def signature_payload(layer_id: str, rel_path: str, content_sha256: str,
                      approved_date: str) -> bytes:
    return f"{layer_id}\n{rel_path}\n{content_sha256}\n{approved_date}\n".encode()


def verify_founder_signature(allowed_signers: Path, layer_id: str, entry: dict) -> bool:
    """Kaydın kurucu imzasını doğrula. Her hata = geçersiz (fail-closed)."""
    approved_by = entry.get("approved_by")
    approved_date = entry.get("approved_date")
    signature = entry.get("approval_signature")
    content_sha256 = entry.get("content_sha256")
    rel_path = entry.get("path")
    if not (approved_by and approved_date and signature and content_sha256 and rel_path):
        return False
    if not allowed_signers.is_file():
        return False
    payload = signature_payload(layer_id, rel_path, content_sha256, approved_date)
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".sig", delete=False) as handle:
            handle.write(signature)
            sig_path = handle.name
        result = subprocess.run(
            ["ssh-keygen", "-Y", "verify", "-f", str(allowed_signers),
             "-I", approved_by, "-n", SIGN_NAMESPACE, "-s", sig_path],
            input=payload, capture_output=True, timeout=30, check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
    finally:
        try:
            Path(sig_path).unlink()
        except (OSError, UnboundLocalError):
            pass


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
            if path.suffix.lower() in KNOWN_BINARY_MEDIA:
                continue
            files.append(path)
    return files


def decode_surface_text(data: bytes) -> str | None:
    """Public yüzey dosyasını metne çöz; çözülemeyen içerik None döner.

    UTF-8 ve UTF-16 (BOM'lu/BOM'suz) denenir. Kontrol karakteri (tab/newline
    dışında) içeren çözümler güvenilir taranamaz sayılır — çözememek geçiş
    değil, bulgudur (fail-closed).
    """
    control_chars = {c for c in range(0x20) if c not in (0x09, 0x0A, 0x0D)}
    control_chars |= set(range(0x7F, 0xA0))
    for encoding in ("utf-8", "utf-16"):
        try:
            text = data.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
        if any(ord(ch) in control_chars for ch in text):
            return None
        return text
    return None


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


def detect_pattern_hits(
    text: str, patterns: list[str], *, ignore_case: bool = False
) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    flags = re.IGNORECASE if ignore_case else 0
    compiled = [(p, re.compile(p, flags)) for p in patterns]
    for idx, line in enumerate(text.splitlines(), start=1):
        for raw, rx in compiled:
            if rx.search(line):
                hits.append((idx, raw))
    return hits


def entry_for(registry: dict, rel_path: str) -> dict | None:
    for entry in registry.get("entries", []):
        if entry.get("path") == rel_path:
            return entry
    return None


def check_layer1(rel_path: str, file_path: Path, hits: list[int], manifest: dict,
                 allowed_signers: Path) -> list[Finding]:
    findings: list[Finding] = []
    entry = entry_for(manifest, rel_path)
    line = hits[0]
    if entry is None:
        findings.append(Finding(
            "1-public-release-gate", "embedded-document-body", rel_path, line,
            "public_release manifest kaydı yok (varsayılan: PRIVATE_NOT_APPROVED)",
            "kurucudan ayrı yayın onayı: imzalı manifest kaydı (bkz. docs/PUBLICATION_GATE.md)",
        ))
        return findings
    if entry.get("content_sha256") != sha256_of(file_path):
        findings.append(Finding(
            "1-public-release-gate", "content-hash-drift", rel_path, line,
            "manifest kaydındaki content_sha256 mevcut içerikle eşleşmiyor",
            "içerik değişikliği için kurucudan yeni imzalı onay",
        ))
        return findings
    if entry.get("status") != "approved" or entry.get("public_release_approved") is not True:
        findings.append(Finding(
            "1-public-release-gate", "not-approved", rel_path, line,
            f"tek geçerli statü 'approved' + public_release_approved=true; bulunan: {entry.get('status')!r}",
            "kurucudan imzalı yayın onayı — ara/bekleyen statü yayın izni değildir",
        ))
        return findings
    if not verify_founder_signature(allowed_signers, LAYER1_ID, entry):
        findings.append(Finding(
            "1-public-release-gate", "approval-signature-invalid", rel_path, line,
            "kurucu imzası yok, çözülemedi veya allowed_signers ile doğrulanamadı",
            "kurucunun ssh-keygen -Y sign ile ürettiği, içerik hash'ine bağlı imza",
        ))
    return findings


def check_layer2(rel_path: str, file_path: Path, text: str, cfg: dict, baseline: dict,
                 allowed_signers: Path) -> list[Finding]:
    findings: list[Finding] = []

    for line, _pattern in detect_pattern_hits(text, cfg.get("secret_patterns", [])):
        findings.append(Finding(
            "2-sensitive-content-boundary", "secret-material", rel_path, line,
            "secret deseni public yüzeyde (hiçbir kayıtla aklanamaz)",
            "secret'ın kaldırılması ve rotasyonu; baseline ile geçilemez",
        ))

    sensitive_hits: list[tuple[int, str]] = []
    # GitHub owner/repo names are case-insensitive; matching must be too.
    for line, _pattern in detect_pattern_hits(
        text, cfg.get("private_source_patterns", []), ignore_case=True
    ):
        sensitive_hits.append((line, "private-source-reference"))
    for line, _pattern in detect_pattern_hits(text, cfg.get("classification_patterns", [])):
        sensitive_hits.append((line, "classification-marker"))

    if not sensitive_hits:
        return findings

    entry = entry_for(baseline, rel_path)
    entry_valid = (
        entry is not None
        and entry.get("content_sha256") == sha256_of(file_path)
        and verify_founder_signature(allowed_signers, LAYER2_ID, entry)
    )
    if not entry_valid:
        for line, rule in sensitive_hits:
            findings.append(Finding(
                "2-sensitive-content-boundary", rule, rel_path, line,
                "kurucu imzalı, hash'i eşleşen baseline kaydı yok",
                "kurucudan ayrı ikinci onay: imzalı baseline kaydı (bkz. docs/PUBLICATION_GATE.md)",
            ))
    return findings


SSH_KEY_TYPE_PREFIXES = ("ssh-", "ecdsa-", "sk-")


def enrolled_signer_lines(allowed_signers: Path) -> list[str]:
    """allowed_signers'taki kayıt satırları (yorum/boş hariç, olduğu gibi)."""
    if not allowed_signers.is_file():
        return []
    lines: list[str] = []
    for line in allowed_signers.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def _fingerprint(pubkey_line: str) -> str | None:
    try:
        result = subprocess.run(
            ["ssh-keygen", "-lf", "-"],
            input=(pubkey_line + "\n").encode(),
            capture_output=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    parts = result.stdout.decode(errors="replace").split()
    if len(parts) >= 2 and parts[1].startswith("SHA256:"):
        return parts[1]
    return None


def validate_signer_roots(allowed_signers: Path) -> list[str]:
    """Kayıtlı imza köklerini SATIR BAZINDA iptal listesine karşı denetle.

    allowed_signers grameri `principal [opsiyonlar] tip blob`dur; opsiyon alanı
    anahtarı parser'dan gizleyebildiği için her satırda tip-önekli TÜM aday
    çiftler ayrı ayrı fingerprint'lenir. Hiçbir aday çözülemeyen satır ve
    ssh-keygen hatası bulgudur — sessiz atlama yoktur (fail-closed).
    """
    problems: list[str] = []
    for lineno, line in enumerate(
            (allowed_signers.read_text(encoding="utf-8").splitlines()
             if allowed_signers.is_file() else []), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        fingerprints: list[str] = []
        for idx in range(1, len(parts) - 1):
            if parts[idx].startswith(SSH_KEY_TYPE_PREFIXES):
                fingerprint = _fingerprint(f"{parts[idx]} {parts[idx + 1]}")
                if fingerprint:
                    fingerprints.append(fingerprint)
        if not fingerprints:
            problems.append(
                f"allowed_signers satır {lineno}: anahtar çözümlenemedi; "
                "iptal denetimi yapılamıyor (fail-closed)")
            continue
        for fingerprint in fingerprints:
            if fingerprint in REVOKED_SIGNER_FINGERPRINTS:
                problems.append(
                    "iptal edilmiş imza anahtarı allowed_signers'a kayıtlı: "
                    f"{fingerprint} (satır {lineno})")
    return problems


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
    allowed_signers = root / cfg["allowed_signers"]
    surface_label = cfg.get(
        "surface_label", "public web (production + preview + public repo/PR)")

    lines: list[str] = []
    findings: list[Finding] = []

    for file_path in iter_surface_files(root, cfg["public_surfaces"]):
        rel_path = file_path.relative_to(root).as_posix()
        text = decode_surface_text(file_path.read_bytes())
        if text is None:
            # Çözülemeyen dosya taranamaz; taranamayan içerik yayına giremez.
            entry = entry_for(baseline, rel_path)
            entry_valid = (
                entry is not None
                and entry.get("content_sha256") == sha256_of(file_path)
                and verify_founder_signature(allowed_signers, LAYER2_ID, entry)
            )
            if not entry_valid:
                findings.append(Finding(
                    "2-sensitive-content-boundary", "unscannable-file", rel_path, 1,
                    "içerik metin olarak çözülemedi; tarama yapılamıyor",
                    "dosyayı taranabilir hale getir veya kurucu imzalı baseline kaydı ekle",
                ))
            continue
        d1_hits = detect_embedded_document_body(text, cfg)
        if d1_hits:
            findings.extend(check_layer1(rel_path, file_path, d1_hits, manifest, allowed_signers))
        findings.extend(check_layer2(rel_path, file_path, text, cfg, baseline, allowed_signers))

    registry_problems = validate_signer_roots(allowed_signers)
    registry_problems += validate_registries(manifest, baseline, root)

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
                        help="tek dosyanın sha256 değerini yazdır (onay imzası hazırlamak için)")
    parser.add_argument("--payload", nargs=3, default=None,
                        metavar=("KATMAN", "DOSYA", "TARIH"),
                        help="kurucunun imzalayacağı yükü yazdır (katman: layer1|layer2)")
    args = parser.parse_args(argv)

    if args.hash is not None:
        print(sha256_of(args.hash))
        return 0

    if args.payload is not None:
        layer_key, file_arg, date = args.payload
        layer_id = {"layer1": LAYER1_ID, "layer2": LAYER2_ID}.get(layer_key)
        if layer_id is None:
            parser.error("KATMAN layer1 veya layer2 olmalı")
        rel = Path(file_arg).resolve().relative_to(args.root.resolve()).as_posix()
        sys.stdout.buffer.write(
            signature_payload(layer_id, rel, sha256_of(Path(file_arg)), date))
        return 0

    exit_code, lines = run_gate(args.root.resolve(), args.config)
    for line in lines:
        print(line)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
