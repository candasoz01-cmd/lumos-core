# Kando v0 — Resmî smoke / demo akışı

Tek senaryo: baştan sona çekirdek CLI akışı (web/tg/ask/chat yok).

---

## 1. Başlatma

**Yapılan:** `lumos` veya `lumos cli` çalıştırılır (varsayılan `LUMOS_MODE=offline`).

**Beklenen:**
- Consent yoksa: önce onboarding önizlemesi (Merhaba, cihaz incelendi, yapabileceklerim, izin gerektiren özellikler, “Bu bilgiler henüz kaydedilmedi”).
- macOS ise: ardından izin satırı (`macOS izinleri: Hazır.` veya `macOS izinleri: Eksik — ...`); varsa maddeler (`• Erişilebilirlik: hazır/eksik/bilinmiyor — ...`).
- Sonra ana prompt: `Sen: `

---

## 2. help

**Yapılan:** `Sen: ` prompt’una `help` yazılır.

**Beklenen:** HELP_TEXT basılır: “Kando v0 resmî komutlar: kilit | kamera | alias | durum | help | exit” ve alt satırlarda kilit/kamera/alias/durum/help/exit açıklamaları. Sonra tekrar `Sen: `.

---

## 3. durum

**Yapılan:** `Sen: ` prompt’una `durum` yazılır.

**Beklenen:** Tek satır: `LOCKED | Presence: OFF | Mode: offline | Log: <son_log_ts_veya_boş>`. Sonra `Sen: `.

---

## 4. Readiness / izin

**Kapsam:** CLI başlarken (adım 1) macOS’ta zaten `print_permission_readiness()` çıktısı gelir. Kullanıcı izin sormak için ek bir komut yazmaz; izin durumu girişte gösterilir.

**Beklenen (özet):** macOS’ta ilk çıktıda “macOS izinleri: Hazır.” veya “macOS izinleri: Eksik — …” ve isteğe bağlı maddeler. macOS dışında: “macOS izinleri bu sistemde uygulanmıyor (macOS only).”

---

## 5. Kamera alt menüsü (temel akış)

**Yapılan:**
- `Sen: ` → `kamera` yazılır.
- Alt menü açılır: “Kamera: durum | ac | kapat | sure | cik” ve `Kamera> ` prompt’u.
- `Kamera> ` → `durum` yazılır.
- Çıktı alındıktan sonra `Kamera> ` → `cik` (veya `çık`) yazılır.

**Beklenen:**
- `kamera` sonrası: “Kamera: durum | ac | kapat | sure | cik” ve `Kamera> `.
- `durum` sonrası: `enabled=False timeout_sec=... face=... mode=... status=...` biçiminde tek satır (presence_lock durumu).
- `cik` sonrası: `OK`, ardından ana `Sen: `.

---

## 6. Çıkış

**Yapılan:** `Sen: ` prompt’una `exit` (veya `q`, `çık`, `cik`, `quit`) yazılır.

**Beklenen:** `OK` basılır ve program sonlanır (exit code 0).

---

## Çalıştırma (terminal)

```bash
# Repo kökünde, venv aktif
cd /Users/candasoz/WORK_2026/lumos-core
python -m lumos_core cli
```

Sırayla gir: `help` → `durum` → `kamera` → `durum` → `cik` → `exit`.

Otomasyon (pipe):

```bash
echo -e "help\ndurum\nkamera\ndurum\ncik\nexit" | python -m lumos_core cli
```

---

## CLI dışı: "adım ne"

"Adım ne" Kando v0 interaktif CLI komut yüzeyinde yok; `Sen: ` prompt’una yazılırsa "Desteklenmeyen komut. help yazın." döner. İsim/hatırlama akışı yalnızca **ask/chat** (lumos ask / lumos chat) tarafında vardır; resmî smoke bu CLI ile sınırlıdır.
