# Lumos Action Permission Matrix

| Alan | Değer |
|------|-------|
| Durum | **Taslak** — ADR-012 companion |
| Tarih | 2026-06-21 |
| İlgili | [ADR-012](../decisions/ADR-012-lumos-security-codex.md), `src/task_engine/profiles.py`, `docs/lumos-karar-sozlesmesi.md` |
| Kapsam | Docs-only; kod değişikliği yok |

## Amaç

Kullanıcıya görünen **eylem alanlarını** (dosya, terminal, mail, …) Lumos **izin seviyeleri** ve **yetki profilleri** (`rapor`, `guvenli_yurut`, `kisitli_otonom`) ile eşlemek.

**İzin seviyeleri (sütunlar):**

| Seviye | Kod karşılığı | Anlam |
|--------|---------------|-------|
| **read / report** | `analyze`, `read` — karar katmanı `analiz` | Okuma, durum, rapor; state değiştirmez |
| **draft / propose** | `plan` — karar katmanı `oner` | Öneri, taslak, plan; uygulama yok |
| **user-confirmed execute** | `safe_local`, `write_local` — karar katmanı `uygulama` | Yerel yürütme; `kisitli_otonom` için genel onay gerekir |
| **blocked / never** | `external`, `critical`, `SECURITY_NEVER_AUTO` — karar katmanı `asla` | Hiçbir profilde otomatik izin yok |

---

## Profil özeti (`profiles.py`)

| Profil | Analiz/öneri | `safe_local` | `write_local` | `external` / `critical` |
|--------|--------------|--------------|---------------|-------------------------|
| **rapor** | ✓ | ✗ | ✗ | ✗ |
| **guvenli_yurut** | ✓ | ✓ (onaysız) | ✗ | ✗ |
| **kisitli_otonom** (genel onay kapalı) | ✓ | ✗ | ✗ | ✗ |
| **kisitli_otonom** (genel onay açık) | ✓ | ✓ | ✓ | ✗ |

Kaynak: `STEP_PERMISSION_MATRIX`, `may_execute_step_at_runtime()`.

---

## Eylem alanı × izin seviyesi (ana matris)

Aşağıdaki tablo **hedef sözleşmedir** (ADR-012). "Bugün enforce" sütunu [runtime enforcement map](lumos-runtime-enforcement-map.md) ile doğrulanır.

| Eylem alanı | read / report | draft / propose | user-confirmed execute | blocked / never | `profiles.py` eşlemesi | Bugün enforce (özet) |
|-------------|---------------|-----------------|------------------------|-----------------|------------------------|----------------------|
| **file** (okuma) | Tüm profiller | — | — | — | `read` | ✓ TaskEngine + CLI |
| **file** (yerel yazma / patch) | — | Plan adımı | `guvenli_yurut`: safe_local; `kisitli_otonom`: write_local + genel onay | Sandbox'ta core path; kalıcı silme | `safe_local`, `write_local` | Kısmi — `write_interceptor`, workspace_contract |
| **terminal** (komut) | Log/durum okuma | Komut önerisi | Tanımlı safe_local araçlar (demo) | Ham shell, prod komut | `safe_local` / `external` | Kısmi — `controlled_bridge` blok |
| **mail** | Inbox okuma (demo) | Taslak öneri | Pilot onaylı gönderim (yok/OSS demo) | OAuth, prod SMTP, toplu gönderim | `external` | ✓ Blok — bridge regex / policy |
| **calendar** | Etkinlik listeleme (demo) | Öneri | Onaylı oluşturma (yok) | Dış API yazma | `external` | ✗ Hedef only |
| **app launch** | Durum | — | Demo sandbox | OS launch, prod | `external` | ✗ Device policy stub |
| **external service** | Health/status | Entegrasyon planı | — | Tüm dış yazma/çağrı | `external` | Kısmi — offline_engine, action_policy |
| **payment** | — | — | — | Her zaman | `critical` + `SECURITY_NEVER_AUTO` | ✓ Profil matrisi |
| **domain** (DNS/mail domain) | Sınır dokümantasyonu | — | — | Prod domain değişikliği | `external` / `critical` | Docs — ADR-009 |
| **security settings** (kilit, keystore, consent) | `durum`, panel read state | — | Kullanıcı passphrase / consent komutu | Otomatik unlock, sıfırlama | `critical` + policy `ACCESS_*` | Kısmi — lock, action_policy, consent dosyası |

---

## Profil × eylem alanı (detay)

### rapor

| Alan | İzin |
|------|------|
| file, terminal, mail, calendar | read / report, draft / propose |
| app launch, external, payment, domain, security | read / report (görünürlük); execute **yok** |

### guvenli_yurut

| Alan | İzin |
|------|------|
| file | read + safe_local (yerel demo işler) |
| terminal | safe_local kapsamındaki araçlar |
| mail, calendar, app, external, payment, domain | read / propose; dış execute **blocked** |
| security | read; unlock yalnızca kullanıcı komutu (CLI), otomatik değil |

### kisitli_otonom

| Alan | Genel onay kapalı | Genel onay açık |
|------|-------------------|-----------------|
| file | read / propose | + write_local |
| terminal | read / propose | + safe_local (profil kapsamı) |
| Diğer dış alanlar | read / propose | execute **hâlâ blocked** (`external`) |

---

## `SECURITY_NEVER_AUTO` — profilden bağımsız

`profiles.py` — hiçbir profilde, genel onay açık olsa bile izin verilmez:

| Kod | Eylem alanı |
|-----|-------------|
| `permanent_delete` | file (kalıcı silme) |
| `external_write` | external service, mail, calendar |
| `irreversible_user_op` | payment, domain, security (geri dönüşsüz) |
| `critical_system_config` | security settings |

Doğrulama referansı: `core/inviolable.py` — sözleşme sabitleri.

---

## Policy katmanı ek kuralları (`action_policy.py`)

Profil matrisinden **bağımsız** runtime snapshot kuralları:

| Action | Koşul | Sonuç |
|--------|-------|-------|
| `create_task`, `complete_task`, `delete_task`, `cancel_task` | `online=False` | blocked |
| `delete_task` | `koruma_active=True` | blocked |
| `access_identity`, `access_keystore` | `consent=False` | blocked |

CLI: `cli/cli_tasks_mutation.py` — `_enforce_task_policy`.

---

## Panel yüzeyi (not)

Panel görev CRUD (`panel_tasks_server.py`) profil matrisini **doğrudan çağırmaz**; `_task_actions_gate()` şu an `enabled: True` döner. Codex hedefi: panel mutasyonları CLI ile aynı policy + profil zincirine bağlanmalı (bkz. [next PR plan](lumos-security-codex-next-pr-plan.md)).

---

## Sonraki adım

Runtime gap'ler: [lumos-runtime-enforcement-map.md](lumos-runtime-enforcement-map.md).  
İlk uygulama PR: [lumos-security-codex-next-pr-plan.md](lumos-security-codex-next-pr-plan.md).
