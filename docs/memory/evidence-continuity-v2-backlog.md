# Evidence Continuity v2 — backlog ve uygulama sırası

> **Durum:** `planning-only` — kod yok; öncelik ve faz planı.
>
> **v1 durumu:** [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md) — `[implemented]` / `[verified]` (PR #248, `main`); OD-058 **closed**.
>
> **Terminoloji:** [`audit-hook-term-decision.md`](./audit-hook-term-decision.md) — «audit hook» ≠ git hook; v2 #4 ve #14 bu belgede backlog olarak kalır.
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md).

**Kaynak:** v1 karar belgesi § «v2'ye ertelenen maddeler» (14 madde) — bu belge önceliklendirme, bağımlılık ve faz sırası ekler.

---

## v1 özeti (başlangıç noktası)

| Alan | v1 durumu |
|------|-----------|
| Journal | `.lumos/logs/evidence_continuity.jsonl` — uygulandı |
| Hook'lar | H0 `append_evidence_event`, H1 `_write_doc`, H2 `save_task_store_json` |
| Kapsam | Panel sunucu + TaskEngine mutasyonları |
| Bilinçli boşluk | Chat, client, köprü, guard/policy mirror, çift depo merge |

---

## v2 madde envanteri (14)

Kaynak: [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md) § «v2'ye ertelenen maddeler».

| ID | Madde | Öncelik | v2 ilk dalga |
|----|-------|---------|--------------|
| EC2-01 | Chat görev persist + `id` + silme UX düzeltmesi | **P0** | Evet |
| EC2-02 | Client evidence queue (`localStorage` → sunucu journal sync) | **P0** | Evet — **`[implemented]`** PR #258 (`bc6e4e0`) / [`evidence-continuity-ec2-02-decision.md`](./evidence-continuity-ec2-02-decision.md) |
| EC2-03 | Köprü `POST /task` outbox append + journal mirror | **P1** | Evet — **`[implemented]`** PR #265 (`b1c48aa`) / [`evidence-continuity-ec2-03-decision.md`](./evidence-continuity-ec2-03-decision.md) |
| EC2-04 | Guard/policy tek semantik journal (`record_guard_event`, `log_policy_blocked`) | **P1** | Evet — **`[implemented]`** PR #268 (`9475a0f`) / [`evidence-continuity-ec2-04-decision.md`](./evidence-continuity-ec2-04-decision.md) |
| EC2-05 | Çift depo birleştirme — ADR-008 drift çözümü | **P2** | Phase 5 — **`[implemented]`** minimum v1 — PR #277 (`6521222`) / [`evidence-continuity-ec2-05-decision.md`](./evidence-continuity-ec2-05-decision.md) |
| EC2-06 | Legacy panel (`panel/js/app.js`) hizalama | **P2** | Hayır — **`[implemented]`** PR #283 (`5ff9660`) / [`evidence-continuity-ec2-06-decision.md`](./evidence-continuity-ec2-06-decision.md) |
| EC2-07 | `events[]` migration veya deprecate | **P2** | Hayır — **`[implemented]`** PR #286 (`424cf19`) / [`evidence-continuity-ec2-07-decision.md`](./evidence-continuity-ec2-07-decision.md) |
| EC2-08 | Correlation UI — «son işlem kanıtı», «buradan devam» | **P1** | Evet (Phase 4) — **`[implemented]`** PR #274 (`fb2af14`) — [`evidence-continuity-ec2-08-decision.md`](./evidence-continuity-ec2-08-decision.md) |
| EC2-09 | Evidence-specific rotation / retention politikası | **P2** | Phase 5 — **`[implemented]`** PR #280 (`121216d`) / [`evidence-continuity-ec2-09-decision.md`](./evidence-continuity-ec2-09-decision.md) |
| EC2-10 | `ObservationEngine` disk spill — CLI step lifecycle | **P2** | Hayır |
| EC2-11 | Structured query / görev durumu reconstruct | **P2** | Hayır |
| EC2-12 | Disconnect + resume integration test harness | **P1** | Evet (Phase 4) — **`[implemented]`** PR #261 (`aa2a6ff`); [`evidence-continuity-ec2-12-decision.md`](./evidence-continuity-ec2-12-decision.md) |
| EC2-13 | `result` fazı — köprü async agent; guard senkron (EC2-04 `after` yeterli) | **P1** | Evet — **`[implemented]`** PR #271 (`41a48fb`) / [`evidence-continuity-ec2-13-decision.md`](./evidence-continuity-ec2-13-decision.md) |
| EC2-14 | Şema validator CI kapısı | **P0** | Evet |

---

## Öncelik katmanları

### P0 — Continuity boşluğu ve doğrulama kapısı

| ID | Neden P0 |
|----|----------|
| EC2-01 | Chat görevleri v1'de journal dışı; kullanıcıya görünür continuity boşluğu |
| EC2-02 | Client-only kanıt kaybolur; EC2-01 sonrası sunucu sync için zorunlu |
| EC2-14 | Journal şema bütünlüğü; «audit hook» karışıklığı #14'e map edildi — CI kapısı |

### P1 — Genişletilmiş hatlar ve operasyonel değer

| ID | Neden P1 |
|----|----------|
| EC2-03 | Köprü yürütme hattı v1 dışı; outbox overwrite modeli |
| EC2-04 | Dağınık guard/policy kanalları teşhisi zorlaştırır |
| EC2-08 | Journal verisi kullanıcıya anlamlı hale gelir |
| EC2-12 | Kopma/devam senaryoları otomatik doğrulanır |
| EC2-13 | Köprü/guard için `result` fazı; EC2-03/04 ile hizalı |

### P2 — Büyük mimari / legacy / opsiyonel

| ID | Neden P2 |
|----|----------|
| EC2-05 | ADR-008 store merge — yüksek etki, ayrı karar gerektirir |
| EC2-06 | Legacy panel; Astro birincil (OD-043) |
| EC2-07 | `events[]` parallel truth; migration riski |
| EC2-09 | v1 rotation yeterli; politika kararı bekler |
| EC2-10 | CLI observation ayrı domain |
| EC2-11 | Query/reconstruct — hook kapsamı genişledikten sonra |

---

## v2 ilk dalga DIŞI (bilinçli)

| Madde | Gerekçe |
|-------|---------|
| **EC2-05 — Store merge (ADR-008)** | Çift depo birleştirme ayrı mimari karar; v2 continuity fazlarından **önce veya paralel ayrı OD** olarak ele alınmalı. v1 journal `source` + `store` ayrımı merge olmadan çalışır. |
| EC2-06, EC2-07, EC2-09–EC2-11 | Legacy, migration, retention, observation, query — P2; ilk dalga sonrası |

---

## Bağımlılık grafi (özet)

```
EC2-14 (şema validator CI)     ── bağımsız; Phase 1'de erken
EC2-01 (chat persist + id)     ──► EC2-02 (client queue)
EC2-03 (köprü mirror)          ──► EC2-13 (result faz — köprü)
EC2-04 (guard mirror)         ──► EC2-13 (result faz — guard)
EC2-01..04, 13                ──► EC2-08 (correlation UI)
EC2-01..04                    ──► EC2-12 (test harness — tam değer için)
EC2-05 (store merge)          ── bağımsız OD; v2 fazlarına hard dependency YOK
```

**Sert sıra:** EC2-02, EC2-01 **sonrasında** başlar (chat persist + sunucu `id` olmadan client queue anlamsız).

---

## Önerilen uygulama sırası (5 faz)

### Phase 1 — Kapılar ve terminoloji

| Hedef | Maddeler | Not |
|-------|----------|-----|
| Terminoloji kapandı | — | [`audit-hook-term-decision.md`](./audit-hook-term-decision.md) |
| Şema doğrulama CI | EC2-14 | Mevcut `validate_evidence_record` + pytest; ince CI kapısı |
| Opsiyonel (geliştirme) | — | CI ruff parity — Paket B; EC v2 dışı ayrı PR |

**Çıktı:** Journal satırları CI'da şema bütünlüğü ile korunur; «audit hook» takip maddesi docs seviyesinde kapalı.

---

### Phase 2 — Chat continuity temeli

| Hedef | Maddeler | Bağımlılık |
|-------|----------|------------|
| Chat görev sunucu persist | EC2-01 | v1 H1 journal hazır |
| `id` + silme UX | EC2-01 | Ayrı «sohbet görev silme» takip maddesi ile hizalı |

**Çıktı:** Chat kaynaklı görevler sunucu mutasyonuna girer; journal boşluğu kapanmaya başlar.

---

### Phase 3 — Client evidence queue

| Hedef | Maddeler | Bağımlılık |
|-------|----------|------------|
| `localStorage` → sunucu sync | EC2-02 | **EC2-01 tamamlanmış olmalı** — merge `5073780` ✓ |

**Durum (2026-06-19):** **`[implemented]`** — merge PR #258 (`bc6e4e0`); pending-op kuyruğu `panel.astro`, flush mevcut REST, journal şeması değişmedi. Karar: [`evidence-continuity-ec2-02-decision.md`](./evidence-continuity-ec2-02-decision.md).

**Çıktı:** Tarayıcı kesintisinde client kanıtı kaybolmaz; sunucu journal ile birleşir. ✓

**Sonraki öncelik (Phase 4):** Phase 4 P1 maddeleri tamamlandı — EC2-08 merge `fb2af14` ✓.

---

### Phase 4 — Köprü, guard ve kullanıcı yüzeyi

| Hedef | Maddeler | Bağımlılık |
|-------|----------|------------|
| Köprü outbox + journal | EC2-03 | v1 şema enum genişlemesi; **`[implemented]`** PR #265 (`b1c48aa`) — [`evidence-continuity-ec2-03-decision.md`](./evidence-continuity-ec2-03-decision.md); EC2-13 ile birlikte planlanır |
| Guard/policy normalize | EC2-04 | EC v1 bilinçli dışı bırakıldı — **`[implemented]`** PR #268 (`9475a0f`) — [`evidence-continuity-ec2-04-decision.md`](./evidence-continuity-ec2-04-decision.md); EC2-13 ile birlikte planlanır |
| `result` faz (köprü async agent) | EC2-13 | EC2-03, EC2-04 — **`[implemented]`** PR #271 (`41a48fb`); [`evidence-continuity-ec2-13-decision.md`](./evidence-continuity-ec2-13-decision.md) |
| Correlation UI | EC2-08 | Yeterli journal kaynağı (Phase 2–3+) — **`[implemented]`** PR #274 (`fb2af14`); [`evidence-continuity-ec2-08-decision.md`](./evidence-continuity-ec2-08-decision.md) |
| Integration test harness | EC2-12 | Kopma/devam senaryoları — **`[implemented]`** PR #261 (`aa2a6ff`); DR1–DR7 pytest harness; runtime değişikliği yok — [`evidence-continuity-ec2-12-decision.md`](./evidence-continuity-ec2-12-decision.md) |

**Durum (2026-06-20):** EC2-12 harness merge edildi — `tests/test_panel_evidence_disconnect_resume_ec2_12.py` (DR1–DR7). EC2-03 köprü mirror merge edildi — PR #265 (`b1c48aa`). EC2-04 guard/policy mirror merge edildi — PR #268 (`9475a0f`). EC2-13 köprü async agent `result` faz merge edildi — PR #271 (`41a48fb`). EC2-08 correlation UI merge edildi — PR #274 (`fb2af14`); [`evidence-continuity-ec2-08-decision.md`](./evidence-continuity-ec2-08-decision.md). **Phase 4 P1 tamamlandı.**

**Çıktı:** Sunucu dışı ve guard hatları journal semantiğine yaklaşır; kullanıcı «son kanıt» görür. EC2-12 disconnect/resume doğrulama katmanı ✓. EC2-08 correlation şeridi ✓.

---

### Phase 5 — P2 ve mimari kararlar (sonra)

| Hedef | Maddeler | Not |
|-------|----------|-----|
| Store merge | EC2-05 | **`[implemented]`** minimum v1 — PR #277; tam merge ayrı OD — [`evidence-continuity-ec2-05-decision.md`](./evidence-continuity-ec2-05-decision.md) |
| Legacy / migration | EC2-06, EC2-07 | EC2-06 **`[implemented]`** PR #283; EC2-07 **`[implemented]`** PR #286 |
| Retention / observation / query | EC2-09, EC2-10, EC2-11 | EC2-09 **`[implemented]`** PR #280; EC2-10/11 sonra |

---

## «Audit hook» eşlemesi (v2)

| Informal «audit hook» anlamı | v2 karşılığı | Faz |
|------------------------------|--------------|-----|
| CI şema / kalite kapısı | EC2-14 | Phase 1 |
| Guard/policy birleştirme | EC2-04 | Phase 4 |
| Git audit logger | **Reddedildi** | — |

Detay: [`audit-hook-term-decision.md`](./audit-hook-term-decision.md).

---

## Riskler

| Risk | Etki | Mitigasyon |
|------|------|------------|
| EC2-02, EC2-01 öncesi | Client sync anlamsız | Sert bağımlılık sırası |
| EC2-05 erken merge | Yüksek regresyon | Ayrı OD; v2 ilk dalga dışı |
| Çoklu audit kanalları (EC2-04 ertelenirse) | Teşhis zor | Phase 4 öncelik |
| `events[]` + journal (EC2-07 ertelenirse) | Çift kayıt | v1 truth kuralı korunur |
| Public repo sınırı | Hassas payload | v1 demo-safe şema devam |

---

## Başarı kriterleri (v2 — planlama)

| Faz | Kriter (yüksek seviye) |
|-----|------------------------|
| 1 | EC2-14 CI kapısı yeşil; şema ihlali PR'da yakalanır |
| 2 | Chat görev create → journal'da `panel_tasks` veya yeni `source` |
| 3 | Client queue disconnect sonrası sunucu journal ile reconcile — **EC2-02 merge `bc6e4e0` ✓** |
| 4 | Köprü/guard olayları tek journal semantiğinde veya normalize edilmiş kanalda; EC2-12 DR1–DR7 harness merge `aa2a6ff` ✓ |
| 5 | Store merge ayrı OD onayı ile; EC2-05 v2 fazlarından bağımsız |

---

## Bağımlılıklar ve çapraz referanslar

| Belge | İlişki |
|-------|--------|
| [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md) | v1 uygulandı; 14 madde kaynağı |
| [`audit-hook-term-decision.md`](./audit-hook-term-decision.md) | Git hook reddi; #14/#4 eşlemesi |
| [ADR-008](../decisions/ADR-008-agent-network-boundary.md) | EC2-05 çift depo — minimum v1 karar |
| [`evidence-continuity-ec2-05-decision.md`](./evidence-continuity-ec2-05-decision.md) | EC2-05 `[implemented]` — PR #277; registry + dual health v1 |
| [`primary-user-surface-decision.md`](./primary-user-surface-decision.md) | EC2-06 legacy panel |
| [`open-decisions-needs-review.md`](./open-decisions-needs-review.md) | OD-058 (v1 closed), OD-059 (audit terminoloji) |
| [`evidence-continuity-ec2-02-decision.md`](./evidence-continuity-ec2-02-decision.md) | EC2-02 `[implemented]` — PR #258 (`bc6e4e0`); Phase 3 kapalı |
| [`evidence-continuity-ec2-12-decision.md`](./evidence-continuity-ec2-12-decision.md) | EC2-12 `[implemented]` — PR #261 (`aa2a6ff`); DR1–DR7 pytest harness |
| [`evidence-continuity-ec2-03-decision.md`](./evidence-continuity-ec2-03-decision.md) | EC2-03 `[implemented]` — PR #265 (`b1c48aa`); köprü POST /task journal mirror |
| [`evidence-continuity-ec2-04-decision.md`](./evidence-continuity-ec2-04-decision.md) | EC2-04 `[implemented]` — PR #268 (`9475a0f`); guard/policy journal mirror |
| [`evidence-continuity-ec2-13-decision.md`](./evidence-continuity-ec2-13-decision.md) | EC2-13 `[implemented]` — PR #271 (`41a48fb`); köprü async agent `result` faz |
| [`evidence-continuity-ec2-08-decision.md`](./evidence-continuity-ec2-08-decision.md) | EC2-08 `[implemented]` — PR #274 (`fb2af14`); correlation UI |
| [`evidence-continuity-ec2-09-decision.md`](./evidence-continuity-ec2-09-decision.md) | EC2-09 `[implemented]` — PR #280; retention metadata v1 |
| [`evidence-continuity-ec2-07-decision.md`](./evidence-continuity-ec2-07-decision.md) | EC2-07 `[implemented]` — PR #286; events[] projection metadata |

---

## Sonraki adım

1. **Phase 5 (P2):** EC2-10/11 (observation/query).
2. **Phase 2 kalan (opsiyonel):** EC2-01 merge edildi; silme UX iyileştirmeleri «sohbet görev silme» takip maddesi ile devam edebilir.
3. **EC2-05:** Karar [`evidence-continuity-ec2-05-decision.md`](./evidence-continuity-ec2-05-decision.md) — tam merge reddedildi; minimum v1 registry + dual health.

---

**İndeks notu:** OD-058 v1 kapalı; v2 uygulama ilerledikçe bu backlog güncellenir — ayrı OD gerekmez (planlama belgesi).

---

Son güncelleme: 2026-06-20 (EC2-07 implemented — PR #286 merge)
