# Audit hook terim kararı — informal takip maddesi kapanışı

> **Durum:** `decision-approved` (terminoloji **closed**) / **Paket B implementation-complete** (CI ruff parity — 2026-06-20).
>
> **Keşif kaynağı:** Audit Hook v1 discovery (2026-06-19) — `.githooks/`, EC v1, CI `ci.yml`, dağınık audit katmanları read-only tarama.
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu kararı gevşetemez.
>
> **Canonical kaynaklar:** [`docs/dev-commit-guard.md`](../dev-commit-guard.md), [`docs/kando-urun-onay-otomasyon-ayrimi.md`](../kando-urun-onay-otomasyon-ayrimi.md), [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md), [`public-repo-boundary.md`](./public-repo-boundary.md) § Bölüm B.

**Karar:** Informal **«audit hook»** takip maddesi **ayrı bir git audit hook v1 gerektirmez**. Terim üç bağımsız katmana ayrılır; yeni pre-commit/post-commit audit logger **açılmaz**.

**İndeks:** [`open-decisions-needs-review.md`](./open-decisions-needs-review.md) **OD-059** (terminoloji kapandı).

---

## Karar özeti

| # | Kural | Durum |
|---|--------|--------|
| AH1 | «Audit hook» ≠ yeni git hook zorunluluğu | `decision-approved` |
| AH2 | Git pre-commit (commit guard) = geliştirme kalite kapısı; ürün audit değil | `decision-approved` |
| AH3 | Evidence Continuity runtime hook'ları (H0/H1/H2) = sunucu mutasyon kanıtı; v1 uygulandı | `implemented` / `verified` |
| AH4 | EC v2 guard mirror + şema validator CI «audit hook» adıyla karıştırılmaz | `decision-approved` |
| AH5 | CI ruff parity (Paket B) — pre-commit ile hizalı | **implementation-complete** |

---

## Amaç

Commit-dışı informal takip listesinde geçen **«audit hook»** maddesinin repo içinde canonical spec'i olmadığı keşfedildi. Bu belge:

- Terimi **üç katmana** ayırarak gelecekteki karışıklığı önler.
- Ayrı git «audit hook v1» ihtiyacını **reddeder**.
- EC v2 backlog maddelerine **yönlendirme** sağlar.
- Geliştirme (commit guard) ile ürün/runtime (EC journal) ayrımını sabitler.

**Uygulama notu:** Bu belge yalnızca terminoloji ve yönetişim kararıdır; kod veya yeni git hook içermez.

---

## Üç katman ayrımı

```
┌─────────────────────────────────────────────────────────────┐
│ Katman 1 — Git pre-commit (commit guard)                    │
│ Amaç: kod kalitesi kapısı (ruff + pytest)                   │
│ Kurulum: opt-in — make setup-commit-guard                   │
│ Katman: geliştirme — ürün audit / continuity DEĞİL         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Katman 2 — Evidence Continuity runtime hook'ları (v1)       │
│ Amaç: sunucu mutasyon kanıtı (panel + engine)               │
│ Ne: append_evidence_event → evidence_continuity.jsonl       │
│ Kapılar: _write_doc(), save_task_store_json()               │
│ Durum: implemented / verified (PR #248, main)               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Katman 3 — EC v2 / dağınık audit (yanlış «audit hook» adı)  │
│ Guard/policy journal mirror (EC v2 #4)                      │
│ Şema validator CI kapısı (EC v2 #14)                        │
│ Git hook DEĞİL — runtime normalizasyon veya CI doğrulama    │
└─────────────────────────────────────────────────────────────┘
```

---

## Katman 1 — Git pre-commit (commit guard)

| Özellik | Değer |
|---------|--------|
| **Konum** | `.githooks/pre-commit` |
| **İçerik** | `ruff check .` → `pytest -q` |
| **Kurulum** | `make setup-commit-guard` (opt-in; otomatik gelmez) |
| **Bypass** | `git commit --no-verify` |
| **Belge** | [`docs/dev-commit-guard.md`](../dev-commit-guard.md) |
| **Ürün onayı** | Hayır — [`docs/kando-urun-onay-otomasyon-ayrimi.md`](../kando-urun-onay-otomasyon-ayrimi.md) |

**Firm:** Commit guard geliştirici makinesinde kalite kapısıdır; git commit/push olayları ürün mutasyonu değildir ve EC journal'a **girmez**.

**CI drift (giderildi — 2026-06-20):** Pre-commit'te ruff varken [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) artık `ruff check .` koşar (OD-059 Paket B). Bu «audit hook» değildir; geliştirme kalite parity'sidir.

---

## Katman 2 — Evidence Continuity runtime hook'ları (v1)

EC «hook» = **runtime yazım kapıları**, git hook değil.

| Hook | Konum | Durum |
|------|-------|--------|
| **H0** | `src/core/evidence_continuity.py` — `append_evidence_event` | `implemented` |
| **H1** | `panel/scripts/panel_tasks_server.py` — `_write_doc()` | `implemented` |
| **H2** | `src/core/workspace_contract.py` — `save_task_store_json()` | `implemented` |

**Journal:** `.lumos/logs/evidence_continuity.jsonl` — şema `lumos.evidence_continuity.v1`.

**Canonical karar:** [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md) — OD-058 **closed** (v1 panel + engine).

**v2 backlog:** [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md).

---

## Katman 3 — Yanlış «audit hook» eşlemesi (EC v2)

Informal takip maddesi muhtemelen aşağıdakilerden birini veya birkaçını kastediyordu; **hiçbiri yeni git hook değildir**:

| Informal anlam | EC v2 madde | Doğru sınıf |
|----------------|-------------|-------------|
| CI kalite / şema kapısı | #14 Şema validator CI | CI doğrulama kapısı |
| Guard/policy birleştirme | #4 Guard/policy journal mirror | Runtime normalizasyon |
| Ruff CI parity | Paket B (keşif) | Geliştirme kalite parity |

**Repo'daki diğer «audit» kavramları (git hook değil):**

| Katman | Konum | Depolama |
|--------|-------|----------|
| Guard audit | `src/core/guard_audit.py` | Python logging |
| Policy blocked | `src/policy/action_policy.py` | `.lumos/logs/log.txt` |
| Lumos execution audit | `packages/kando_runtime/.../lumos_audit.py` | `.lumos/logs/YYYY-MM-DD.log` |
| Evolution log | `src/core/evolution_log.py` | `logs/lumos_evolution.jsonl` |

Bunların EC v2 #4 ile normalize edilmesi ayrı iş paketidir; «audit hook v1» adıyla açılmaz.

---

## Karar: NO separate git audit hook v1

**Reddedilen:** Yeni pre-commit/post-commit audit logger, commit metadata'sını journal'a yazan git hook, «Audit Hook v1» adlı ek `.githooks/*` dosyası.

**Gerekçe (keşif kanıtı):**

1. EC v1 runtime audit'i panel + engine mutasyonlarını zaten journal'a yazıyor.
2. Commit guard farklı problem çözer (kalite); ürün continuity üretmez.
3. Yeni git audit hook pre-commit süresini anlamsız uzatır (zaten tam pytest koşuyor).
4. Guard/policy mirror EC v1 bilinçli dışı; v2 runtime işi — git katmanı değil.
5. Repo'da «Audit Hook v1» spec'i yoktu; EC keşfi «audit hook noktaları» ile commit guard karışmış.

---

## Hangi olaylar audit'e girer / girmez

| Girer (EC journal) | Girmez |
|------------------|--------|
| Panel sunucu CRUD (`panel.task.*`) | Git commit/push olayları |
| TaskEngine mutasyonları | Chat-local görevler (v1 kapsam dışı) |
| `before` / `after` / `error` fazları | Ham kullanıcı mesajı, token, credential |
| Demo-safe `payload_summary` | Guard deny/allow — v2 #4 |
| | Policy blocked (`log.txt`) — farklı kanal |
| | Evolution lifecycle — ayrı domain |
| | Lumos execution audit — farklı şema |

---

## Keşif Paket A + B (önerilen yol)

| Paket | İçerik | Bu belge / PR |
|-------|--------|---------------|
| **Paket A** | Terminoloji kararı (bu dosya) + informal takip maddesi kapanışı | **Bu belge** |
| **Paket B** | CI'ya `ruff check .` eklenmesi (pre-commit parity) | **Tamamlandı** — `.github/workflows/ci.yml` + `requirements.txt` |

**Paket C/D (EC v2):** Şema validator CI (#14) ve guard/policy normalize (#4) — [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md).

---

## Informal takip maddesi — kapanış

| Madde | Önceki durum | Yeni durum |
|-------|--------------|------------|
| **audit hook** (informal) | Tanımsız backlog etiketi | **CLOSED** (docs) — git hook reddi; EC v2 + opsiyonel Paket B'ye map |

**Ayrı tutulacak takip maddeleri (audit hook ile birleştirilmez):**

- sohbet görev silme
- `.env.example`
- `ui/.env.local`

---

## Riskler

| Risk | Mitigasyon |
|------|------------|
| «Audit hook» = yeni git hook sanılması | Bu belge + OD-059 |
| CI ruff drift (pre-commit vs CI) | Paket B **tamamlandı** |
| Dağınık audit kanalları (5+ sistem) | EC v2 #4 backlog |
| EC v1 chat/client boşluğu | EC v2 Phase 2 — audit hook ile kapanmaz |

---

## Bağımlılıklar ve çapraz referanslar

| Belge | İlişki |
|-------|--------|
| [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md) | EC runtime hook'ları; OD-058 closed |
| [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md) | #4, #14 ve faz planı |
| [`docs/dev-commit-guard.md`](../dev-commit-guard.md) | Katman 1 — commit guard |
| [`public-repo-boundary.md`](./public-repo-boundary.md) § Bölüm B | Public repo sınırı; operasyonel runbook gitignored vault'ta |
| [`docs/kando-urun-onay-otomasyon-ayrimi.md`](../kando-urun-onay-otomasyon-ayrimi.md) | Geliştirme vs ürün otomasyon ayrımı |

---

## Sonraki adım

1. **Paket A (tamamlandı):** Bu terminoloji belgesi + OD-059 indeks senkronu.
2. **Paket B (tamamlandı):** CI ruff parity — `.github/workflows/ci.yml`.
3. **EC v2:** [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md) faz sırası.

---

**İndeks notu:** `open-decisions-needs-review.md` OD-059 satırı bu belgeyle senkron tutulur.

---

Son güncelleme: 2026-06-20 (Paket B — CI ruff parity)
