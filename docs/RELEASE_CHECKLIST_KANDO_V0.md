# Kando v0 — Release checklist

Önemli değişiklikten sonra hızlı doğrulama. Kando v0 çekirdek CLI ile sınırlı; web/tg dışarıda.

---

## 1. Git

- Working tree temiz veya sadece bilinçli değişiklikler (`git status`).
- Commit’ler anlamlı mesajla; gerekiyorsa branch güncel.

---

## 2. Test ve smoke

- `make test` (veya `python -m pytest -q`) geçiyor.
- `./scripts/smoke_kando_v0.sh` PASS veriyor (help, durum, kamera alt menüsü, çıkış).
- İsteğe bağlı: `make cli` ve `make smoke` (presence) — ortam uygunsa.

---

## 3. Komut yüzeyi ve izin

- `lumos cli` (veya `python -m lumos_core cli`) başlıyor; `help` yazınca “Kando v0 resmî komutlar: kilit | kamera | alias | durum | help | exit” ve alt satırlar görünüyor.
- Bilinmeyen komut “Desteklenmeyen komut. help yazın.” döndürüyor.
- macOS’ta başlangıçta izin satırı çıkıyor (macOS izinleri: Hazır. / Eksik — …); diğer OS’ta “macOS only” mesajı.

---

## 4. Ask akışı

- `lumos ask "merhaba"` (veya `python -m lumos_core ask "merhaba"`) hata vermeden tamamlanıyor (API/network yoksa cevap boş veya hata olabilir; çökme olmamalı).

---

## 5. Presence (aşama-1)

- CLI’dan `kamera` → alt menü açılıyor; `durum` ile presence ayarı satırı; `cik` ile ana prompt’a dönülüyor.
- `make smoke` (presence aç/kapat smoke) ortamda kamera/izin varsa geçiyor.

---

## 6. Ertelenen / scope dışı

Bunlar bu checklist’te doğrulanmaz; bilgi için:

- Web v1, tg, consent kalıcılığı, “adım ne” CLI komutu.
- Kando v0 = interaktif CLI (kilit, kamera, alias, durum, help, exit) + ask/chat + env.

---

**Hızlı komutlar (repo kökünde, venv aktif):**

```bash
git status
make test
./scripts/smoke_kando_v0.sh
make cli
# isteğe bağlı: make smoke && make web
```
