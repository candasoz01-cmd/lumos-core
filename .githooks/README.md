# Git hooks (geliştirme)

## `pre-commit`

Her `git commit` öncesi:

1. `ruff check .`
2. `pytest -q`

Başarısızlıkta commit oluşturulmaz. **Bypass:** `git commit --no-verify`

## `pre-push`

Her `git push` öncesi yayın kapısı koşar: `python3 ops/publication_gate/gate.py`.
Public remote'a giden içerik push anında yayımlanmış olur; bu kanca son yerel
bariyerdir. `--no-verify`, kancasız klon veya API push'u bunu atlayabilir —
detay ve kalan risk: `docs/PUBLICATION_GATE.md`.

## Kurulum (repo kökünde, tek komut)

```bash
make setup-commit-guard
```

Sonra venv içinde: `pip install -e .` ve `pip install -U ruff pytest`.

Ayrıntı: **`docs/dev-commit-guard.md`**

---

*Bu dizin ürün onay kurallarından bağımsızdır; yalnız geliştirme kalitesi içindir.*
