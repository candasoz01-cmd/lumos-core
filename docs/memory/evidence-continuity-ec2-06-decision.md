# Evidence Continuity EC2-06 — Legacy panel hizalama (onaylı karar)

> **Durum:** `[implemented]` — merge PR #283 (`5ff9660`); legacy read-only evidence strip uygulandı.
>
> **Keşif kaynağı:** Evidence Continuity v2 backlog Phase 5 (EC2-06); OD-043 Astro birincil; legacy `panel/js/app.js` EC2-02/08 dışı bırakıldı; read-only keşif (2026-06-20).
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md).
>
> **Canonical kaynaklar:** [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md), [`primary-user-surface-decision.md`](./primary-user-surface-decision.md), [`evidence-continuity-ec2-08-decision.md`](./evidence-continuity-ec2-08-decision.md), [`evidence-continuity-ec2-02-decision.md`](./evidence-continuity-ec2-02-decision.md).

**Karar:** **Seçenek 1 (minimum v1)** — legacy panel Görevler ekranına read-only **«Son işlem kanıtı»** şeridi (`GET /evidence/recent`, EC2-08 ile aynı API ve gruplama kuralları); paylaşılan `panel/js/evidence-correlation-strip.js`; birincil yüzey uyarısı; **EC2-02 pending-op kuyruğu Astro-only** kalır; tam feature parity ve E2E Astro migrasyonu v1 dışı.

**Bağımlılık:** EC2-08 merge edildi (PR #274); panel sunucusu `GET /evidence/recent` mevcut.

---

## Karar özeti

| # | Kural | Durum |
|---|--------|--------|
| LG1 | Legacy panel: read-only evidence strip — `GET /evidence/recent` + EC2-08 gruplama | `decision-approved` |
| LG2 | Paylaşılan modül: `panel/js/evidence-correlation-strip.js` — Astro inline mantığı ile parity | `decision-approved` |
| LG3 | «Buradan devam»: görev detayına odak veya sohbet prefill (legacy hash `#tasks` / `#chat`) | `decision-approved` |
| LG4 | EC2-02 client pending-op kuyruğu **legacy'de yok** — Astro birincil continuity yazımı | `decision-approved` |
| LG5 | Birincil yüzey banner: üretim Astro `/panel`; legacy E2E/statik kapı | `decision-approved` |
| LG6 | Journal yazım hook'ları ve şema v1'de değişmez | `decision-approved` |
| LG7 | Playwright E2E legacy evidence UI v1 dışı — pytest statik/davranış testi | `decision-approved` |

---

## Problem / mevcut boşluk

| Yüzey | EC2-02 queue | EC2-08 correlation | Rol |
|-------|--------------|-------------------|-----|
| `ui/src/pages/panel.astro` | ✓ | ✓ | Birincil üretim (OD-043) |
| `panel/js/app.js` | ✗ | ✗ | Legacy statik; root E2E hedefi |

Legacy panel görev mutasyonları `panel_tasks_server` üzerinden journal'a yazar (H1); kullanıcı journal özetini **göremez**. Kopma/teşhis «events[]» ve localStorage'a kalır — EC2-08 ile aynı boşluk.

---

## Seçenekler

### Seçenek 1 — Read-only evidence strip + shared JS module (SEÇİLDİ)

Dar hizalama: okuma + görünürlük; yazım yüzeyi genişlemez.

### Seçenek 2 — Tam feature parity (EC2-02 queue + tam UI port)

Legacy bakım yükü; Astro birincil ilkesi ile çelişir — **v1 reddedildi**.

### Seçenek 3 — Docs-only deferral

Operasyonel değer düşük; legacy kullanıcı kanıt göremez — **reddedildi** (EC2-05/09 minimum kod slice ile uyumlu).

### Seçenek 4 — Legacy panel kaldırma

OD-046 E2E migrasyonu ayrı paket — **v1 dışı**.

---

## Minimum v1 uygulama sınırı

| Dosya | Değişiklik |
|-------|------------|
| `panel/js/evidence-correlation-strip.js` | **Yeni** — fetch, group, render helpers (EC2-08 parity) |
| `panel/index.html` | Script include (app.js öncesi) |
| `panel/js/app.js` | Görevler şeridi HTML + refresh hook + continue handlers |
| `panel/css/app.css` | Kompakt strip stilleri |
| `tests/test_legacy_panel_evidence_ec2_06.py` | **Yeni** — L1–L6 |

**Bilerek dokunulmayacak:** `panel.astro`, EC2-02 queue, journal şema, Playwright E2E, köprü/guard hook'ları.

---

## Test planı

| # | Senaryo | Beklenen |
|---|---------|----------|
| L1 | Modül dosyası mevcut | `evidence-correlation-strip.js` |
| L2 | `index.html` script sırası | Modül app.js öncesi |
| L3 | `app.js` strip mount | `legacy-evidence-strip` id |
| L4 | Grup mantığı parity | EC2-08 bridge pair heuristic |
| L5 | `GET /evidence/recent` route | panel_tasks_server mevcut |
| L6 | EC2-08 U1–U12 regresyonsuz | Mevcut pytest yeşil |

---

## Kapsam dışı v1

| Madde | Gerekçe |
|-------|---------|
| EC2-02 pending-op queue legacy | LG4; Astro birincil |
| Tam Astro UI port | Bakım maliyeti |
| Legacy panel kaldırma | OD-046 |
| Retention UI (EC2-09) | API metadata opsiyonel; strip v1'de zorunlu değil |

---

## Bağımlılıklar

| Belge | İlişki |
|-------|--------|
| [`evidence-continuity-ec2-08-decision.md`](./evidence-continuity-ec2-08-decision.md) | API + gruplama kaynağı |
| [`primary-user-surface-decision.md`](./primary-user-surface-decision.md) | Astro birincil |
| EC2-14 | Journal şema — değişmez |

---

## Uygulama

**Merge:** PR #283 (`5ff9660` — `feat/ec2-06-legacy-evidence-strip`).

| Dosya | Değişiklik |
|-------|------------|
| `panel/js/evidence-correlation-strip.js` | Paylaşılan fetch + group + strip helpers |
| `panel/index.html` | Script include |
| `panel/js/app.js` | Görevler şeridi + wire/continue |
| `panel/css/app.css` | Strip stilleri |
| `tests/test_legacy_panel_evidence_ec2_06.py` | L1–L6 |

EC2-02 pending-op queue legacy'de **uygulanmadı** — LG4 bilinçli sınır.
