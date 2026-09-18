<!-- markdownlint-disable MD013 -->

# Lumos Board (Duvar) Çalışma Sözleşmesi v1 — TASLAK

| Alan | Değer |
| --- | --- |
| Durum | **TASLAK — kurucu onayı bekliyor.** Bu belge kod izni değildir; merge edilene kadar hiçbir kuralı yürürlükte saymaz. |
| Tarih | 2026-09-18 |
| Dayanak | Kurucu kararları (2026-09-18, sekiz madde + ana yasa, birebir çerçeve); OD-063 minimal dilim yetkisi; [ADR-008](../decisions/ADR-008-agent-network-boundary.md) § Lumos Board (blackboard, star topology) |
| Katman | Süreç sözleşmesi. Mevcut KA-002 claim altyapısının (`src/lumos_board/task_claim.py`, `src/lumos_board/claim_cli.py`, [task-claim-v1](task-claim-v1.md)) **üstüne** oturur; yeni veya paralel claim mekanizması **kurmaz**. |
| Kapsam dışı | UI/görsel yüz (önce hukuk, sonra ekran; iş mantığı UI'ya gömülmez). Board yazıcı tarafı ayrı kurucu onayı ister (OD-063). #366/#368/#369, #858, #859/#860/#861 ve iOS RC zinciri bu işin dışındadır. |

**Kapsam notu (2026-09-18):** Bu belge kurucunun 2026-09-18 tarihli sekiz maddelik çerçevesini kayda geçirir ve her maddeyi mevcut altyapıyla eşler. "Mevcut altyapı" iddiaları bu tarihte `task_claim.py`, `claim_cli.py`, `agent_status.py`, `coordination_gateway.py` ve ilgili sözleşme belgeleri okunarak doğrulanmıştır. Karar durumu (kurucu çerçevesi) ile uygulama durumu (kod karşılığı) her maddede ayrı yazılır.

---

## 0. Ana yasa

> **"Duvar'da kaydı olmayan iş, Lumos açısından yürütülen iş sayılmaz."**

Bu, [CONSTITUTION](../CONSTITUTION.md) 9. maddesindeki kanıt ilkesinin ve 3. maddesindeki sahiplik ilkesinin Duvar'a uygulanmış hâlidir — o maddeleri değiştirmez, onlara referans verir. Uygulama karşılığı bugün kısmidir: claim olayları `claim_events.jsonl` append-only denetim izinde tutulur (task-claim-v1 kural 11), ancak claim'siz görev kaydı tutan bir Duvar envanteri yoktur (bkz. § Eşleme tablosu).

---

## Maddeler

### Madde 1 — Tek aktif sahip

Her aktif görevin aynı anda tek bir `owner_agent`'ı olur.

- **Altyapı bağı (VAR):** `TaskClaimStore.claim` aynı repo içindeki aktif aynı `task_id`'yi `DUPLICATE_TASK` ile reddeder; `heartbeat`, `release` ve `attach_pr` yalnız kayıt sahibince yapılabilir (`_require_owned_open`, task-claim-v1 kural 1 ve 7).
- **Devir istisnası çelişki değildir:** alt görev (delegation) parent kapsamı içinde ayrı bir `task_id` ve ayrı bir owner taşır; her görev kimliği yine tek sahiplidir (task-claim-v1 kural 5).

### Madde 2 — Claim zorunluluğu

Ajan yazmaya başlamadan görevi claim eder; claim yoksa yalnız okuyabilir.

- **Altyapı bağı (KISMİ):** claim kapısı `python -m lumos_board.claim_cli claim` ile vardır ve atomiktir (OS dosya kilidi, task-claim-v1 kural 3); `list` komutu okuma için claim istemez — "claim'siz yalnız okuma" ile uyumlu.
- **Boşluk:** claim'i hiç çağırmayan bir yazıcıyı fiilen durduran teknik zorlayıcı yoktur; v1 güven sınırı kooperatif ajan varsayımıdır (task-claim-v1 § Güven sınırı). Bu madde o varsayımı **davranış kuralı** olarak bağlar; zorlayıcı kapı ayrı bir dilimdir ve bu sözleşmeyle kurulmaz.
- CONSTITUTION 3. maddesi ("yazmaya başlamadan sahiplik/claim kontrol edilir") bu maddenin anayasal dayanağıdır.

### Madde 3 — Çalışma alanı beyanı

Repo/branch/worktree/dosya kapsamı göreve bağlı olur.

- **Altyapı bağı (VAR):** `TaskClaim` alanları `repo`, `branch`, `worktree` ve repo-relative `scopes` zorunludur; en az bir kapsam şarttır, repo kökü kapsam olarak alınamaz, mutlak yol ve `..` reddedilir (`_normalize_scopes`). CLI'da `--repo --branch --worktree --scope` zorunlu argümanlardır.

### Madde 4 — Durum makinesi

Görev yaşam döngüsü: `INBOX → CLAIMED → WORKING → TEST → FOUNDER_REVIEW → READY → CLOSED`; ayrıca `BLOCKED` ve `PARKED`.

- **İki eksen, tek makine değil:** bu durum kümesi **görev** eksenidir. `ClaimStatus` (`ACTIVE / QUEUED / RELEASED / EXPIRED / OVERRIDDEN`) ise **sahiplik lease'i** eksenidir ve değişmez. Bu sözleşme ClaimStatus'u yeniden tanımlamaz; iki ekseni şöyle bağlar:

| Görev durumu (bu sözleşme) | Claim karşılığı (`task_claim.py`) | Not |
| --- | --- | --- |
| INBOX | Claim yok | Sahipsiz görev; bugün store'da karşılığı yok (claim'siz görev kaydı tutulmuyor) |
| CLAIMED / WORKING / TEST | `ACTIVE` (heartbeat sürdürülür) | TTL varsayılan 1800 sn; heartbeat sahip yükümlülüğüdür |
| Sıra bekleyen ikinci istekli | `QUEUED` | Yer tutar, `started_at` sırasıyla otomatik terfi eder (kural 12) |
| BLOCKED | `ACTIVE` kalır + agent-status-v2 `blocked` (insan-dışı bekleme) | [agent-status-v2](agent-status-v2.md) `blocked`/`awaiting_decision` ayrımı esastır |
| FOUNDER_REVIEW | `ACTIVE` kalır + agent-status-v2 `awaiting_decision` + `decision_ref` | Kapsam inceleme bitene dek serbest bırakılmaz |
| READY / CLOSED | `RELEASED` | Kanıt bağlanmadan geçilemez (Madde 5) |
| PARKED | `RELEASED` (kapsam serbest kalır) | Görev kaydı olarak "park" alanı bugün yok |
| — (istisna yolları) | `EXPIRED`, `OVERRIDDEN` | TTL dolması veya insan-onaylı devralma; görev INBOX'a döner |

- **Uygulama durumu (KISMİ/YOK):** claim ekseni tamamen mevcuttur; görev ekseni (`INBOX`, `TEST`, `FOUNDER_REVIEW`, `PARKED` alanları) hiçbir store'da tutulmamaktadır. agent-status-v2 salt-okunur projeksiyondur, görev durumu deposu değildir.

### Madde 5 — Kanıt zorunluluğu

"Bitti" sözü yetmez; commit/PR/test/log kanıtı bağlanmadan görev READY/CLOSED olamaz.

- **Anayasal dayanak:** CONSTITUTION 9. maddesi (kanıt beyandan üstündür; scope-accounting merdiveni) — kopyalanmaz, uygulanır.
- **Altyapı bağı (KISMİ):** PR kanıtı için `attach_pr` / `claim_cli attach-pr` vardır ve yalnız sahip bağlayabilir; olay audit'e yazılır (`CLAIM_PR_ATTACHED`). Commit SHA / test sonucu / log referansı için ayrı kanıt alanı yoktur.

### Madde 6 — Çakışma koruması

Aynı dosya/görev alanında ikinci yazıcı = conflict işareti; sessiz paralel yazma yok.

- **Altyapı bağı (VAR):** eşit veya üst-alt dizin ilişkili kapsamlar `SCOPE_CONFLICT`, aynı görev `DUPLICATE_TASK` üretir (`_find_conflicts`, `ClaimConflict`); ikinci istekli reddedilir (CLI çıkış kodu 2) veya `--queue` ile sırada bekler. Kontrol ve kayıt tek OS dosya kilidi altındadır (task-claim-v1 kural 2–4, 12).

### Madde 7 — Kurucu kapısı

Merge/deploy/yetki genişletme gibi anayasal sınırlar gerekiyorsa görev otomatik `FOUNDER_REVIEW`'a geçer.

- **Anayasal dayanak (kopyalanmaz, bağlanır):** hangi eylemlerin insan kapısı gerektirdiğini bu sözleşme tanımlamaz; [CONSTITUTION](../CONSTITUTION.md) 11. maddesi (tek kontrollü çekirdek yazıcısı; Lumos yetkisini kendisi genişletemez) ve 2. maddesi (en yeni açık kullanıcı kararı otoritedir; çelişkide `DECISION_CONFLICT`) esastır. ADR-027 oradaki referansıyla geçerlidir.
- **Altyapı bağı (KISMİ):** insan kapısının mevcut somut örneği override akışıdır: HMAC imzalı approval token, fail-closed approver registry ve "override onaycısı eski ve yeni owner'lardan farklı olmalı" kuralı (`OverrideApprovalVerifier`, task-claim-v1 kural 8–10) bu sözleşmeyle **aynen korunur**. "Otomatik FOUNDER_REVIEW'a geçiş" tetikleyicisi ise bugün yoktur; Madde 4'teki görev ekseni boşluğuna bağlıdır.

### Madde 8 — Gürültü ayıklama

Kurucuya yalnız karar/blokaj/risk/tamamlanma çıkar; normal ajan hareketleri Duvar'da kalır.

- **Anayasal dayanak:** CONSTITUTION 10. maddesi (kullanıcı yalnız dört şey görür) — birebir aynı ilke; kopyalanmaz, referans verilir.
- **Altyapı bağı (KISMİ):** agent-status-v2, insana yalnız `awaiting_decision` gösterme ayrımını sözleşme düzeyinde tanımlar; claim audit olayları (heartbeat, promotion vb.) Duvar içi kayıttır ve kurucuya taşınmaz. Kurucu-yüzü filtre mekanizması (Decision Queue) henüz inşa edilmemiştir.

---

## Mevcut semantikle çelişki kontrolü (madde madde)

Kurucu çerçevesinin KA-002 semantiğiyle çelişip çelişmediği tek tek kontrol edilmiştir:

| Madde | Kontrol edilen KA-002 semantiği | Sonuç |
| --- | --- | --- |
| 1 | `DUPLICATE_TASK`, sahip-dışı heartbeat/release reddi; delegation'da alt görevin ayrı `task_id` taşıması | Çelişki yok — delegation tek-sahip ilkesini bozmaz |
| 2 | `list` claim istemez; claim yazma öncesi kapıdır; kimlikler self-asserted (güven sınırı) | Çelişki yok — madde güven sınırını daraltmaz, davranış kuralı ekler |
| 3 | `repo/branch/worktree/scopes` zorunlu; kök kapsam yasak | Çelişki yok — birebir örtüşür |
| 4 | `ClaimStatus` beş durumu, `QUEUED` yer tutma + `started_at` terfisi, TTL/`EXPIRED`, kaskadlı öksüz kapama | Çelişki yok — görev ekseni claim ekseninin **üstüne** eklenir, hiçbir ClaimStatus geçişi değişmez |
| 5 | `attach_pr` yalnız sahip ve açık claim | Çelişki yok — kanıt kümesi genişletilir, mevcut kural daraltılmaz |
| 6 | `SCOPE_CONFLICT` üst-alt dizin ilişkisi; ret veya `QUEUED`; tek dosya kilidi | Çelişki yok — "conflict işareti" = mevcut `ClaimConflict` kaydı |
| 7 | Override: imzalı token + fail-closed registry + onaycı ≠ owner'lar; override ile devir aynı istekte birleşemez | Çelişki yok — kurucu kapısı bu kuralları aynen korur, gevşetmez |
| 8 | Audit append-only, yalnız kalıcılaşan durum yazılır | Çelişki yok — filtre okuma katmanındadır, audit'e dokunmaz |

---

## Mevcut altyapıyla eşleme tablosu

| Kurucu maddesi | `task_claim.py` / `claim_cli.py` karşılığı | CONSTITUTION karşılığı | Durum |
| --- | --- | --- | --- |
| 1. Tek aktif sahip | `DUPLICATE_TASK`, `owner`, `_require_owned_*` | 3. madde | **VAR** |
| 2. Claim zorunluluğu | `claim` komutu, atomik kapı; zorlayıcı engel yok (kooperatif güven sınırı) | 3. madde | **KISMİ** |
| 3. Çalışma alanı beyanı | `repo/branch/worktree/scopes` zorunlu alanlar | — | **VAR** |
| 4. Durum makinesi | Claim ekseni tam (`ClaimStatus`); görev ekseni (INBOX/TEST/FOUNDER_REVIEW/PARKED) hiçbir store'da yok | — (agent-status-v2 yalnız projeksiyon) | **KISMİ** |
| 5. Kanıt zorunluluğu | `attach_pr` (PR kanıtı); commit/test/log alanı yok | 9. madde | **KISMİ** |
| 6. Çakışma koruması | `SCOPE_CONFLICT`, `QUEUED`, OS dosya kilidi | 3. madde (sessiz üzerine yazma yasağı) | **VAR** |
| 7. Kurucu kapısı | Override insan kapısı var; otomatik FOUNDER_REVIEW tetikleyicisi yok | 11. ve 2. madde | **KISMİ** |
| 8. Gürültü ayıklama | Audit Duvar içi; kurucu-yüzü filtre yok (agent-status-v2 ayrımı sözleşmede) | 10. madde | **KISMİ** |
| Ana yasa | Append-only claim audit'i var; claim'siz görev envanteri yok | 9. madde | **KISMİ** |

**Boşlukların ortak paydası:** eksik olan claim mekanizması değil, claim'in üstündeki **görev kaydı katmanıdır** (görev ekseni durumları + kanıt alanları + kurucu-yüzü filtre). Bu katman ADR-008'deki Task Queue/Agent Status taksonomisine denk düşer ve OD-063 kapsamındaki "yazıcı tarafı ayrı onay ister" kuralına tabidir — bu sözleşme onun için izin değil, gereksinim kaydıdır.

## Yürürlük

1. Bu taslak kurucu onayı olmadan yürürlüğe girmez; PR draft olarak açılır ve merge edilmez (çekirdek sözleşme = insan kapısı; `main` merge'i prod deploy'dur).
2. Onaylandığında da **kod izni doğurmaz**: görev ekseni store'u, kurucu-yüzü filtre ve her türlü Duvar yazıcısı ayrı kurucu kararı ister (OD-063).
3. Değişiklik usulü CONSTITUTION başlığındaki kuralla aynıdır: yalnız kurucu kararıyla, tarihli commit ile.
