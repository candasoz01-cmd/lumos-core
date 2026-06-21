# ADR-011: Lock Semantiği — İki Sinyal Kararı

| Alan | Değer |
|------|-------|
| Durum | **Kabul edildi** (2026-06-21) — Faz 1–3 **tamamlandı** (#436–#438); Faz 4 (trust motor) bekliyor |
| Tarih | 2026-06-21 |
| İlgili | `docs/lumos-karar-sozlesmesi.md`, public GitHub sınırı kuralları, [ADR-007](ADR-007-trust-engine-layer.md), [ADR-010](ADR-010-guard-policy-trust-terminology.md), [usage map](../analysis/ADR-010-guard-policy-trust-usage-map.md) |

## Amaç

Lumos'ta **aynı "lock" kelimesiyle** taşınan iki farklı güven sinyalini resmi karar kaydı olarak ayırmak; tek boolean'a birleştirmemek; CLI `durum` / `hazir`, panel, policy ve runtime katmanlarında hangi sinyalin nerede kullanıldığını haritalamak.

Bu belge **yalnızca dokümantasyondur**. Bu turda kod, import, test, rename (`_lock_ok` → `keystore_ready`), panel UI veya lock davranışı değişikliği **kapsam dışıdır**.

**Terminoloji:** Lock, trust, consent ve panel görünürlüğü **[ADR-010](ADR-010-guard-policy-trust-terminology.md)** kabul edilmiş sözlüğüne tabidir. Bu ADR **iki lock sinyalinin ayrı kalması** kararını kaydeder; trust durumları ADR-007'ye aittir.

## Bağlam

ADR-010 usage map (2026-06-21) lock semantik drift'i **doğruladı**: `startup_health._lock_ok(keystore_initialized)` ile runtime `LockState.unlocked` **farklı anlam, aynı kelime** taşır. ADR-010 drift tablosu bunu teşhis listesi olarak kaydeder; birleştirme veya düzeltme **ayrı checkpoint** olarak bırakılmıştır.

CLI'da ek drift: `durum` komutu keystore init sinyalini kullanırken `hazir` komutu runtime `LockState` tersini (`not is_locked()`) aynı `_lock_ok` yardımcısına geçirir — parametre adı (`keystore_initialized`) her iki sinyali maskelemektedir.

**Öncelik sırası (ADR-006, ADR-007, ADR-010 ile hizalı):** Guard → Trust → Router. Lock sinyalleri **trust** katmanına aittir; guard kararı değildir.

**İlgili ADR'ler:**

| ADR | Konu | Bu ADR ile ilişki |
|-----|------|-------------------|
| [ADR-007](ADR-007-trust-engine-layer.md) | Trust Engine | Trust durumları `locked` / `unlocked`; sinyal #3 koruma kilidi |
| [ADR-010](ADR-010-guard-policy-trust-terminology.md) | Terminoloji | `lock` tanımı; drift tablosu § Repo drift |
| [usage map](../analysis/ADR-010-guard-policy-trust-usage-map.md) | Repo doğrulama | `_lock_ok` vs `LockState` drift kanıtı |

---

## Mevcut durum (repo analiz bulguları, Haziran 2026 — usage map doğrulandı)

### İki ayrı sinyal — birleştirilmez

Repo'da "lock" kelimesi en az **iki bağımsız sinyali** taşır. Bunlar **tek boolean'a indirgenmemelidir**; birleşik `lock_ok` veya `_lock_ok` ≡ `LockState.unlocked` varsayımı **yasaktır** (ADR-010 terminoloji disiplini).

| # | Kabul edilen ad | Eski / mevcut kod adı | Anlam | Tipik kaynak |
|---|-----------------|----------------------|-------|--------------|
| 1 | **keystore_ready** | `_lock_ok`, `lock_ok` (durum bağlamında), `keystore_initialized` parametresi | Anahtar kasası dosyası / init tamamlandı mı? (`FileKeyStore.is_initialized()`) | `startup_health._lock_ok`, CLI `durum`, `get_durum_parts` |
| 2 | **session_unlocked** | `LockState.unlocked`, `lock_status()` → `UNLOCKED`, `is_locked()` tersi | Passphrase ile kök anahtar runtime'da yüklü mü? | `src/security/lock.py`, `CoreState.lock_status()`, CLI `hazir` |

**Analiz bulgusu (doğrulandı):** Keystore init olabilir ama oturum kilitli kalabilir; oturum açık olsa bile keystore henüz init edilmemiş olabilir. İki sinyal **bağımsız**dır.

### ADR-010 drift çapraz referansı

Usage map ve ADR-010 § Repo drift riskleri bu kararı doğrular:

| ADR-010 drift satırı | Bu ADR karşılığı |
|----------------------|------------------|
| **runtime `LockState` vs `startup_health._lock_ok`** | `session_unlocked` vs `keystore_ready` — **ayrı kalır** |
| **CLI LOCKED vs runtime** | `durum` (keystore_ready) vs snapshot `lock_status` (session_unlocked) — **bilinçli ayrım** |
| **Panel mock durumları** | Panel keystore alanı consent vekili — **session_unlocked / keystore_ready yansıtmaz** |

Tam drift tablosu: [ADR-010 § Repo drift riskleri](ADR-010-guard-policy-trust-terminology.md#repo-drift-riskleri-terminoloji-kayması), [usage map § Doğrulanan drift](../analysis/ADR-010-guard-policy-trust-usage-map.md).

---

## Kabul edilen semantik sözleşme

### keystore_ready

**Anlam:** Anahtar kasası yapılandırması / dosyası hazır — `FileKeyStore.is_initialized()` veya eşdeğeri.

**Hedef rol:** Startup hazırlık kontrolü; `durum` komutunda "Lock: aktif/pasif" satırı (mevcut `lock_ok` etiketi — rename sonrası netleşecek).

**Repo karşılığı:** `startup_health._lock_ok(keystore_initialized)` → `bool(keystore_initialized)`.

**Ne değildir:** Passphrase ile runtime unlock (`session_unlocked`).

---

### session_unlocked

**Anlam:** Koruma kilidi runtime'da açık — kök anahtar bellekte (`LockState.unlocked == True`).

**Hedef rol:** Hassas işlem öncesi trust durumu `unlocked` (ADR-007); policy `koruma_active`; enforcement zinciri.

**Repo karşılığı:** `LockState.unlocked`, `CoreState.lock_status()` → `"UNLOCKED"` / `"LOCKED"`, `CoreState.is_locked()`.

**Ne değildir:** Keystore dosyasının varlığı veya init (`keystore_ready`).

---

## CLI: `durum` vs `hazir` (doğrulanmış harita)

| Komut | Kullanılan sinyal | Kodda geçirilen argüman | `_lock_ok` / özet anlamı | Çıktıda lock satırı |
|-------|-------------------|-------------------------|--------------------------|---------------------|
| **durum** | **keystore_ready** | `ctx.ks.is_initialized()` → `get_durum_parts(..., keystore_initialized, ...)` | `lock_ok` = keystore init | `Lock: aktif/pasif` (`format_durum` — keystore_ready) |
| **hazir** | **session_unlocked** | `not ctx.state.is_locked()` → `get_startup_summary(..., keystore_initialized, ...)` | `_lock_ok(unlocked)` — parametre adı **yanıltıcı** | "Lock aktif" / "Lock yok" (runtime unlock anlamında) |

**Drift notu (kod kanıtı):** `hazir` aynı `get_startup_summary` / `_lock_ok` yardımcısını kullanır ancak **farklı sinyal** geçirir. Parametre adı `keystore_initialized` her iki komutta da **semantik maskeleme** yapar — rename PR'da düzeltilecek (**bu ADR kapsam dışı**).

**durum ek satır:** Snapshot satırı (`format_status_line`) ayrıca `lock_status` (session_unlocked) gösterir; `format_durum` içindeki `Lock:` satırı keystore_ready'dir — **aynı çıktıda iki farklı lock anlamı** mümkündür.

---

## Katman eşlemesi: panel, policy, runtime

| Katman / giriş noktası | Birincil sinyal | Mevcut repo karşılığı | Drift / not |
|------------------------|-----------------|----------------------|-------------|
| **Runtime enforcement** | **session_unlocked** | `LockState`, `CoreState.lock_status()`, `is_locked()` | Canonical hassas işlem kilidi |
| **Policy (`action_policy`)** | **session_unlocked** | `koruma_active` ← `policy_is_locked()` (callable) | Delete red when locked |
| **CLI `durum`** | **keystore_ready** (+ snapshot'ta session_unlocked ayrı satır) | `get_durum_parts` + `format_durum` | İki anlam aynı ekranda |
| **CLI `hazir`** | **session_unlocked** | `not ctx.state.is_locked()` → `_lock_ok` | Parametre adı yanıltıcı |
| **Startup özeti metinleri** | Bağlama göre **keystore_ready** veya **session_unlocked** | `get_startup_summary` / `get_durum_parts` | Aynı `_lock_ok` helper |
| **Panel keystore kartı** | **consent vekili** (ne keystore_ready ne session_unlocked) | `keystore_ready`: `consent_ok`; `keystore_state`: consent'e göre Hazır/Kilitli | Bilinçli proxy; anahtar ifşası yok |
| **Panel guidance.lock** | **consent vekili** | `UNLOCKED` if consent else `LOCKED` | Runtime `LockState` yansıtmaz |
| **Trust durumu (ADR-007)** | **session_unlocked** hedef | `locked` / `unlocked` trust durumları | `keystore_ready` trust durumu değil |
| **Task mutation policy snapshot** | **session_unlocked** | `_task_mutation_policy_context` → `koruma_active: locked` | Keystore init ayrı kontrol |

**Zorunlu ayrım (ADR-010 ile uyumlu):** **panel görünürlüğü ≠ runtime enforcement**. Panel keystore alanı production lock semantiği **garanti etmez**.

---

## Karar

1. **İki sinyal resmi olarak ayrılır:** `keystore_ready` (anahtar kasası init) ve `session_unlocked` (runtime passphrase unlock). **Tek boolean birleştirme yapılmaz.**
2. **Kabul edilen CLI eşlemesi:** `durum` → **keystore_ready**; `hazir` → **session_unlocked** (mevcut kod davranışı kayıt altına alınır; parametre adları henüz hizalı değildir).
3. **Runtime / policy enforcement:** **session_unlocked** esas alınır; `koruma_active`, `LockState`, ADR-007 `locked`/`unlocked` durumları bu sinyale bağlıdır.
4. **Panel:** Keystore/guidance alanları **consent vekili** olarak kalır; bu ADR panel kodunu değiştirmez — drift bilinçli kayıtlıdır.
5. **Terminoloji (ADR-010):** Dokümantasyon ve sonraki PR'larda bağlam belirtilmeden "lock" kullanılmaz; `keystore_ready` veya `session_unlocked` tercih edilir.
6. **Bu ADR kod değiştirmez** — rename, davranış düzeltmesi ve panel hizası **fazlı takip checkpoint'lerindedir**.

Kaynak: [ADR-010 guard/policy/trust usage map](../analysis/ADR-010-guard-policy-trust-usage-map.md) (2026-06-21).

---

## Riskler (usage map doğrulandı)

| Risk | Etki | Azaltma (hedef) |
|------|------|-----------------|
| **Tek `lock_ok` boolean varsayımı** | Yanlış "hazır" / "güvenli" yorumu | Bu ADR: birleştirme yasağı; iki ad zorunlu |
| **durum çıktısında çift anlam** | `Lock: aktif` (keystore) vs snapshot `UNLOCKED` (session) karışıklığı | Rename PR: etiket ayrımı (`Keystore` / `Oturum`) |
| **`hazir` parametre adı drift** | `keystore_initialized=not is_locked()` okuyucu yanıltması | Rename PR: ayrı parametre veya iki argüman |
| **Panel consent proxy** | Kullanıcı keystore/session durumunu yanlış sanabilir | Dürüst demo metni (ADR-010); enforcement runtime'da |
| **Policy vs durum sinyali farkı** | Keystore init var, session locked — farklı katman kararları | Katman tablosu; trust sözleşmesi (ADR-007) |
| **Erken tek enum refactor** | Regresyon; semantik kaybı | Fazlı rename; test her fazda |

---

## Fazlı sonraki adımlar (bu PR dışı)

| Faz | İş | Kapsam | Durum |
|-----|-----|--------|-------|
| **1 — Rename (docs-first kod)** | `_lock_ok` → `keystore_ready`; `get_durum_parts` alan adları; `hazir` ayrı argüman | `startup_health.py`, CLI çağrıları, testler | **Tamamlandı** — #436 |
| **2 — CLI çıktı etiketleri** | `durum` Lock satırını `Keystore` / `Oturum` diye ayır | `format_durum`, kullanıcı metinleri | **Tamamlandı** — #437 |
| **3 — Panel dürüstlük** | Keystore kartında vekili açık etiketle; runtime bridge varsa session sinyali | Panel adapter (onaylı) | **Tamamlandı** — #438 |
| **4 — Trust engine tüketimi** | Merkezi trust sinyal modeli iki alanı ayrı taşır | ADR-007 motor checkpoint | Bekliyor |

**Bu PR yalnızca karar belgesi (+ isteğe bağlı journal notu) içerir.**

---

## Ne yapılmamalı (bu ADR kapsamında)

| Yapılmaması gereken | Gerekçe |
|---------------------|---------|
| `_lock_ok` ve `LockState` birleştirme | Farklı sinyaller; regresyon |
| Tek `is_ready` boolean | Ürün yanıltması |
| Kod / rename / test değişikliği | Karar ADR'si |
| Panel UI değişikliği | Ayrı onaylı faz |
| Trust = guard birleştirme | ADR-010 zorunlu ayrım |
| Abartılı ürün vaadi | Demo foundation |

---

## Takip checkpoint'leri

| Checkpoint | Durum |
|------------|-------|
| ADR-010 usage map lock drift | **Tamamlandı** — drift doğrulandı |
| ADR-011 lock semantiği kararı (bu belge) | **Kabul edildi** — #435 (2026-06-21) |
| Faz 1 — Rename (`keystore_ready`, CLI argümanları) | **Tamamlandı** — #436 |
| Faz 2 — CLI çıktı etiketleri (`Keystore` / `Oturum`) | **Tamamlandı** — #437 |
| Faz 3 — Panel keystore vekili etiketleme | **Tamamlandı** — #438 |
| Faz 4 — ADR-007 trust sinyal tablosu / motor tüketimi | Bekliyor — iki lock alanı referansı |

---

## Sonuç

Haziran 2026 repo analizi ve ADR-010 usage map sonrasında Lumos lock semantiği **iki ayrı sinyal** olarak kayıt altına alınmıştır: **keystore_ready** (anahtar kasası init) ve **session_unlocked** (runtime passphrase unlock). **Tek boolean birleştirme yapılmaz.** CLI `durum` keystore_ready, CLI `hazir` session_unlocked kullanır; panel consent vekili olarak kalır; runtime ve policy session_unlocked esas alır. Faz 1–3 rename, CLI etiketleri ve panel dürüstlüğü **#436–#438** ile uygulandı; Faz 4 (trust motor) bekliyor.

## Sonraki gözden geçirme

- Rename PR — `_lock_ok`, parametre adları, testler
- ADR-007 § Trust sinyalleri — lock satırı iki alana bölme referansı
- ADR-010 drift tablosu — ADR-011 çapraz link (isteğe bağlı küçük senkron)
- Public repo sınırı ve çekirdek stabilizasyon durumu ile uyum kontrolü
