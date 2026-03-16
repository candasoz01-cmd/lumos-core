from __future__ import annotations

"""
Change sensitivity modeli.

Amaç:
- Sadece dosya path'ine değil, dosyanın sistem içindeki rolüne göre değişiklik hassasiyetini
  sınıflandırmak.
- Write interceptor ve patch pipeline, bu sınıflamayı kullanarak yüksek etkili değişikliklerde
  patch lifecycle'ı zorunlu kılabilir.
"""

from enum import Enum, auto
from pathlib import Path


class ChangeSensitivity(Enum):
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    CRITICAL = auto()


def classify_sensitivity(path: Path) -> ChangeSensitivity:
    """
    Basit heuristic'lerle dosya için değişiklik hassasiyetini belirle.

    Heuristics (path tabanlı, gerektiğinde genişletilebilir):
    - CRITICAL:
      - src/core/*
      - src/policy/*
      - src/security/*
      - workspace_contract, inviolable ve guard ile doğrudan ilişkili çekirdekler
    - HIGH:
      - src/engine/*
      - src/task_engine/*
      - core/lumos_runtime.py, core/brain.py
    - NORMAL:
      - src/tools/*
      - src/scripts/*
      - cli/*
    - LOW:
      - tests/*
      - docs/*, panel/* vb. dış yardımcılar
    """
    p = path.resolve()
    parts = p.parts

    # Basit dizin tabanlı sınıflama
    # src/... kökünü bul
    try:
        # src dizini index'ini bulmaya çalış
        idx = parts.index("src")
    except ValueError:
        # src dışında kalan her şey için LOW varsay
        return ChangeSensitivity.LOW

    rel_parts = parts[idx + 1 :]  # src'den sonrası
    if not rel_parts:
        return ChangeSensitivity.LOW

    top = rel_parts[0]
    name = rel_parts[-1]

    # CRITICAL katman
    if top in ("core", "policy", "security"):
        # docs/test gibi alt dizinler için özel durum yoksa CRITICAL tercih edilir.
        return ChangeSensitivity.CRITICAL

    # engine / task_engine yüksek etkili
    if top in ("engine", "task_engine"):
        return ChangeSensitivity.HIGH

    # Bazı tekil core dosyalar HIGH olarak işaretlenebilir (ileride detaylandırılabilir).
    if top == "core" and name in ("lumos_runtime.py", "brain.py"):
        return ChangeSensitivity.HIGH

    # NORMAL katmanlar
    if top in ("tools", "scripts", "cli"):
        return ChangeSensitivity.NORMAL

    # Testler ve panel/dokümanlar düşük hassasiyet
    if top in ("tests", "panel", "docs"):
        return ChangeSensitivity.LOW

    # Varsayılan: NORMAL
    return ChangeSensitivity.NORMAL

