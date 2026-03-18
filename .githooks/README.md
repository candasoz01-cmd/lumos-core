# Git hooks (geliştirme)

## `pre-commit`

Her `git commit` öncesi:

1. `ruff check .`
2. `pytest -q`

Başarısızlıkta commit oluşturulmaz. **Bypass:** `git commit --no-verify`

## Kurulum (repo kökünde, tek komut)

```bash
make setup-commit-guard
```

Sonra venv içinde: `pip install -e .` ve `pip install -U ruff pytest`.

Ayrıntı: **`docs/dev-commit-guard.md`**

---

*Bu dizin ürün onay kurallarından bağımsızdır; yalnız geliştirme kalitesi içindir.*
