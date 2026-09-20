<!-- markdownlint-disable MD013 -->

# Lumos Duvar v1 — görev ve ajan sözleşmesi

| Alan | Değer |
| --- | --- |
| Durum | **Yürürlükte — 2026-09-19 kurucu onayı** (çerçeve: 2026-09-18 kurucu kararı) — hukuk bu dilimde; ekran yok |
| Karar | [ADR-032](../decisions/ADR-032-lumos-wall-v1.md) (Accepted) |
| Ad | **Duvar = Lumos Board'un iç operasyon yüzü.** Katmanın resmi adı Lumos Board'dur ([ADR-008](../decisions/ADR-008-agent-network-boundary.md)); "Duvar" bu sözleşmenin ve operasyon yüzünün adıdır, ikinci bir katman değildir |
| Üst sınır | [CONSTITUTION.md](../CONSTITUTION.md) (metin burada kopyalanmaz) |
| Yazma kapısı | Mevcut [`task-claim-v1.md`](task-claim-v1.md) + `src/lumos_board/claim_cli.py` / `task_claim.py` |
| Bu dilim | Sözleşme. Yeni claim deposu, yeni CLI, yeni sayfa, yeni UI **yok** |

Duvar, mevcut Lumos Board + claim + anayasa **üstünde** oturan iç operasyon
yüzüdür. Paralel sahiplik sistemi kurulmaz. Görsel yüz (ayrı onay) yalnız
bu sözleşmenin görüntüsüdür; iş mantığı UI'ya gömülmez.

## Ana yasa

> **Duvar'da kaydı olmayan iş, Lumos açısından yürütülen iş sayılmaz.**

Uygulama karşılığı bugün **kısmidir**: claim olayları `claim_events.jsonl`
append-only denetim izinde tutulur ([task-claim-v1](task-claim-v1.md) kural 11),
ancak claim'siz görev kaydı tutan bir Duvar envanteri henüz yoktur (bkz.
§ Mevcut altyapıyla eşleme). Ana yasa bu boşluğu kapatana kadar davranış
kuralı olarak geçerlidir; kapatan katman ayrı onay ister.

## Teknik kilit

> **`claim_cli` tek yetkili yazma/claim kapısıdır; Duvar, claim durumunu tüketir ve gösterir, ayrı claim üretmez.**

Duvar, bu kapının üstüne **görev durumu, sahiplik, kanıt, çakışma ve kurucu
kapısını** görünür hale getirir. Paralel claim, ikinci lease veya ayrı yazma
kapısı açılmaz. Görsel Duvar sonraki dilimdir; iş mantığı UI'ya dağılmaz.

Kayıt = Duvar görev kartı + KA-002 claim (yazma varsa). Sohbet cümlesi,
dal üzerindeki commit veya "ben yaptım" Duvar kaydının yerine geçmez.
Anayasa maddeleri ([CONSTITUTION.md](../CONSTITUTION.md) §3 sahiplik, §9 kanıt,
§10 kurucu süzgeci, §11 merge/yazma yetkisi) burada tekrar yazılmaz; çelişide
anayasa geçerli kalır.

## Sekiz madde

### 1. Tek aktif sahip

Her aktif görevin aynı anda bir `owner_agent`ı olur. `owner_agent`, claim
kaydındaki `owner` alanıdır; ikinci bir sahip kimliği icat edilmez. Başka ajan
göreve bakabilir, yazamaz.

Devir (delegation) istisnası bu maddeyle çelişmez: alt görev parent kapsamı
içinde **ayrı bir `task_id`** ve ayrı bir owner taşır; her görev kimliği yine
tek sahiplidir ve parent'ın görev kimliği devirle ikinci kez aktifleşemez
([task-claim-v1](task-claim-v1.md) kural 5).

### 2. Claim zorunluluğu

Ajan yazmaya başlamadan görevi **mevcut** claim kapısından alır
(`python -m lumos_board.claim_cli claim` → `TaskClaimStore`). Claim yoksa
yalnız okuyabilir (`list` komutu claim istemez). Yeni lease, yeni store veya
ikinci CLI **yasaktır**.

Güven sınırı: v1'de kimlikler (`owner`, `actor`) **self-asserted**'dır ve
claim'i hiç çağırmayan bir yazıcıyı fiilen durduran teknik zorlayıcı yoktur
([task-claim-v1](task-claim-v1.md) § Güven sınırı — kooperatif ajan varsayımı).
Bu madde o varsayımı davranış kuralı olarak bağlar; zorlayıcı kapı ayrı bir
dilimdir ve bu sözleşmeyle kurulmaz.

### 3. Çalışma alanı beyanı

`repo` / `branch` / `worktree` / dosya kapsamı göreve bağlıdır. Kaynak claim
alanlarıdır (`task-claim-v1` zorunlu alanlar). Duvar bunları karta yansıtır;
ayrı bir workspace şeması açılmaz.

### 4. Durum makinesi

Görev yaşamı (Duvar):

```text
INBOX → CLAIMED → WORKING → TEST → FOUNDER_REVIEW → READY → CLOSED
```

Yan durumlar: `BLOCKED`, `PARKED`.

Bu küme **claim `ClaimStatus` yerine geçmez.** Claim değerleri kodda sabit:
`ACTIVE`, `QUEUED`, `RELEASED`, `EXPIRED`, `OVERRIDDEN`
(`src/lumos_board/task_claim.py`). Duvar durumu, claim + ajan-status üzerine
projeksiyondur:

| Duvar | ClaimStatus | Not |
| --- | --- | --- |
| `INBOX` | kayıt yok | Yazma yok |
| `CLAIMED` | `ACTIVE` | Sahiplik alındı |
| `WORKING` | `ACTIVE` | Yazma/üretim |
| `TEST` | `ACTIVE` | Doğrulama |
| `FOUNDER_REVIEW` | `ACTIVE` | Anayasal insan kapısı; kapsam inceleme bitene dek bırakılmaz |
| `READY` | `ACTIVE` | Kanıt bağlı; merge izni değil; kapsam `CLOSED`'a kadar tutulur |
| `CLOSED` | `RELEASED` | Görev kapandı |
| `BLOCKED` | `ACTIVE` | İnsan-dışı bekleyiş; sahip lease'i tutmaya devam eder |
| `PARKED` | `RELEASED` | Bilinçli park; kapsam serbest kalır, rehin tutulmaz; `FOUNDER_REVIEW` değildir |

Eşleme kilidi (2026-09-18 kurucu kararı): `READY` = `ACTIVE`,
`PARKED` = `RELEASED`, `BLOCKED` = `ACTIVE`. `QUEUED` bir Duvar görev durumu
değildir; kapsam sırasında bekleyen **ikinci isteklinin** lease hâlidir ve
Duvar'da çakışma/kuyruk göstergesi olarak görünür (Madde 6).

Lease yükümlülüğü ve istisna yolları: claim TTL varsayılanı 1800 sn'dir ve
heartbeat sahip yükümlülüğüdür (`claim_cli heartbeat`); TTL dolarsa claim
`EXPIRED` olur. `EXPIRED` veya `OVERRIDDEN` (insan-onaylı devralma) sonrası
görev Duvar'da `INBOX`'a döner; kapsam yeniden alınabilir.

Ajan anlık koşu hali ayrıdır: [agent-status-v1.md](agent-status-v1.md) /
[v2](agent-status-v2.md). v2 `awaiting_decision` Duvar `FOUNDER_REVIEW` ile
hizalanır; `blocked` Duvar `BLOCKED` ile. `PARKED` ajan-status'a yeni enum
eklemez.

### 5. Kanıt zorunluluğu

"Bitti" sözü yetmez. `READY` ve `CLOSED` ancak commit, PR, test veya log
işaretçisi karta bağlanınca geçerlidir. Kanıt merdiveni anayasa §9; içerik
kopyalanmaz, referans verilir.

### 6. Çakışma koruması

Aynı dosya veya aynı görev alanında ikinci yazıcı **bloklanır**; sessiz
paralel yazma yok. Duvar conflict'i **gösterir**; uygulayan kapı mevcut
claim kurallarıdır: `DUPLICATE_TASK`, `SCOPE_CONFLICT`, kuyruk, devir,
override ([task-claim-v1.md](task-claim-v1.md)). Duvar yeni bir kilit icat
etmez.

### 7. Kurucu kapısı

Merge, deploy veya yetki genişletme gibi anayasal sınırlar (anayasa §11 ve
yayın kapısı) gerektiğinde görev otomatik `FOUNDER_REVIEW`e geçer. Ajan bu
durumu `READY` veya `CLOSED` ilan edemez. `READY`, kurucuya **karar** düşürür;
üçlü merge kapısını yeşil saymaz.

İnsan kapısının bugünkü somut örneği claim override akışıdır ve **aynen
korunur**: HMAC imzalı approval token, fail-closed approver registry ve
"override onaycısı eski ve yeni owner'lardan farklı olmalı" kuralı
([task-claim-v1](task-claim-v1.md) kural 8–10, `OverrideApprovalVerifier`).
Bu sözleşme o kuralları gevşetmez, genişletmez. Override, aşağıdaki onay
şemasının uygulaması değildir.

Kurucu kararı Duvar kartına düştüğünde kayıt [onay şeması v1](#onay-şeması-v1-sözleşme-gereksinimi)
alanlarını taşır; minimal kayıt deposu 2026-09-20 kurucu talimatıyla
uygulanmıştır (`lumos_board.founder_approval` + `claim_cli approval`).

### 8. Gürültü ayıklama

Kurucuya yalnız `karar`, `risk`, `blokaj`, `tamamlanma` çıkar. Normal ajan
hareketi (heartbeat, retry, log, dal gürültüsü) Duvar'da kalır. Bu süzgeç
anayasa §10'un operatör→kurucu kanalıdır; dördüncü bir rapor dili yazılmaz.

## Onay şeması v1 (sözleşme gereksinimi)

Minimal kayıt deposu 2026-09-20 kurucu talimatıyla uygulanmıştır:
`src/lumos_board/founder_approval.py` (FounderApprovalStore, append-only
`founder_approval_events.jsonl` denetim izi) ve mevcut tek kapı içinde
`python -m lumos_board.claim_cli approval request|grant|check|list`.
`grant`, `LUMOS_FOUNDER_APPROVER_REGISTRY` ile verilen fail-closed insan
onaycı allowlist'ini zorunlu kılar. İmza servisi, GitHub CheckRun veya
yayın güvenlik kökü **hâlâ açılmaz.** Anayasa metni bu dilimde değişmez;
anayasa farkı ayrı açık karardır. Yayın güvenliği uygulaması ayrı hattır
ve bu eke izin bağlanmaz.

Kurucu onayı (Madde 7 / `FOUNDER_REVIEW` → karar) kayda geçecekse aşağıdaki
altı alan zorunlu gereksinimdir. Boş kayıt, bekleyen kayıt olabilir; uydurma
`approved_by` yazılamaz.

| Alan | Anlam |
| --- | --- |
| `approval_id` | Bu onay kaydının kimliği |
| `task` | Duvar / claim görev kimliği |
| `gate` | Hangi kapı için verildiği (ör. kurucu inceleme; üçlü merge kapısı 3). İsim yeni bir kapı icat etmez |
| `action` | Ne onaylandı; kapsam bundan okunur |
| `head_sha` | Onayın bağlandığı commit. Head değişince sayaç sıfırlanır |
| `approved_by` | Nihai insan yetkili. Ajan, bot veya App bu alanı insan onayı olarak dolduramaz |

Tek nihai yetkili kurucudur; ikinci insan şartı yoktur.

Aynı geçerli onay tekrar sorulmaz: `task` + `gate` + `action` + `head_sha`
eşleşen ve `approved_by` dolu bir kayıt varken Lumos, verilen kapsamda aynı
soruyu yeniden açmaz. Farklı `action`, farklı `gate` veya yeni `head_sha`
yeni kayıttır.

Bu şema, claim override HMAC'inden ayrıdır (lease devralma; task-claim-v1
kural 8–10). İnsan etkileşimli yayın imzası ve PR'ın değiştiremediği
doğrulayıcı bu dilimin kapsamı değildir.

## Mevcut semantikle çelişki kontrolü (madde madde)

Sekiz maddenin KA-002 semantiğiyle (`task_claim.py` / `claim_cli.py`) çelişip
çelişmediği tek tek kontrol edilmiştir (2026-09-18):

| Madde | Kontrol edilen KA-002 semantiği | Sonuç |
| --- | --- | --- |
| 1 | `DUPLICATE_TASK`, sahip-dışı heartbeat/release reddi; delegation'da alt görevin ayrı `task_id` taşıması | Çelişki yok — delegation tek-sahip ilkesini bozmaz |
| 2 | `list` claim istemez; claim yazma öncesi kapıdır; kimlikler self-asserted (güven sınırı) | Çelişki yok — madde güven sınırını daraltmaz, davranış kuralı ekler |
| 3 | `repo/branch/worktree/scopes` zorunlu; kök kapsam yasak | Çelişki yok — birebir örtüşür |
| 4 | `ClaimStatus` beş durumu, `QUEUED` yer tutma + `started_at` terfisi, TTL/`EXPIRED`, kaskadlı öksüz kapama | Çelişki yok — Duvar durumu claim ekseninin **üstüne** projeksiyondur, hiçbir ClaimStatus geçişi değişmez |
| 5 | `attach_pr` yalnız sahip ve açık claim | Çelişki yok — kanıt kümesi genişletilir, mevcut kural daraltılmaz |
| 6 | `SCOPE_CONFLICT` üst-alt dizin ilişkisi; ret veya `QUEUED`; tek OS dosya kilidi | Çelişki yok — "conflict işareti" = mevcut `ClaimConflict` kaydı |
| 7 | Override: imzalı token + fail-closed registry + onaycı ≠ owner'lar; override ile devir aynı istekte birleşemez | Çelişki yok — kurucu kapısı bu kuralları aynen korur, gevşetmez |
| 8 | Audit append-only, yalnız kalıcılaşan durum yazılır | Çelişki yok — süzgeç okuma katmanındadır, audit'e dokunmaz |
| Onay şeması v1 | Override `approval_id` / HMAC token (lease) | Çelişki yok — Duvar onay şeması ayrı depodadır (`founder_approval.py`); override HMAC'ine dokunmaz |

## Mevcut altyapıyla eşleme

| Madde | `task_claim.py` / `claim_cli.py` karşılığı | CONSTITUTION karşılığı | Durum |
| --- | --- | --- | --- |
| 1. Tek aktif sahip | `DUPLICATE_TASK`, `owner`, sahip-dışı işlem reddi | §3 | **VAR** |
| 2. Claim zorunluluğu | `claim` komutu, atomik kapı; zorlayıcı engel yok (kooperatif güven sınırı) | §3 | **KISMİ** |
| 3. Çalışma alanı beyanı | `repo/branch/worktree/scopes` zorunlu alanlar | — | **VAR** |
| 4. Durum makinesi | Claim ekseni tam (`ClaimStatus`); Duvar ekseni (`INBOX`/`TEST`/`FOUNDER_REVIEW`/`PARKED`) hiçbir store'da yok | — (agent-status v1/v2 yalnız projeksiyon) | **KISMİ** |
| 5. Kanıt zorunluluğu | `attach_pr` (PR kanıtı); commit/test/log kanıt alanı yok | §9 | **KISMİ** |
| 6. Çakışma koruması | `SCOPE_CONFLICT`, `QUEUED`, OS dosya kilidi | §3 | **VAR** |
| 7. Kurucu kapısı | Override insan kapısı var; otomatik `FOUNDER_REVIEW` tetikleyicisi yok | §11, §2 | **KISMİ** |
| 8. Gürültü ayıklama | Audit Duvar içi; kurucu-yüzü süzgeç mekanizması yok (agent-status-v2 ayrımı sözleşmede) | §10 | **KISMİ** |
| Onay şeması v1 | Altı alan (`approval_id` `task` `gate` `action` `head_sha` `approved_by`) `founder_approval.py` + `claim_cli approval`; imza kökü/CheckRun yok; override HMAC ayrı | — (anayasa farkı ayrı karar) | **VAR** |
| Ana yasa | Append-only claim audit'i var; claim'siz görev envanteri yok | §9 | **KISMİ** |

**Boşlukların ortak paydası:** eksik olan claim mekanizması değil, claim'in
üstündeki **görev-kaydı katmanıdır** (Duvar ekseni durumları + kanıt alanları +
kurucu-yüzü süzgeç). Bu katman [ADR-008](../decisions/ADR-008-agent-network-boundary.md)
taksonomisindeki Task Queue / Agent Status'a denk düşer ve OD-063 kapsamındaki
"yazıcı tarafı ayrı onay ister" kuralına tabidir — bu sözleşme onun için izin
değil, gereksinim kaydıdır.

## Görsel yüz (yetkisiz)

Ekran, kart ve kuyruk bu maddelerin **görüntüsüdür**. İş mantığı CSS/sayfaya
gömülmez. Yeni sayfa STOP LIST'tedir; görsel dilim ayrı kurucu onayı ister.

## Bilinçli yapılmaz

- İkinci `TaskClaimStore` veya `claim_cli` çatalı
- Anayasa maddelerinin bu dosyaya kopyalanması; bu dilimde anayasa dosyasına yazma
- Onay şeması için imza kökü, imza servisi veya GitHub CheckRun (minimal depo/CLI 2026-09-20 diliminde uygulandı)
- Ajanlar arası komut ağı, auto-merge, auto-deploy
- Son kullanıcı paneline claim/worktree sızdırma (PR-005 / ADR-019)
