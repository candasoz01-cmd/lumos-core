# src layout ve AMAÇ 4 (tek paket ağacı)

## Mevcut durum: Zaten doğru

- **Tek top-level paket:** `src/lumos_core/`. Altında: context, core, device, engine, memory, policy, security, tools, ui, scripts, ai_providers, system.
- **src/ altında başka paket klasörü yok** (src/core, src/security gibi ayrı dizinler yok; hepsi lumos_core içinde).
- Tüm aktif importlar `lumos_core.*` kullanıyor; eski `from core.` / `from security.` sadece `.bak` / `.broken` dosyalarında.

Sonuç: **“En az kırılma” ile tek doğru paket ağacı zaten var.** Taşıma yapmaya gerek yok.

## Opsiyonel temizlik (ayrı PR)

- **src/main.py.bak*, main.py.broken***: Repo kirletiyor; silinmeyip **ayrı bir PR’da** arşivlenebilir veya .gitignore’a `*.bak` eklenip sonra temizlenebilir. Bu iş için otomatik silme yapılmadı; kullanıcı karar verir.

## pytest prensibi (uygulandı)

- **Komuta güvenilmez;** her yerde `python -m pytest`. Makefile: `PYTEST := $(PYTHON) -m pytest`; CI `make check` → `make test` → aynı çağrı.
- Dev deps: `python -m pip install -e ".[dev]"` (pytest + ruff). CI: `python -m pip install -e ".[dev]"` sonra `make check`, `python -m ruff check .`.

## Branch

Bu düzen **chore/restructure-src** branch’inde geçerli; ayrı branch açmaya gerek yok (layout zaten bu branch’te doğru).
