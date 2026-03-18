# Geliştirme: commit guard (pre-commit)

**Bu belge yalnızca geliştirme akışı içindir.** Ürün/Kando tarafında kullanıcı onayı kurallarından **farklı bir katmandır**; karıştırılmamalıdır.

## Ne işe yarar?

`git commit` çalıştırıldığında, commit oluşmadan önce otomatik olarak:

1. `ruff check .`
2. `pytest -q` (projede standart test komutu)

koşar. **Biri başarısız olursa commit yapılmaz.**

## Kurulum (tek komut)

Repo kökünde:

```bash
make setup-commit-guard
```

Ardından sanal ortamda (önerilir):

```bash
pip install -e .
pip install -U ruff pytest
```

Hook, varsa `.venv` veya `venv` içindeki ortamı etkinleştirir.

## Bypass

Acil veya bilinçli istisna: `git commit --no-verify`

Normal akışta bypass kullanılmamalıdır.

## Dosya konumu

- Hook: `.githooks/pre-commit`
- Git yapılandırması: `git config core.hooksPath .githooks` (`setup-commit-guard` bunu ayarlar)

---

*Ürün tarafında otomatik işlem ve kullanıcı onayı: `docs/kando-urun-onay-otomasyon-ayrimi.md`*
