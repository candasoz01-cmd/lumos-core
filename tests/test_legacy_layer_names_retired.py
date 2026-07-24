"""Legacy iç katman adları (Kando/Cando/Bando) yalnız Legacy Naming allowlist dosyalarında kalır."""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_LAYER = re.compile(r"\b(Bando|Kando|Cando|BANDO|KANDO|CANDO)\b")

# Yalnızca tarihçe / karar kaydı — yeni mimari metin burada yazılmaz.
_ALLOW_FILES = frozenset(
    {
        "docs/memory/legacy-naming.md",
        "docs/decisions/ADR-018-internal-layers-core-local-sentinel.md",
        "docs/memory/od-061-legacy-layer-naming-retirement.md",
        "docs/memory/internal-agent-layers.md",  # Legacy Naming bölümü
        "docs/memory/internal-communication-sentinel-decision.md",  # ad geçiş notu
        "tests/test_legacy_layer_names_retired.py",
    }
)

# Teknik tanımlayıcı / marka — katman adı sayılmaz.
_LINE_ALLOW = re.compile(
    r"X-Kando-Token|x-kando-token|KandoLumos|KANDO_|kando_|cando_|"
    r"packages/kando|src/kando|archive/packages/kando|"
    r"local-kando|kando-urun|kando-packages|kando-lumos|"
    r"internal-communication-bando|README_kando|"
    r"Legacy Naming|legacy-naming|legacy ad|eski:\s*Bando|eski:\s*Kando|eski:\s*Cando|"
    r"\(eski:\s*(Kando|Cando|Bando)\)|legacy:\s*(Kando|Cando|Bando)|"
    r"Kando\s*/\s*Cando\s*/\s*Bando|Kando,\s*Cando,\s*Bando"
)


def test_docs_do_not_reuse_legacy_layer_names_outside_allowlist() -> None:
    violations: list[str] = []
    for path in sorted((_REPO / "docs").rglob("*.md")):
        rel = str(path.relative_to(_REPO)).replace("\\", "/")
        if rel in _ALLOW_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            if not _LAYER.search(line):
                continue
            if _LINE_ALLOW.search(line):
                continue
            violations.append(f"{rel}:{i}: {line.strip()[:120]}")
    assert not violations, "Legacy layer names outside allowlist:\n" + "\n".join(violations[:40])


def test_canonical_layers_use_core_local_sentinel() -> None:
    text = (_REPO / "docs/memory/internal-agent-layers.md").read_text(encoding="utf-8")
    assert "| **Core** |" in text
    assert "| **Local** |" in text
    assert "| **Sentinel** |" in text
    assert "## Legacy Naming" in text
