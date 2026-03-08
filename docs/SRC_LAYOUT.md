# Kaynak ağacı (tek paket)

**Hedef:** Tek doğru paket ağacı; import yolları kırılmadan, en az kırılma ile.

## Mevcut yapı

- **Tek top-level paket:** `src/lumos_core/`. Tüm çekirdek modüller bu altında: `context`, `core`, `device`, `engine`, `memory`, `policy`, `security`, `system`, `tools`, `ui`, `scripts`, `ai_providers`, vb.
- **Paket dışında tek dosya:** `src/main.py` — sadece `lumos_core.interactive_cli.main` yönlendirmesi (geriye dönük uyum). Tercih edilen giriş: `python -m lumos_core` veya `lumos`.
- **`src/scripts/`:** Git’te takip edilmiyor; boş/legacy. Tek yardımcı scriptler: `lumos_core.scripts` (init_keystore, init_identity).

## Import kuralı

- Tüm canlı kod `from lumos_core....` kullanır. Eski `from core.`, `from security.` vb. yalnızca `.bak` dosyalarında kalır; paket yapısına dokunulmaz.

## Test / CI

- **pytest:** Her yerde `python -m pytest` (komut adına güvenilmez). Makefile: `PYTEST := $(PYTHON) -m pytest`.
- **Kurulum:** `python -m pip install -e .`; test için pytest gerekirse `python -m pip install pytest` veya `pip install -e ".[dev]"`.

Bu yapı `chore/restructure-src` branch’inde geçerlidir; tek klasör “yanlış yerde” sayılmaz (sadece bilinçli stub).
