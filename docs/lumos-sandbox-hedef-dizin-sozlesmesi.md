# Sandbox hedef dizini sözleşmesi

Sandbox modu açıkken yazım hedefinin nereye yönleneceği ve canlı çekirdek path korumasıyla hizası. **Sadece sözleşme tanımı;** sink'lerin bu hedefe yazması ayrı adım.

**Referans:** `lumos-sandbox-mode-milestone-checkpoint.md`, `lumos-guard-sandbox-kopya-siniri.md`, `core/workspace_contract.py`.

---

## 1. Karar: Gerekli mi?

**Evet — eksik ön koşul.**  
Checkpoint: "Runtime sandbox hedefi: Sandbox açıkken 'nereye yazılır' tanımlı değil; sadece 'canlı çekirdek path'e yazma reddedilir' guard'ı var." Guard canlıya yazmayı engelliyor; sandbox açıkken yazılacak **hedef base** tek kaynakta tanımlı değildi. Bu adımda sadece hedef dizin sözleşmesi tanımlanır; tüm davranışların açılması kapsam dışı.

---

## 2. Önerilen sözleşme

### 2.1 Tek kaynak

- **Sabit:** `LUMOS_SANDBOX_DIRNAME = "sandbox"` — tek sandbox alt dizin adı; trash gibi yeni alternatif üretilmez.
- **Türetme:**
  - `sandbox_base_path(live_base_dir) -> Path`: Canlı çalışma köküne göre sandbox kök path.  
    `sandbox_base_path(live_base) == Path(live_base) / LUMOS_SANDBOX_DIRNAME`
  - `writing_base_dir(live_base_dir, is_sandbox_mode: bool) -> Path`:  
    - `is_sandbox_mode=False` → `Path(live_base_dir)` (canlı base).  
    - `is_sandbox_mode=True` → `sandbox_base_path(live_base_dir)`.

### 2.2 Base path / sandbox path ilişkisi

- **Canlı base:** Çalışma kökü (örn. `.lumos`); `_lumos_dir()` ile aynı kavram.
- **Sandbox base:** Her zaman `live_base_dir / LUMOS_SANDBOX_DIRNAME`.  
  Sistem keyfi sandbox hedefi seçemez; hedef tek bu formülden türetilir.

### 2.3 Canlı çekirdeğe yazı reddiyle hizası

- Mevcut **guard** değişmez: `allow_write_to_core(live_base_dir, target_path, is_sandbox_mode)` — sandbox modunda canlı çekirdek path'e yazma reddedilir.
- **writing_base_dir** sadece “yazım hedefi hangi base?” sorusunun cevabı. Sink'ler ileride `writing_base = writing_base_dir(live_base, is_sandbox_mode)` alıp bu base altına yazacak; bu base canlı değilse (sandbox base) zaten canlı çekirdek path'e yazılmıyor demektir.
- `is_core_state_path(live_base, path)` altında `live_base/sandbox` ve altı **çekirdek sayılmaz** (zaten testlerde `base/sandbox` False). Yani sandbox base altına yazmak guard ile çakışmaz.

---

## 3. En dar uygulanabilir paket

- **Kod:** `workspace_contract.py` içinde:
  - `LUMOS_SANDBOX_DIRNAME` sabiti.
  - `sandbox_base_path(live_base_dir)`.
  - `writing_base_dir(live_base_dir, is_sandbox_mode)`.
- **Davranış:** Hiçbir sink veya main değişmez; sadece sözleşme API’si eklenir. Mevcut guard ve sink davranışı aynen kalır.
- **Test:** `sandbox_base_path` ve `writing_base_dir` için unit testler (path eşitlikleri).

---

## 4. Test yaklaşımı

- `sandbox_base_path(live_base)` == `Path(live_base) / LUMOS_SANDBOX_DIRNAME`.
- `writing_base_dir(live_base, False)` == `Path(live_base)`.
- `writing_base_dir(live_base, True)` == `sandbox_base_path(live_base)`.
- İsteğe bağlı: `writing_base_dir(live_base, True)` sonucunun `is_core_state_path(live_base, ...)` için False olduğunu doğrula (sandbox çekirdek değil).

---

## 5. Commit

Evet. Sözleşme + test; davranış değişmediği için tek, dar commit yeterli.
