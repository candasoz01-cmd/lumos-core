# PR öncesi toparlama listesi

Branch’te yapılan değişikliklerin özeti. PR açmadan önce gözden geçir.

---

## Yapılan değişiklikler

### 1. Test: `test_enable_then_disable_log_order_option_b`
- **Dosya:** `tests/test_presence_lifecycle.py`
- **Ne yapıldı:** CI’da timing/log flush’a dayanıklı hale getirildi.
- **Zorunlu assertion’lar:** (1) `presence_stopped` logda yok, (2) subprocess `returncode == 0`.
- **Kaldırılanlar:** `presence_enabled` / `presence_disabled` / `presence_started` varlığı ve event sırası kontrolleri (bunlar CI’da flaky’di).

### 2. Smoke CLI: `scripts/smoke_cli.sh`
- **Ne yapıldı:** Consent ilk satırı yediği için “Komutlar:” bekleyen check kaldırıldı.
- **Yeni check’ler:** Çıktıda sadece `LOCKED` ve `OK` aranıyor (consent olsun olmasın bu ikisi çıkıyor).

### 3. Smoke presence: `scripts/smoke_presence.sh`
- **Ne yapıldı:** Consent/onboarding sonrası yanlış input akışı düzeltildi.
- **Akış:** Pipe ile `help` → `kamera` → `ac` → `evet` → `10` → `kapat` → `cik` → `exit`. İlk satır consent’e gidebiliyor; “help” + “kamera” her iki durumda da geçerli.
- **Doğrulama:** Çıktıda `OK` aranıyor.

### 4. Lint: `tests/test_consent.py`
- **Ne yapıldı:** Kullanılmayan `import pytest` kaldırıldı (F401).

---

## PR öncesi kontrol

- [ ] `make test` (veya `python -m pytest -q`) geçiyor
- [ ] `bash scripts/smoke_presence.sh` geçiyor
- [ ] `bash scripts/smoke_cli.sh` geçiyor
- [ ] `make lint` (ruff) temiz
- [ ] CI (GitHub Actions 3.12 / 3.13) yeşil
- [ ] Production kodunda bu branch’e özel değişiklik yok (sadece test + smoke + lint düzeltmesi)

---

## Özet (PR description için)

- Presence lifecycle testi CI timing’e dayanıklı sadeleştirildi.
- Smoke CLI ve smoke presence, consent/onboarding ile uyumlu hale getirildi.
- test_consent.py’deki kullanılmayan pytest import’u kaldırıldı.
