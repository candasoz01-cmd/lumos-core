# Evidence Continuity EC2-01 — Silme UX follow-up (onaylı karar)

> **Durum:** `[implemented]` — karar PR #297 (`f74dd63`); V1-a…V1-e uygulama PR #298 (`d778fc9`); `main`.
>
> **Keşif kaynağı:** EC2-01 core merge PR #256 (`5073780`); read-only tarama `panel.astro` + `tests/test_panel_gorev_delete_phase1.py` + legacy `app.js` parity karşılaştırması (2026-06-20); opsiyonel UX boşlukları G1–G9.
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu kararı gevşetemez.
>
> **Canonical kaynaklar:** [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md) § Phase 2 opsiyonel takip, [`evidence-continuity-ec2-02-decision.md`](./evidence-continuity-ec2-02-decision.md), [`primary-user-surface-decision.md`](./primary-user-surface-decision.md).

**Karar:** **Dar v1 (V1-a … V1-e)** — yalnızca `ui/src/pages/panel.astro` + pytest; chat «görev sil» / «görev geri al» UX boşluklarını kapat; sunucu, journal, legacy panel ve E2E **değişmez**.

**Bağımlılık:** EC2-01 core merge edildi (PR #256); EC2-02 client queue merge edildi (PR #258) — delete/restore enqueue davranışı korunur.

---

## Karar özeti

| # | Kural | Durum |
|---|--------|--------|
| SU1 | «Görev geri al» chat komutu parse + handler (V1-a) | `decision-approved` |
| SU2 | Silme sonrası restore ipucu mesajı chat yanıtında (V1-b) | `decision-approved` |
| SU3 | Delete/restore sonrası `panelEvidenceRefreshStrip()` çağrısı (V1-c) | `decision-approved` |
| SU4 | Chat silme sunucu/yerel başarı yolunda açık detay paneli kapat (V1-d) | `decision-approved` |
| SU5 | `not_found` / bulunamadı mesajları kullanıcı-dostu ve tutarlı (V1-e) | `decision-approved` |
| SU6 | Değişiklik yalnızca Astro birincil panel — legacy `app.js` v1 dışı | `decision-approved` |
| SU7 | Sunucu endpoint, journal şeması, EC2-02 kuyruk semantiği v1'de değişmez | `decision-approved` |
| SU8 | Demo-safe — chat snippet, token, credential kuyruk/mesajlara girmez | `decision-approved` |

---

## Problem / bağlam

EC2-01 core (PR #256) chat kaynaklı görev **oluşturmayı** sunucuya persist eder (`POST /tasks` → H1 journal; sunucu `tsk_*` id). Silme/restore **temel yolları** panel Görevler UI'sında ve kısmen chat «görev sil» ile çalışır; fakat keşifte **opsiyonel UX boşlukları** (G1–G9) tespit edildi:

| ID | Boşluk | Mevcut davranış (özet) | v1 hedef |
|----|--------|------------------------|----------|
| **G1** | «Görev geri al» parse yok | `parsePanelGorevKomutu` yalnızca `sil`, `oluştur`, `ekle` — restore chat komutu tanınmaz | V1-a |
| **G2** | Chat restore handler yok | `runSend` yalnızca `verb === "sil"` dalını işler; `restoreLastGorevlerTask` UI butonuna bağlı | V1-a |
| **G3** | Restore ipucu eksik | Chat silme yanıtı başarı metni; «Geri al» / `restoreLastBtn` ipucu yok | V1-b |
| **G4** | Evidence strip refresh — delete | `deleteGorevlerTaskFromChat` sunucu başarı yolunda `panelEvidenceRefreshStrip` çağrılmaz; `finishDeleteGorevlerTaskLocal` yolu da eksik | V1-c |
| **G5** | Evidence strip refresh — restore | `restoreLastGorevlerTask` tamamlanınca strip yenilenmez | V1-c |
| **G6** | Detay paneli chat delete | Yerel silme `finishDeleteGorevlerTaskLocal` → `closeGorevlerDetail`; chat sunucu başarı yolu detayı açık bırakabilir | V1-d |
| **G7** | `not_found` mesaj netliği | «Silinecek görev bulunamadı» — ref türü (`id` vs title) veya sonraki adım ipucu yok | V1-e |
| **G8** | Grace period / geniş undo penceresi | Legacy'de farklı semantik; Astro'da yalnızca son silinen | **v1 dışı** |
| **G9** | Legacy parity (app.js restore-by-ref) | Legacy chat/detail restore daha zengin; tam port v1 kapsam dışı | **v1 dışı** (SU6) |

**Kullanıcıya görünür semptom:** Chat'ten görev silindikten sonra kanıt şeridi güncellenmeyebilir; açık görev detayı kalabilir; «görev geri al …» komutu işlenmez; restore yalnızca Görevler panelindeki «Son silineni geri al» butonu ile mümkün.

**EC2-01 core ile ilişki:** Journal ve sunucu persist **doğru**; bu follow-up yalnızca **birincil panel UX tutarlılığı** — continuity yazım katmanına dokunmaz.

---

## EC2-01 / EC2-02 bağımlılık doğrulaması

| Kontrol | Kanıt |
|---------|--------|
| EC2-01 merge | `5073780` — PR #256; chat create → `POST /tasks` + H1 journal |
| EC2-02 merge | `bc6e4e0` — PR #258; `enqueueEvidencePendingOp` delete/restore offline yollarında mevcut |
| Birincil yüzey | OD-043 — `ui/src/pages/panel.astro` |
| Mevcut pytest | `tests/test_panel_gorev_delete_phase1.py` — sil parse aynası; restore parse **henüz yok** |

**Sonuç:** Önkoşullar **karşılandı**; dar v1 implementasyon PR'ı açılabilir. EC2-02 kuyruk enqueue noktaları **korunmalı** — yalnızca UX wiring eklenir.

---

## Seçenekler

### Seçenek 1 — Dar v1: V1-a … V1-e, yalnızca panel.astro + pytest (SEÇİLDİ)

Minimum UX düzeltmeleri; sunucu/journal/legacy/E2E dokunulmaz.

### Seçenek 2 — Geniş UX paketi (grace period, chat restore-by-ref, legacy parity)

Legacy `app.js` semantiğinin tam portu; bakım yükü ve kapsam genişlemesi — **v1 reddedildi**.

### Seçenek 3 — Sunucu tarafı silme/restore mesaj API'si

Yeni endpoint veya hata kodu genişlemesi; public yüzey büyür — **v1 reddedildi**.

### Seçenek 4 — Docs-only erteleme

Opsiyonel takip maddesi açık kalır; chat restore ve strip senkronu eksik — **reddedildi** (dar maliyet, yüksek kullanıcı görünürlüğü).

---

## Minimum v1 tasarım (V1-a … V1-e)

### V1-a — «Görev geri al» parse + chat handler

| Öğe | Tasarım |
|-----|---------|
| Parse | `parsePanelGorevKomutu`: `^(?:görev\|gorev)\s+geri\s+al(?=\s\|:|$)` — ref opsiyonel; boş ref → son silinen (`lastGorevlerDeletedId`) |
| Handler | `runSend` (local + online dalları): `verb === "geri_al"` → mevcut `restoreLastGorevlerTask()` veya ref ile hedef restore |
| Yanıt | Başarı: «Görev geri alındı: …»; boş kuyruk: «Geri alınacak silinen görev yok.» |
| Sınır | Ref ile restore yalnızca **son silinen** veya panel listesinde eşleşen satır — grace-period çoklu undo **yok** (G8 dışı) |

### V1-b — Restore ipucu mesajı (silme sonrası)

| Öğe | Tasarım |
|-----|---------|
| Chat silme yanıtı | Başarı metnine kısa ek: «Geri almak için «görev geri al» yazabilir veya Görevler'de «Son silineni geri al» kullan.» |
| Tutarlılık | Yerel ve sunucu başarı yollarında aynı ipucu; `restoreLastBtn.hidden = false` ile uyumlu |

### V1-c — `panelEvidenceRefreshStrip` after delete/restore

| Tetikleyici | Davranış |
|-------------|----------|
| `finishDeleteGorevlerTaskLocal` sonu | `panelEvidenceRefreshStrip()` (typeof guard) |
| `deleteGorevlerTaskFromChat` sunucu başarı | strip refresh |
| `restoreLastGorevlerTask` başarı (tüm yollar) | strip refresh |
| `deleteOpenGorevlerTask` sunucu başarı | strip refresh (panel UI parity) |

### V1-d — Chat delete → açık detay kapat

| Yol | Davranış |
|-----|----------|
| `deleteGorevlerTaskFromChat` sunucu başarı | `closeGorevlerDetail(true)` — yerel yol zaten `finishDeleteGorevlerTaskLocal` içinde kapatıyor |
| Render | Mevcut `panelGorevlerTasksRender` / `render()` sırası korunur |

### V1-e — `not_found` mesaj netliği

| Durum | Mesaj (örnek) |
|-------|----------------|
| Ref boş | «Görev adı eksik. Örnek: görev sil alışveriş» (mevcut) |
| Liste/API `not_found` | «Görev bulunamadı: «{ref}». Başlık veya görev kimliği (tsk_…) kontrol edin.» |
| Silme iptal | «Silme iptal edildi.» (mevcut confirm akışı) |

**Not:** Ham `error` kodları (`not_found`, `delete_failed`) kullanıcıya **doğrudan** gösterilmez; Türkçe özet tercih edilir (mevcut `restore_failed` → «geri alma başarısız» pattern'i ile uyumlu).

---

## Değişecek dosyalar (gelecek implementasyon — şimdi yapılmaz)

| Dosya | Değişiklik |
|-------|------------|
| `ui/src/pages/panel.astro` | V1-a … V1-e: parse, chat handler, mesajlar, strip refresh, detail close |
| `tests/test_panel_gorev_delete_phase1.py` | Restore parse aynası; mesaj/ref edge case'leri (ve/veya strip wiring spot check) |
| `tests/test_panel_gorev_create_ec2_01.py` | **Dokunulmaz** — create kapsamı ayrı |

**Bilerek dokunulmayacak (v1):**

- `panel/scripts/panel_tasks_server.py` — endpoint/yüzey değişikliği yok
- `src/core/evidence_continuity.py` — journal şema değişikliği yok
- `panel/js/app.js` — legacy panel (EC2-06 bilinçli sınır)
- Playwright E2E — EC2-12 pytest harness yeterli; UI E2E v1 dışı
- EC2-02 kuyruk anahtarı / flush algoritması — semantik korunur

---

## Başarı kriterleri

| # | Kriter |
|---|--------|
| SK1 | Chat «görev geri al» (ref'li/ref'siz) parse edilir ve restore tetiklenir |
| SK2 | Chat «görev sil» başarı yanıtında restore ipucu görünür |
| SK3 | Delete/restore sonrası evidence correlation şeridi güncellenir (EC2-08 read path) |
| SK4 | Chat silme sonrası açık görev detay dialogu kapanır |
| SK5 | `not_found` ve boş ref mesajları Türkçe, eyleme yönelik |
| SK6 | EC2-02 enqueue/delete/restore offline yolları regresyonsuz |
| SK7 | Mevcut EC2-01 create pytest + EC2-14 şema CI yeşil |

---

## Test planı

| # | Senaryo | Beklenen |
|---|---------|----------|
| T1 | `parse_panel_gorev_geri_al("görev geri al")` | `{ verb: "geri_al", ref: "" }` |
| T2 | `parse_panel_gorev_geri_al("gorev geri al: tsk_abc")` | `{ verb: "geri_al", ref: "tsk_abc" }` |
| T3 | «görev geri al» sil parse ile karışmaz | `parse_panel_gorev_sil` / restore ayrı |
| T4 | Silme başarı mesajı restore ipucu içerir | Metin spot check (Python string sabiti veya extract) |
| T5 | `not_found` mesaj ref içerir, ham kod göstermez | V1-e |
| T6 | EC2-01 create testleri | Regresyonsuz (`test_panel_gorev_create_ec2_01.py`) |
| T7 | EC2-02 queue testleri | Regresyonsuz (`test_panel_evidence_queue_ec2_02.py`) |
| T8 | EC2-12 disconnect harness | Regresyonsuz — runtime değişikliği yok |
| T9 | pytest paketi CI yeşil | `ruff` + tam suite |

**Doğrulama kanalları:** pytest (T1–T5 otomasyon); manuel panel: chat sil → strip güncelleme → detay kapalı → «görev geri al».

---

## Riskler

| Risk | Etki | v1 mitigasyon |
|------|------|----------------|
| Restore ref yanlış hedef | Yanlış görev geri gelir | Ref'siz → yalnızca `lastGorevlerDeletedId`; ref'li → `findGorevlerTaskIndexByRef` + trash id |
| Strip refresh sıklığı | Gereksiz `GET /evidence/recent` | Yalnızca delete/restore sonrası; typeof guard |
| Legacy parity beklentisi | Kullanıcı app.js davranışı arar | SU6 — Astro birincil; legacy docs notu |
| Chat handler çift dal | local + online `runSend` | Her iki dalda aynı verb işleme |
| EC2-02 kuyruk çift enqueue | Duplicate pending op | Mevcut `(op, ref)` dedup korunur; UX değişikliği enqueue noktalarını taşımaz |

---

## Kapsam dışı v1

| Madde | Gerekçe |
|-------|---------|
| **Grace period / çoklu undo penceresi (G8)** | Legacy semantik; ayrı ürün kararı |
| **Legacy panel `app.js` hizalama (G9)** | EC2-06 bilinçli sınır — read-only strip yeterli |
| **Sunucu/journal değişikliği** | EC2-01 core + EC2-14 şema CI |
| **Playwright E2E** | EC2-12 pytest harness; maliyet/yield düşük |
| **Yeni REST endpoint** | Minimum sunucu yüzeyi ilkesi |
| **Chat geçmişi replay** | PII; journal kaynağı değil |
| **Köprü/guard/store merge** | EC2-03..05 ayrı kararlar |

---

## Bağımlılıklar ve çapraz referanslar

| Belge / artefakt | İlişki |
|------------------|--------|
| [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md) | EC2-01 Phase 2 opsiyonel takip |
| EC2-01 merge `5073780` / PR #256 | Core — chat create persist |
| EC2-02 merge `bc6e4e0` / PR #258 | Delete/restore enqueue + flush |
| EC2-08 merge `fb2af14` / PR #274 | `panelEvidenceRefreshStrip` / correlation UI |
| [`primary-user-surface-decision.md`](./primary-user-surface-decision.md) | Astro birincil |
| `tests/test_panel_gorev_delete_phase1.py` | Mevcut sil parse harness — genişletilecek |

---

## Uygulama

| Dosya | Değişiklik |
|-------|------------|
| `ui/src/pages/panel.astro` | V1-a … V1-e |
| `tests/test_panel_gorev_delete_phase1.py` | Restore parse + mesaj testleri (T1–T9) |

**Merge:** PR #297 (karar belgesi) + PR #298 (`d778fc9`) — V1-a…V1-e; pytest + CI yeşil.

---

## Sonraki adım

1. **Backlog / decision-log sync:** EC2-01 silme UX `[implemented]` — docs PR (backlog + DL-A16).
2. **v2 kapsam dışı (v1 reddedildi):** Seçenek 3 sunucu mesaj API; legacy panel; Playwright E2E — ayrı OD gerekmeden takip edilmez.

---

**İndeks notu:** EC2-01 silme UX follow-up ayrı OD açmaz; v2 backlog § Phase 2 opsiyonel + bu belge canonical. **`docs/decision-log.md` DL-A16** kapandı (PR #298).

---

Son güncelleme: 2026-06-20 (`[implemented]` PR #297–#298)
