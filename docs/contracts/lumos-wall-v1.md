<!-- markdownlint-disable MD013 -->

# Lumos Duvar v1 — görev ve ajan sözleşmesi

| Alan | Değer |
| --- | --- |
| Durum | **Kilitli (2026-09-18 kurucu kararı)** — hukuk bu dilimde; ekran yok |
| Karar | [ADR-032](../decisions/ADR-032-lumos-wall-v1.md) |
| Üst sınır | [CONSTITUTION.md](../CONSTITUTION.md) (metin burada kopyalanmaz) |
| Yazma kapısı | Mevcut [`task-claim-v1.md`](task-claim-v1.md) + `src/lumos_board/claim_cli.py` / `task_claim.py` |
| Bu dilim | Sözleşme. Yeni claim deposu, yeni CLI, yeni sayfa, yeni UI **yok** |

Duvar, mevcut Lumos Board + claim + anayasa **üstünde** oturan iç operasyon
merkezidir. Paralel sahiplik sistemi kurulmaz. Görsel yüz (ayrı onay) yalnız
bu sözleşmenin görüntüsüdür; iş mantığı UI'ya gömülmez.

## Ana yasa

> **Duvar'da kaydı olmayan iş, Lumos açısından yürütülen iş sayılmaz.**

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

### 2. Claim zorunluluğu

Ajan yazmaya başlamadan görevi **mevcut** claim kapısından alır
(`python -m lumos_board.claim_cli claim` → `TaskClaimStore`). Claim yoksa
yalnız okuyabilir. Yeni lease, yeni store veya ikinci CLI **yasaktır**.

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
| `FOUNDER_REVIEW` | `ACTIVE` | Anayasal insan kapısı |
| `READY` | `ACTIVE` | Kanıt bağlı; merge izni değil |
| `CLOSED` | `RELEASED` | Görev kapandı |
| `BLOCKED` | `ACTIVE` veya `QUEUED` | İnsan-dışı bekleyiş / kapsam kuyruğu |
| `PARKED` | `ACTIVE` veya `QUEUED` | Bilinçli park; `FOUNDER_REVIEW` değildir |

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

### 8. Gürültü ayıklama

Kurucuya yalnız `karar`, `risk`, `blokaj`, `tamamlanma` çıkar. Normal ajan
hareketi (heartbeat, retry, log, dal gürültüsü) Duvar'da kalır. Bu süzgeç
anayasa §10'un operatör→kurucu kanalıdır; dördüncü bir rapor dili yazılmaz.

## Görsel yüz (yetkisiz)

Ekran, kart ve kuyruk bu maddelerin **görüntüsüdür**. İş mantığı CSS/sayfaya
gömülmez. Yeni sayfa STOP LIST'tedir; görsel dilim ayrı kurucu onayı ister.

## Bilinçli yapılmaz

- İkinci `TaskClaimStore` veya `claim_cli` çatalı
- Anayasa maddelerinin bu dosyaya kopyalanması
- Ajanlar arası komut ağı, auto-merge, auto-deploy
- Son kullanıcı paneline claim/worktree sızdırma (PR-005 / ADR-019)
