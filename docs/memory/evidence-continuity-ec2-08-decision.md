# Evidence Continuity EC2-08 — Correlation UI (onaylı karar)

> **Durum:** `[decision-approved]` — kod yok; uygulama bekliyor.
>
> **Keşif kaynağı:** Evidence Continuity v2 backlog Phase 4 (EC2-08); `panel.astro` bridgeLast / evidence queue read-only keşif; `evidence_continuity.py` journal şeması ve mirror hatları; EC2-03/04/13 correlation bağımlılıkları (2026-06-20 read-only keşif).
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu kararı gevşetemez.
>
> **Canonical kaynaklar:** [`evidence-continuity-v1-decision.md`](./evidence-continuity-v1-decision.md), [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md), [`evidence-continuity-ec2-02-decision.md`](./evidence-continuity-ec2-02-decision.md), [`evidence-continuity-ec2-03-decision.md`](./evidence-continuity-ec2-03-decision.md), [`evidence-continuity-ec2-04-decision.md`](./evidence-continuity-ec2-04-decision.md), [`evidence-continuity-ec2-13-decision.md`](./evidence-continuity-ec2-13-decision.md).

**Karar:** **Seçenek 1** — panel sunucusunda **read-only** `GET /evidence/recent` (tail N journal satırı, demo-safe projeksiyon); Astro panel (`panel.astro`) içinde **«Son işlem kanıtı»** özeti + **«Buradan devam»** eylemi; istemci tarafı dar gruplama kuralları; journal şeması ve yazım hook'ları v1'de **değişmez**.

**Bağımlılık:** **EC2-01** merge edildi (`5073780`, PR #256); **EC2-02** merge edildi (`bc6e4e0`, PR #258); **EC2-03** merge edildi (`b1c48aa`, PR #265); **EC2-04** merge edildi (`9475a0f`, PR #268); **EC2-13** merge edildi (`41a48fb`, PR #271). EC2-08 için sert önkoşullar **karşılandı**.

---

## Karar özeti

**Onaylı karar (firm):** Kullanıcı, panel üzerinden sunucu journal'ından türetilmiş **son işlem kanıtını** salt okunur görür; aynı yüzeyden ilgili göreve veya sohbet girişine **«Buradan devam»** ile yönlendirilir. Journal yalnızca sunucu tarafından okunur; istemci journal'a **yazmaz**. Yeni yazım hook'u veya şema sürümü v1'de **açılmaz**.

| # | Kural | Durum |
|---|--------|--------|
| CR1 | Read-only API: `GET /evidence/recent?limit=N` — `panel_tasks_server.py`; varsayılan `limit=20`, üst sınır `50` | `decision-approved` |
| CR2 | Yanıt yalnızca demo-safe alanlar: `ts`, `source`, `store`, `operation`, `phase`, `outcome`, `mutation`, `entity_ref`, `payload_summary`, `error.code` (message kısaltılmış) | `decision-approved` |
| CR3 | `correlation_id` API yanıtında **omit** veya kısaltılmış hash — ham UUID UI'da zorunlu değil; gruplama sunucu veya istemci kurallarıyla | `decision-approved` |
| CR4 | UI birincil yüzey: `ui/src/pages/panel.astro` — Görevler bölümü üstünde veya yanında kompakt «Son işlem kanıtı» şeridi | `decision-approved` |
| CR5 | «Buradan devam»: `entity_ref.id` varsa Görevler detayına odak; yoksa `payload_summary.title_preview` ile sohbet giriş alanına **prefill** (gönderim yok, kullanıcı onayı) | `decision-approved` |
| CR6 | Köprü `after`+`result` zinciri: `job_id` (result) + zaman yakınlığı (`ts` ≤60s) + aynı `operation` — EC2-13 BR11 ile hizalı | `decision-approved` |
| CR7 | Panel H1 `before`/`after`: aynı `correlation_id` (sunucu üretimi) — yalnızca `after` UI'da gösterilir; `before` isteğe bağlı debug | `decision-approved` |
| CR8 | `bridgeLast` istemci overlay **korunur** — journal kanıtı ile birleştirilmez; paralel «Son iletim» satırı kalır | `decision-approved` |
| CR9 | Journal okuma hatası panel mutasyonlarını **kırmaz**; UI boş durum metni gösterir | `decision-approved` |
| CR10 | EC2-01..04, EC2-13 merge **önkoşul** karşılandı | `verified` — PR #256, #258, #265, #268, #271 |

---

## Keşif özeti / mevcut boşluk

### Bugün hangi veri var?

| Kaynak | Journal | Bağlantı anahtarı | UI bugün |
|--------|---------|-------------------|----------|
| Panel H1 (`panel_tasks_server`) | `before`/`after`/`error`; `entity_ref.id` = `tsk_*` | Aynı `correlation_id` çifti | Yok |
| TaskEngine H2 | `engine.task.mutation` | `entity_ref` (engine id) | Panel UI'da yok |
| Köprü H3 EC2-03 | `bridge.task.post` `phase: after` | Bağımsız `correlation_id` | `bridgeLast` (istemci-only) |
| Köprü H5 EC2-13 | `bridge.task.post` `phase: result`; `job_id` | `job_id` + zaman/title heuristic | Yok |
| Guard H4a EC2-04 | `guard.decision` `after` | Bağımsız `correlation_id`; `entity_ref` yok | Yok |
| Policy H4b EC2-04 | `policy.blocked` `after` | Bağımsız `correlation_id` | Yok |
| EC2-02 client queue | Flush → H1 journal | `op_id` istemci-only; journal'da yok | Kuyruk gizli |

**Journal dosyası:** `.lumos/logs/evidence_continuity.jsonl` — append-only; rotation 1 MB × 3 (v1).

**Okuma yüzeyi bugün:** Yok. `panel_tasks_server.py` yalnızca `GET /tasks`, `/tasks/trash`, `/lumos-read-state` sunar; journal read endpoint **tanımlı değil**. `evidence_continuity.py` içinde read helper **yok** (yalnızca append + validate).

### Panel UI ipuçları (`panel.astro`)

| Öğe | Davranış | EC2-08 ilişkisi |
|-----|----------|-----------------|
| `bridgeLast` | İstemci meta overlay; «Son iletim» kart satırı | Journal kanıtı değil; CR8 ile korunur |
| EC2-02 pending-op kuyruğu | `localStorage`; flush REST | UI'da görünür değil; kanıt sunucu flush sonrası journal'da |
| «Köprü kanıtı doğrulandı» (chat) | Köprü yanıt doğrulama metni | Journal özeti değil |

**Kullanıcıya görünür semptom:** Görev mutasyonları, köprü yürütmesi ve guard/policy olayları journal'da birikir; panel kullanıcısı bunu **göremez**. Kopma sonrası «ne oldu?» sorusu `bridgeLast` veya chat metnine kalır — sunucu kanıt zinciri eksik kalır.

---

## EC2-01 / EC2-02 / EC2-03 / EC2-04 / EC2-13 bağımlılık doğrulaması

| Kontrol | Kanıt |
|---------|--------|
| EC2-01 merge | `5073780` — PR #256; `entity_ref.id` (`tsk_*`) panel create |
| EC2-02 merge | `bc6e4e0` — PR #258; client queue → H1 flush |
| EC2-03 merge | `b1c48aa` — PR #265; köprü `after` mirror |
| EC2-04 merge | `9475a0f` — PR #268; guard/policy `after` mirror |
| EC2-13 merge | `41a48fb` — PR #271; köprü `result` + `job_id` |
| Backlog sırası | `EC2-01..04, 13 ──► EC2-08` — [`evidence-continuity-v2-backlog.md`](./evidence-continuity-v2-backlog.md) § bağımlılık grafi |

**Sonuç:** Tüm sert önkoşullar **karşılandı**; EC2-08 implementasyon PR'ı açılabilir.

---

## Seçilen yol ve neden bu yol

### Seçenek 1: read-only tail API + panel.astro correlation şeridi

```
[LUMOS_BASE_DIR/logs/evidence_continuity.jsonl]
       │
       ▼
  read_recent_evidence_events(limit)   ← evidence_continuity.py (yeni read helper)
       │
       ▼
  GET /evidence/recent                 ← panel_tasks_server.py (yeni read-only route)
       │
       ▼
  panel.astro fetch + group + render   ← «Son işlem kanıtı» + «Buradan devam»
```

**Neden bu yol:**

1. **Minimum yazım yüzeyi** — mevcut H0–H5 hook'ları ve şema değişmez; yalnızca okuma eklenir.
2. **Truth kuralı** — journal sunucu truth; istemci yalnızca tüketir (EC2-02 CEQ4 ile uyumlu).
3. **Dar UI kapsamı** — tek birincil yüzey (`panel.astro`); legacy `panel/js/app.js` dışı (EC2-06).
4. **Demo-safe** — API yanıtı `payload_summary` izinli anahtarlarla sınırlı; ham journal dump yok.
5. **EC2-13 ile hizalı** — köprü zinciri `job_id` + heuristic; `correlation_id` propagate zorunlu değil.
6. **Public repo güvenli** — read-only, loopback panel sunucusu; yeni mutasyon veya dış yazma yok.

---

## Reddedilen alternatifler

| Alternatif | Red gerekçesi |
|------------|---------------|
| **İstemci `localStorage` kanıt kaynağı** | Truth kuralı ihlali; EC2-02 kuyruk journal değil |
| **Tam journal dump tarayıcıya** | Demo-safe / rotation riski; gereksiz payload |
| **`correlation_id` propagate zorunlu (runtime değişiklik)** | EC2-13 BR11 bilinçli erteleme; scope genişler |
| **`bridgeLast` → journal migrate** | Farklı semantik; istemci overlay (CEQ6/CR8) |
| **Structured query / reconstruct (EC2-11)** | P2; UI v1 için ağır |
| **Yeni şema `lumos.evidence_continuity.v2`** | EC2-14 CI; enum/payload yeterli |
| **Legacy panel `app.js` hizalama** | EC2-06 P2; Astro birincil |
| **Playwright E2E** | EC2-12 harness pytest yeterli; UI E2E v1 reddedildi |
| **`GET /evidence/query?correlation_id=`** | v1 dar kapsam; tail recent yeterli |
| **Guard/policy ↔ panel task otomatik link** | `entity_ref` yok; sahte correlation üretir |

---

## Minimum v1 tasarım

### Sunucu read katmanı

| Bileşen | Rol |
|---------|-----|
| `read_recent_evidence_events(base_dir, limit)` | JSONL tail read; bozuk satır skip; `validate_evidence_record` filtre |
| `project_evidence_for_ui(record)` | Demo-safe DTO; secret/PII strip |
| `GET /evidence/recent` | `panel_tasks_server.Handler`; CORS mevcut pattern |

**API yanıt şekli (örnek):**

```json
{
  "schema": "lumos.evidence_continuity.ui_projection.v1",
  "events": [
    {
      "ts": "2026-06-19T22:05:00.000Z",
      "source": "kando_bridge",
      "operation": "bridge.task.post",
      "phase": "result",
      "outcome": "ok",
      "entity_ref": null,
      "payload_summary": {
        "title_preview": "README düzelt",
        "route": "agent/async",
        "job_id": "a1b2c3d4e5f67890"
      }
    }
  ],
  "truncated": false
}
```

### İstemci gruplama (v1)

| Zincir tipi | Kural | UI etiketi |
|-------------|-------|------------|
| Panel mutasyon | Ardışık `before`+`after` aynı `correlation_id` (sunucu) veya yalnızca `after` | «Görev: {mutation}» |
| Köprü agent | `result` satırı; eşleşen `after` (±60s, aynı `title_preview` prefix) | «Köprü: {outcome}» |
| Guard/policy | Tekil `after` | «Koruma: {reason_code}» |
| Engine | Tekil satır | «Motor» (Görevler dışı; düşük öncelik gösterim) |

**«Son işlem kanıtı»:** Gruplanmış listeden **en yeni** olay — `ts` desc; özet satır: kaynak + işlem + outcome + `title_preview` (varsa).

**«Buradan devam»:**

| Koşul | Eylem |
|-------|-------|
| `entity_ref.id` mevcut | `#gorevler` sekmesi; ilgili görev kartı scroll + detay aç |
| Yalnızca `title_preview` | `#chat` sekmesi; giriş alanına prefill; **otomatik gönderim yok** |
| Guard/policy | Bilgi mesajı; görev linki yok (bilinçli) |

### UI yerleşim

- **Birincil:** Görevler listesi üstünde kompakt şerit (`aria-label="Son işlem kanıtı"`).
- **Boş durum:** «Henüz sunucu kanıtı yok» — journal boş veya API erişilemez.
- **Yenileme:** Sayfa yükleme + Görevler sekmesi görünür olduğunda fetch; periyodik poll **v1'de yok** (manuel refresh veya sekme değişimi yeterli).

---

## Değişecek dosyalar (gelecek implementasyon — şimdi yapılmaz)

| Dosya | Değişiklik |
|-------|------------|
| `src/core/evidence_continuity.py` | `read_recent_evidence_events`, `project_evidence_for_ui` |
| `panel/scripts/panel_tasks_server.py` | `GET /evidence/recent` handler |
| `ui/src/pages/panel.astro` | Fetch, gruplama, «Son işlem kanıtı» + «Buradan devam» UI |
| `tests/test_evidence_continuity_read_ec2_08.py` | **Yeni** — U1–U12 read + projection |
| `tests/test_panel_evidence_correlation_ui_ec2_08.py` | **Yeni** — API + gruplama mantığı (HTTP veya extract) |

**Bilerek dokunulmayacak (v1):**

- `packages/kando_bridge/src/kando_bridge/server.py` — H3/H5 yazım değişmez
- `src/kando/agent_runner.py`, `guard_audit.py`, `action_policy.py` — mirror hook'ları
- `panel/js/app.js` — legacy (EC2-06)
- Journal şema sürümü / yazım hook'ları
- EC2-05 store merge, EC2-09 retention, EC2-11 query

---

## Test planı

| # | Senaryo | Beklenen |
|---|---------|----------|
| U1 | Boş journal → `GET /evidence/recent` | `events: []`, 200 |
| U2 | 3 geçerli + 1 bozuk JSONL satırı | 3 event; bozuk skip |
| U3 | `limit=5` rotation sonrası | En yeni 5; `truncated` doğru |
| U4 | `payload_summary` yanıtında | Yalnızca izinli anahtarlar |
| U5 | Secret benzeri ek alan journal'da (test fixture) | Projection strip |
| U6 | Panel create `after` | UI DTO'da `entity_ref`, `mutation` |
| U7 | Köprü `after` + `result` çifti | Gruplama tek zincir; 2 ham → 1 özet |
| U8 | Guard deny tekil | Ayrı satır; «Buradan devam» görev linki yok |
| U9 | API unreachable | UI boş durum; mutasyon akışı etkilenmez |
| U10 | `entity_ref.id` → buradan devam | Görevler detay odak (DOM veya state assert) |
| U11 | Yalnızca `title_preview` → buradan devam | Chat prefill; submit yok |
| U12 | EC2-14 / EC2-03/04/13 testleri | Regresyonsuz |

---

## Riskler

| Risk | Etki | v1 mitigasyon |
|------|------|----------------|
| **`after`/`result` correlation kopuk** | Köprü zinciri eksik görünür | `job_id` + zaman/title heuristic; tek satır fallback |
| **Cross-source sahte link** | Yanlış «devam» hedefi | `entity_ref` zorunlu link; title-only prefill |
| **Journal rotation** | Eski kanıt UI'da yok | Bilinçli v1; EC2-09 retention ayrı |
| **Engine olayları panel bağlamı dışı** | Kafa karışıklığı | Düşük öncelik etiket veya filtre |
| **Prod loopback skip** | API fetch fail | Boş durum; `bridgeLast` paralel kalır |
| **Büyük journal tail read** | Panel sunucu yavaşlar | `limit` üst sınır 50; tail-only |
| **Public repo** | Hassas sızıntı | `project_evidence_for_ui` strip |

---

## Kapsam dışı v1

| Madde | Gerekçe |
|-------|---------|
| **`correlation_id` runtime propagate** | EC2-13 BR11; read-side heuristic yeterli |
| **`bridgeLast` journal merge** | İstemci overlay; CR8 |
| **Structured query (EC2-11)** | P2 |
| **Retention politikası (EC2-09)** | P2 |
| **Store merge (EC2-05)** | Ayrı OD |
| **Legacy panel (EC2-06)** | Astro birincil |
| **Chat geçmişi replay** | PII |
| **Guard/policy → görev otomatik eşleme** | `entity_ref` yok |
| **Real-time WebSocket push** | Poll/stream v1 dışı |
| **Yazım hook / şema değişikliği** | EC2-08 yalnızca okuma + UI |

---

## Bağımlılıklar ve çapraz referanslar

| Belge / artefakt | İlişki |
|------------------|--------|
| [`evidence-continuity-ec2-03-decision.md`](./evidence-continuity-ec2-03-decision.md) | Köprü `after`; correlation kopuk bilinçli |
| [`evidence-continuity-ec2-04-decision.md`](./evidence-continuity-ec2-04-decision.md) | Guard/policy `after`; panel policy boşluğu |
| [`evidence-continuity-ec2-13-decision.md`](./evidence-continuity-ec2-13-decision.md) | `result` + `job_id`; BR11 UI bağlantısı |
| [`evidence-continuity-ec2-02-decision.md`](./evidence-continuity-ec2-02-decision.md) | Client queue gizli; flush sonrası journal |
| [`evidence-continuity-ec2-12-decision.md`](./evidence-continuity-ec2-12-decision.md) | DR harness; UI test ayrı pytest |
| EC2-14 / PR #255 | Şema CI — yazım değişmez |
| [`primary-user-surface-decision.md`](./primary-user-surface-decision.md) | `panel.astro` birincil |

---

## Sonraki adım

1. **Backlog senkron:** v2 backlog EC2-08 → `[decision-approved]` ✓.
2. **Implementasyon PR:** yukarıdaki dosya listesi; tek sorumluluk PR.
3. **Doğrulama:** U1–U12 pytest; manuel panel spot check (journal dolu ortam).

---

**İndeks notu:** EC2-08 ayrı OD kaydı açmaz; v2 backlog + bu belge canonical. `docs/decision-log.md` DL-A07 satırı ile senkron.

---

Son güncelleme: 2026-06-20 (karar onaylandı — `[decision-approved]`)
